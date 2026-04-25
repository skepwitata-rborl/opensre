"""Base tool interface for OpenSRE integrations.

All tools must inherit from BaseTool and implement the required
interface methods: is_available, extract_params, and run.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Encapsulates the result of a tool execution."""

    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any, **metadata: Any) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> "ToolResult":
        """Create a failed result."""
        return cls(success=False, error=error, metadata=metadata)


class BaseTool(abc.ABC):
    """Abstract base class for all OpenSRE tools.

    Subclasses must implement:
        - ``name``: unique snake_case identifier (e.g. ``my_tool_name``)
        - ``display_name``: human-readable class name (e.g. ``MyToolName``)
        - ``is_available``: check whether the tool can run in this environment
        - ``extract_params``: parse and validate raw input into typed params
        - ``run``: execute the tool logic and return a ToolResult
    """

    # --- class-level attributes (override in subclasses) ---

    #: Unique snake_case identifier, e.g. ``prometheus_query``
    name: str = ""

    #: Human-readable PascalCase name, e.g. ``PrometheusQuery``
    display_name: str = ""

    #: Short description shown in the tool registry / UI
    description: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Use abc.ABC in cls.__mro__ to correctly detect abstract intermediates
        if abc.ABC not in cls.__bases__:  # only validate concrete classes
            if not cls.name:
                raise TypeError(f"{cls.__name__} must define a non-empty `name`")
            if not cls.display_name:
                raise TypeError(
                    f"{cls.__name__} must define a non-empty `display_name`"
                )

    # --- abstract interface ---

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if the tool's dependencies/credentials are present."""

    @abc.abstractmethod
    def extract_params(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Validate and coerce *raw* input dict into typed parameters.

        Raise ``ValueError`` with a descriptive message on invalid input.
        """

    @abc.abstractmethod
    def run(self, params: dict[str, Any]) -> ToolResult:
        """Execute the tool with validated *params* and return a ToolResult."""

    # --- convenience helpers ---

    def safe_run(self, raw: dict[str, Any]) -> ToolResult:
        """Validate params then run the tool, catching all exceptions.

        This is the recommended entry point for calling tools — it ensures
        that any unexpected errors are captured and returned as a ToolResult
        rather than propagating as uncaught exceptions.
        """
        try:
            params = self.extract_params(raw)
        except ValueError as exc:
            logger.warning("%s param validation failed: %s", self.name, exc)
            return ToolResult.fail(f"Invalid parameters: {exc}")

        try:
            return self.run(params)
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s raised an unexpected error", self.name)
            return ToolResult.fail(f"Unexpected error: {exc}")
