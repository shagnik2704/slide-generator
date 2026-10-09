"""Unit and integration tests for fail-safe activity tracking."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.activity.tracker import log_activity, record_activity


TEST_DATABASE_URL = os.getenv("SCRIPT_CHAT_TEST_DATABASE_URL")


class ActivityTrackerUnitTests(unittest.IsolatedAsyncioTestCase):
    """Unit tests ensuring activity tracker is 100% fail-safe and error-free."""

    async def test_record_activity_never_raises_when_db_down_or_uninitialized(self):
        """Even if get_pool raises an exception, record_activity must not raise."""
        with patch("src.script_chat.persistence.get_pool", side_effect=RuntimeError("DB pool not initialized")):
            try:
                await record_activity(
                    user_id=str(uuid4()),
                    email="test@example.com",
                    activity_type="voice_generation",
                    detail="Generated 5 slides",
                    status="completed",
                )
            except Exception as exc:
                self.fail(f"record_activity raised an exception when DB was down: {exc}")

    async def test_record_activity_handles_corrupt_or_invalid_user_id(self):
        """Invalid user_id strings (not UUIDs) should be sanitized to None rather than raising ValueError."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__aenter__.return_value = mock_conn

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            await record_activity(
                user_id="invalid-not-a-uuid",
                email="user@test.org",
                activity_type="slide_generation",
                detail="Test details",
            )

            # Check that execute was called with None for user_id
            self.assertTrue(mock_conn.execute.called)
            args = mock_conn.execute.call_args[0][1]
            self.assertIsNone(args[0])  # user_id should be None
            self.assertEqual(args[1], "user@test.org")
            self.assertEqual(args[2], "slide_generation")

    async def test_record_activity_truncates_long_strings(self):
        """Overly long details or statuses should be truncated safely."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__aenter__.return_value = mock_conn

        valid_uid = str(uuid4())
        super_long_detail = "X" * 500
        super_long_status = "S" * 100

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            await record_activity(
                user_id=valid_uid,
                email="user@test.org",
                activity_type="test_type",
                detail=super_long_detail,
                status=super_long_status,
                metadata={"foo": "bar"},
            )

            self.assertTrue(mock_conn.execute.called)
            args = mock_conn.execute.call_args[0][1]
            self.assertEqual(args[0], valid_uid)
            self.assertEqual(len(args[3]), 255)  # detail truncated to 255
            self.assertEqual(len(args[4]), 32)   # status truncated to 32

    async def test_log_activity_schedules_async_task(self):
        """log_activity should create an asyncio task on the running event loop."""
        loop = asyncio.get_running_loop()
        task_created = []

        def custom_create_task(coro):
            task_created.append(coro)
            # Close coroutine to avoid un-awaited coroutine warning
            coro.close()
            return MagicMock()

        with patch.object(loop, "create_task", side_effect=custom_create_task):
            log_activity(
                user_id=str(uuid4()),
                email="async@example.com",
                activity_type="batch_translation",
                detail="Batch 3 languages",
            )

        self.assertEqual(len(task_created), 1)

    def test_log_activity_failsafe_without_running_loop(self):
        """If there is no running loop, log_activity handles RuntimeError silently."""
        with patch("asyncio.get_running_loop", side_effect=RuntimeError("no running event loop")):
            try:
                log_activity(
                    activity_type="voice_patch",
                    detail="Patch slide 1",
                )
            except Exception as exc:
                self.fail(f"log_activity raised exception when no event loop: {exc}")

    async def test_get_user_activities_failsafe_when_db_down(self):
        """get_user_activities returns empty list if db pool fails."""
        from src.activity.tracker import get_user_activities
        with patch("src.script_chat.persistence.get_pool", side_effect=RuntimeError("DB down")):
            res = await get_user_activities(email="test@example.com")
            self.assertEqual(res, [])

    async def test_get_user_activities_returns_empty_when_no_user_or_email(self):
        """get_user_activities returns empty list if neither user_id nor email is provided."""
        from src.activity.tracker import get_user_activities
        res = await get_user_activities(user_id=None, email=None)
        self.assertEqual(res, [])

    async def test_get_my_activities_route(self):
        """get_my_activities endpoint calls get_user_activities and returns expected dict."""
        from types import SimpleNamespace
        from src.api.routes.activity import get_my_activities

        user = SimpleNamespace(sub=str(uuid4()), email="testuser@example.com")
        mock_activities = [{"id": 1, "activity_type": "slide_generation", "detail": "Test"}]
        with patch("src.api.routes.activity.get_user_activities", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_activities
            resp = await get_my_activities(current_user=user)
            self.assertEqual(resp, {"activities": mock_activities})
            mock_get.assert_awaited_once_with(user_id=user.sub, email=user.email, limit=50)

    async def test_get_user_creations_failsafe_when_db_down(self):
        """get_user_creations returns empty dict structure if db pool fails."""
        from src.activity.tracker import get_user_creations
        with patch("src.script_chat.persistence.get_pool", side_effect=RuntimeError("DB down")):
            res = await get_user_creations(email="test@example.com")
            self.assertIn("timed_scripts", res)
            self.assertIn("scripts", res)
            self.assertIn("slides", res)
            self.assertIn("audio", res)
            self.assertIn("videos", res)
            self.assertEqual(res["total_count"], 0)

    async def test_get_user_creations_returns_empty_when_no_user_or_email(self):
        """get_user_creations returns empty dict structure if neither user_id nor email is provided."""
        from src.activity.tracker import get_user_creations
        res = await get_user_creations(user_id=None, email=None)
        self.assertEqual(res["total_count"], 0)

    async def test_val_helper(self):
        """_val safely extracts from dicts, tuples, and objects."""
        from src.activity.tracker import _val
        d = {"id": "abc", "status": "completed"}
        t = ("abc", "completed")
        self.assertEqual(_val(d, "id", 0), "abc")
        self.assertEqual(_val(d, "status", 1), "completed")
        self.assertEqual(_val(d, "nonexistent", 99, default="def"), "def")
        self.assertEqual(_val(t, "id", 0), "abc")
        self.assertEqual(_val(t, "status", 1), "completed")
        self.assertEqual(_val(t, "nonexistent", 99, default="def"), "def")

    async def test_get_user_creations_handles_dict_row_from_psycopg(self):
        """get_user_creations extracts background_jobs and script_chat_threads when rows are dicts."""
        from datetime import datetime, timezone
        from src.activity.tracker import get_user_creations

        now = datetime.now(timezone.utc)
        mock_job_row = {
            "id": uuid4(),
            "original_filename": "lecture.wav",
            "status": "completed",
            "progress": 100,
            "current_stage": "done",
            "result": {"sentences": [1, 2]},
            "error_message": None,
            "created_at": now,
            "started_at": now,
            "completed_at": now,
        }
        mock_thread_row = {
            "thread_id": uuid4(),
            "title": "Python Basics",
            "outline_preview": "Intro to Python",
            "foss_name": "Python",
            "current_stage": "completed",
            "status": "completed",
            "created_at": now,
            "updated_at": now,
        }
        mock_cur = AsyncMock()
        mock_cur.fetchall.side_effect = [
            [mock_job_row],     # background_jobs
            [mock_thread_row],  # script_chat_threads
            [],                 # user_activities
        ]
        mock_cursor_ctx = MagicMock()
        mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor_ctx
        mock_conn_ctx = MagicMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn_ctx

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            creations = await get_user_creations(user_id=str(uuid4()))
            self.assertEqual(len(creations["timed_scripts"]), 1)
            self.assertEqual(creations["timed_scripts"][0]["original_filename"], "lecture.wav")
            self.assertEqual(len(creations["scripts"]), 1)
            self.assertEqual(creations["scripts"][0]["title"], "Python Basics")
            self.assertEqual(creations["total_count"], 2)

    async def test_get_user_activities_handles_dict_row_from_psycopg(self):
        """get_user_activities correctly parses dict rows for user_activities and synthesized jobs."""
        from datetime import datetime, timezone
        from src.activity.tracker import get_user_activities

        now = datetime.now(timezone.utc)
        mock_activity_row = {
            "id": 123,
            "user_id": str(uuid4()),
            "email": "user@example.com",
            "activity_type": "slide_generation",
            "detail": "Generated 5 slides",
            "status": "completed",
            "metadata": {"slide_count": 5},
            "created_at": now,
        }
        mock_cur = AsyncMock()
        mock_cur.fetchall.side_effect = [
            [mock_activity_row], # user_activities
            [],                  # background_jobs
            [],                  # script_chat_threads
        ]
        mock_cursor_ctx = MagicMock()
        mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor_ctx
        mock_conn_ctx = MagicMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn_ctx

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            acts = await get_user_activities(user_id=str(uuid4()), email="user@example.com")
            self.assertEqual(len(acts), 1)
            self.assertEqual(acts[0]["detail"], "Generated 5 slides")
            self.assertEqual(acts[0]["activity_type"], "slide_generation")

    async def test_get_my_creations_route(self):
        """get_my_creations endpoint calls get_user_creations and returns expected dict."""
        from types import SimpleNamespace
        from src.api.routes.activity import get_my_creations

        user = SimpleNamespace(sub=str(uuid4()), email="testuser@example.com")
        mock_creations = {
            "timed_scripts": [{"id": "1", "original_filename": "audio.wav"}],
            "scripts": [],
            "slides": [],
            "audio": [],
            "videos": [],
            "total_count": 1,
        }
        with patch("src.api.routes.activity.get_user_creations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_creations
            resp = await get_my_creations(current_user=user)
            self.assertEqual(resp, {"creations": mock_creations})
            mock_get.assert_awaited_once_with(user_id=user.sub, email=user.email, limit=100)

    async def test_get_user_creations_resolves_audio_and_slide_urls(self):
        """get_user_creations retroactively resolves audio_url and zip_url for voice and slides activities."""
        from datetime import datetime, timezone
        from src.activity.tracker import get_user_creations

        now = datetime.now(timezone.utc)
        mock_activities = [
            # 1. Slide generation with zip_filename
            {
                "id": 1,
                "activity_type": "slide_generation",
                "detail": "Generated 5 slides",
                "status": "completed",
                "metadata": {"zip_filename": "presentation_123.zip", "slide_count": 5},
                "created_at": now,
            },
            # 2. Combined voice without explicit audio_url (legacy)
            {
                "id": 2,
                "activity_type": "voice_generation_combined",
                "detail": "Combined voice (5 slides)",
                "status": "completed",
                "metadata": {"project_id": "proj-abc", "duration": "01:25"},
                "created_at": now,
            },
            # 3. Voice patch with patch_id
            {
                "id": 3,
                "activity_type": "voice_patch",
                "detail": "Patch: hello world",
                "status": "completed",
                "metadata": {"patch_id": "patch_456"},
                "created_at": now,
            },
            # 4. Regenerate slide with project_id and slide_number
            {
                "id": 4,
                "activity_type": "regenerate_slide",
                "detail": "Row 3 (project proj-abc)",
                "status": "completed",
                "metadata": {"project_id": "proj-abc", "slide_number": 3},
                "created_at": now,
            },
            # 5. Voice generation with explicit audio_url and zip_url
            {
                "id": 5,
                "activity_type": "voice_generation",
                "detail": "Generated 3 slides voice",
                "status": "completed",
                "metadata": {
                    "project_id": "proj-explicit",
                    "audio_url": "/output/audio/project_proj_explicit/slide_1.wav",
                    "zip_url": "/output/audio/project_proj_explicit/audio_project_proj_explicit.zip",
                },
                "created_at": now,
            },
        ]

        mock_cur = AsyncMock()
        mock_cur.fetchall.side_effect = [
            [],                 # background_jobs
            [],                 # script_chat_threads
            mock_activities,    # user_activities
        ]
        mock_cursor_ctx = MagicMock()
        mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor_ctx
        mock_conn_ctx = MagicMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn_ctx

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            creations = await get_user_creations(user_id=str(uuid4()))
            self.assertEqual(len(creations["slides"]), 1)
            slide = creations["slides"][0]
            self.assertEqual(slide["zip_url"], "/output/slides/presentation_123.zip")
            self.assertEqual(slide["download_url"], "/output/slides/presentation_123.zip")
            self.assertEqual(slide["url"], "/output/slides/presentation_123.zip")

            self.assertEqual(len(creations["audio"]), 4)
            # Combined voice
            comb_aud = creations["audio"][0]
            self.assertEqual(comb_aud["audio_url"], "/output/audio/project_proj-abc/full_narration.wav")
            self.assertEqual(comb_aud["zip_url"], "/output/audio/project_proj-abc/audio_project_proj-abc.zip")
            self.assertEqual(comb_aud["duration"], "01:25")

            # Patch
            patch_aud = creations["audio"][1]
            self.assertEqual(patch_aud["audio_url"], "/output/audio/patches/patch_patch_456.wav")

            # Slide regen
            regen_aud = creations["audio"][2]
            self.assertEqual(regen_aud["audio_url"], "/output/audio/project_proj-abc/slide_3.wav")
            self.assertEqual(regen_aud["zip_url"], "/output/audio/project_proj-abc/audio_project_proj-abc.zip")

            # Explicit voice
            exp_aud = creations["audio"][3]
            self.assertEqual(exp_aud["audio_url"], "/output/audio/project_proj_explicit/slide_1.wav")
            self.assertEqual(exp_aud["zip_url"], "/output/audio/project_proj_explicit/audio_project_proj_explicit.zip")

    def test_extract_client_context(self):
        """extract_client_context accurately extracts IP and user agent headers."""
        from types import SimpleNamespace
        from src.activity.tracker import extract_client_context

        # Request with X-Forwarded-For
        req1 = SimpleNamespace(
            headers={"x-forwarded-for": "203.0.113.195, 70.41.3.18", "user-agent": "Mozilla/5.0"},
            client=SimpleNamespace(host="10.0.0.1"),
        )
        ctx1 = extract_client_context(req1)
        self.assertEqual(ctx1["ip_address"], "203.0.113.195")
        self.assertEqual(ctx1["user_agent"], "Mozilla/5.0")

        # Request with X-Real-IP
        req2 = SimpleNamespace(
            headers={"x-real-ip": "198.51.100.22", "user-agent": "Curl/8.0"},
            client=SimpleNamespace(host="10.0.0.1"),
        )
        ctx2 = extract_client_context(req2)
        self.assertEqual(ctx2["ip_address"], "198.51.100.22")
        self.assertEqual(ctx2["user_agent"], "Curl/8.0")

        # Fallback to client.host
        req3 = SimpleNamespace(
            headers={},
            client=SimpleNamespace(host="192.168.1.50"),
        )
        ctx3 = extract_client_context(req3)
        self.assertEqual(ctx3["ip_address"], "192.168.1.50")

        # None request
        self.assertEqual(extract_client_context(None), {})

    async def test_record_activity_stores_client_context_in_metadata(self):
        """record_activity automatically adds IP and user agent to metadata."""
        from types import SimpleNamespace
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__aenter__.return_value = mock_conn

        req = SimpleNamespace(
            headers={"x-real-ip": "203.0.113.5", "user-agent": "Chrome/120"},
            client=SimpleNamespace(host="10.0.0.1"),
        )

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            await record_activity(
                email="user@test.org",
                activity_type="auth_login",
                detail="User login",
                request=req,
                metadata={"provider": "google"},
            )

            self.assertTrue(mock_conn.execute.called)
            args = mock_conn.execute.call_args[0][1]
            jsonb_meta = args[5].obj  # Access underlying dictionary
            self.assertEqual(jsonb_meta.get("provider"), "google")
            self.assertEqual(jsonb_meta.get("ip_address"), "203.0.113.5")
            self.assertEqual(jsonb_meta.get("user_agent"), "Chrome/120")

    async def test_query_all_activities_failsafe_when_db_down(self):
        """query_all_activities returns safe empty structure when DB is unreachable."""
        from src.activity.tracker import query_all_activities
        with patch("src.script_chat.persistence.get_pool", side_effect=RuntimeError("DB down")):
            res = await query_all_activities()
            self.assertEqual(res["total"], 0)
            self.assertEqual(res["activities"], [])
            self.assertEqual(res["page"], 1)

    async def test_query_all_activities_pagination_and_mapping(self):
        """query_all_activities calculates total_pages and maps columns accurately."""
        from datetime import datetime, timezone
        from src.activity.tracker import query_all_activities

        now = datetime.now(timezone.utc)
        test_uid = uuid4()
        fake_rows = [
            (1, test_uid, "admin@test.org", "slide_generation", "5 slides", "completed", {"ip_address": "1.2.3.4"}, now),
        ]

        mock_cur = AsyncMock()
        mock_cur.fetchone.return_value = (25,)  # 25 total records
        mock_cur.fetchall.return_value = fake_rows

        mock_cursor_ctx = MagicMock()
        mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor_ctx
        mock_conn_ctx = MagicMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn_ctx

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            res = await query_all_activities(limit=10, offset=0, activity_type="slide_generation")
            self.assertEqual(res["total"], 25)
            self.assertEqual(res["total_pages"], 3)
            self.assertEqual(res["page"], 1)
            self.assertEqual(len(res["activities"]), 1)
            act = res["activities"][0]
            self.assertEqual(act["id"], 1)
            self.assertEqual(act["user_id"], str(test_uid))
            self.assertEqual(act["email"], "admin@test.org")
            self.assertEqual(act["metadata"]["ip_address"], "1.2.3.4")

    async def test_get_distinct_activity_types(self):
        """get_distinct_activity_types extracts list of unique strings."""
        from src.activity.tracker import get_distinct_activity_types

        mock_cur = AsyncMock()
        mock_cur.fetchall.return_value = [("auth_login",), ("slide_generation",), ("voice_generation",)]
        mock_cursor_ctx = MagicMock()
        mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor_ctx
        mock_conn_ctx = MagicMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn_ctx

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            types = await get_distinct_activity_types()
            self.assertEqual(types, ["auth_login", "slide_generation", "voice_generation"])

    async def test_get_user_journey(self):
        """get_user_journey queries timeline for a user."""
        from src.activity.tracker import get_user_journey

        with patch("src.activity.tracker.query_all_activities", new_callable=AsyncMock) as mock_q:
            mock_q.return_value = {
                "total": 2,
                "activities": [{"id": 1, "activity_type": "login"}, {"id": 2, "activity_type": "slides"}],
            }
            journey = await get_user_journey("user@test.org", limit=100)
            self.assertEqual(journey["user_identifier"], "user@test.org")
            self.assertEqual(journey["total_actions"], 2)
            self.assertEqual(len(journey["timeline"]), 2)

    async def test_export_activities_csv_and_json(self):
        """export_activities generates well-formatted CSV and JSON streams."""
        import json
        from src.activity.tracker import export_activities

        sample_data = {
            "activities": [
                {
                    "id": 101,
                    "created_at": "2026-10-09T12:00:00Z",
                    "user_id": str(uuid4()),
                    "email": "audit@test.org",
                    "activity_type": "voice_generation",
                    "status": "completed",
                    "detail": "Generated 4 slides",
                    "metadata": {"ip_address": "127.0.0.1", "user_agent": "TestRunner"},
                }
            ]
        }

        with patch("src.activity.tracker.query_all_activities", new_callable=AsyncMock) as mock_q:
            mock_q.return_value = sample_data

            # Test JSON export
            json_str, content_type = await export_activities(export_format="json")
            self.assertEqual(content_type, "application/json")
            parsed = json.loads(json_str)
            self.assertEqual(len(parsed), 1)
            self.assertEqual(parsed[0]["id"], 101)

            # Test CSV export
            csv_str, content_type = await export_activities(export_format="csv")
            self.assertEqual(content_type, "text/csv")
            self.assertIn("Timestamp,User ID,Email,Activity Type", csv_str)
            self.assertIn("audit@test.org", csv_str)
            self.assertIn("127.0.0.1", csv_str)

    async def test_admin_api_routes(self):
        """Admin endpoints return correct payloads."""
        from types import SimpleNamespace
        from src.api.routes.activity import (
            export_activity_logs,
            get_activity_types_endpoint,
            get_all_activities,
            get_user_activity_journey,
        )

        user = SimpleNamespace(sub=str(uuid4()), email="admin@test.org")

        with patch("src.api.routes.activity.query_all_activities", new_callable=AsyncMock) as mock_q:
            mock_q.return_value = {"total": 1, "activities": []}
            resp = await get_all_activities(limit=50, offset=0, current_user=user)
            self.assertEqual(resp["total"], 1)

        with patch("src.api.routes.activity.get_distinct_activity_types", new_callable=AsyncMock) as mock_types:
            mock_types.return_value = ["auth_login", "slide_generation"]
            resp = await get_activity_types_endpoint(current_user=user)
            self.assertEqual(resp, {"activity_types": ["auth_login", "slide_generation"]})

        with patch("src.api.routes.activity.get_user_journey", new_callable=AsyncMock) as mock_j:
            mock_j.return_value = {"user_identifier": "u1", "timeline": []}
            resp = await get_user_activity_journey(user_identifier="u1", current_user=user)
            self.assertEqual(resp["user_identifier"], "u1")

        with patch("src.api.routes.activity.export_activities", new_callable=AsyncMock) as mock_exp:
            mock_exp.return_value = ("col1,col2\nval1,val2", "text/csv")
            resp = await export_activity_logs(format="csv", current_user=user)
            self.assertEqual(resp.media_type, "text/csv")
            self.assertIn("attachment; filename=", resp.headers["content-disposition"])



@unittest.skipUnless(TEST_DATABASE_URL, "Set SCRIPT_CHAT_TEST_DATABASE_URL to run PostgreSQL integration tests")
class ActivityTrackerPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Integration test with real PostgreSQL instance and migrations."""

    async def asyncSetUp(self):
        from src.script_chat.migrate import (
            migrate_application_schema,
            migrate_checkpoint_schema,
        )
        from src.script_chat.persistence import open_script_chat_pool

        self._previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        await asyncio.to_thread(migrate_application_schema)
        await migrate_checkpoint_schema()
        await open_script_chat_pool()

    async def asyncTearDown(self):
        from src.script_chat.persistence import close_script_chat_pool

        await close_script_chat_pool()
        if self._previous_database_url is not None:
            os.environ["DATABASE_URL"] = self._previous_database_url
        else:
            os.environ.pop("DATABASE_URL", None)

    async def test_roundtrip_persist_activity(self):
        from src.script_chat.persistence import get_pool

        test_email = f"track_{uuid4().hex[:8]}@example.com"
        await record_activity(
            email=test_email,
            activity_type="voice_generation",
            detail="5 slides generated",
            status="completed",
            metadata={"sample": "data"},
        )

        pool = get_pool()
        async with pool.connection() as conn:
            cursor = await conn.execute(
                "SELECT email, activity_type, detail, status, metadata FROM user_activities WHERE email = %s",
                (test_email,),
            )
            row = await cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], test_email)
        self.assertEqual(row[1], "voice_generation")
        self.assertEqual(row[2], "5 slides generated")
        self.assertEqual(row[3], "completed")
        self.assertEqual(row[4], {"sample": "data"})
