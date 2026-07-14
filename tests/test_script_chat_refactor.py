import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ["LANGSMITH_TRACING"] = "false"

from fastapi import HTTPException
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import ValidationError

from src.script_chat.graph import build_script_chat_graph
from src.script_chat import routes
from src.script_chat.routes import ManualEditRequest, ResumeRequest
from src.script_chat.schemas import GroundingReport, ScriptMetadata, ScriptResult, ScriptSlide, parse_script


TEST_USER = SimpleNamespace(sub="tester@example.com")


class ScriptChatSchemaTests(unittest.TestCase):
    def test_script_slide_rejects_missing_fields(self):
        with self.assertRaises(ValidationError):
            ScriptSlide.model_validate({"slide_number": 1, "narration": "Hello"})

    def test_script_slide_rejects_extra_fields(self):
        with self.assertRaises(ValidationError):
            ScriptSlide.model_validate(
                {
                    "slide_number": 1,
                    "slide_type": "Title Slide",
                    "visual_cue": "Title",
                    "narration": "Hello",
                    "unexpected": True,
                }
            )

    def test_parse_script_validates_each_slide(self):
        slides = parse_script(
            [
                {
                    "slide_number": 1,
                    "slide_type": "Title Slide",
                    "visual_cue": "Title",
                    "narration": "Hello",
                }
            ]
        )
        self.assertEqual(slides[0].slide_number, 1)

    def test_script_result_rejects_empty_script(self):
        with self.assertRaises(ValidationError):
            ScriptResult.model_validate({"message": "Empty", "script": []})

    def test_route_models_reject_invalid_actions_and_fields(self):
        with self.assertRaises(ValidationError):
            ResumeRequest(action="aprove")
        with self.assertRaises(ValidationError):
            ManualEditRequest(slide_number=1, field="title", value="x")


class ScriptChatGraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_api_key_reaches_grounding_review_with_fallback_report(self):
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            graph = build_script_chat_graph(checkpointer=MemorySaver())
            config = {"configurable": {"thread_id": "fallback-grounding"}}
            inputs = {
                "raw_outline": "Tutorial: Creating tensors with PyTorch\nimport torch",
                "messages": [],
                "script_version": 0,
            }

            async for _ in graph.astream(inputs, config=config, stream_mode=["custom", "updates"]):
                pass

            state = graph.get_state(config)
            report = GroundingReport.model_validate(state.values["grounding_report"])
            self.assertEqual(state.values["current_stage"], "grounding")
            self.assertEqual(state.values["foss_name"], "PyTorch")
            self.assertTrue(report.error)
            self.assertTrue(state.tasks[0].interrupts)
        finally:
            if original_key is not None:
                os.environ["OPENAI_API_KEY"] = original_key

    async def test_metadata_failure_stops_graph_after_grounding_approval(self):
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            graph = build_script_chat_graph(checkpointer=MemorySaver())
            config = {"configurable": {"thread_id": "fail-closed"}}
            inputs = {
                "raw_outline": "Tutorial: Creating tensors with PyTorch\nimport torch",
                "messages": [],
                "script_version": 0,
            }

            async for _ in graph.astream(inputs, config=config, stream_mode=["custom", "updates"]):
                pass
            async for _ in graph.astream(
                Command(resume={"action": "approve"}),
                config=config,
                stream_mode=["custom", "updates"],
            ):
                pass

            state = graph.get_state(config)
            self.assertEqual(state.values["current_stage"], "error")
            self.assertEqual(state.next, ())
            self.assertIsNone(state.values.get("metadata"))
        finally:
            if original_key is not None:
                os.environ["OPENAI_API_KEY"] = original_key


class ScriptChatMetadataTests(unittest.TestCase):
    def test_metadata_schema_trims_list_values(self):
        metadata = ScriptMetadata.model_validate(
            {
                "title": "Demo",
                "learning_objectives": [" Use **Python** ", ""],
                "prerequisites": "Basic computer literacy",
                "system_requirements": "Web browser",
                "outline_topics": [" Topic one "],
                "meta_tags": [" python ", ""],
            }
        )
        self.assertEqual(metadata.learning_objectives, ["Use **Python**"])
        self.assertEqual(metadata.outline_topics, ["Topic one"])
        self.assertEqual(metadata.meta_tags, ["python"])

    def test_metadata_schema_rejects_empty_lists_after_trimming(self):
        with self.assertRaises(ValidationError):
            ScriptMetadata.model_validate(
                {
                    "title": "Demo",
                    "learning_objectives": [" "],
                    "prerequisites": "Basic computer literacy",
                    "system_requirements": "Web browser",
                    "outline_topics": ["Topic one"],
                    "meta_tags": ["python"],
                }
            )


class FakeGraph:
    def __init__(self, state):
        self.state = state
        self.update = None

    async def aget_state(self, config):
        return self.state

    async def aupdate_state(self, config, update, as_node=None):
        self.update = update


def make_state(values, interrupt_type=None):
    interrupts = []
    if interrupt_type:
        interrupts = [SimpleNamespace(value={"type": interrupt_type})]
    task = SimpleNamespace(interrupts=interrupts)
    return SimpleNamespace(values=values, tasks=[task], next=("script_review",))


class ScriptChatRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_get_thread = routes.get_thread
        self.original_update_thread = routes.update_thread
        self.original_create_thread = routes.create_thread
        self.original_delete_thread = routes.delete_thread
        self.original_archive_thread = routes.archive_thread
        routes.get_thread = AsyncMock(return_value={"thread_id": "thread", "user_id": TEST_USER.sub})
        routes.update_thread = AsyncMock()
        routes.create_thread = AsyncMock()
        routes.delete_thread = AsyncMock()
        routes.archive_thread = AsyncMock(return_value=True)

    async def asyncTearDown(self):
        routes._graph = None
        routes.get_thread = self.original_get_thread
        routes.update_thread = self.original_update_thread
        routes.create_thread = self.original_create_thread
        routes.delete_thread = self.original_delete_thread
        routes.archive_thread = self.original_archive_thread

    async def test_start_session_creates_an_owned_thread_before_checkpointing(self):
        graph = FakeGraph(make_state({}))
        routes._graph = graph

        result = await routes.start_session(
            routes.StartRequest(outline="Create a TensorFlow tensor", foss_name="TensorFlow"),
            TEST_USER,
        )

        routes.create_thread.assert_awaited_once()
        create_args = routes.create_thread.await_args.args
        self.assertEqual(create_args[:3], (result.thread_id, TEST_USER.sub, "TensorFlow"))
        self.assertEqual(create_args[3], "Create a TensorFlow tensor")
        self.assertEqual(graph.update["raw_outline"], "Create a TensorFlow tensor")

    async def test_manual_edit_requires_script_review_interrupt(self):
        routes._graph = FakeGraph(
            make_state(
                {
                    "script": [
                        {
                            "slide_number": 1,
                            "slide_type": "Title Slide",
                            "visual_cue": "Title",
                            "narration": "Hello",
                        }
                    ],
                    "script_version": 1,
                },
                interrupt_type="metadata_review",
            )
        )

        with self.assertRaises(HTTPException) as ctx:
            await routes.manual_edit(
                "thread",
                ManualEditRequest(slide_number=1, field="narration", value="Updated"),
                TEST_USER,
            )

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_manual_edit_validates_and_updates_script_version(self):
        graph = FakeGraph(
            make_state(
                {
                    "script": [
                        {
                            "slide_number": 1,
                            "slide_type": "Title Slide",
                            "visual_cue": "Title",
                            "narration": "Hello",
                        }
                    ],
                    "script_version": 1,
                },
                interrupt_type="script_review",
            )
        )
        routes._graph = graph

        result = await routes.manual_edit(
            "thread",
            ManualEditRequest(slide_number=1, field="narration", value="Updated"),
            TEST_USER,
        )

        self.assertTrue(result["success"])
        self.assertEqual(graph.update["script"][0]["narration"], "Updated")
        self.assertEqual(graph.update["script_version"], 2)
        routes.update_thread.assert_awaited_once()

    async def test_thread_access_returns_not_found_for_a_different_user(self):
        routes.get_thread = AsyncMock(return_value=None)
        routes._graph = FakeGraph(make_state({"script": []}, interrupt_type="script_review"))

        with self.assertRaises(HTTPException) as ctx:
            await routes.manual_edit(
                "thread",
                ManualEditRequest(slide_number=1, field="narration", value="Updated"),
                TEST_USER,
            )

        self.assertEqual(ctx.exception.status_code, 404)

    async def test_archive_is_scoped_to_the_current_user(self):
        result = await routes.archive_thread_endpoint("thread", TEST_USER)

        self.assertTrue(result["success"])
        routes.archive_thread.assert_awaited_once_with("thread", TEST_USER.sub)


if __name__ == "__main__":
    unittest.main()
