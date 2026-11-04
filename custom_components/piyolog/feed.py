"""Data feed parsing and aggregation for the PiyoLog integration.

This module is intentionally free of Home Assistant imports so the whole
aggregation logic can be unit tested in isolation.

Feed specification (schema v1):
- A feed URL returns a JSON snapshot: ``schema_version``, ``generated_at``,
  ``range`` and ``records``.
- Each record has ``event_id``, ``datetime`` (UTC, ISO 8601) and ``type``,
  plus optional type-specific fields. Optional fields are omitted when the
  value was not entered; an omitted value must never be interpreted as 0.
- ``Sleep`` and ``WakeUp`` are independent records; sleep durations are not
  provided and must be derived by pairing them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, tzinfo
import math
from typing import Any

import aiohttp

from .const import (
    CUSTOM_TYPE_PREFIX,
    POOP_AMOUNT_JA,
    POOP_COLOR_JA,
    POOP_HARDNESS_JA,
    SUPPORTED_SCHEMA_VERSION,
    TYPE_BREAST_FEEDING,
    TYPE_DRINK,
    TYPE_EXPRESSED_BREAST_MILK,
    TYPE_FORMULA,
    TYPE_LABELS_JA,
    TYPE_PUMPING,
    TYPE_SLEEP,
    TYPE_WAKE_UP,
)

FEED_TIMEOUT_SECONDS = 30
TIMELINE_LIMIT = 50
RECENT_LIMIT = 100


class FeedError(Exception):
    """Base error for feed handling."""


class FeedHttpError(FeedError):
    """The feed endpoint returned an HTTP error status."""

    def __init__(self, status: int) -> None:
        super().__init__(f"Feed request failed with status {status}")
        self.status = status


class FeedFormatError(FeedError):
    """The feed response did not match the expected schema."""


@dataclass(frozen=True)
class Record:
    """A single normalized feed record."""

    event_id: str
    dt: datetime  # timezone-aware, UTC
    type: str
    raw: dict[str, Any]

    @property
    def value(self) -> dict[str, Any] | None:
        """Return the ``value`` object, if present."""
        val = self.raw.get("value")
        return val if isinstance(val, dict) else None

    def numeric_value(self) -> float | None:
        """Return ``value.value`` as a float, or None when omitted."""
        val = self.value
        if not val:
            return None
        num = val.get("value")
        if isinstance(num, (int, float)) and not isinstance(num, bool):
            return float(num)
        return None

    @property
    def memo(self) -> str | None:
        memo = self.raw.get("memo")
        return memo if isinstance(memo, str) and memo else None


@dataclass(frozen=True)
class FeedSnapshot:
    """A parsed feed response."""

    generated_at: datetime
    records: tuple[Record, ...]


def _parse_datetime(text: Any) -> datetime:
    if not isinstance(text, str):
        raise FeedFormatError("datetime is not a string")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as err:
        raise FeedFormatError(f"unparseable datetime: {text!r}") from err
    if dt.tzinfo is None:
        raise FeedFormatError("datetime has no timezone")
    return dt


def parse_feed(payload: Any) -> FeedSnapshot:
    """Validate and parse a feed JSON payload."""
    if not isinstance(payload, dict):
        raise FeedFormatError("feed payload is not an object")
    if payload.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise FeedFormatError(
            f"unsupported schema_version: {payload.get('schema_version')!r}"
        )
    generated_at = _parse_datetime(payload.get("generated_at"))
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        raise FeedFormatError("records is not a list")
    records: list[Record] = []
    for item in raw_records:
        if not isinstance(item, dict):
            continue
        event_id = item.get("event_id")
        rtype = item.get("type")
        if not isinstance(event_id, str) or not isinstance(rtype, str):
            continue
        try:
            dt = _parse_datetime(item.get("datetime"))
        except FeedFormatError:
            continue
        records.append(Record(event_id=event_id, dt=dt, type=rtype, raw=item))
    records.sort(key=lambda r: r.dt)
    return FeedSnapshot(generated_at=generated_at, records=tuple(records))


async def fetch_feed(session: aiohttp.ClientSession, url: str) -> FeedSnapshot:
    """Fetch and parse a feed URL."""
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=FEED_TIMEOUT_SECONDS)
        ) as resp:
            if resp.status != 200:
                raise FeedHttpError(resp.status)
            try:
                payload = await resp.json(content_type=None)
            except (aiohttp.ContentTypeError, ValueError) as err:
                raise FeedFormatError("feed response is not JSON") from err
    except aiohttp.ClientError as err:
        raise FeedError(f"feed request failed: {err}") from err
    return parse_feed(payload)


def merge_snapshots(snapshots: list[FeedSnapshot]) -> list[Record]:
    """Merge snapshots, de-duplicating by event_id.

    When the same event_id appears in several snapshots, the record from the
    snapshot with the newest ``generated_at`` wins, so edits are reflected.
    """
    by_id: dict[str, tuple[datetime, Record]] = {}
    for snap in snapshots:
        for record in snap.records:
            current = by_id.get(record.event_id)
            if current is None or snap.generated_at >= current[0]:
                by_id[record.event_id] = (snap.generated_at, record)
    merged = [rec for _, rec in by_id.values()]
    merged.sort(key=lambda r: r.dt)
    return merged


def type_label(record_type: str) -> str:
    """Return the Japanese label for a record type."""
    if record_type.startswith(CUSTOM_TYPE_PREFIX):
        return f"カスタム{record_type[len(CUSTOM_TYPE_PREFIX):]}"
    return TYPE_LABELS_JA.get(record_type, record_type)


def summarize(record: Record) -> str:
    """Build a short human-readable summary of a record."""
    rtype = record.type
    num = record.numeric_value()
    if rtype == TYPE_BREAST_FEEDING:
        left = record.raw.get("leftTime")
        right = record.raw.get("rightTime")
        parts: list[str] = []
        if isinstance(left, (int, float)) and left:
            parts.append(f"左{round(left / 60)}分")
        if isinstance(right, (int, float)) and right:
            parts.append(f"右{round(right / 60)}分")
        if num is not None:
            parts.append(f"{_fmt_num(num)}ml")
        return " ".join(parts)
    if rtype in (TYPE_FORMULA, TYPE_EXPRESSED_BREAST_MILK, TYPE_PUMPING, TYPE_DRINK):
        return f"{_fmt_num(num)}ml" if num is not None else ""
    if rtype == "Poop":
        details = record.raw.get("details")
        if isinstance(details, dict):
            parts = [
                POOP_AMOUNT_JA.get(details.get("amount", ""), ""),
                POOP_HARDNESS_JA.get(details.get("hardness", ""), ""),
                POOP_COLOR_JA.get(details.get("color", ""), ""),
            ]
            return "・".join(p for p in parts if p)
        return ""
    if rtype == "Temperature":
        return f"{_fmt_num(num)}℃" if num is not None else ""
    if rtype == "Weight":
        return f"{_fmt_num(num)}kg" if num is not None else ""
    if rtype in ("Height", "Head", "Chest"):
        return f"{_fmt_num(num)}cm" if num is not None else ""
    if rtype == "Foot":
        val = record.value or {}
        left, right = val.get("left"), val.get("right")
        parts = []
        if isinstance(left, (int, float)):
            parts.append(f"左{_fmt_num(float(left))}cm")
        if isinstance(right, (int, float)):
            parts.append(f"右{_fmt_num(float(right))}cm")
        return " ".join(parts)
    return ""


def _fmt_num(num: float) -> str:
    if math.isclose(num, round(num)):
        return str(int(round(num)))
    return f"{num:g}"


@dataclass
class AggregatedData:
    """Everything the entities need, computed from merged records."""

    generated_at: datetime | None = None
    record_count: int = 0
    last_by_type: dict[str, Record] = field(default_factory=dict)
    today_counts: dict[str, int] = field(default_factory=dict)
    today_breast_feeding_duration_seconds: int = 0
    today_breast_feeding_ml: float = 0.0
    today_breast_feeding_measured_count: int = 0
    today_formula_ml: float = 0.0
    today_expressed_ml: float = 0.0
    today_pumping_ml: float = 0.0
    today_drink_ml: float = 0.0
    today_sleep_seconds: int = 0
    currently_sleeping: bool = False
    sleeping_since: datetime | None = None
    timeline_today: list[dict[str, Any]] = field(default_factory=list)
    recent_events: list[dict[str, Any]] = field(default_factory=list)

    def last(self, record_type: str) -> Record | None:
        return self.last_by_type.get(record_type)

    def today_count(self, record_type: str) -> int:
        return self.today_counts.get(record_type, 0)


def aggregate(
    records: list[Record],
    tz: tzinfo,
    now: datetime,
    generated_at: datetime | None = None,
) -> AggregatedData:
    """Aggregate merged records into entity-ready data.

    ``now`` must be timezone-aware. "Today" is the local calendar day of
    ``now`` in ``tz``.
    """
    data = AggregatedData(generated_at=generated_at, record_count=len(records))
    today_start = datetime.combine(now.astimezone(tz).date(), time.min, tzinfo=tz)
    today_end = today_start + timedelta(days=1)

    for record in records:
        current = data.last_by_type.get(record.type)
        if current is None or record.dt >= current.dt:
            data.last_by_type[record.type] = record

    today_records = [
        r for r in records if today_start <= r.dt.astimezone(tz) < today_end
    ]
    for record in today_records:
        data.today_counts[record.type] = data.today_counts.get(record.type, 0) + 1
        num = record.numeric_value()
        if record.type == TYPE_BREAST_FEEDING:
            left = record.raw.get("leftTime")
            right = record.raw.get("rightTime")
            total = 0
            if isinstance(left, (int, float)):
                total += int(left)
            if isinstance(right, (int, float)):
                total += int(right)
            data.today_breast_feeding_duration_seconds += total
            # BreastFeeding records can carry a measured amount (ml).
            if num is not None:
                data.today_breast_feeding_ml += num
                data.today_breast_feeding_measured_count += 1
        elif record.type == TYPE_FORMULA and num is not None:
            data.today_formula_ml += num
        elif record.type == TYPE_EXPRESSED_BREAST_MILK and num is not None:
            data.today_expressed_ml += num
        elif record.type == TYPE_PUMPING and num is not None:
            data.today_pumping_ml += num
        elif record.type == TYPE_DRINK and num is not None:
            data.today_drink_ml += num

    _aggregate_sleep(data, records, today_start, today_end, now)

    data.timeline_today = [
        _timeline_entry(record, tz)
        for record in sorted(today_records, key=lambda r: r.dt, reverse=True)[
            :TIMELINE_LIMIT
        ]
    ]
    # Most recent events across all days in the feed window (newest first).
    data.recent_events = [
        _timeline_entry(record, tz)
        for record in sorted(records, key=lambda r: r.dt, reverse=True)[
            :RECENT_LIMIT
        ]
    ]
    return data


def _timeline_entry(record: Record, tz: tzinfo) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "time": record.dt.astimezone(tz).isoformat(),
        "type": record.type,
        "label": type_label(record.type),
        "summary": summarize(record),
    }
    if record.memo:
        entry["memo"] = record.memo
    return entry


def _aggregate_sleep(
    data: AggregatedData,
    records: list[Record],
    today_start: datetime,
    today_end: datetime,
    now: datetime,
) -> None:
    """Pair Sleep/WakeUp records and compute sleep state and today's total."""
    sleeping_since: datetime | None = None
    intervals: list[tuple[datetime, datetime]] = []
    for record in records:
        if record.type == TYPE_SLEEP:
            # Consecutive Sleep records: the newest start wins (corrections).
            sleeping_since = record.dt
        elif record.type == TYPE_WAKE_UP and sleeping_since is not None:
            intervals.append((sleeping_since, record.dt))
            sleeping_since = None
    if sleeping_since is not None:
        data.currently_sleeping = True
        data.sleeping_since = sleeping_since
        intervals.append((sleeping_since, now))

    total = 0.0
    for start, end in intervals:
        overlap_start = max(start, today_start)
        overlap_end = min(end, today_end, now)
        if overlap_end > overlap_start:
            total += (overlap_end - overlap_start).total_seconds()
    data.today_sleep_seconds = int(total)
