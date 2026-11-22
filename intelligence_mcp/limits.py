"""Limits on decoded MCP arguments, before storage or use as lookup keys."""

MAX_ID_BYTES = 256
MAX_LABEL_BYTES = 256
MAX_REFERENCE_BYTES = 4096
MAX_TIMESTAMP_BYTES = 64
SHA256_TEXT_BYTES = len("sha256:") + 64


class InputLimitError(ValueError):
    """An application limit was exceeded; no input is included in the error."""


def bounded_bytes(value: str, limit: int) -> bytes:
    if len(value) > limit:
        raise InputLimitError("input exceeds the size limit")
    payload = value.encode("utf-8")
    if len(payload) > limit:
        raise InputLimitError("input exceeds the size limit")
    return payload


def bounded_text(value: str, limit: int) -> str:
    bounded_bytes(value, limit)
    return value
