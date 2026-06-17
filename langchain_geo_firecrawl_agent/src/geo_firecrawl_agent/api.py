from __future__ import annotations

from contextlib import asynccontextmanager
import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from geo_firecrawl_agent.agent import GeoFirecrawlAgent
from geo_firecrawl_agent.config import Settings
from geo_firecrawl_agent.schemas import ChatRequest, ChatResponse
from geo_firecrawl_agent.schemas import ClearThreadRequest


STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    agent = GeoFirecrawlAgent(settings)
    await agent.initialize()
    app.state.agent = agent
    app.state.settings = settings
    yield


app = FastAPI(
    title="LangChain Geo + Firecrawl Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tools")
async def tools() -> dict[str, list[str]]:
    agent: GeoFirecrawlAgent = app.state.agent
    return {"tools": agent.tool_names}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    agent: GeoFirecrawlAgent = app.state.agent
    settings: Settings = app.state.settings
    thread_id = request.thread_id or settings.default_thread_id

    try:
        answer = await agent.ask(
            request.message,
            thread_id=thread_id,
            structured=request.structured,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        thread_id=thread_id,
        answer=answer.answer,
        tool_calls=answer.tool_calls,
        structured_response=answer.structured_response,
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    agent: GeoFirecrawlAgent = app.state.agent
    settings: Settings = app.state.settings
    thread_id = request.thread_id or settings.default_thread_id

    async def event_stream() -> AsyncIterator[str]:
        try:
            yield _sse("meta", {"thread_id": thread_id})
            async for event in agent.stream(
                request.message,
                thread_id=thread_id,
                structured=request.structured,
            ):
                yield _sse(event["type"], event)
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@app.post("/threads/clear")
async def clear_thread(request: ClearThreadRequest) -> dict[str, str]:
    agent: GeoFirecrawlAgent = app.state.agent
    settings: Settings = app.state.settings
    thread_id = request.thread_id or settings.default_thread_id
    await agent.clear_thread(thread_id)
    return {"status": "ok", "thread_id": thread_id}
