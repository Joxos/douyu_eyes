import os
from datetime import datetime
from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.engine import Connection
from sqlmodel import Field, Session, SQLModel, create_engine, select

ROOM_ID = "6979222"
MSG_TYPE = "chatmsg"

MAX_KEYWORDS = 5
MAX_KEYWORD_LEN = 50
MAX_LIMIT = 100
DEFAULT_LIMIT = 20

_ENGINE = None
_ENGINE_DSN = None

SYNC_BATCH_SIZE = 10_000


class Danmaku(SQLModel, table=True):
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
        Danmaku.content != None,
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


def _ensure_aggregate_tables(conn: Connection) -> None:
    conn.execute(
        text(
        """
        CREATE TABLE IF NOT EXISTS public.danmaku_unique_stats (
            room_id text NOT NULL,
            content text NOT NULL,
            hit_count bigint NOT NULL DEFAULT 0,
            first_seen_at timestamp NOT NULL,
            last_seen_at timestamp NOT NULL,
            updated_at timestamp NOT NULL DEFAULT now(),
            PRIMARY KEY (room_id, content)
        )
        """
        )
    )
    conn.execute(
        text(
        """
        CREATE INDEX IF NOT EXISTS idx_danmaku_unique_stats_room_hit
        ON public.danmaku_unique_stats (room_id, hit_count DESC)
        """
        )
    )
    conn.execute(
        text(
        """
        CREATE INDEX IF NOT EXISTS idx_danmaku_unique_stats_room_last_seen
        ON public.danmaku_unique_stats (room_id, last_seen_at DESC)
        """
        )
    )
    conn.execute(
        text(
        """
        CREATE TABLE IF NOT EXISTS public.danmaku_sync_state (
            room_id text PRIMARY KEY,
            last_processed_id bigint NOT NULL DEFAULT 0,
            updated_at timestamp NOT NULL DEFAULT now()
        )
        """
        )
    )


def run_incremental_unique_sync(batch_size: int = SYNC_BATCH_SIZE) -> int:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DYKIT_DSN is not set")

    total_processed = 0
    last_processed_id = 0

    with engine.begin() as conn:
        _ensure_aggregate_tables(conn)
        conn.execute(
            text(
                """
                INSERT INTO public.danmaku_sync_state (room_id, last_processed_id)
                VALUES (:room_id, 0)
                ON CONFLICT (room_id) DO NOTHING
                """
            ),
            {"room_id": ROOM_ID},
        )
        row = conn.execute(
            text("SELECT last_processed_id FROM public.danmaku_sync_state WHERE room_id = :room_id"),
            {"room_id": ROOM_ID},
        ).first()
        if row is not None:
            last_processed_id = int(row[0])

    while True:
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, content, timestamp
                    FROM public.danmaku
                    WHERE room_id = :room_id
                      AND msg_type = :msg_type
                      AND content IS NOT NULL
                      AND id > :last_processed_id
                    ORDER BY id ASC
                    LIMIT :batch_size
                    """
                ),
                {
                    "room_id": ROOM_ID,
                    "msg_type": MSG_TYPE,
                    "last_processed_id": last_processed_id,
                    "batch_size": batch_size,
                },
            ).all()

            if not rows:
                break

            aggregates: dict[str, dict[str, Any]] = {}
            max_id = last_processed_id
            for rid, content, ts in rows:
                if content is None:
                    continue
                max_id = max(max_id, int(rid))
                item = aggregates.get(content)
                if item is None:
                    aggregates[content] = {
                        "room_id": ROOM_ID,
                        "content": content,
                        "hit_count": 1,
                        "first_seen_at": ts,
                        "last_seen_at": ts,
                    }
                else:
                    item["hit_count"] = int(item["hit_count"]) + 1
                    if ts < item["first_seen_at"]:
                        item["first_seen_at"] = ts
                    if ts > item["last_seen_at"]:
                        item["last_seen_at"] = ts

            if aggregates:
                params: Iterable[dict[str, object]] = aggregates.values()
                conn.execute(
                    text(
                        """
                        INSERT INTO public.danmaku_unique_stats
                            (room_id, content, hit_count, first_seen_at, last_seen_at)
                        VALUES
                            (:room_id, :content, :hit_count, :first_seen_at, :last_seen_at)
                        ON CONFLICT (room_id, content) DO UPDATE
                        SET hit_count = public.danmaku_unique_stats.hit_count + EXCLUDED.hit_count,
                            first_seen_at = LEAST(public.danmaku_unique_stats.first_seen_at, EXCLUDED.first_seen_at),
                            last_seen_at = GREATEST(public.danmaku_unique_stats.last_seen_at, EXCLUDED.last_seen_at),
                            updated_at = now()
                        """
                    ),
                    list(params),
                )

            conn.execute(
                text(
                    """
                    UPDATE public.danmaku_sync_state
                    SET last_processed_id = :last_processed_id,
                        updated_at = now()
                    WHERE room_id = :room_id
                    """
                ),
                {"room_id": ROOM_ID, "last_processed_id": max_id},
            )

            total_processed += len(rows)
            last_processed_id = max_id

    return total_processed
