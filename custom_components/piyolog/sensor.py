"""Sensor platform for the PiyoLog integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_NAME,
    UnitOfLength,
    UnitOfMass,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PiyologConfigEntry
from .const import (
    TYPE_BATH,
    TYPE_BREAST_FEEDING,
    TYPE_CHEST,
    TYPE_COUGH,
    TYPE_DRINK,
    TYPE_EXPRESSED_BREAST_MILK,
    TYPE_FOOT,
    TYPE_FORMULA,
    TYPE_HEAD,
    TYPE_HEIGHT,
    TYPE_HOSPITAL,
    TYPE_INJURY,
    TYPE_MEDICINE,
    TYPE_MEAL,
    TYPE_MEMO,
    TYPE_MILESTONE,
    TYPE_OTHER,
    TYPE_PEE,
    TYPE_POOP,
    TYPE_PUMPING,
    TYPE_RASH,
    TYPE_SLEEP,
    TYPE_SNACK,
    TYPE_SOLID,
    TYPE_TEMPERATURE,
    TYPE_VACCINE,
    TYPE_VOMITING,
    TYPE_WAKE_UP,
    TYPE_WALKING,
    TYPE_WEIGHT,
)
from .coordinator import PiyologCoordinator
from .feed import AggregatedData, Record


@dataclass(frozen=True, kw_only=True)
class PiyologSensorDescription(SensorEntityDescription):
    """Sensor description with a value getter on AggregatedData."""

    value_fn: Callable[[AggregatedData], Any] | None = None


class PiyologEntity(CoordinatorEntity[PiyologCoordinator]):
    """Base entity bound to one config entry (one child)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PiyologCoordinator,
        entry: PiyologConfigEntry,
        key: str,
        platform_domain: str = "sensor",
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        # Force entity ids to piyolog_* regardless of the device label.
        self.entity_id = f"{platform_domain}.piyolog_{key}"
        self._attr_device_info = {
            "identifiers": {("piyolog", entry.entry_id)},
            "name": entry.data.get(CONF_NAME) or "PiyoLog",
            "manufacturer": "PiyoLog",
            "model": "Data Feed",
        }


# ---------------------------------------------------------------------------
# Last-event sensors (state = datetime of the most recent record of a type)
# ---------------------------------------------------------------------------

LAST_EVENT_TYPES: list[tuple[str, str, str]] = [
    # (key suffix, feed type, icon)
    ("last_breast_feeding", TYPE_BREAST_FEEDING, "mdi:mother-nurse"),
    ("last_formula", TYPE_FORMULA, "mdi:baby-bottle-outline"),
    ("last_expressed_breast_milk", TYPE_EXPRESSED_BREAST_MILK, "mdi:beaker-outline"),
    ("last_pumping", TYPE_PUMPING, "mdi:beaker-plus-outline"),
    ("last_sleep", TYPE_SLEEP, "mdi:sleep"),
    ("last_wake_up", TYPE_WAKE_UP, "mdi:alarm"),
    ("last_pee", TYPE_PEE, "mdi:toilet"),
    ("last_poop", TYPE_POOP, "mdi:emoticon-poop"),
    ("last_drink", TYPE_DRINK, "mdi:cup-water"),
    ("last_solid", TYPE_SOLID, "mdi:food-apple-outline"),
    ("last_snack", TYPE_SNACK, "mdi:cookie"),
    ("last_meal", TYPE_MEAL, "mdi:food"),
    ("last_bath", TYPE_BATH, "mdi:bathtub-outline"),
    ("last_medicine", TYPE_MEDICINE, "mdi:pill"),
    ("last_hospital", TYPE_HOSPITAL, "mdi:hospital-box-outline"),
    ("last_walking", TYPE_WALKING, "mdi:walk"),
    ("last_vaccine", TYPE_VACCINE, "mdi:needle"),
    ("last_milestone", TYPE_MILESTONE, "mdi:star"),
    ("last_cough", TYPE_COUGH, "mdi:emoticon-sick-outline"),
    ("last_vomiting", TYPE_VOMITING, "mdi:emoticon-sick"),
    ("last_rash", TYPE_RASH, "mdi:bandage"),
    ("last_injury", TYPE_INJURY, "mdi:bandage"),
    ("last_memo", TYPE_MEMO, "mdi:note-outline"),
    ("last_other", TYPE_OTHER, "mdi:dots-horizontal"),
]


def _last_event_attrs(data: AggregatedData, record: Record) -> dict[str, Any]:
    attrs: dict[str, Any] = {"count_today": data.today_count(record.type)}
    num = record.numeric_value()
    if num is not None and record.value is not None:
        attrs["value"] = num
        if record.value.get("unit"):
            attrs["unit"] = record.value["unit"]
    if record.type == TYPE_BREAST_FEEDING:
        left = record.raw.get("leftTime")
        right = record.raw.get("rightTime")
        if isinstance(left, (int, float)):
            attrs["left_minutes"] = round(left / 60)
        if isinstance(right, (int, float)):
            attrs["right_minutes"] = round(right / 60)
        if record.raw.get("last"):
            attrs["last_side"] = record.raw["last"]
    if record.type == TYPE_POOP:
        details = record.raw.get("details")
        if isinstance(details, dict):
            for name in ("amount", "hardness", "color"):
                if details.get(name):
                    attrs[name] = details[name]
    if record.memo:
        attrs["memo"] = record.memo
    return attrs


class PiyologLastEventSensor(PiyologEntity, SensorEntity):
    """Most recent record of one type, as a timestamp sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: PiyologCoordinator,
        entry: PiyologConfigEntry,
        key: str,
        feed_type: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, entry, key)
        self._feed_type = feed_type
        self._attr_icon = icon
        self._attr_translation_key = key

    @property
    def native_value(self) -> datetime | None:
        record = self.coordinator.data.last(self._feed_type)
        return record.dt if record else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        record = self.coordinator.data.last(self._feed_type)
        if record is None:
            return {"count_today": self.coordinator.data.today_count(self._feed_type)}
        return _last_event_attrs(self.coordinator.data, record)


class PiyologLastCustomSensor(PiyologEntity, SensorEntity):
    """Most recent custom record (Custom1..Custom10 aggregated)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:shape-outline"

    def __init__(
        self, coordinator: PiyologCoordinator, entry: PiyologConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "last_custom")
        self._attr_translation_key = "last_custom"

    def _latest_custom(self) -> Record | None:
        latest: Record | None = None
        for record_type, record in self.coordinator.data.last_by_type.items():
            if record_type.startswith("Custom"):
                if latest is None or record.dt > latest.dt:
                    latest = record
        return latest

    @property
    def native_value(self) -> datetime | None:
        record = self._latest_custom()
        return record.dt if record else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        record = self._latest_custom()
        if record is None:
            return None
        attrs: dict[str, Any] = {"custom_type": record.type}
        if record.memo:
            attrs["memo"] = record.memo
        return attrs


# ---------------------------------------------------------------------------
# Body measurement sensors (state = latest measured value)
# ---------------------------------------------------------------------------

BODY_SENSORS: list[PiyologSensorDescription] = [
    PiyologSensorDescription(
        key="weight",
        translation_key="weight",
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        value_fn=lambda d: (r.numeric_value() if (r := d.last(TYPE_WEIGHT)) else None),
    ),
    PiyologSensorDescription(
        key="height",
        translation_key="height",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        value_fn=lambda d: (r.numeric_value() if (r := d.last(TYPE_HEIGHT)) else None),
    ),
    PiyologSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: (
            r.numeric_value() if (r := d.last(TYPE_TEMPERATURE)) else None
        ),
    ),
    PiyologSensorDescription(
        key="head_circumference",
        translation_key="head_circumference",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        value_fn=lambda d: (r.numeric_value() if (r := d.last(TYPE_HEAD)) else None),
    ),
    PiyologSensorDescription(
        key="chest_circumference",
        translation_key="chest_circumference",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        value_fn=lambda d: (r.numeric_value() if (r := d.last(TYPE_CHEST)) else None),
    ),
]

BODY_TYPES = {
    "weight": TYPE_WEIGHT,
    "height": TYPE_HEIGHT,
    "temperature": TYPE_TEMPERATURE,
    "head_circumference": TYPE_HEAD,
    "chest_circumference": TYPE_CHEST,
}


class PiyologBodySensor(PiyologEntity, SensorEntity):
    """Latest body measurement value, with the measurement time as attribute."""

    entity_description: PiyologSensorDescription

    def __init__(
        self,
        coordinator: PiyologCoordinator,
        entry: PiyologConfigEntry,
        description: PiyologSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        assert self.entity_description.value_fn is not None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        record = self.coordinator.data.last(BODY_TYPES[self._key])
        if record is None:
            return None
        return {
            "measured_at": record.dt.isoformat(),
            # All measurements in the feed window (oldest first), so
            # dashboard charts can show data from before the integration
            # was installed (HA's recorder has no older states).
            "history": self.coordinator.data.history_by_type.get(
                BODY_TYPES[self._key], []
            ),
        }


class PiyologFootSizeSensor(PiyologEntity, SensorEntity):
    """Latest foot size; state is the left value when both sides exist."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_translation_key = "foot_size"
    _attr_icon = "mdi:shoe-print"

    def __init__(
        self, coordinator: PiyologCoordinator, entry: PiyologConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "foot_size")

    @property
    def native_value(self) -> float | None:
        record = self.coordinator.data.last(TYPE_FOOT)
        if record is None or not record.value:
            return None
        left = record.value.get("left")
        right = record.value.get("right")
        chosen = left if isinstance(left, (int, float)) else right
        return float(chosen) if isinstance(chosen, (int, float)) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        record = self.coordinator.data.last(TYPE_FOOT)
        if record is None or not record.value:
            return None
        attrs: dict[str, Any] = {"measured_at": record.dt.isoformat()}
        for side in ("left", "right"):
            val = record.value.get(side)
            if isinstance(val, (int, float)):
                attrs[side] = float(val)
        return attrs


# ---------------------------------------------------------------------------
# Today's aggregate sensors
# ---------------------------------------------------------------------------

TODAY_SENSORS: list[PiyologSensorDescription] = [
    PiyologSensorDescription(
        key="today_breast_feeding_count",
        translation_key="today_breast_feeding_count",
        icon="mdi:mother-nurse",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.today_count(TYPE_BREAST_FEEDING),
    ),
    PiyologSensorDescription(
        key="today_breast_feeding_duration",
        translation_key="today_breast_feeding_duration",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: round(d.today_breast_feeding_duration_seconds / 60, 1),
    ),
    PiyologSensorDescription(
        key="today_breast_feeding_total",
        translation_key="today_breast_feeding_total",
        icon="mdi:mother-nurse",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.today_breast_feeding_ml,
    ),
    PiyologSensorDescription(
        key="today_formula_total",
        translation_key="today_formula_total",
        icon="mdi:baby-bottle-outline",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.today_formula_ml,
    ),
    PiyologSensorDescription(
        key="today_expressed_breast_milk_total",
        translation_key="today_expressed_breast_milk_total",
        icon="mdi:beaker-outline",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.today_expressed_ml,
    ),
    PiyologSensorDescription(
        key="today_pumping_total",
        translation_key="today_pumping_total",
        icon="mdi:beaker-plus-outline",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.today_pumping_ml,
    ),
    PiyologSensorDescription(
        key="today_drink_total",
        translation_key="today_drink_total",
        icon="mdi:cup-water",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.today_drink_ml,
    ),
    PiyologSensorDescription(
        key="today_pee_count",
        translation_key="today_pee_count",
        icon="mdi:toilet",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.today_count(TYPE_PEE),
    ),
    PiyologSensorDescription(
        key="today_poop_count",
        translation_key="today_poop_count",
        icon="mdi:emoticon-poop",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.today_count(TYPE_POOP),
    ),
    PiyologSensorDescription(
        key="today_sleep_total",
        translation_key="today_sleep_total",
        icon="mdi:sleep",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: round(d.today_sleep_seconds / 60, 1),
    ),
]


class PiyologTodaySensor(PiyologEntity, SensorEntity):
    """One of today's aggregate values."""

    entity_description: PiyologSensorDescription

    def __init__(
        self,
        coordinator: PiyologCoordinator,
        entry: PiyologConfigEntry,
        description: PiyologSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        assert self.entity_description.value_fn is not None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._key == "today_formula_total":
            return {"count_today": self.coordinator.data.today_count(TYPE_FORMULA)}
        if self._key == "today_breast_feeding_total":
            data = self.coordinator.data
            return {
                "count_today": data.today_count(TYPE_BREAST_FEEDING),
                "measured_count": data.today_breast_feeding_measured_count,
            }
        return None


# ---------------------------------------------------------------------------
# Timeline / feed status
# ---------------------------------------------------------------------------


class PiyologTimelineSensor(PiyologEntity, SensorEntity):
    """Today's timeline; state is the newest record time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timeline-text-outline"
    _attr_translation_key = "timeline"

    def __init__(
        self, coordinator: PiyologCoordinator, entry: PiyologConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "timeline")

    @property
    def native_value(self) -> datetime | None:
        lasts = [
            r.dt for r in self.coordinator.data.last_by_type.values() if r is not None
        ]
        return max(lasts) if lasts else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        return {
            "records": data.timeline_today,
            "records_today": len(data.timeline_today),
            "generated_at": data.generated_at.isoformat()
            if data.generated_at
            else None,
        }


class PiyologRecentEventsSensor(PiyologEntity, SensorEntity):
    """Recent events across all days; state is the newest record time.

    Attributes hold the newest 100 records of the whole feed window
    (newest first), regardless of the calendar day.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:history"
    _attr_translation_key = "recent_events"

    def __init__(
        self, coordinator: PiyologCoordinator, entry: PiyologConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "recent_events")

    @property
    def native_value(self) -> datetime | None:
        lasts = [
            r.dt for r in self.coordinator.data.last_by_type.values() if r is not None
        ]
        return max(lasts) if lasts else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        return {
            "records": data.recent_events,
            "count": len(data.recent_events),
            "total_records": data.record_count,
            "generated_at": data.generated_at.isoformat()
            if data.generated_at
            else None,
        }


class PiyologLastUpdateSensor(PiyologEntity, SensorEntity):
    """When the feed data was generated."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:update"
    _attr_translation_key = "last_update"

    def __init__(
        self, coordinator: PiyologCoordinator, entry: PiyologConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "last_update")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data.generated_at

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        return {"record_count": self.coordinator.data.record_count}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PiyologConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PiyoLog sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for key, feed_type, icon in LAST_EVENT_TYPES:
        entities.append(
            PiyologLastEventSensor(coordinator, entry, key, feed_type, icon)
        )
    entities.append(PiyologLastCustomSensor(coordinator, entry))
    for description in BODY_SENSORS:
        entities.append(PiyologBodySensor(coordinator, entry, description))
    entities.append(PiyologFootSizeSensor(coordinator, entry))
    for description in TODAY_SENSORS:
        entities.append(PiyologTodaySensor(coordinator, entry, description))
    entities.append(PiyologTimelineSensor(coordinator, entry))
    entities.append(PiyologRecentEventsSensor(coordinator, entry))
    entities.append(PiyologLastUpdateSensor(coordinator, entry))
    async_add_entities(entities)
