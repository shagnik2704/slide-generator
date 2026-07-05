import os
import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import ValidationError

from src.script_chat.graph import build_script_chat_graph
from src.script_chat import routes
from src.script_chat.routes import ManualEditRequest, ResumeRequest
from src.script_chat.schemas import GroundingReport, ScriptMetadata, ScriptResult, ScriptSlide, parse_script


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
    async def asyncTearDown(self):
        routes._graph = None

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
        )

        self.assertTrue(result["success"])
        self.assertEqual(graph.update["script"][0]["narration"], "Updated")
        self.assertEqual(graph.update["script_version"], 2)


if __name__ == "__main__":
    unittest.main()
