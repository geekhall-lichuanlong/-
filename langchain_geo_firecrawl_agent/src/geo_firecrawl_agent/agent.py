from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langgraph.checkpoint.memory import InMemorySaver
from mcp.types import TextContent

from geo_firecrawl_agent.config import Settings
from geo_firecrawl_agent.mcp_config import build_mcp_connections
from geo_firecrawl_agent.model_factory import build_chat_model
from geo_firecrawl_agent.schemas import GeoWebReport


SYSTEM_PROMPT = """You are a single-agent geospatial research assistant.

You have two families of MCP tools:
1. AMap tools for geocoding, reverse geocoding, POI search, route planning, weather,
   and other live map/location tasks.
2. Firecrawl tools for live web search, scraping, crawling, and structured extraction.

Rules:
- For locations, coordinates, POIs, routes, distance, travel time, and weather, use AMap tools.
- For websites, documents, latest pages, opening hours, policies, ticket info, guides, or
  supporting evidence, use Firecrawl tools and keep source URLs.
- In linked geo + web tasks, first clarify missing city, origin, destination, time, or preference
  if the task cannot be completed safely. Otherwise, call tools directly.
- Combine geographic facts and web evidence. Do not invent coordinates, routes, business hours,
  prices, or source URLs.
- Prefer concise Chinese answers when the user writes Chinese.
- When the user asks for structured output, return fields that can be consumed by an application:
  places, routes, web_sources, recommended_next_actions, and data_limitations.
"""


async def append_structured_content(request: MCPToolCallRequest, handler: Any) -> Any:
    """Make MCP structuredContent visible to the model as JSON text."""

    result = await handler(request)
    structured_content = getattr(result, "structuredContent", None)
    if structured_content:
        result.content += [
            TextContent(
                type="text",
                text=json.dumps(structured_content, ensure_ascii=False),
            )
        ]
    return result


@dataclass
class AgentAnswer:
    answer: str
    tool_calls: list[str] = field(default_factory=list)
    structured_response: GeoWebReport | None = None


class GeoFirecrawlAgent:
    """LangChain agent wrapper that loads tools from multiple MCP servers."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._client: MultiServerMCPClient | None = None
        self._tools: list[Any] | None = None
        self._checkpointer = InMemorySaver()
        self._agent: Any | None = None
        self._structured_agent: Any | None = None

    async def initialize(self) -> None:
        if self._client and self._tools and self._agent:
            return

        connections = build_mcp_connections(self.settings)
        if not connections:
            raise ValueError("No MCP servers are enabled.")

        self._client = MultiServerMCPClient(
            connections,
            tool_interceptors=[append_structured_content],
        )
        self._tools = await self._client.get_tools()
        self._agent = self._build_agent(response_format=None)

    @property
    def tool_names(self) -> list[str]:
        if self._tools is None:
            return []
        return [getattr(tool, "name", repr(tool)) for tool in self._tools]

    async def clear_thread(self, thread_id: str) -> None:
        await self._checkpointer.adelete_thread(thread_id)

    async def ask(
        self,
        message: str,
        thread_id: str | None = None,
        structured: bool = False,
    ) -> AgentAnswer:
        await self.initialize()

        runnable = await self._get_structured_agent() if structured else self._agent
        if runnable is None:
            raise RuntimeError("Agent was not initialized.")

        result = await runnable.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": thread_id or self.settings.default_thread_id}},
        )
        return self._parse_result(result)

    async def stream(
        self,
        message: str,
        thread_id: str | None = None,
        structured: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        await self.initialize()

        runnable = await self._get_structured_agent() if structured else self._agent
        if runnable is None:
            raise RuntimeError("Agent was not initialized.")

        tool_calls: list[str] = []
        final_answer: AgentAnswer | None = None
        config = {"configurable": {"thread_id": thread_id or self.settings.default_thread_id}}

        async for event in runnable.astream_events(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            version="v2",
        ):
            event_name = event.get("event")
            data = event.get("data") or {}

            if event_name == "on_chat_model_stream":
                text = _content_to_text(getattr(data.get("chunk"), "content", ""))
                if text:
                    yield {"type": "token", "text": text}

            elif event_name == "on_tool_start":
                name = str(event.get("name") or "")
                if name:
                    tool_calls.append(name)
                    yield {"type": "tool_start", "name": name}

            elif event_name == "on_tool_end":
                name = str(event.get("name") or "")
                if name:
                    yield {"type": "tool_end", "name": name}

            elif event_name == "on_chain_end" and event.get("name") == "LangGraph":
                output = data.get("output")
                if isinstance(output, dict):
                    final_answer = self._parse_result(output)

        if final_answer is None:
            final_answer = AgentAnswer(answer="", tool_calls=tool_calls)

        yield {
            "type": "final",
            "answer": final_answer.answer,
            "tool_calls": final_answer.tool_calls or tool_calls,
            "structured_response": (
                final_answer.structured_response.model_dump()
                if final_answer.structured_response
                else None
            ),
        }

    def _build_agent(self, response_format: type[GeoWebReport] | None) -> Any:
        if self._tools is None:
            raise RuntimeError("Tools must be loaded before building the agent.")

        kwargs: dict[str, Any] = {
            "model": build_chat_model(self.settings.agent_model),
            "tools": self._tools,
            "system_prompt": SYSTEM_PROMPT,
            "checkpointer": self._checkpointer,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        return create_agent(**kwargs)

    async def _get_structured_agent(self) -> Any:
        await self.initialize()
        if self._structured_agent is None:
            self._structured_agent = self._build_agent(response_format=GeoWebReport)
        return self._structured_agent

    def _parse_result(self, result: dict[str, Any]) -> AgentAnswer:
        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None
        answer = _content_to_text(getattr(final_message, "content", "")) if final_message else ""

        tool_calls: list[str] = []
        for message in messages:
            for call in getattr(message, "tool_calls", []) or []:
                name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
                if name:
                    tool_calls.append(str(name))

        structured = result.get("structured_response")
        if structured is not None and not isinstance(structured, GeoWebReport):
            structured = GeoWebReport.model_validate(structured)

        if structured and not answer:
            answer = structured.answer

        return AgentAnswer(
            answer=answer,
            tool_calls=tool_calls,
            structured_response=structured,
        )


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)
