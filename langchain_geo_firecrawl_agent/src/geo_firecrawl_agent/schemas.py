from __future__ import annotations

from pydantic import BaseModel, Field


class RouteOption(BaseModel):
    mode: str = Field(description="Transit, driving, walking, cycling, or mixed.")
    origin: str
    destination: str
    estimated_duration: str | None = None
    distance: str | None = None
    cost: str | None = None
    steps: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class PlaceInfo(BaseModel):
    name: str
    category: str | None = None
    address: str | None = None
    coordinates: str | None = Field(default=None, description="Longitude,latitude if available.")
    phone: str | None = None
    opening_hours: str | None = None
    rating_or_popularity: str | None = None
    source: str | None = None


class WebSource(BaseModel):
    title: str | None = None
    url: str
    summary: str
    extracted_facts: list[str] = Field(default_factory=list)
    locations_mentioned: list[str] = Field(default_factory=list)


class GeoWebReport(BaseModel):
    answer: str = Field(description="Human-readable final answer.")
    places: list[PlaceInfo] = Field(default_factory=list)
    routes: list[RouteOption] = Field(default_factory=list)
    web_sources: list[WebSource] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    structured: bool = False


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    tool_calls: list[str] = Field(default_factory=list)
    structured_response: GeoWebReport | None = None


class ClearThreadRequest(BaseModel):
    thread_id: str | None = None
