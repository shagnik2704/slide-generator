"""Unit tests for LoggingMiddleware and silent path filtering."""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response

from src.api.middleware import LoggingMiddleware


class LoggingMiddlewareUnitTests(unittest.IsolatedAsyncioTestCase):
    """Ensure LoggingMiddleware filters out high-frequency scraping/health noise on 200 OK."""

    def setUp(self):
        self.app = MagicMock()
        self.middleware = LoggingMiddleware(self.app)

    async def test_metrics_and_health_200_are_suppressed(self):
        """Routine /metrics and /health requests returning 200 OK must not produce logs."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/metrics",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)

        call_next = AsyncMock(return_value=Response("ok", status_code=200))

        with patch("src.api.middleware.logger.info") as mock_info, \
             patch("src.api.middleware.logger.log") as mock_log:
            response = await self.middleware.dispatch(request, call_next)
            self.assertEqual(response.status_code, 200)
            mock_info.assert_not_called()
            mock_log.assert_not_called()

    async def test_failing_health_check_is_logged(self):
        """Failing health check (status >= 400) must be logged as WARNING or ERROR."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)

        call_next = AsyncMock(return_value=Response("db down", status_code=503))

        with patch("src.api.middleware.logger.log") as mock_log:
            response = await self.middleware.dispatch(request, call_next)
            self.assertEqual(response.status_code, 503)
            self.assertTrue(mock_log.called)
            args = mock_log.call_args[0]
            self.assertEqual(args[0], 40)  # logging.ERROR is 40
            self.assertIn("/health", args[1])

    async def test_regular_application_traffic_is_logged(self):
        """Real application routes must be logged with request start and response time."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/slides/generate",
            "headers": [
                (b"x-forwarded-for", b"203.0.113.195, 10.0.0.1"),
                (b"user-agent", b"Chrome/120"),
            ],
            "query_string": b"",
        }
        request = Request(scope)

        call_next = AsyncMock(return_value=Response("created", status_code=200))

        with patch("src.api.middleware.logger.info") as mock_info, \
             patch("src.api.middleware.logger.log") as mock_log:
            response = await self.middleware.dispatch(request, call_next)
            self.assertEqual(response.status_code, 200)

            # Request logged
            self.assertTrue(mock_info.called)
            info_call = mock_info.call_args
            self.assertIn("POST /api/slides/generate", info_call[0][0])
            self.assertEqual(info_call[1]["extra"]["client_ip"], "203.0.113.195")

            # Response logged
            self.assertTrue(mock_log.called)
            log_call = mock_log.call_args
            self.assertIn("200", log_call[0][1])

    def test_is_silent_path(self):
        """_is_silent_path identifies metrics, health, and subpaths."""
        self.assertTrue(LoggingMiddleware._is_silent_path("/metrics"))
        self.assertTrue(LoggingMiddleware._is_silent_path("/metrics/"))
        self.assertTrue(LoggingMiddleware._is_silent_path("/health"))
        self.assertTrue(LoggingMiddleware._is_silent_path("/health/status"))
        self.assertTrue(LoggingMiddleware._is_silent_path("/favicon.ico"))

        # Real endpoints are not silent
        self.assertFalse(LoggingMiddleware._is_silent_path("/api/slides/generate"))
        self.assertFalse(LoggingMiddleware._is_silent_path("/auth/callback"))
        self.assertFalse(LoggingMiddleware._is_silent_path("/api/voice/synthesize"))
