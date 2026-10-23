from __future__ import annotations

import logging
import re
from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback

from .const import (
    CONF_CHANNELS,
    CONF_CONNECT_TIMEOUT,
    CONF_FORCED_INPUT_SOURCE,
    CONF_LAST_INPUT_SOURCE,
    CONF_PER_CHANNEL_TIMEOUT,
    CONF_PERSISTENT_CONNECTION,
    CONF_POLL_INTERVAL,
    CONF_POWERED,
    CONNECT_TIMEOUT,
    DEFAULT_CHANNELS,
    DEFAULT_FORCED_INPUT_SOURCE,
    DEFAULT_NAME,
    DOMAIN,
    DEFAULT_PERSISTENT_CONNECTION,
    DEFAULT_POLL_INTERVAL,
    FORCED_INPUT_SOURCE_OPTIONS,
    PER_CHANNEL_TIMEOUT,
)
from .coordinator import probe_soundbar

_LOGGER = logging.getLogger(__name__)


class LGUS60TRConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure an LG soundbar through the Home Assistant UI."""

    VERSION = 1

    @staticmethod
    @callback
    @override
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return LGUS60TROptionsFlowHandler()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}
        address: str | None = None
        channels_str = "1, 2"

        if user_input is not None:
            channels_input = user_input.get(CONF_CHANNELS, "1, 2")
            try:
                channels_tuple = tuple(
                    int(c.strip()) for c in str(channels_input).split(",") if c.strip()
                )
                if not channels_tuple:
                    raise ValueError
            except ValueError:
                channels_tuple = DEFAULT_CHANNELS
            channels_str = ", ".join(str(c) for c in channels_tuple)

            try:
                address = _normalize_address(user_input[CONF_ADDRESS])
            except ValueError:
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                _LOGGER.debug(
                    "Validating RFCOMM access to soundbar %s on channels %s",
                    address,
                    channels_tuple,
                )
                try:
                    state = await self.hass.async_add_executor_job(
                        probe_soundbar, address, channels_tuple
                    )
                except (OSError, TimeoutError) as error:
                    _LOGGER.warning(
                        "Unable to connect to soundbar %s: %s", address, error
                    )
                    errors["base"] = "cannot_connect"
                    description_placeholders["error_detail"] = str(error)
                except Exception as error:
                    _LOGGER.exception(
                        "Unexpected error while connecting to %s", address
                    )
                    errors["base"] = "unknown"
                    description_placeholders["error_detail"] = str(error)
                else:
                    _LOGGER.info("Validated soundbar %s during config flow", address)
                    await self.async_set_unique_id(address.replace(":", "").lower())
                    self._abort_if_unique_id_configured()
                    options: dict[str, Any] = {
                        CONF_POWERED: True,
                        CONF_CHANNELS: channels_str,
                        CONF_FORCED_INPUT_SOURCE: DEFAULT_FORCED_INPUT_SOURCE,
                    }
                    if state.input_source is not None:
                        options[CONF_LAST_INPUT_SOURCE] = int(state.input_source)
                    entry_title = DEFAULT_NAME
                    if state.model:
                        entry_title = f"LG {state.model} Soundbar"
                    return self.async_create_entry(
                        title=entry_title,
                        data={CONF_ADDRESS: address},
                        options=options,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ADDRESS,
                        default=address or (user_input or {}).get(CONF_ADDRESS, ""),
                    ): str,
                    vol.Optional(
                        CONF_CHANNELS,
                        default=channels_str,
                    ): str,
                }
            ),
            errors=errors,
            description_placeholders=description_placeholders,
        )


class LGUS60TROptionsFlowHandler(OptionsFlow):
    """Handle options for the LG soundbar integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the soundbar options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        channels_val = options.get(CONF_CHANNELS)
        if isinstance(channels_val, (list, tuple)):
            channels_str = ", ".join(str(c) for c in channels_val)
        else:
            channels_str = str(
                channels_val or ", ".join(str(c) for c in DEFAULT_CHANNELS)
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CHANNELS,
                        default=channels_str,
                    ): str,
                    vol.Optional(
                        CONF_CONNECT_TIMEOUT,
                        default=options.get(CONF_CONNECT_TIMEOUT, CONNECT_TIMEOUT),
                    ): vol.Coerce(float),
                    vol.Optional(
                        CONF_PER_CHANNEL_TIMEOUT,
                        default=options.get(
                            CONF_PER_CHANNEL_TIMEOUT, PER_CHANNEL_TIMEOUT
                        ),
                    ): vol.Coerce(float),
                    vol.Optional(
                        CONF_FORCED_INPUT_SOURCE,
                        default=options.get(
                            CONF_FORCED_INPUT_SOURCE, DEFAULT_FORCED_INPUT_SOURCE
                        ),
                    ): vol.In(FORCED_INPUT_SOURCE_OPTIONS),
                    vol.Optional(
                        CONF_PERSISTENT_CONNECTION,
                        default=options.get(
                            CONF_PERSISTENT_CONNECTION,
                            DEFAULT_PERSISTENT_CONNECTION,
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_POLL_INTERVAL,
                        default=options.get(
                            CONF_POLL_INTERVAL,
                            DEFAULT_POLL_INTERVAL,
                        ),
                    ): int,
                }
            ),
        )


def _normalize_address(value: str) -> str:
    compact = value.strip().replace(":", "").replace("-", "")
    if re.fullmatch(r"[0-9A-Fa-f]{12}", compact) is None:
        raise ValueError("invalid Bluetooth address")
    return ":".join(compact[index : index + 2] for index in range(0, 12, 2)).upper()
