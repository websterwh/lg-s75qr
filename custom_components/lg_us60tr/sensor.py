from __future__ import annotations

from dataclasses import dataclass
from typing import override

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LGUS60TRConfigEntry
from .entity import LGUS60TREntity


@dataclass(frozen=True, kw_only=True)
class LGUS60TRSensorDescription(SensorEntityDescription):
    """Describe an LG soundbar sensor entity."""


SENSOR_DESCRIPTIONS: tuple[LGUS60TRSensorDescription, ...] = (
    LGUS60TRSensorDescription(
        key="audio_format",
        translation_key="audio_format",
        icon="mdi:surround-sound",
    ),
    LGUS60TRSensorDescription(
        key="rfcomm_channel",
        translation_key="rfcomm_channel",
        icon="mdi:bluetooth-connect",
    ),
    LGUS60TRSensorDescription(
        key="sound_mode_control",
        translation_key="sound_mode_control",
        icon="mdi:television-speaker",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LGUS60TRConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up soundbar sensor entities."""
    async_add_entities(
        LGUS60TRSensor(entry, description) for description in SENSOR_DESCRIPTIONS
    )


class LGUS60TRSensor(LGUS60TREntity, SensorEntity):
    """Represent an LG soundbar sensor entity."""

    entity_description: LGUS60TRSensorDescription

    def __init__(
        self,
        entry: LGUS60TRConfigEntry,
        description: LGUS60TRSensorDescription,
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    @override
    def native_value(self) -> str | int | None:
        if self.entity_description.key == "audio_format":
            return self.coordinator.data.audio_format if self.coordinator.data else None
        if self.entity_description.key == "rfcomm_channel":
            return self.coordinator.channel
        if self.entity_description.key == "sound_mode_control":
            if not self.coordinator.data:
                return None
            return (
                "TV (TV Sound Mode Share)"
                if self.coordinator.data.tv_mode_control
                else "Soundbar"
            )
        return None
