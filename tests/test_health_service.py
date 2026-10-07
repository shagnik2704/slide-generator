"""Tests for the infrastructure and dependency health service."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.health_service import (
    check_all_services,
    check_celery_worker,
    check_postgres,
    check_redis,
    check_storage,
)


class TestHealthService(TestCase := unittest.TestCase):
    @patch("src.script_chat.persistence.get_pool")
    async def _test_pg_healthy(self, mock_get_pool):
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        ok, latency, msg = await check_postgres()
        self.assertTrue(ok)
        self.assertGreater(latency, 0)
        self.assertIn("responsive", msg)

    def test_check_postgres(self):
        import asyncio
        asyncio.run(self._test_pg_healthy())

    @patch("redis.asyncio.from_url")
    async def _test_redis_healthy(self, mock_from_url):
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        ok, latency, msg = await check_redis()
        self.assertTrue(ok)
        self.assertGreater(latency, 0)
        self.assertIn("responsive", msg)

    def test_check_redis(self):
        import asyncio
        asyncio.run(self._test_redis_healthy())

    def test_check_storage(self):
        ok, details, msg = check_storage()
        self.assertTrue(ok)
        self.assertIn("free_gb", details)
        self.assertIn("writable", details)
        self.assertTrue(details["writable"])

    @patch("src.services.health_service.check_postgres", new_callable=AsyncMock)
    @patch("src.services.health_service.check_redis", new_callable=AsyncMock)
    @patch("src.services.health_service.check_celery_worker", new_callable=AsyncMock)
    async def _test_check_all_services_healthy(self, mock_celery, mock_redis, mock_pg):
        mock_pg.return_value = (True, 0.005, "PostgreSQL connected")
        mock_redis.return_value = (True, 0.002, "Redis connected")
        mock_celery.return_value = (True, 1, ["celery@worker-1"], "1 worker online")

        report = await check_all_services(update_metrics=True)
        self.assertEqual(report["status"], "healthy")
        self.assertIn("dependencies", report)
        self.assertEqual(report["dependencies"]["postgres"]["status"], "healthy")
        self.assertEqual(report["dependencies"]["redis"]["status"], "healthy")
        self.assertEqual(report["dependencies"]["celery_worker"]["status"], "healthy")

    def test_check_all_services_healthy(self):
        import asyncio
        asyncio.run(self._test_check_all_services_healthy())

    @patch("src.services.health_service.check_postgres", new_callable=AsyncMock)
    @patch("src.services.health_service.check_redis", new_callable=AsyncMock)
    async def _test_check_all_services_degraded_when_celery_offline(self, mock_redis, mock_pg):
        mock_pg.return_value = (True, 0.005, "PostgreSQL connected")
        mock_redis.return_value = (False, 0.002, "Redis down")

        report = await check_all_services(update_metrics=True)
        self.assertEqual(report["status"], "degraded")
        self.assertEqual(report["dependencies"]["celery_worker"]["status"], "unhealthy")

    def test_check_all_services_degraded(self):
        import asyncio
        asyncio.run(self._test_check_all_services_degraded_when_celery_offline())


if __name__ == "__main__":
    unittest.main()
