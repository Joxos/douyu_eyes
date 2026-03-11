# AGENTS Working Rules

## Internal Contract Policy (Backend ↔ Frontend)

- For **internal, fully controlled components** (this repo's frontend and backend), do **not** add defensive fallback logic for schema drift.
- Treat API contracts as strict:
  - Backend must return the agreed response shape.
  - Frontend must consume that exact shape.
- If the shape is wrong, **fail fast** (raise/report clearly) and fix the producer or consumer at the source.
- Avoid "best-effort" parsing like `data.results || data.data || []` for internal APIs.

## Rationale

- Silent fallback hides real bugs.
- Strict contracts keep failures obvious and easier to debug.
- Controlled systems should prioritize correctness over permissive parsing.
