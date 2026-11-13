"""Bounded, content-free diagnostics for the local alpha runtime."""

import json
import sys
from collections import deque
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from intelligence_core.contracts import ContractValidationError
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.exceptions import MCPError
from mcp_types import INTERNAL_ERROR

from .workspace import EvidenceBoundaryError, ProjectLifecycleError

P = ParamSpec("P")
R = TypeVar("R")


class SafeToolError(ToolError):
    """Content-free tool failure suitable for MCP clients."""


class DiagnosticRecorder:
    """Records safe error metadata without retaining inputs or messages."""

    def __init__(self, capacity: int = 100) -> None:
        if capacity < 1:
            raise ValueError("diagnostic capacity must be positive")
        self._capacity = capacity
        self._events: deque[dict[str, object]] = deque(maxlen=capacity)
        self._sequence = 0

    @staticmethod
    def _classification(error: Exception) -> tuple[str, str]:
        if isinstance(error, EvidenceBoundaryError):
            return ("evidence_boundary", "RQ-EVIDENCE-001")
        if isinstance(error, ProjectLifecycleError):
            return ("project_lifecycle", "RQ-PROJECT-001")
        if isinstance(error, ContractValidationError):
            return ("graph_validation", "RQ-GRAPH-001")
        if isinstance(error, (TypeError, ValueError)):
            return ("input_contract", "RQ-INPUT-001")
        return ("internal", "RQ-INTERNAL-001")

    def record_error(self, operation: str, error: Exception) -> dict[str, object]:
        self._sequence += 1
        category, code = self._classification(error)
        event: dict[str, object] = {
            "diagnostic_id": f"diag-{self._sequence:06d}",
            "operation": operation,
            "status": "error",
            "category": category,
            "code": code,
        }
        self._events.append(event)
        print(json.dumps(event, sort_keys=True), file=sys.stderr, flush=True)
        return event

    def capture(self, operation: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
        def decorate(function: Callable[P, R]) -> Callable[P, R]:
            @wraps(function)
            def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    return function(*args, **kwargs)
                except Exception as error:  # noqa: BLE001
                    event = self.record_error(operation, error)
                    raise SafeToolError(
                        f"{event['code']} ({event['diagnostic_id']})"
                    ) from None

            return wrapped

        return decorate

    def capture_resource(self, operation: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
        """Use a protocol error so the SDK cannot log the URI or exception chain."""
        def decorate(function: Callable[P, R]) -> Callable[P, R]:
            @wraps(function)
            def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    return function(*args, **kwargs)
                except Exception as error:  # noqa: BLE001
                    event = self.record_error(operation, error)
                    raise MCPError(
                        code=INTERNAL_ERROR,
                        message=f"{event['code']} ({event['diagnostic_id']})",
                    ) from None

            return wrapped

        return decorate

    def report(self) -> dict[str, object]:
        return {
            "retention": "memory_only",
            "capacity": self._capacity,
            "event_count": len(self._events),
            "events": list(self._events),
        }

