"""Tests for feed.py (pure aggregation logic, no Home Assistant needed)."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from custom_components.piyolog.feed import (
    FeedFormatError,
    aggregate,
    merge_snapshots,
    parse_feed,
    summarize,
)

from .fixtures import payload, rec, sample_records

UTC = timezone.utc
NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


def _aggregate(records=None, tz=UTC, now=NOW):
    snap = parse_feed(payload(records if records is not None else sample_records()))
    return aggregate(list(snap.records), tz=tz, now=now, generated_at=snap.generated_at)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_parse_feed_ok():
    snap = parse_feed(payload(sample_records()))
    assert len(snap.records) == 12
    assert snap.records[0].type == "Weight"  # sorted by datetime
    assert snap.generated_at == NOW


def test_parse_feed_rejects_unknown_schema():
    bad = payload([])
    bad["schema_version"] = 99
    with pytest.raises(FeedFormatError):
        parse_feed(bad)


def test_parse_feed_skips_broken_records():
    records = sample_records() + [
        {"event_id": "broken"},  # no datetime/type
        {"datetime": "2026-09-09T00:00:00.000Z", "type": "Pee"},  # no event_id
    ]
    snap = parse_feed(payload(records))
    assert len(snap.records) == 12


def test_parse_feed_empty_records():
    snap = parse_feed(payload([]))
    assert snap.records == ()


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


def test_merge_dedup_newer_snapshot_wins():
    older = parse_feed(
        payload(
            [rec("a", "2026-09-09T09:00:00.000Z", "Formula",
                 value={"value": 100, "unit": "ml"})],
            generated_at="2026-09-09T10:00:00.000Z",
        )
    )
    newer = parse_feed(
        payload(
            [rec("a", "2026-09-09T09:00:00.000Z", "Formula",
                 value={"value": 150, "unit": "ml"})],
            generated_at="2026-09-09T11:00:00.000Z",
        )
    )
    merged = merge_snapshots([older, newer])
    assert len(merged) == 1
    assert merged[0].numeric_value() == 150


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def test_last_values():
    data = _aggregate()
    weight = data.last("Weight")
    assert weight is not None and weight.numeric_value() == 6.3
    temp = data.last("Temperature")
    assert temp is not None and temp.numeric_value() == 36.7
    assert data.last("Formula") is not None
    assert data.last("Formula").event_id == "formula-2"


def test_today_counts_and_totals():
    data = _aggregate()
    assert data.today_count("Formula") == 2
    # The second Formula record has no value entered: counted, but 0 ml added.
    assert data.today_formula_ml == 120
    assert data.today_count("Pee") == 2
    assert data.today_count("Poop") == 1
    assert data.today_count("Weight") == 1  # yesterday's weight is not today's


def test_breast_feeding_duration():
    data = _aggregate()
    assert data.today_count("BreastFeeding") == 1
    assert data.today_breast_feeding_duration_seconds == 300 + 240


def test_breast_feeding_ml_total():
    # BreastFeeding records may carry a measured amount (ml); records
    # without a value are counted as sessions but add nothing to the total.
    records = [
        rec("bf1", "2026-09-09T07:00:00.000Z", "BreastFeeding",
            leftTime=300, value={"value": 100, "unit": "ml"}),
        rec("bf2", "2026-09-09T09:00:00.000Z", "BreastFeeding",
            rightTime=240, value={"value": 50, "unit": "ml"}),
        rec("bf3", "2026-09-09T11:00:00.000Z", "BreastFeeding", leftTime=60),
    ]
    data = _aggregate(records)
    assert data.today_count("BreastFeeding") == 3
    assert data.today_breast_feeding_ml == 150
    assert data.today_breast_feeding_measured_count == 2
    assert data.today_breast_feeding_duration_seconds == 300 + 240 + 60


def test_sleep_pairing_and_today_total():
    data = _aggregate()
    # 22:00 -> 02:00 contributes 2h to today; open sleep from 10:00 adds 2h.
    assert data.today_sleep_seconds == 4 * 3600
    assert data.currently_sleeping is True
    assert data.sleeping_since == datetime(2026, 9, 9, 10, 0, tzinfo=UTC)


def test_sleep_closed_interval_only():
    records = [
        rec("s", "2026-09-09T01:00:00.000Z", "Sleep"),
        rec("w", "2026-09-09T03:30:00.000Z", "WakeUp"),
    ]
    data = _aggregate(records)
    assert data.currently_sleeping is False
    assert data.today_sleep_seconds == int(2.5 * 3600)


def test_sleep_in_local_timezone():
    # 15:00Z sleep -> 17:00Z wake is 00:00 -> 02:00 JST on 2026-09-10.
    records = [
        rec("s", "2026-09-09T15:00:00.000Z", "Sleep"),
        rec("w", "2026-09-09T17:00:00.000Z", "WakeUp"),
    ]
    jst = ZoneInfo("Asia/Tokyo")
    now_jst = datetime(2026, 9, 10, 12, 0, tzinfo=jst)
    data = _aggregate(records, tz=jst, now=now_jst)
    assert data.today_sleep_seconds == 2 * 3600
    assert data.today_count("Sleep") == 1


def test_empty_aggregate():
    data = _aggregate([])
    assert data.record_count == 0
    assert data.last("Weight") is None
    assert data.currently_sleeping is False
    assert data.today_sleep_seconds == 0
    assert data.timeline_today == []
    assert data.recent_events == []


def test_recent_events_span_days_newest_first():
    data = _aggregate()
    # All 12 sample records, including yesterday's, newest first.
    assert len(data.recent_events) == 12
    times = [e["time"] for e in data.recent_events]
    assert times == sorted(times, reverse=True)
    assert data.recent_events[-1]["type"] == "Weight"  # 2026-09-08 record
    assert len(data.timeline_today) < len(data.recent_events)


def test_recent_events_capped_at_100():
    base = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    records = []
    for i in range(150):
        dt = base + timedelta(minutes=i)
        records.append(
            rec(f"r{i}", dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "Pee")
        )
    data = _aggregate(records)
    assert data.record_count == 150
    assert len(data.recent_events) == 100
    times = [e["time"] for e in data.recent_events]
    assert times == sorted(times, reverse=True)
    assert data.recent_events[0]["time"] == "2026-09-01T02:29:00+00:00"


def test_timeline_today_newest_first_with_summary():
    data = _aggregate()
    times = [e["time"] for e in data.timeline_today]
    assert times == sorted(times, reverse=True)
    poop = next(e for e in data.timeline_today if e["type"] == "Poop")
    assert poop["label"] == "うんち"
    assert poop["summary"] == "ふつう・やわらかめ・黄"
    formula = next(
        e for e in data.timeline_today
        if e["type"] == "Formula" and e["summary"] == "120ml"
    )
    assert formula["label"] == "ミルク"


def test_measurement_buckets_past_days_only():
    data = _aggregate()
    buckets = data.measurement_buckets["Weight"]
    # Yesterday's 10:00 measurement becomes a bucket; today's is left to
    # the recorder (it compiles today's statistics from live states).
    assert len(buckets) == 1
    assert buckets[0]["start"] == datetime(2026, 9, 8, 10, 0, tzinfo=UTC)
    assert buckets[0]["mean"] == buckets[0]["min"] == buckets[0]["max"] == 6.25
    assert "Temperature" not in data.measurement_buckets


def test_daily_totals():
    data = _aggregate()

    def by_day(key):
        return {
            p["start"].date().isoformat(): p["value"]
            for p in data.daily_totals[key]
        }

    assert by_day("formula_ml") == {"2026-09-09": 120.0}
    assert by_day("breast_feeding_count") == {"2026-09-09": 1.0}
    assert by_day("breast_feeding_minutes") == {"2026-09-09": 9.0}
    assert by_day("pee_count") == {"2026-09-09": 2.0}
    assert by_day("poop_count") == {"2026-09-09": 1.0}
    # Sleep crossing midnight is split across both days; the still-open
    # sleep counts up to `now`.
    assert by_day("sleep_minutes") == {"2026-09-08": 120.0, "2026-09-09": 240.0}


def test_entries_for_day():
    from datetime import date as date_cls

    from custom_components.piyolog.feed import entries_for_day, parse_feed

    snapshot = parse_feed(payload(sample_records()))
    entries = entries_for_day(list(snapshot.records), UTC, date_cls(2026, 9, 9))
    # Newest first, only that day's records.
    assert [e["type"] for e in entries] == [
        "Pee",
        "Formula",
        "Sleep",
        "Poop",
        "Pee",
        "Formula",
        "Temperature",
        "Weight",
        "BreastFeeding",
        "WakeUp",
    ]
    wake = entries[9]
    assert wake["type"] == "WakeUp"
    # Slept 22:00 (Sep 8) -> 02:00 (Sep 9) = 240 minutes, paired across days.
    assert wake["duration_minutes"] == 240
    bf = entries[8]
    assert bf["summary"] == "左5分 右4分"
    # A day with no records is an empty list, not an error.
    assert entries_for_day(list(snapshot.records), UTC, date_cls(2026, 9, 1)) == []


def test_history_by_type():
    data = _aggregate()
    weight_history = data.history_by_type["Weight"]
    # Both the yesterday and today measurements, oldest first.
    assert [h["value"] for h in weight_history] == [6.25, 6.3]
    times = [h["time"] for h in weight_history]
    assert times == sorted(times)
    assert [h["value"] for h in data.history_by_type["Temperature"]] == [36.7]
    # Non-measurement types have no history.
    assert "Pee" not in data.history_by_type


def test_summarize_breast_feeding():
    snap = parse_feed(
        payload(
            [rec("bf", "2026-09-09T07:00:00.000Z", "BreastFeeding",
                 leftTime=300, rightTime=181, last="left")]
        )
    )
    assert summarize(snap.records[0]) == "左5分 右3分"
