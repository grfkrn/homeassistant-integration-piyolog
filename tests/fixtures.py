"""Fictional feed fixtures shared by tests.

All data below is invented for testing; it is not anyone's real records.
Times are on 2026-09-09 (UTC) unless noted.
"""

from __future__ import annotations

from typing import Any


def rec(event_id: str, dt: str, type_: str, **extra: Any) -> dict[str, Any]:
    return {"event_id": event_id, "datetime": dt, "type": type_, **extra}


def payload(
    records: list[dict[str, Any]], generated_at: str = "2026-09-09T12:00:00.000Z"
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "range": {"from": "2026-09-08T12:00:00.000Z", "to": generated_at},
        "records": records,
    }


def sample_records() -> list[dict[str, Any]]:
    """A small day of fictional records."""
    return [
        rec("w-yesterday", "2026-09-08T10:00:00.000Z", "Weight",
            value={"value": 6.25, "unit": "kg"}),
        rec("sleep-1", "2026-09-08T22:00:00.000Z", "Sleep"),
        rec("wake-1", "2026-09-09T02:00:00.000Z", "WakeUp"),
        rec("bf-1", "2026-09-09T07:00:00.000Z", "BreastFeeding",
            leftTime=300, rightTime=240, last="right"),
        rec("weight-1", "2026-09-09T08:00:00.000Z", "Weight",
            value={"value": 6.3, "unit": "kg"}),
        rec("temp-1", "2026-09-09T08:30:00.000Z", "Temperature",
            value={"value": 36.7, "unit": "celsius"}),
        rec("formula-1", "2026-09-09T09:00:00.000Z", "Formula",
            value={"value": 120, "unit": "ml"}),
        rec("pee-1", "2026-09-09T09:30:00.000Z", "Pee"),
        rec("poop-1", "2026-09-09T09:45:00.000Z", "Poop",
            details={"amount": "normal", "hardness": "soft", "color": "yellow"}),
        rec("sleep-2", "2026-09-09T10:00:00.000Z", "Sleep"),
        rec("formula-2", "2026-09-09T11:00:00.000Z", "Formula"),  # no value entered
        rec("pee-2", "2026-09-09T11:30:00.000Z", "Pee"),
    ]
