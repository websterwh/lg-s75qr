from __future__ import annotations

from typing import ClassVar, override

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from . import LGUS60TRConfigEntry
from .const import (
    CONF_FORCED_INPUT_SOURCE,
    DEFAULT_FORCED_INPUT_SOURCE,
    FORCED_INPUT_SOURCE_OPTIONS,
)
from .core import InputSource, SoundMode
from .entity import LGUS60TREntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LGUS60TRConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the soundbar select entities."""
    async_add_entities(
        [
            LGUS60TRInputSourceSelect(entry),
            LGUS60TRSoundModeSelect(entry),
            LGUS60TRForcedInputSelect(entry),
        ]
    )


class LGUS60TRInputSourceSelect(LGUS60TREntity, SelectEntity):
    """Allow switching the soundbar's active audio input function."""

    _attr_translation_key = "input_source"
    _attr_icon = "mdi:import"
    _attr_options: ClassVar[list[str]] = [source.label for source in InputSource]

    def __init__(self, entry: LGUS60TRConfigEntry) -> None:
        super().__init__(entry, "input_source")

    @property
    @override
    def current_option(self) -> str | None:
        if self.coordinator.data and self.coordinator.data.input_source:
            return self.coordinator.data.input_source.label
        return None

    @override
    async def async_select_option(self, option: str) -> None:
        """Switch the soundbar input function immediately."""
        target = InputSource.from_name(option)
        await self.coordinator.async_set_input_source(target)


class LGUS60TRSoundModeSelect(LGUS60TREntity, SelectEntity):
    """Allow changing the active sound effect mode."""

    _attr_translation_key = "sound_mode"
    _attr_icon = "mdi:equalizer"
    _attr_options: ClassVar[list[str]] = ["TV Sound Mode Share"] + [
        mode.label for mode in SoundMode
    ]

    def __init__(self, entry: LGUS60TRConfigEntry) -> None:
        super().__init__(entry, "sound_mode")

    @property
    @override
    def current_option(self) -> str | None:
        if self.coordinator.data:
            if self.coordinator.data.tv_mode_control:
                return "TV Sound Mode Share"
            if self.coordinator.data.sound_mode:
                return self.coordinator.data.sound_mode.label
        return None

    @override
    async def async_select_option(self, option: str) -> None:
        """Switch the sound mode immediately."""
        if self.coordinator.data and self.coordinator.data.tv_mode_control:
            raise HomeAssistantError(
                "Cannot change sound mode: Soundbar is in TV Sound Mode Share / Mode Control "
                "(sound mode is controlled by the TV). Switch sound mode on your TV, or disable "
                "'TV Sound Mode Share' in your TV audio settings to allow soundbar mode control."
            )
        if option == "TV Sound Mode Share":
            return
        target = SoundMode.from_name(option)
        await self.coordinator.async_set_sound_mode(target)


class LGUS60TRForcedInputSelect(LGUS60TREntity, SelectEntity):
    """Allow configuring the power-on / wake forced input setting."""

    _attr_translation_key = "forced_input_source"
    _attr_icon = "mdi:cog-transfer"
    _attr_entity_category = EntityCategory.CONFIG
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
        """Change the forced input option and persist it."""
        options = dict(self.coordinator.config_entry.options)
        options[CONF_FORCED_INPUT_SOURCE] = option
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry,
            options=options,
        )
        self.async_write_ha_state()

        if option not in ("restore_previous", "none"):
            try:
                target_source = InputSource.from_name(option)
                await self.coordinator.async_set_input_source(target_source)
            except ValueError:
                pass
