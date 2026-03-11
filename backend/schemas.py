"""
Pydantic response models for API endpoints.

Do NOT include user-identifying fields (user_id, username) or raw_data in these
response models — responses must be safe to return to API clients.

Models included:
 - StatsSummary: statistics summary used by /api/stats/* endpoints
 - SearchResponse: paginated list of string items
 - RandomResponse: single random content string
 - ErrorResponse: standard error payload

These models are plain data containers (no validation/business logic).
"""
from typing import List

from pydantic import BaseModel, Field


class Top20Item(BaseModel):
    content: str
    count: int


class StatsSummary(BaseModel):
    """Summary statistics for the application.

    Fields:
    - unique_count_all_time: total number of unique items seen since the service started
    - current_minute_count: number of items seen in the current minute
    - top20: ordered list of the top 20 items with counts
    """

    unique_count_all_time: int = Field(..., description="Total unique items seen all time")
    current_minute_count: int = Field(..., description="Count of items observed in the current minute")
    top20: List[Top20Item] = Field(default_factory=list, description="Top 20 items (ordered by count)")


class SearchResponse(BaseModel):
    """Response model for search endpoints.

    - items: list of matching item strings (identifiers or short content snippets)
    - limit: the requested limit for pagination
    - offset: the requested offset for pagination
    """

    items: List[str] = Field(default_factory=list, description="Matching items")
    limit: int = Field(..., description="Requested maximum number of items")
    offset: int = Field(..., description="Requested result offset")


class RandomResponse(BaseModel):
    """Response for /api/random-like endpoints returning a single piece of content."""

    content: str = Field(..., description="Randomly selected content")


class ErrorResponse(BaseModel):
    """Standard error response model returned on failures."""

    detail: str = Field(..., description="Human-readable error message")


__all__ = ["StatsSummary", "SearchResponse", "RandomResponse", "ErrorResponse", "Top20Item"]
