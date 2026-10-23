from __future__ import annotations

from typing import ClassVar, override

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LGUS60TRConfigEntry
from .const import (
    CONF_FORCED_INPUT_SOURCE,
    DEFAULT_FORCED_INPUT_SOURCE,
    FORCED_INPUT_SOURCE_OPTIONS,
)
from .core import InputSource
from .entity import LGUS60TREntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LGUS60TRConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the soundbar select entity."""
    async_add_entities([LGUS60TRForcedInputSelect(entry)])


class LGUS60TRForcedInputSelect(LGUS60TREntity, SelectEntity):
    """Allow configuring the forced power-on / wake input source."""

    _attr_translation_key = "forced_input_source"
    _attr_icon = "mdi:import"
    _attr_options: ClassVar[list[str]] = list(FORCED_INPUT_SOURCE_OPTIONS)

    def __init__(self, entry: LGUS60TRConfigEntry) -> None:
        super().__init__(entry, "forced_input_source")

    @property
    @override
    def current_option(self) -> str:
        return self.coordinator.config_entry.options.get(
            CONF_FORCED_INPUT_SOURCE, DEFAULT_FORCED_INPUT_SOURCE
        )

    @override
    async def async_select_option(self, option: str) -> None:
        """Change the forced input option and apply it immediately."""
        options = dict(self.coordinator.config_entry.options)
        options[CONF_FORCED_INPUT_SOURCE] = option
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry,
            options=options,
        )
        self.async_write_ha_state()

        # If a concrete input is chosen (not "restore_previous" or "none"), apply it to soundbar
        if option not in ("restore_previous", "none"):
            try:
                target_source = InputSource.from_name(option)
                await self.coordinator.async_set_input_source(target_source)
            except ValueError:
                pass
