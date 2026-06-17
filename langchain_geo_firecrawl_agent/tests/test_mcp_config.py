from geo_firecrawl_agent.config import Settings
from geo_firecrawl_agent.mcp_config import build_mcp_connections


def test_default_builds_amap_http_and_firecrawl_stdio() -> None:
    settings = Settings(
        AMAP_MAPS_API_KEY="amap-key",
        FIRECRAWL_API_KEY="fc-key",
    )

    connections = build_mcp_connections(settings)

    assert connections["amap"]["transport"] == "http"
    assert connections["amap"]["url"] == "https://mcp.amap.com/mcp?key=amap-key"
    assert connections["firecrawl"]["transport"] == "stdio"
    assert connections["firecrawl"]["args"] == ["-y", "firecrawl-mcp"]


def test_services_can_be_disabled() -> None:
    settings = Settings(
        ENABLE_AMAP=False,
        ENABLE_FIRECRAWL=False,
    )

    assert build_mcp_connections(settings) == {}
