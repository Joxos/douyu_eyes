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

from datetime import datetime

from pydantic import BaseModel, Field


class Top20Item(BaseModel):
    content: str
    count: int
    last_seen_at: datetime | None = None


class StatsSummary(BaseModel):
    """Summary statistics for the application.

    Fields:
    - unique_count_all_time: total number of unique items seen since the service started
    - current_minute_count: number of items seen in the current minute
    - top20: ordered list of the top 20 items with counts
    """

    unique_count_all_time: int = Field(
        ..., description="Total unique items seen all time"
    )
    current_minute_count: int = Field(
        ..., description="Count of items observed in the current minute"
    )
    top20: list[Top20Item] = Field(
        default_factory=list, description="Top 20 items (ordered by count)"
    )
    # Latest danmu content and timestamp (optional when DB empty)
    latest_danmu_content: str | None = Field(
        None, description="Most recent danmu content matching current filters"
    )
    latest_danmu_ts: datetime | None = Field(
        None, description="Timestamp of the most recent danmu matching current filters"
    )


class SearchResponse(BaseModel):
    """Response model for search endpoints.

    - items: list of matching item strings (identifiers or short content snippets)
    - limit: the requested limit for pagination
    - offset: the requested offset for pagination
    """

    items: list[Top20Item] = Field(
        default_factory=list,
        description="Matching items with occurrence count",
    )
    limit: int = Field(..., description="Requested maximum number of items")
    offset: int = Field(..., description="Requested result offset")
    total: int = Field(..., description="Total number of matched unique items")
    total_pages: int = Field(..., description="Total pages based on limit")
    current_page: int = Field(..., description="Current page number (1-indexed)")


class RandomResponse(BaseModel):
    """Response for /api/random-like endpoints returning a single piece of content."""

    content: str = Field(..., description="Randomly selected content")
    count: int | None = Field(None, description="Occurrence count for selected content")
    last_seen_at: datetime | None = Field(
        None, description="Last seen timestamp for selected content"
    )


class ErrorResponse(BaseModel):
    """Standard error response model returned on failures."""

    detail: str = Field(..., description="Human-readable error message")


__all__ = [
    "StatsSummary",
    "SearchResponse",
    "RandomResponse",
    "ErrorResponse",
    "Top20Item",
]


class LatestDanmuResponse(BaseModel):
    """Latest danmu payload used by the live polling endpoint.

    Fields are optional to allow empty-database cases.
    """

    content: str | None = Field(None, description="Latest danmu content or null if none")
    timestamp: datetime | None = Field(
        None, description="Timestamp of the latest danmu or null if none"
    )


__all__.append("LatestDanmuResponse")
