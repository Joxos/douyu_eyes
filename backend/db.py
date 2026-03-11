import os
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Field, Session, SQLModel, create_engine, select

ROOM_ID = "6979222"
MSG_TYPE = "chatmsg"

MAX_KEYWORDS = 5
MAX_KEYWORD_LEN = 50
MAX_LIMIT = 100
DEFAULT_LIMIT = 20

_ENGINE = None
_ENGINE_DSN = None


class Danmaku(SQLModel, table=True):
    __tablename__ = "danmaku"
    __table_args__ = {"schema": "public"}

    id: int = Field(primary_key=True)
    timestamp: datetime
    room_id: str
    msg_type: str
    content: str | None = None


def get_engine():
    global _ENGINE
    global _ENGINE_DSN

    dsn = os.getenv("DYKIT_DSN", "").strip()
    if not dsn:
        return None

    if _ENGINE is None or _ENGINE_DSN != dsn:
        _ENGINE = create_engine(dsn, pool_pre_ping=True)
        _ENGINE_DSN = dsn

    return _ENGINE


def base_filters():
    return (
        Danmaku.room_id == ROOM_ID,
        Danmaku.msg_type == MSG_TYPE,
        Danmaku.content.is_not(None),
    )


def parse_keywords(query: str) -> list[str]:
    """Split query into keywords.

    Raises ValueError when token count exceeds MAX_KEYWORDS so callers
    can return HTTP 400 instead of silently truncating.
    """
    tokens = [t.strip() for t in query.split() if t.strip()]
    if len(tokens) == 0:
        return []
    if len(tokens) > MAX_KEYWORDS:
        raise ValueError(f"too many keywords: max is {MAX_KEYWORDS}")
    # enforce per-keyword length but do not silently drop tokens
    return [t[:MAX_KEYWORD_LEN] for t in tokens]


def normalize_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    if limit < 1:
        return 1
    return min(limit, MAX_LIMIT)


def filtered_count(session: Session) -> int:
    stmt = select(func.count()).select_from(Danmaku).where(*base_filters())
    count = session.exec(stmt).one()
    return int(count)


def filtered_count_from_engine() -> int:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DYKIT_DSN is not set")

    with Session(engine) as session:
        return filtered_count(session)
