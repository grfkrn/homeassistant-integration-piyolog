"""Tests for the long-term statistics import."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.piyolog.const import DOMAIN, TYPE_WEIGHT
from custom_components.piyolog.feed import AggregatedData
from custom_components.piyolog.statistics import async_import_feed_statistics

# Uppercase on purpose: external statistic ids must use it lowercased.
ENTRY_ID = "01TESTENTRYIDABC"


def _data() -> AggregatedData:
    start = datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc)
    return AggregatedData(
        measurement_buckets={
            TYPE_WEIGHT: [{"start": start, "mean": 6.0, "min": 5.9, "max": 6.1}]
        },
        daily_totals={"sleep_minutes": [{"start": start, "value": 600.0}]},
    )


@pytest.fixture
def mock_imports():
    """Capture the recorder import calls instead of executing them."""
    with (
        patch(
            "custom_components.piyolog.statistics.async_import_statistics"
        ) as import_stats,
        patch(
            "custom_components.piyolog.statistics.async_add_external_statistics"
        ) as add_external,
    ):
        yield import_stats, add_external


async def test_statistics_use_resolved_entity_and_entry_scoped_ids(
    hass: HomeAssistant, mock_imports
) -> None:
    """Measurements follow the registry; daily ids carry the entry id."""
    import_stats, add_external = mock_imports
    hass.config.components.add("recorder")
    entry = MockConfigEntry(domain=DOMAIN, entry_id=ENTRY_ID)
    entry.add_to_hass(hass)
    # A second child's weight sensor: same unique id pattern, _2 entity id.
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{ENTRY_ID}_weight",
        config_entry=entry,
        suggested_object_id="piyolog_weight_2",
    )
    state: dict = {}
    async_import_feed_statistics(hass, _data(), state, ENTRY_ID)

    assert import_stats.call_count == 1
    metadata = import_stats.call_args[0][1]
    assert metadata["statistic_id"] == "sensor.piyolog_weight_2"

    assert add_external.call_count == 1
    ext_metadata = add_external.call_args[0][1]
    assert (
        ext_metadata["statistic_id"]
        == f"piyolog:daily_sleep_minutes_{ENTRY_ID.lower()}"
    )

    # Unchanged content is not re-imported.
    async_import_feed_statistics(hass, _data(), state, ENTRY_ID)
    assert import_stats.call_count == 1
    assert add_external.call_count == 1


async def test_measurement_skipped_until_entity_registered(
    hass: HomeAssistant, mock_imports
) -> None:
    """An unregistered measurement entity is skipped, then retried."""
    import_stats, add_external = mock_imports
    hass.config.components.add("recorder")
    entry = MockConfigEntry(domain=DOMAIN, entry_id=ENTRY_ID)
    entry.add_to_hass(hass)
    state: dict = {}

    async_import_feed_statistics(hass, _data(), state, ENTRY_ID)
    assert import_stats.call_count == 0
    # Daily series do not depend on the registry and still import.
    assert add_external.call_count == 1

    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{ENTRY_ID}_weight",
        config_entry=entry,
        suggested_object_id="piyolog_weight",
    )
    async_import_feed_statistics(hass, _data(), state, ENTRY_ID)
    assert import_stats.call_count == 1
    assert import_stats.call_args[0][1]["statistic_id"] == "sensor.piyolog_weight"
    # The daily series was already imported and is not sent again.
    assert add_external.call_count == 1
