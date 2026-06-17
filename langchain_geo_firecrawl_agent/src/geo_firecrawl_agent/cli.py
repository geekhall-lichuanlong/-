from __future__ import annotations

import argparse
import asyncio

from pydantic import ValidationError

from geo_firecrawl_agent.agent import GeoFirecrawlAgent
from geo_firecrawl_agent.config import Settings


async def run_chat(thread_id: str | None, structured: bool) -> None:
    settings = Settings()
    agent = GeoFirecrawlAgent(settings)
    await agent.initialize()

    active_thread_id = thread_id or settings.default_thread_id
    print(f"Loaded {len(agent.tool_names)} MCP tools.")
    print(f"Thread: {active_thread_id}")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        answer = await agent.ask(user_input, thread_id=active_thread_id, structured=structured)
        print(f"\nAgent> {answer.answer}\n")
        if answer.tool_calls:
            print("Tools:", ", ".join(answer.tool_calls))
            print()
        if answer.structured_response:
            print(answer.structured_response.model_dump_json(indent=2))
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the AMap + Firecrawl LangChain agent.")
    parser.add_argument("--thread-id", default=None, help="Conversation thread id for memory.")
    parser.add_argument(
        "--structured",
        action="store_true",
        help="Ask the agent to return the GeoWebReport schema on each turn.",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_chat(args.thread_id, args.structured))
    except ValidationError as exc:
        print("Configuration error:")
        print(exc)
    except ValueError as exc:
        print(f"Configuration error: {exc}")


if __name__ == "__main__":
    main()
