"""Tool registry for managing and discovering available SRE tools."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from opensre.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all available SRE tools.

    Tools are registered either explicitly via `register()` or automatically
    when a `BaseTool` subclass is defined (via `__init_subclass__` hooks).
    """

    _instance: Optional["ToolRegistry"] = None
    _tools: Dict[str, Type[BaseTool]]

    def __init__(self) -> None:
        self._tools = {}

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """Return the global singleton registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool_cls: Type[BaseTool]) -> Type[BaseTool]:
        """Register a tool class by its declared *tool_name*.

        Args:
            tool_cls: A concrete subclass of :class:`BaseTool`.

        Returns:
            The same class, so this can be used as a decorator.

        Raises:
            ValueError: If a different class is already registered under
                        the same name.
        """
        name: str = tool_cls.tool_name  # type: ignore[attr-defined]
        if not name:
            raise ValueError(
                f"Tool class '{tool_cls.__name__}' has no tool_name defined."
            )

        existing = self._tools.get(name)
        if existing is not None and existing is not tool_cls:
            raise ValueError(
                f"Tool name '{name}' is already registered by '{existing.__name__}'."
            )

        self._tools[name] = tool_cls
        logger.debug("Registered tool: %s -> %s", name, tool_cls.__name__)
        return tool_cls

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry (mainly useful in tests)."""
        self._tools.pop(name, None)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Type[BaseTool]]:
        """Return the tool class for *name*, or ``None`` if not found."""
        return self._tools.get(name)

    def get_or_raise(self, name: str) -> Type[BaseTool]:
        """Return the tool class for *name*, raising if not registered."""
        tool_cls = self._tools.get(name)
        if tool_cls is None:
            available = ", ".join(sorted(self._tools)) or "<none>"
            raise KeyError(
                f"No tool named '{name}' is registered. "
                f"Available tools: {available}"
            )
        return tool_cls

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_tools(self) -> List[str]:
        """Return a sorted list of all registered tool names."""
        return sorted(self._tools)

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:  # handy when debugging in a REPL
        return f"ToolRegistry(tools={self.list_tools()})"
