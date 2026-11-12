"""Tests for structured logging configuration and redaction.

These tests verify that:

- the logging module is configured once with a documented level and format;
- a redaction filter removes credential-like and session-like values;
- operational code paths emit log records instead of writing to stdout;
- sensitive values do not appear in captured logs.
"""

import io
import logging
import re

import pytest

from app.core.config import Settings
from app.core.logging_config import (
    RedactingFilter,
    configure_logging,
    get_log_level,
    get_logger,
    redact,
)


UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


@pytest.fixture(autouse=True)
def restore_root_logger():
    """Restore the root logger configuration after each test."""

    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level

    yield

    root.handlers = handlers
    root.setLevel(level)


def build_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def capture_logs(logger_name: str, level: int = logging.INFO):
    """Attach a capturing handler and return (buffer, cleanup)."""

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))

    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)
    logger.setLevel(level)

    return stream, lambda: logger.removeHandler(handler)


def test_get_log_level_maps_known_levels():
    assert get_log_level("debug") == logging.DEBUG
    assert get_log_level("INFO") == logging.INFO
    assert get_log_level("Warning") == logging.WARNING
    assert get_log_level("ERROR") == logging.ERROR
    assert get_log_level("CRITICAL") == logging.CRITICAL


def test_get_log_level_falls_back_to_info():
    assert get_log_level("NOT-A-LEVEL") == logging.INFO


def test_configure_logging_applies_configured_level():
    settings = build_settings(log_level="WARNING")

    logger = configure_logging(settings)

    assert logger.level == logging.WARNING
    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_is_idempotent():
    settings = build_settings(log_level="INFO")

    configure_logging(settings)
    configure_logging(settings)

    root = logging.getLogger()
    owned = [
        handler
        for handler in root.handlers
        if getattr(handler, "_attendance_app_handler", False)
    ]

    assert len(owned) == 1


def test_get_logger_uses_application_namespace():
    assert get_logger("api.routes").name == "attendance.api.routes"
    assert get_logger("attendance.custom").name == "attendance.custom"


def test_redact_removes_bearer_tokens():
    token = "abc123def456ghi789jkl"

    redacted = redact(f"Authorization: Bearer {token}")

    assert token not in redacted
    assert "[REDACTED]" in redacted


def test_redact_removes_password_assignments():
    redacted = redact("password=hunter2secret")

    assert "hunter2secret" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_removes_token_assignments():
    redacted = redact("token: abcdef123456")

    assert "abcdef123456" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_removes_uuid_session_identifiers():
    session_id = "123e4567-e89b-42d3-a456-426614174000"

    redacted = redact(f"liveness session {session_id}")

    assert session_id not in redacted
    assert "[REDACTED]" in redacted


def test_redact_leaves_ordinary_messages_unchanged():
    message = "Attendance verification completed: similarity=0.91"

    assert redact(message) == message


def test_redacting_filter_sanitizes_rendered_message():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    handler.addFilter(RedactingFilter())

    logger = logging.getLogger("attendance.test.filter")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        logger.info("Using bearer %s", "supersecretvalue123")

        output = stream.getvalue()

        assert "supersecretvalue123" not in output
        assert "[REDACTED]" in output
    finally:
        logger.removeHandler(handler)


def test_configured_logger_redacts_emitted_records():
    settings = build_settings(log_level="INFO")

    configure_logging(settings)

    stream, cleanup = capture_logs("attendance")
    try:
        logger = get_logger("test.redaction")

        logger.info("Auth header was Bearer %s", "leakedtokenvalue")

        output = stream.getvalue()

        assert "leakedtokenvalue" not in output
        assert "[REDACTED]" in output
    finally:
        cleanup()


def test_record_factory_redacts_for_handlers_attached_later():
    """Redaction happens at record creation, so late handlers are covered."""

    configure_logging(build_settings(log_level="INFO"))

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger = get_logger("test.late_handler")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        logger.info("session=%s", "123e4567-e89b-42d3-a456-426614174000")

        output = stream.getvalue()

        assert "123e4567-e89b-42d3-a456-426614174000" not in output
        assert "[REDACTED]" in output
    finally:
        logger.removeHandler(handler)


def test_operational_logs_do_not_contain_raw_embeddings():
    settings = build_settings(log_level="INFO")

    configure_logging(settings)

    stream, cleanup = capture_logs("attendance")
    try:
        logger = get_logger("test.embeddings")

        # A realistic embedding vector must never reach the log stream.
        embedding = [0.123456, -0.654321, 0.987654]

        logger.info("embedding=%s", embedding)

        output = stream.getvalue()

        assert "0.123456" not in output
    finally:
        cleanup()


def test_no_operational_print_calls_remain_in_api_and_services():
    """Operational modules must not write to stdout via print()."""

    import pathlib

    app_root = pathlib.Path(__file__).resolve().parents[2] / "app"

    offenders = []

    for path in app_root.rglob("*.py"):
        if path.name == "cli.py":
            # The auth CLI intentionally prints user-facing confirmations.
            continue

        source = path.read_text(encoding="utf-8")

        if re.search(r"^[^#\n]*\bprint\s*\(", source, re.MULTILINE):
            offenders.append(str(path.relative_to(app_root)))

    assert offenders == []
