import asyncio
import math
import os
import random
import time
from contextlib import asynccontextmanager
from importlib import import_module
from datetime import datetime, timezone

try:
    _fastapi_module = import_module("fastapi")
    FastAPI = _fastapi_module.FastAPI
    HTTPException = _fastapi_module.HTTPException
except Exception:  # pragma: no cover - optional dev dependency
    FastAPI = None
    HTTPException = RuntimeError


_engine_cache = None
_engine_dsn = None
_stats_summary_cache_value = None
_stats_summary_cache_expires_at = 0.0
_sync_task = None
_sync_stop_event = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_engine():
    global _engine_cache
    global _engine_dsn

    dsn = os.getenv("DYKIT_DSN", "").strip()
    if not dsn:
        return None

    try:
        create_engine = import_module("sqlmodel").create_engine
    except Exception:
        return None

    if _engine_cache is None or _engine_dsn != dsn:
        try:
            _engine_cache = create_engine(dsn, pool_pre_ping=True)
            _engine_dsn = dsn
        except Exception:
            return None
    return _engine_cache


def _stats_summary_cache_ttl_seconds() -> int:
    raw_ttl = os.getenv("STATS_SUMMARY_CACHE_TTL_SECONDS", "60").strip()
    try:
        ttl = int(raw_ttl)
    except Exception:
        ttl = 60
    return max(30, min(120, ttl))


def _compute_stats_summary():
    db_module = import_module("backend.db")
    schemas_module = import_module("backend.schemas")
    sqlmodel_module = import_module("sqlmodel")
    sqlalchemy_module = import_module("sqlalchemy")

    Danmaku = db_module.Danmaku
    base_filters = db_module.base_filters
    db_get_engine = db_module.get_engine
    StatsSummary = schemas_module.StatsSummary
    Session = sqlmodel_module.Session
    select = sqlmodel_module.select
    func = sqlalchemy_module.func

    engine = db_get_engine()
    if engine is None:
        raise RuntimeError("DYKIT_DSN is not set")

    minute_start = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    with Session(engine) as session:
        conn = session.connection()
        unique_count_all_time = int(
            conn.execute(
                sqlalchemy_module.text(
                    """
                    SELECT COUNT(*)
                    FROM public.danmaku_unique_stats
                    WHERE room_id = :room_id
                    """
                ),
                {"room_id": db_module.ROOM_ID},
            ).scalar_one()
        )

        minute_stmt = (
            select(func.count())
            .select_from(Danmaku)
            .where(*base_filters(), Danmaku.timestamp >= minute_start)
        )
        current_minute_count = int(session.exec(minute_stmt).one())

        top20_rows = conn.execute(
            sqlalchemy_module.text(
                """
                SELECT content, hit_count
                FROM public.danmaku_unique_stats
                WHERE room_id = :room_id
                ORDER BY hit_count DESC
                LIMIT 20
                """
            ),
            {"room_id": db_module.ROOM_ID},
        ).all()
        top20 = [
            {"content": content, "count": int(cnt)}
            for content, cnt in top20_rows
            if content is not None
        ]

        # Reuse helper to fetch latest danmu deterministically
        latest_content, latest_ts = _get_latest_danmu(session, Danmaku, base_filters)

    return StatsSummary(
        unique_count_all_time=unique_count_all_time,
        current_minute_count=current_minute_count,
        top20=top20,
        latest_danmu_content=latest_content,
        latest_danmu_ts=latest_ts,
    )


def get_stats_summary_cached():
    global _stats_summary_cache_value
    global _stats_summary_cache_expires_at

    now = time.monotonic()
    if _stats_summary_cache_value is not None and now < _stats_summary_cache_expires_at:
        return _stats_summary_cache_value

    summary = _compute_stats_summary()
    _stats_summary_cache_value = summary
    _stats_summary_cache_expires_at = now + _stats_summary_cache_ttl_seconds()
    return summary


def _get_latest_danmu(session, Danmaku, base_filters_func):
    """Return tuple (content_or_none, timestamp_or_none) for the latest danmu.

    Deterministic ordering: timestamp DESC, id DESC to break ties. Expects a
    live Session object and the Danmaku model and base_filters() function.
    """
    select = import_module("sqlmodel").select

    stmt = (
        select(Danmaku.content, Danmaku.timestamp, Danmaku.id)
        .where(*base_filters_func())
        .order_by(Danmaku.timestamp.desc(), Danmaku.id.desc())
        .limit(1)
    )
    row = session.exec(stmt).first()
    if row is None:
        return None, None
    # row is (content, timestamp, id)
    return row[0], row[1]


def get_current_minute_stats():
    sqlmodel_module = import_module("sqlmodel")
    sqlalchemy_module = import_module("sqlalchemy")
    db_module = import_module("backend.db")

    Session = sqlmodel_module.Session
    text = sqlalchemy_module.text
    db_get_engine = db_module.get_engine
    ROOM_ID = db_module.ROOM_ID
    MSG_TYPE = db_module.MSG_TYPE

    engine = db_get_engine()
    if engine is None:
        raise RuntimeError("DYKIT_DSN is not set")

    stmt = text(
        """
        WITH minute_window AS (
            SELECT
                date_trunc('minute', now() AT TIME ZONE 'UTC') AS minute_start
        )
        SELECT
            mw.minute_start AS minute_start,
            mw.minute_start + interval '1 minute' AS minute_end,
            COUNT(d.id)::int AS count
        FROM minute_window mw
        LEFT JOIN public.danmaku d
            ON d.timestamp >= mw.minute_start
           AND d.timestamp < mw.minute_start + interval '1 minute'
           AND d.room_id = :room_id
           AND d.msg_type = :msg_type
           AND d.content IS NOT NULL
        GROUP BY mw.minute_start
        """
    )

    with Session(engine) as session:
        row = (
            session.connection()
            .execute(
                stmt,
                {
                    "room_id": ROOM_ID,
                    "msg_type": MSG_TYPE,
                },
            )
            .mappings()
            .one()
        )

    return {
        "minute_start": row["minute_start"],
        "minute_end": row["minute_end"],
        "count": int(row["count"]),
    }


def get_random_content() -> dict[str, object]:
    sqlmodel_module = import_module("sqlmodel")
    sqlalchemy_module = import_module("sqlalchemy")
    db_module = import_module("backend.db")

    Danmaku = db_module.Danmaku
    base_filters = db_module.base_filters
    db_get_engine = db_module.get_engine
    Session = sqlmodel_module.Session
    select = sqlmodel_module.select
    func = sqlalchemy_module.func

    engine = db_get_engine()
    if engine is None:
        raise RuntimeError("DYKIT_DSN is not set")

    with Session(engine) as session:
        min_max_stmt = select(func.min(Danmaku.id), func.max(Danmaku.id)).where(
            *base_filters()
        )
        min_id, max_id = session.exec(min_max_stmt).one()
        if min_id is None or max_id is None:
            raise LookupError("no content found")

        random_id = random.randint(int(min_id), int(max_id))

        primary_stmt = (
            select(Danmaku.content)
            .where(*base_filters(), Danmaku.id >= random_id)
            .order_by(Danmaku.id.asc())
            .limit(1)
        )
        content = session.exec(primary_stmt).first()

        if content is None:
            fallback_stmt = (
                select(Danmaku.content)
                .where(*base_filters(), Danmaku.id < random_id)
                .order_by(Danmaku.id.asc())
                .limit(1)
            )
            content = session.exec(fallback_stmt).first()

    if content is None:
        raise LookupError("no content found")

    with Session(engine) as session:
        aggregate_row = (
            session.connection()
            .execute(
                sqlalchemy_module.text(
                    """
                    SELECT hit_count, COALESCE(last_seen_at, first_seen_at) AS last_seen_at
                    FROM public.danmaku_unique_stats
                    WHERE room_id = :room_id AND content = :content
                    """
                ),
                {"room_id": db_module.ROOM_ID, "content": content},
            )
            .first()
        )

    if aggregate_row is None:
        raise LookupError("aggregate stats not found for random content")

    return {
        "content": content,
        "count": int(aggregate_row[0]),
        "last_seen_at": aggregate_row[1],
    }


def health_check():
    payload = {
        "status": "ok",
        "db_ok": False,
        "now": _utc_now_iso(),
        "latest_ts": None,
    }

    try:
        sqlmodel_module = import_module("sqlmodel")
        sqlalchemy_module = import_module("sqlalchemy")
        Session = sqlmodel_module.Session
        text = sqlalchemy_module.text
    except Exception:
        return payload

    engine = _get_engine()
    if engine is None:
        return payload

    try:
        with Session(engine) as session:
            conn = session.connection()
            select_one = conn.execute(text("SELECT 1")).scalar_one()
            if int(select_one) == 1:
                payload["db_ok"] = True
            latest_ts = conn.execute(
                text("SELECT MAX(timestamp) FROM public.danmaku")
            ).scalar_one_or_none()
            if latest_ts is not None:
                payload["latest_ts"] = latest_ts.isoformat()
    except Exception:
        payload["db_ok"] = False

    return payload


async def _run_unique_sync_loop():
    db_module = import_module("backend.db")
    run_incremental_unique_sync = db_module.run_incremental_unique_sync
    interval = max(5, int(os.getenv("UNIQUE_SYNC_INTERVAL_SECONDS", "30")))

    while _sync_stop_event is not None and not _sync_stop_event.is_set():
        try:
            await asyncio.to_thread(run_incremental_unique_sync)
        except Exception:
            pass

        try:
            _ = await asyncio.wait_for(_sync_stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue


if FastAPI:
    schemas_mod = import_module("backend.schemas")
    StatsSummary = schemas_mod.StatsSummary
    SearchResponse = schemas_mod.SearchResponse
    RandomResponse = schemas_mod.RandomResponse
    LatestDanmuResponse = schemas_mod.LatestDanmuResponse

    @asynccontextmanager
    async def _lifespan(_app_instance):
        global _sync_task
        global _sync_stop_event
        db_module = import_module("backend.db")
        run_incremental_unique_sync = db_module.run_incremental_unique_sync
        _sync_stop_event = asyncio.Event()
        await asyncio.to_thread(run_incremental_unique_sync)
        _sync_task = asyncio.create_task(_run_unique_sync_loop())
        try:
            yield
        finally:
            if _sync_stop_event is not None:
                _sync_stop_event.set()
            if _sync_task is not None:
                await _sync_task
                _sync_task = None

    app = FastAPI(title="douyu_eyes-backend", lifespan=_lifespan)

    @app.get("/api/health")
    def api_health_check():
        return health_check()

    @app.get("/health")
    def legacy_health_check():
        return health_check()

    @app.get("/api/stats/summary", response_model=StatsSummary)
    def api_stats_summary():
        try:
            return get_stats_summary_cached()
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc

    @app.get("/api/stats/latest-danmu", response_model=LatestDanmuResponse)
    def api_stats_latest_danmu():
        """Non-cached endpoint returning the latest danmu (content + timestamp).

        Uses deterministic ordering (timestamp DESC, id DESC) and reuses the
        same base_filters() to ensure parity with the cached summary values.
        """
        try:
            db_module = import_module("backend.db")
            sqlmodel_module = import_module("sqlmodel")
            db_get_engine = db_module.get_engine
            Session = sqlmodel_module.Session

            engine = db_get_engine()
            if engine is None:
                raise RuntimeError("DYKIT_DSN is not set")

            with Session(engine) as session:
                content, ts = _get_latest_danmu(session, db_module.Danmaku, db_module.base_filters)

            return LatestDanmuResponse(content=content, timestamp=ts)
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc

    @app.get("/api/stats/current-minute")
    def api_stats_current_minute():
        try:
            return get_current_minute_stats()
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc

    @app.get("/api/search", response_model=SearchResponse)
    def api_search(
        q: str,
        limit: int | None = None,
        offset: int = 0,
        sort: str = "count",
    ):
        db_module = import_module("backend.db")
        sqlmodel_module = import_module("sqlmodel")
        sqlalchemy_module = import_module("sqlalchemy")

        db_get_engine = db_module.get_engine
        parse_keywords = db_module.parse_keywords
        normalize_limit = db_module.normalize_limit
        Session = sqlmodel_module.Session

        if not q or not q.strip():
            raise HTTPException(400, "q must not be empty")
        if offset < 0:
            raise HTTPException(400, "offset must be >= 0")
        if sort not in {"count", "last_seen"}:
            raise HTTPException(400, "sort must be one of: count, last_seen")

        try:
            keywords = parse_keywords(q)
        except ValueError as exc:
            # parse_keywords raises ValueError when too many tokens
            # Convert to HTTP 400 with a clear message for clients.
            raise HTTPException(400, str(exc)) from exc
        if not keywords:
            raise HTTPException(400, "q must contain at least one keyword")

        normalized_limit = normalize_limit(limit)
        engine = db_get_engine()
        if engine is None:
            raise HTTPException(500, "DYKIT_DSN is not set")

        with Session(engine) as session:
            where_clause = " AND ".join(
                [f"content ILIKE :kw{i}" for i in range(len(keywords))]
            )
            params = {
                "room_id": db_module.ROOM_ID,
                "offset": offset,
                "limit": normalized_limit,
            }
            for i, token in enumerate(keywords):
                params[f"kw{i}"] = f"%{token}%"

            order_clause = "hit_count DESC, content ASC"
            if sort == "last_seen":
                order_clause = "COALESCE(last_seen_at, first_seen_at) DESC, content ASC"

            rows = (
                session.connection()
                .execute(
                    sqlalchemy_module.text(
                        f"""
                    SELECT content, hit_count,
                           COALESCE(last_seen_at, first_seen_at) AS last_seen_at
                    FROM public.danmaku_unique_stats
                    WHERE room_id = :room_id AND {where_clause}
                    ORDER BY {order_clause}
                    OFFSET :offset
                    LIMIT :limit
                    """
                    ),
                    params,
                )
                .all()
            )
            items = [
                {
                    "content": row[0],
                    "count": int(row[1]),
                    "last_seen_at": row[2],
                }
                for row in rows
                if row[0] is not None
            ]

            total = int(
                session.connection()
                .execute(
                    sqlalchemy_module.text(
                        f"""
                        SELECT COUNT(*)
                        FROM public.danmaku_unique_stats
                        WHERE room_id = :room_id AND {where_clause}
                        """
                    ),
                    {
                        k: v
                        for k, v in params.items()
                        if k.startswith("kw") or k == "room_id"
                    },
                )
                .scalar_one()
            )

        total_pages = max(1, math.ceil(total / normalized_limit))
        current_page = (offset // normalized_limit) + 1

        return SearchResponse(
            items=items,
            limit=normalized_limit,
            offset=offset,
            total=total,
            total_pages=total_pages,
            current_page=current_page,
        )

    @app.get("/api/random", response_model=RandomResponse)
    def api_random():
        try:
            return RandomResponse(**get_random_content())
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc

else:
    # Allow tests to import health_check without installing FastAPI.
    app = None


def create_app():
    return app


if __name__ == "__main__":
    uvicorn = import_module("uvicorn")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="info")
