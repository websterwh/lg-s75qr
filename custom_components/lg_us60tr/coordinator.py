from __future__ import annotations

import logging
import threading
from functools import partial
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    COMMAND_TIMEOUT,
    CONF_CHANNELS,
    CONF_CONNECT_TIMEOUT,
    CONF_FORCED_INPUT_SOURCE,
    CONF_LAST_INPUT_SOURCE,
    CONF_PER_CHANNEL_TIMEOUT,
    CONF_POWERED,
    CONNECT_TIMEOUT,
    DEFAULT_CHANNELS,
    DEFAULT_FORCED_INPUT_SOURCE,
    DOMAIN,
    PER_CHANNEL_TIMEOUT,
)
from .core import InputSource, SoundbarClient, SoundbarState, SoundMode
from .core.linux import LinuxRFCOMMTransport

_LOGGER = logging.getLogger(__name__)


class LGUS60TRCoordinator(DataUpdateCoordinator[SoundbarState]):
    """Run explicit soundbar operations in short, phone-safe SPP sessions."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=None,
            always_update=False,
        )
        self._entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self._io_lock = threading.Lock()
        channels_opt = entry.options.get(CONF_CHANNELS)
        if isinstance(channels_opt, str):
            channels = tuple(
                int(c.strip()) for c in channels_opt.split(",") if c.strip()
            )
        elif isinstance(channels_opt, (list, tuple)):
            channels = tuple(int(c) for c in channels_opt)
        else:
            channels = DEFAULT_CHANNELS

        self._connect_timeout = float(
            entry.options.get(CONF_CONNECT_TIMEOUT, CONNECT_TIMEOUT)
        )
        per_channel_timeout = float(
            entry.options.get(CONF_PER_CHANNEL_TIMEOUT, PER_CHANNEL_TIMEOUT)
        )

        self._client = SoundbarClient(
            LinuxRFCOMMTransport(
                self.address,
                channels,
                per_channel_timeout=per_channel_timeout,
            )
        )
        try:
            self._preferred_source = InputSource(entry.options[CONF_LAST_INPUT_SOURCE])
        except (KeyError, TypeError, ValueError):
            self._preferred_source = None
        stored_powered = entry.options.get(CONF_POWERED)
        self._powered = stored_powered if isinstance(stored_powered, bool) else None
        _LOGGER.debug(
            "Created on-demand coordinator for %s with RFCOMM channels %s (timeout %.1fs)",
            self.address,
            channels,
            self._connect_timeout,
        )

    @property
    def channel(self) -> int | None:
        """Return the active RFCOMM channel."""
        return self._client.channel

    @property
    def powered(self) -> bool | None:
        """Return the last observed or commanded power state."""
        return self._powered

    @property
    def preferred_source(self) -> InputSource | None:
        """Return the input restored after a command-driven wake."""
        return self._preferred_source

    @callback
    def async_initialize(self) -> None:
        """Initialize entities from persisted state without opening Bluetooth."""
        self.async_set_updated_data(SoundbarState(input_source=self._preferred_source))

    async def _async_update_data(self) -> SoundbarState:
        _LOGGER.debug("Refreshing soundbar state in an explicit SPP session")
        try:
            state = await self.hass.async_add_executor_job(
                self._refresh, self._preferred_source
            )
        except (OSError, TimeoutError) as error:
            _LOGGER.warning("Soundbar refresh failed: %s", error, exc_info=True)
            raise UpdateFailed(
                f"Unable to communicate with {self.address}: {error}"
            ) from error
        self._record_success(state, powered=True)
        return state

    def _refresh(self, previous_source: InputSource | None) -> SoundbarState:
        return self._run_command(None, previous_source)

    async def async_turn_on(self) -> None:
        await self._async_command(None)

    async def async_power_off(self) -> None:
        if self._powered is False:
            return
        await self._async_command("power_off")

    async def async_set_volume(self, volume: int) -> None:
        await self._async_command("set_volume", volume)

    async def async_set_input_source(self, source: InputSource | str) -> None:
        await self._async_command("set_input_source", source)

    async def async_set_sound_mode(self, mode: SoundMode | str) -> None:
        await self._async_command("set_sound_mode", mode)

    async def async_set_woofer_level(self, level: int) -> None:
        await self._async_command("set_woofer_level", level)

    async def async_set_center_level(self, level: int) -> None:
        await self._async_command("set_center_level", level)

    async def async_set_rear_level(self, level: int) -> None:
        await self._async_command("set_rear_level", level)

    async def async_set_night_mode(self, enabled: bool) -> None:
        await self._async_command("set_night_mode", enabled)
    async def async_set_mute(self, mute: bool) -> None:
        await self._async_command("set_mute", mute)
    async def async_set_overhead_level(self, level: int) -> None:
        await self._async_command("set_overhead_level", level)

    async def _async_command(self, method: str | None, *args: Any) -> None:
        operation = method or "turn_on"
        _LOGGER.debug(
            "Running soundbar operation %s with arguments %r", operation, args
        )
        restore_source = (
            None
            if method in {"set_input_source", "power_off"}
            else self._preferred_source
        )
        try:
            state = await self.hass.async_add_executor_job(
                partial(self._run_command, method, restore_source, *args)
            )
        except (OSError, TimeoutError) as error:
            _LOGGER.exception("Soundbar operation %s failed", operation)
            raise HomeAssistantError(
                f"Unable to send command to {self.address}: {error}"
            ) from error
        powered = method != "power_off"
        self._record_success(
            state,
            powered=powered,
            update_source=powered,
        )
        self.async_set_updated_data(state)
        _LOGGER.info("Soundbar operation %s completed", operation)

    def _run_command(
        self,
        method: str | None,
        previous_source: InputSource | None,
        *args: Any,
    ) -> SoundbarState:
        with self._io_lock:
            try:
                if self._client.state.connected:
                    self._client.query_state(timeout=COMMAND_TIMEOUT)
                else:
                    self._connect(previous_source)
                if method is not None:
                    command = getattr(self._client, method)
                    command(*args, timeout=COMMAND_TIMEOUT)
            finally:
                self._client.close()
            return self._client.state

    def _connect(self, previous_source: InputSource | None) -> SoundbarState:
        _LOGGER.info("Opening on-demand RFCOMM connection to %s", self.address)
        state = self._client.connect(timeout=self._connect_timeout)

        forced_opt = self._entry.options.get(
            CONF_FORCED_INPUT_SOURCE, DEFAULT_FORCED_INPUT_SOURCE
        )
        target_source: InputSource | None = None

        if forced_opt == "restore_previous":
            if (
                previous_source is not None
                and previous_source is not InputSource.BLUETOOTH
                and state.input_source is InputSource.BLUETOOTH
            ):
                target_source = previous_source
        elif forced_opt and forced_opt not in ("none", "disabled"):
            try:
                target_source = InputSource.from_name(forced_opt)
            except ValueError:
                target_source = None

        if target_source is not None and state.input_source != target_source:
            _LOGGER.info(
                "Soundbar connected (input: %s); forcing configured input %s",
                state.input_source.label if state.input_source else "unknown",
                target_source.label,
            )
            return self._client.set_input_source(
                target_source,
                timeout=COMMAND_TIMEOUT,
            )
        return state
    @callback
    def _record_success(
        self,
        state: SoundbarState,
        *,
        powered: bool,
        update_source: bool = True,
    ) -> None:
        self._powered = powered
        if update_source and state.input_source is not None:
            self._preferred_source = state.input_source

        options = dict(self._entry.options)
        options[CONF_POWERED] = powered
        if self._preferred_source is not None:
            options[CONF_LAST_INPUT_SOURCE] = int(self._preferred_source)
        if options != dict(self._entry.options):
            self.hass.config_entries.async_update_entry(
                self._entry,
                options=options,
            )

    async def async_shutdown(self) -> None:
        _LOGGER.info("Shutting down LG US60TR coordinator")
        await self.hass.async_add_executor_job(self._close)

    def _close(self) -> None:
        with self._io_lock:
            self._client.close()


def probe_soundbar(
    address: str,
    channels: tuple[int, ...] = DEFAULT_CHANNELS,
    timeout: float = CONNECT_TIMEOUT,
    per_channel_timeout: float = PER_CHANNEL_TIMEOUT,
) -> SoundbarState:
    """Connect once during config flow validation and return the initial state."""
    _LOGGER.info("Probing soundbar %s over RFCOMM channels %s", address, channels)
    client = SoundbarClient(
        LinuxRFCOMMTransport(
            address,
            channels,
            per_channel_timeout=per_channel_timeout,
        )
    )
    try:
        state = client.connect(timeout=timeout, per_channel_timeout=per_channel_timeout)
        _LOGGER.info(
            "Soundbar %s RFCOMM probe succeeded on channel %s",
            address,
            client.channel,
        )
        return state
    finally:
        client.close()
