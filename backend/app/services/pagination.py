"""Opaque keyset cursors for the `{items, next_cursor}` list shape."""

import base64
import binascii
from datetime import datetime, timezone

from sqlalchemy import Select, and_, or_

from app.errors import invalid

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    if limit < 1 or limit > MAX_LIMIT:
        raise invalid(f"limit must be between 1 and {MAX_LIMIT}.", field="limit")
    return limit


def encode_cursor(created_at: datetime, row_id: str) -> str:
    raw = f"{created_at.isoformat()}|{row_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        timestamp, row_id = raw.split("|", 1)
        parsed = datetime.fromisoformat(timestamp)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise invalid("Malformed cursor.", field="cursor") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed, row_id


def apply_cursor(stmt: Select, model, cursor: str | None) -> Select:
    """Newest first, tie-broken by ID so the order is total and stable."""
    stmt = stmt.order_by(model.created_at.desc(), model.id.desc())
    if not cursor:
        return stmt
    created_at, row_id = decode_cursor(cursor)
    return stmt.where(
        or_(
            model.created_at < created_at,
            and_(model.created_at == created_at, model.id < row_id),
        )
    )


def build_page(rows: list, limit: int, serializer) -> dict:
    """Takes limit+1 rows and turns them into a page plus a next cursor."""
    has_more = len(rows) > limit
    visible = rows[:limit]
    next_cursor = None
    if has_more and visible:
        last = visible[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    return {"items": [serializer(row) for row in visible], "next_cursor": next_cursor}
