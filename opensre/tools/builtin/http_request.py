"""Built-in HTTP request tool for opensre.

Allows graph nodes to perform HTTP GET/POST requests as part of an SRE workflow,
e.g. hitting health-check endpoints, triggering webhooks, or querying REST APIs.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from opensre.tools.base import BaseTool, ToolResult


class HttpRequestTool(BaseTool):
    """Performs a synchronous HTTP request and returns the response.

    Parameters (passed via ``params`` dict)
    ----------------------------------------
    url : str
        The target URL (required).
    method : str
        HTTP method – ``GET``, ``POST``, ``PUT``, ``PATCH``, ``DELETE``.
        Defaults to ``"GET"``.
    headers : dict[str, str], optional
        Additional request headers.
    body : dict | str | None, optional
        Request body.  Dicts are serialised to JSON automatically.
    timeout : float, optional
        Request timeout in seconds.  Defaults to ``30.0``.
        (Increased from 10.0 – 10s was too aggressive for slow internal APIs.)
    expected_status : int | list[int], optional
        If provided the tool will fail when the response status code is not in
        this set.  Defaults to accepting any 2xx status code.
    """

    my_tool_name = "http_request"

    # ------------------------------------------------------------------
    # BaseTool protocol
    # ------------------------------------------------------------------

    @classmethod
    def is_available(cls) -> bool:  # noqa: D401
        """Return *True* – httpx is a core dependency."""
        try:
            import httpx  # noqa: F401  (already imported at module level)
            return True
        except ImportError:  # pragma: no cover
            return False

    @classmethod
    def extract_params(cls, raw: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalise raw parameter dict."""
        url: str | None = raw.get("url")
        if not url:
            raise ValueError("'url' is a required parameter for HttpRequestTool")

        method: str = str(raw.get("method", "GET")).upper()
        allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        if method not in allowed_methods:
            raise ValueError(f"Unsupported HTTP method '{method}'. Choose from {allowed_methods}")

        expected_status = raw.get("expected_status")
        if isinstance(expected_status, int):
            expected_status = [expected_status]

        return {
            "url": url,
            "method": method,
            "headers": raw.get("headers") or {},
            "body": raw.get("body"),
            "timeout": float(raw.get("timeout", 30.0)),  # default bumped to 30s
            "expected_status": expected_status,  # None means accept any 2xx
        }

    def run(self, params: dict[str, Any]) -> ToolResult:
        """Execute the HTTP request and return a :class:`ToolResult`."""
        p = self.extract_params(params)

        headers: dict[str, str] = dict(p["headers"])
        body = p["body"]
        content: bytes | None = None

        if b