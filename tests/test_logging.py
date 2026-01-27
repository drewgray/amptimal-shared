"""Tests for logging utilities."""
import json
import logging
import os
import pytest
from unittest.mock import patch
from amptimal_shared.logging import setup_logging, get_logger, JsonFormatter


class TestSetupLogging:
    def teardown_method(self):
        """Clean up loggers after each test."""
        # Remove all handlers to prevent pollution between tests
        for name in logging.root.manager.loggerDict:
            logger = logging.getLogger(name)
            logger.handlers = []

    def test_returns_logger_with_service_name(self):
        logger = setup_logging("test-service")
        assert logger.name == "test-service"

    def test_default_level_is_info(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove LOG_LEVEL if present
            os.environ.pop("LOG_LEVEL", None)
            logger = setup_logging("test-service")
            assert logger.level == logging.INFO

    def test_respects_level_argument(self):
        logger = setup_logging("test-service", level="DEBUG")
        assert logger.level == logging.DEBUG

    def test_respects_log_level_env_var(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            logger = setup_logging("test-service-env")
            assert logger.level == logging.WARNING

    def test_level_argument_overrides_env_var(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            logger = setup_logging("test-service-override", level="ERROR")
            assert logger.level == logging.ERROR

    def test_default_format_is_text(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LOG_FORMAT", None)
            logger = setup_logging("test-service-text")
            handler = logger.handlers[0]
            assert not isinstance(handler.formatter, JsonFormatter)

    def test_json_format_argument(self):
        logger = setup_logging("test-service-json", json_format=True)
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)

    def test_json_format_from_env_var(self):
        with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
            logger = setup_logging("test-service-json-env")
            handler = logger.handlers[0]
            assert isinstance(handler.formatter, JsonFormatter)

    def test_text_format_from_env_var(self):
        with patch.dict(os.environ, {"LOG_FORMAT": "text"}):
            logger = setup_logging("test-service-text-env")
            handler = logger.handlers[0]
            assert not isinstance(handler.formatter, JsonFormatter)

    def test_json_format_argument_overrides_env_var(self):
        with patch.dict(os.environ, {"LOG_FORMAT": "text"}):
            logger = setup_logging("test-service-json-override", json_format=True)
            handler = logger.handlers[0]
            assert isinstance(handler.formatter, JsonFormatter)

    def test_removes_existing_handlers(self):
        logger = setup_logging("test-service-handlers")
        assert len(logger.handlers) == 1

        # Setup again - should still have only one handler
        logger = setup_logging("test-service-handlers")
        assert len(logger.handlers) == 1

    def test_case_insensitive_level(self):
        logger = setup_logging("test-service-case", level="debug")
        assert logger.level == logging.DEBUG

        logger = setup_logging("test-service-case2", level="WARNING")
        assert logger.level == logging.WARNING


class TestJsonFormatter:
    def test_formats_basic_message(self):
        formatter = JsonFormatter("test-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["service"] == "test-service"
        assert data["message"] == "test message"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_includes_exception_info(self):
        formatter = JsonFormatter("test-service")

        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "test error" in data["exception"]

    def test_includes_extra_fields(self):
        formatter = JsonFormatter("test-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.extra = {"user_id": "123", "request_id": "abc"}

        output = formatter.format(record)
        data = json.loads(output)

        assert data["user_id"] == "123"
        assert data["request_id"] == "abc"


class TestGetLogger:
    def test_returns_logger_with_name(self):
        logger = get_logger("my.custom.logger")
        assert logger.name == "my.custom.logger"

    def test_returns_same_logger_for_same_name(self):
        logger1 = get_logger("shared.logger")
        logger2 = get_logger("shared.logger")
        assert logger1 is logger2

    def test_supports_dotted_names(self):
        logger = get_logger("parent.child.grandchild")
        assert logger.name == "parent.child.grandchild"
