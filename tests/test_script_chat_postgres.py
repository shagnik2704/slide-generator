"""Optional integration coverage for the Script Chat PostgreSQL migration.

Run with SCRIPT_CHAT_TEST_DATABASE_URL set to an isolated PostgreSQL database.
The test verifies both app-level ownership metadata and a fresh LangGraph saver
can reload the same checkpoint, which models an API process restart.
"""
import os
import asyncio
import unittest
import uuid

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.script_chat.graph import build_script_chat_graph
from src.script_chat.migrate import migrate_application_schema, migrate_checkpoint_schema
from src.script_chat.persistence import (
    archive_thread,
    close_script_chat_pool,
    create_thread,
    get_thread,
    get_pool,
    list_threads,
    open_script_chat_pool,
)
from src.users.persistence import upsert_user


TEST_DATABASE_URL = os.getenv("SCRIPT_CHAT_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "Set SCRIPT_CHAT_TEST_DATABASE_URL to run PostgreSQL integration tests")
class ScriptChatPostgresPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_thread_metadata_and_checkpoint_survive_a_new_saver(self):
        thread_id = f"postgres-test-{uuid.uuid4()}"
        previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        try:
            await asyncio.to_thread(migrate_application_schema)
            await migrate_checkpoint_schema()
            await open_script_chat_pool()
            owner = await upsert_user(
                provider="google",
                provider_subject="google-owner-123",
                email="owner@example.com",
                name="Owner",
            )
            owner_id = str(owner["id"])
            other = await upsert_user(
                provider="google",
                provider_subject="google-other-456",
                email="other@example.com",
                name="Other",
            )
            await create_thread(
                thread_id,
                owner_id,
                "TensorFlow",
                "Create tensors with TensorFlow",
            )

            config = {"configurable": {"thread_id": thread_id}}
            initial_state = {
                "raw_outline": "Create tensors with TensorFlow",
                "foss_name": "TensorFlow",
                "messages": [],
                "script_version": 0,
                "current_stage": "ingest",
            }

            async with AsyncPostgresSaver.from_conn_string(TEST_DATABASE_URL) as saver:
                await saver.setup()
                graph = build_script_chat_graph(checkpointer=saver)
                await graph.aupdate_state(config, initial_state, as_node="__start__")

            async with AsyncPostgresSaver.from_conn_string(TEST_DATABASE_URL) as saver:
                graph_after_restart = build_script_chat_graph(checkpointer=saver)
                state = await graph_after_restart.aget_state(config)

            self.assertEqual(state.values["raw_outline"], initial_state["raw_outline"])
            self.assertEqual(state.values["foss_name"], "TensorFlow")
            self.assertIsNotNone(await get_thread(thread_id, owner_id))
            self.assertIsNone(await get_thread(thread_id, str(other["id"])))

            refreshed_owner = await upsert_user(
                provider="google",
                provider_subject="google-owner-123",
                email="owner@example.com",
                name="Updated Owner",
            )
            self.assertEqual(refreshed_owner["id"], owner["id"])
            self.assertEqual(refreshed_owner["name"], "Updated Owner")

            legacy_email = f"legacy-{uuid.uuid4()}@example.com"
            async with get_pool().connection() as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        """
                        INSERT INTO users (provider, provider_subject, email)
                        VALUES ('legacy', %s, %s)
                        RETURNING id
                        """,
                        (legacy_email, legacy_email),
                    )
                    legacy_user = await cursor.fetchone()

            upgraded_user = await upsert_user(
                provider="google",
                provider_subject=f"google-{uuid.uuid4()}",
                email=legacy_email,
                name="Migrated Owner",
            )
            self.assertEqual(upgraded_user["id"], legacy_user["id"])
            self.assertEqual(upgraded_user["provider"], "google")

            from src.script_chat import routes

            await routes.init_script_chat_graph()
            self.assertIsNotNone(routes.get_graph())
            await routes.close_script_chat_graph()

            await open_script_chat_pool()
            self.assertTrue(any(row["thread_id"] == thread_id for row in await list_threads(owner_id)))
            self.assertTrue(await archive_thread(thread_id, owner_id))
            self.assertIsNone(await get_thread(thread_id, owner_id))
        finally:
            await close_script_chat_pool()
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url
