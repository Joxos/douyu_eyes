import os
import random
import time
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
        unique_stmt = select(func.count(func.distinct(Danmaku.content))).where(*base_filters())
        unique_count_all_time = int(session.exec(unique_stmt).one())

        minute_stmt = (
            select(func.count())
            .select_from(Danmaku)
            .where(*base_filters(), Danmaku.timestamp >= minute_start)
        )
        current_minute_count = int(session.exec(minute_stmt).one())

        cnt_expr = func.count().label("cnt")
        top20_stmt = (
            select(Danmaku.content, cnt_expr)
            .where(*base_filters())
            .group_by(Danmaku.content)
            .order_by(cnt_expr.desc())
            .limit(20)
        )
        top20_rows = session.exec(top20_stmt).all()
        top20 = [{"content": content, "count": int(cnt)} for content, cnt in top20_rows if content is not None]

    return StatsSummary(
        unique_count_all_time=unique_count_all_time,
        current_minute_count=current_minute_count,
        top20=top20,
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
                date_trunc('minute', now() AT TIME ZONE 'Asia/Shanghai') AS minute_start
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
        row = session.connection().execute(
            stmt,
            {
                "room_id": ROOM_ID,
                "msg_type": MSG_TYPE,
            },
        ).mappings().one()

    return {
        "minute_start": row["minute_start"],
        "minute_end": row["minute_end"],
        "count": int(row["count"]),
    }


def get_random_content() -> str:
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
        min_max_stmt = select(func.min(Danmaku.id), func.max(Danmaku.id)).where(*base_filters())
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
    return content


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


if FastAPI:
    StatsSummary = import_module("backend.schemas").StatsSummary
    SearchResponse = import_module("backend.schemas").SearchResponse
    RandomResponse = import_module("backend.schemas").RandomResponse
    app = FastAPI(title="douyu_eyes-backend")

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

    @app.get("/api/stats/current-minute")
    def api_stats_current_minute():
        try:
            return get_current_minute_stats()
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc

    @app.get("/api/search", response_model=SearchResponse)
    def api_search(q: str, limit: int | None = None, offset: int = 0):
        db_module = import_module("backend.db")
        sqlmodel_module = import_module("sqlmodel")

        Danmaku = db_module.Danmaku
        base_filters = db_module.base_filters
        db_get_engine = db_module.get_engine
        parse_keywords = db_module.parse_keywords
        normalize_limit = db_module.normalize_limit
        Session = sqlmodel_module.Session
        select = sqlmodel_module.select

        if not q or not q.strip():
            raise HTTPException(400, "q must not be empty")
        if offset < 0:
            raise HTTPException(400, "offset must be >= 0")

        try:
            keywords = parse_keywords(q)
        except ValueError as exc:
            # parse_keywords raises ValueError when too many tokens
            # Convert to HTTP 400 with a clear message for clients.
            raise HTTPException(400, str(exc)) from exc
        if not keywords:
            raise HTTPException(400, "q must contain at least one keyword")

        normalized_limit = normalize_limit(limit)
        token_filters = [Danmaku.content.ilike(f"%{token}%") for token in keywords]

        engine = db_get_engine()
        if engine is None:
            raise HTTPException(500, "DYKIT_DSN is not set")

        stmt = (
            select(Danmaku.content)
            .where(*base_filters(), *token_filters)
            .order_by(Danmaku.timestamp.desc(), Danmaku.id.desc())
            .offset(offset)
            .limit(normalized_limit)
        )

        with Session(engine) as session:
            items = [row for row in session.exec(stmt).all() if row is not None]

        return SearchResponse(items=items, limit=normalized_limit, offset=offset)

    @app.get("/api/random", response_model=RandomResponse)
    def api_random():
        try:
            return RandomResponse(content=get_random_content())
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
