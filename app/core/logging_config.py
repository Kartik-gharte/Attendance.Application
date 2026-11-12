"""Structured logging configuration for the application.

This module provides a single place to configure the standard-library
``logging`` package so that operational output is consistent, leveled, and
free of biometric or credential material.

Redaction policy
----------------
The following values must never appear in logs at any level:

- raw images, video frames, face crops, or face embeddings (including the
  contents of ``.npy`` embedding files);
- authentication bearer tokens, passwords, API keys, or other secrets;
- liveness session identifiers (a session is a bearer-like capability);
- full multipart request bodies or uploaded file contents.

Redaction is applied through a :class:`logging.LogRecordFactory` so that every
record is sanitized at creation time. Any handler that an operator attaches
later therefore still receives redacted records.

``student_id`` is treated as personal data. It is logged at ``INFO`` for
attendance outcomes that an administrator must be able to reconcile, and is
never logged together with raw biometric material.

Internal filesystem paths may appear in exception diagnostics. Operators who
require path-free logs should run at ``WARNING`` level or above, where
server-side diagnostics are limited to the exception type.
"""

import logging
import re
import sys

from app.core.config import Settings


DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

# Values that look like credentials or capabilities.
REDACTION_PATTERNS = (
    # "Authorization: Bearer <token>" and "bearer <token>"
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}"),
    # "password=...", "password: ..."
    re.compile(r"(?i)\bpassword\s*[=:]\s*\S+"),
    # "token=...", "secret=...", "api_key: ..."
    re.compile(r"(?i)\b(token|secret|api[_-]?key|access[_-]?key)\s*[=:]\s*\S+"),
    # UUID-shaped liveness session identifiers
    re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    ),
)

# Face embeddings and other float vectors, for example
# "[0.123456, -0.654321]" or "array([0.1, 0.2])".
FLOAT_VECTOR_PATTERN = re.compile(
    r"(?<![\w.])-?\d+\.\d+(?:\s*,\s*-?\d+\.\d+){2,}(?![\w.])"
)


def redact(message: str) -> str:
    """Return ``message`` with credential, session, and vector values masked."""
    if not isinstance(message, str):
        return message

    for pattern in REDACTION_PATTERNS:
        message = pattern.sub("[REDACTED]", message)

    message = FLOAT_VECTOR_PATTERN.sub("[REDACTED_VECTOR]", message)

    return message


class RedactingLogRecordFactory:
    """Create log records whose rendered message is already redacted.

    Because the redaction happens while the record is created, it applies to
    every handler regardless of when or where the handler is attached.

    This mirrors :class:`logging.LogRecordFactory`, which only exists from
    Python 3.12 onwards, so the project keeps working on Python 3.11.
    """

    def __init__(self, factory=None):
        self._factory = factory or logging.getLogRecordFactory()

    def __call__(self, *args, **kwargs) -> logging.LogRecord:
        record = self._factory(*args, **kwargs)

        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return record

        redacted = redact(message)

        if redacted != message:
            record.msg = redacted
            record.args = ()

        return record


class RedactingFilter(logging.Filter):
    """Redact values in records that were created before the factory was set.

    This is a defence-in-depth measure for applications that install their
    own :class:`logging.LogRecordFactory` and therefore bypass the default
    redaction path.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True

        redacted = redact(message)

        if redacted != message:
            record.msg = redacted
            record.args = ()

        return True


def get_log_level(level: str) -> int:
    """Translate a configured level name into a logging constant."""
    return LOG_LEVELS.get(str(level).upper(), logging.INFO)


def configure_logging(settings: Settings) -> logging.Logger:
    """Configure logging once and return the application logger.

    The configuration is idempotent: repeated calls replace the handlers that
    this module owns instead of stacking duplicates.
    """
    level = get_log_level(settings.log_level)

    # Redact at record creation so that every handler is protected.
    logging.setLogRecordFactory(RedactingLogRecordFactory())

    root = logging.getLogger()

    # Remove handlers previously installed by this function so that repeated
    # calls (for example in tests) do not duplicate output.
    for handler in list(root.handlers):
        if getattr(handler, "_attendance_app_handler", False):
            root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt=settings.log_format or DEFAULT_LOG_FORMAT,
            datefmt=DEFAULT_DATE_FORMAT,
        )
    )
    handler.addFilter(RedactingFilter())
    handler._attendance_app_handler = True  # type: ignore[attr-defined]

    root.addHandler(handler)
    root.setLevel(level)

    # Third-party libraries are chatty at DEBUG level and may emit request
    # details or filesystem paths. Keep them at WARNING unless the operator
    # explicitly raises the application log level to DEBUG.
    if level > logging.DEBUG:
        for noisy in (
            "uvicorn",
            "uvicorn.error",
            "uvicorn.access",
            "httpx",
            "httpcore",
        ):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    logger = logging.getLogger("attendance")
    logger.setLevel(level)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the application logger namespace."""
    if name.startswith("attendance"):
        return logging.getLogger(name)

    return logging.getLogger(f"attendance.{name}")
