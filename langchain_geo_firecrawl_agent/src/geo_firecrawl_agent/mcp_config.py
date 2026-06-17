from __future__ import annotations

import os
from typing import Any

from geo_firecrawl_agent.config import Settings


def _npx_command() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


def build_mcp_connections(settings: Settings) -> dict[str, dict[str, Any]]:
    """Build connection config accepted by langchain-mcp-adapters."""

    connections: dict[str, dict[str, Any]] = {}

    if settings.enable_amap:
        if settings.amap_transport == "http":
            url = settings.amap_mcp_url
            if not url:
                url = f"https://mcp.amap.com/mcp?key={settings.amap_maps_api_key}"
            connections["amap"] = {
                "transport": "http",
                "url": url,
            }
        else:
            connections["amap"] = {
                "transport": "stdio",
                "command": _npx_command(),
                "args": ["-y", "@amap/amap-maps-mcp-server"],
                "env": {"AMAP_MAPS_API_KEY": settings.amap_maps_api_key or ""},
            }

    if settings.enable_firecrawl:
        if settings.firecrawl_transport == "http":
            connections["firecrawl"] = {
                "transport": "http",
                "url": settings.firecrawl_mcp_url,
            }
        else:
            connections["firecrawl"] = {
                "transport": "stdio",
                "command": _npx_command(),
                "args": ["-y", "firecrawl-mcp"],
                "env": {"FIRECRAWL_API_KEY": settings.firecrawl_api_key or ""},
            }

    return connections
