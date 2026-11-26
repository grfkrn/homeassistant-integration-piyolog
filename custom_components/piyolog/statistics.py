"""Import feed history into Home Assistant long-term statistics.

The official data feed returns up to 28 days of records, but Home
Assistant's recorder only holds states from the moment the integration
was installed. To make the past visible in graphs, the aggregated feed
data is imported as long-term statistics:

- Body measurements are imported as statistics of their sensor entities
  (``async_import_statistics``, source ``recorder``). The entity id is
  resolved from the entity registry by unique id, so renamed entities
  and the ``_2`` suffixes of additional config entries map to the right
  series. Only past days are imported; the recorder compiles today's
  buckets from live states.
- Per-day totals are imported as external statistics under
  entry-specific ``piyolog:daily_*_<entry id>`` statistic ids
  (``async_add_external_statistics``), so the series of several
  children never share one bucket.

Imports are idempotent (the same bucket overwrites itself) and are only
re-sent when the aggregated content of that series changes.
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
from homeassistant.helpers import entity_registry as er

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

# (feed type, sensor key, unit_of_measurement, unit_class)
# The sensor key is the suffix of the entity's unique id
# (``<entry_id>_<key>``); the entity id itself is resolved from the
# entity registry at import time.
MEASUREMENTS: list[tuple[str, str, str, str]] = [
    (TYPE_WEIGHT, "weight", "kg", "mass"),
    (TYPE_HEIGHT, "height", "cm", "length"),
    (TYPE_TEMPERATURE, "temperature", "°C", "temperature"),
    (TYPE_HEAD, "head_circumference", "cm", "length"),
    (TYPE_CHEST, "chest_circumference", "cm", "length"),
]

# stat key -> (unit_of_measurement, unit_class)
# NOTE: the recorder does not support unit_class "time" for imported
# statistics, so minute-based series use no unit class.
DAILY_SERIES: dict[str, tuple[str | None, str | None]] = {
    "breast_feeding_ml": ("mL", "volume"),
    "breast_feeding_count": (None, None),
    "breast_feeding_minutes": ("min", None),
    "formula_ml": ("mL", "volume"),
    "expressed_breast_milk_ml": ("mL", "volume"),
    "pumping_ml": ("mL", "volume"),
    "drink_ml": ("mL", "volume"),
    "pee_count": (None, None),
    "poop_count": (None, None),
    "sleep_minutes": ("min", None),
}


def _series_fingerprint(payload: Any) -> str:
    """Cheap content hash so unchanged series are not re-imported."""

    def default(obj: Any) -> str:
        return obj.isoformat() if hasattr(obj, "isoformat") else str(obj)

    return hashlib.sha1(
        json.dumps(payload, default=default, sort_keys=True).encode()
    ).hexdigest()


def _hour_floor_utc(dt) -> Any:
    return dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def async_import_feed_statistics(
    hass: HomeAssistant, data: AggregatedData, state: dict[str, Any], entry_id: str
) -> None:
    """Import statistics for one config entry if the content changed.

    ``state`` is a per-entry mutable dict used to remember the last
    imported fingerprint of each series. Failures are logged and
    swallowed: statistics must never break the regular data update.
    """
    if "recorder" not in hass.config.components:
        return
    entity_registry = er.async_get(hass)
    # Each series is imported independently: one bad series must not
    # block the others.
    for feed_type, key, unit, unit_class in MEASUREMENTS:
        buckets = data.measurement_buckets.get(feed_type)
        if not buckets:
            continue
        state_key = f"measurement:{key}"
        fingerprint = _series_fingerprint(buckets)
        if state.get(state_key) == fingerprint:
            continue
        # Resolve the real entity id from the unique id: additional
        # entries get _2-suffixed entity ids and users may rename them.
        entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{entry_id}_{key}"
        )
        if entity_id is None:
            # Entity not registered yet; retry on the next update
            # without marking this series as imported.
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
        try:
            async_import_statistics(hass, metadata, stats)
        except HomeAssistantError as err:
            _LOGGER.warning(
                "PiyoLog statistics import failed for %s: %s", entity_id, err
            )
            continue
        state[state_key] = fingerprint
    for key, (unit, unit_class) in DAILY_SERIES.items():
        points = data.daily_totals.get(key)
        if not points:
            continue
        state_key = f"daily:{key}"
        fingerprint = _series_fingerprint(points)
        if state.get(state_key) == fingerprint:
            continue
        # The entry id keeps the external series of several config
        # entries (one per child) apart.
        statistic_id = f"{DOMAIN}:daily_{key}_{entry_id.lower()}"
        metadata = {
            "mean_type": StatisticMeanType.ARITHMETIC,
            "has_sum": False,
            "name": None,
            "source": DOMAIN,
            "statistic_id": statistic_id,
            "unit_class": unit_class,
            "unit_of_measurement": unit,
        }
        stats = [
            {"start": _hour_floor_utc(point["start"]), "mean": point["value"]}
            for point in points
        ]
        try:
            async_add_external_statistics(hass, metadata, stats)
        except HomeAssistantError as err:
            _LOGGER.warning(
                "PiyoLog statistics import failed for %s: %s",
                statistic_id,
                err,
            )
            continue
        state[state_key] = fingerprint
    _LOGGER.debug("PiyoLog statistics import pass done for entry %s", entry_id[:8])
