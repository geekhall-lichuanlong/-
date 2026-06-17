from __future__ import annotations

from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


Transport = Literal["http", "stdio"]


class Settings(BaseSettings):
    """Environment-backed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    agent_model: str = Field(default="openai:gpt-4.1-mini", alias="AGENT_MODEL")

    enable_amap: bool = Field(default=True, alias="ENABLE_AMAP")
    amap_transport: Transport = Field(default="http", alias="AMAP_TRANSPORT")
    amap_maps_api_key: str | None = Field(default=None, alias="AMAP_MAPS_API_KEY")
    amap_mcp_url: str | None = Field(default=None, alias="AMAP_MCP_URL")

    enable_firecrawl: bool = Field(default=True, alias="ENABLE_FIRECRAWL")
    firecrawl_transport: Transport = Field(default="stdio", alias="FIRECRAWL_TRANSPORT")
    firecrawl_api_key: str | None = Field(default=None, alias="FIRECRAWL_API_KEY")
    firecrawl_mcp_url: str | None = Field(
        default="http://localhost:3000/mcp",
        alias="FIRECRAWL_MCP_URL",
    )

    default_thread_id: str = Field(default="demo", alias="DEFAULT_THREAD_ID")

    @model_validator(mode="after")
    def validate_required_keys(self) -> "Settings":
        missing: list[str] = []

        if self.enable_amap and not (self.amap_maps_api_key or self.amap_mcp_url):
            missing.append("AMAP_MAPS_API_KEY or AMAP_MCP_URL")

        if self.enable_firecrawl and self.firecrawl_transport == "stdio":
            if not self.firecrawl_api_key:
                missing.append("FIRECRAWL_API_KEY")

        if self.enable_firecrawl and self.firecrawl_transport == "http":
            if not self.firecrawl_mcp_url:
                missing.append("FIRECRAWL_MCP_URL")

        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required configuration: {names}")

        return self
