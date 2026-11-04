"""Import feed history into Home Assistant long-term statistics.

The official data feed returns up to 28 days of records, but Home
Assistant's recorder only holds states from the moment the integration
was installed. To make the past visible in graphs, the aggregated feed
data is imported as long-term statistics:

- Body measurements are imported as statistics of their sensor entities
  (``async_import_statistics``, source ``recorder``). Only past days are
  imported; the recorder compiles today's buckets from live states.
- Per-day totals are imported as external statistics under
  ``piyolog:daily_*`` statistic ids (``async_add_external_statistics``).

Imports are idempotent (the same bucket overwrites itself) and are only
re-sent when the aggregated content changes.
"""

from __future__ import annotations

from datetime import timezone
import hashlib
import json
import logging
from typing import Any

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    async_import_statistics,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    TYPE_CHEST,
    TYPE_HEAD,
    TYPE_HEIGHT,
    TYPE_TEMPERATURE,
    TYPE_WEIGHT,
)
from .feed import AggregatedData

_LOGGER = logging.getLogger(__name__)

# (feed type, entity_id, unit_of_measurement, unit_class)
MEASUREMENTS: list[tuple[str, str, str, str]] = [
    (TYPE_WEIGHT, "sensor.piyolog_weight", "kg", "mass"),
    (TYPE_HEIGHT, "sensor.piyolog_height", "cm", "length"),
    (TYPE_TEMPERATURE, "sensor.piyolog_temperature", "°C", "temperature"),
    (TYPE_HEAD, "sensor.piyolog_head_circumference", "cm", "length"),
    (TYPE_CHEST, "sensor.piyolog_chest_circumference", "cm", "length"),
]

# stat key -> (unit_of_measurement, unit_class)
DAILY_SERIES: dict[str, tuple[str | None, str | None]] = {
    "breast_feeding_ml": ("mL", "volume"),
    "breast_feeding_count": (None, None),
    "breast_feeding_minutes": ("min", "time"),
    "formula_ml": ("mL", "volume"),
    "expressed_breast_milk_ml": ("mL", "volume"),
    "pumping_ml": ("mL", "volume"),
    "drink_ml": ("mL", "volume"),
    "pee_count": (None, None),
    "poop_count": (None, None),
    "sleep_minutes": ("min", "time"),
}


def _fingerprint(data: AggregatedData) -> str:
    """Cheap content hash so unchanged data is not re-imported."""

    def default(obj: Any) -> str:
        return obj.isoformat() if hasattr(obj, "isoformat") else str(obj)

    payload = json.dumps(
        {"buckets": data.measurement_buckets, "daily": data.daily_totals},
        default=default,
        sort_keys=True,
    )
    return hashlib.sha1(payload.encode()).hexdigest()


def _hour_floor_utc(dt) -> Any:
    return dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def async_import_feed_statistics(
    hass: HomeAssistant, data: AggregatedData, state: dict[str, Any]
) -> None:
    """Import statistics for one config entry if the content changed.

    ``state`` is a per-entry mutable dict used to remember the last
    imported fingerprint. Failures are logged and swallowed: statistics
    must never break the regular data update.
    """
    if "recorder" not in hass.config.components:
        return
    fingerprint = _fingerprint(data)
    if state.get("fingerprint") == fingerprint:
        return
    try:
        for feed_type, entity_id, unit, unit_class in MEASUREMENTS:
            buckets = data.measurement_buckets.get(feed_type)
            if not buckets:
                continue
            metadata: StatisticMetaData = {
                "mean_type": StatisticMeanType.ARITHMETIC,
                "has_sum": False,
                "name": None,
                "source": "recorder",
                "statistic_id": entity_id,
                "unit_class": unit_class,
                "unit_of_measurement": unit,
            }
            stats: list[StatisticData] = [
                {
                    "start": bucket["start"],
                    "mean": bucket["mean"],
                    "min": bucket["min"],
                    "max": bucket["max"],
                }
                for bucket in buckets
            ]
            async_import_statistics(hass, metadata, stats)
        for key, (unit, unit_class) in DAILY_SERIES.items():
            points = data.daily_totals.get(key)
            if not points:
                continue
            metadata = {
                "mean_type": StatisticMeanType.ARITHMETIC,
                "has_sum": False,
                "name": None,
                "source": DOMAIN,
                "statistic_id": f"{DOMAIN}:daily_{key}",
                "unit_class": unit_class,
                "unit_of_measurement": unit,
            }
            stats = [
                {"start": _hour_floor_utc(point["start"]), "mean": point["value"]}
                for point in points
            ]
            async_add_external_statistics(hass, metadata, stats)
    except HomeAssistantError as err:
        _LOGGER.warning("PiyoLog statistics import failed: %s", err)
        return
    state["fingerprint"] = fingerprint
    _LOGGER.debug("PiyoLog statistics imported (fingerprint %s)", fingerprint[:8])
