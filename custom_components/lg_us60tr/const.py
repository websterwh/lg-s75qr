from __future__ import annotations

DOMAIN = "lg_us60tr"
DEFAULT_CHANNELS = (1, 2)
DEFAULT_NAME = "LG S75QR Soundbar"
MANUFACTURER = "LG Electronics"
MODEL = "S75QR"
CONNECT_TIMEOUT = 12.0
PER_CHANNEL_TIMEOUT = 5.0
CONF_CHANNELS = "channels"
CONF_CONNECT_TIMEOUT = "connect_timeout"
CONF_PER_CHANNEL_TIMEOUT = "per_channel_timeout"
CONF_FORCED_INPUT_SOURCE = "forced_input_source"
DEFAULT_FORCED_INPUT_SOURCE = "restore_previous"
FORCED_INPUT_SOURCE_OPTIONS = [
    "restore_previous",
    "Optical / HDMI ARC",
    "HDMI In",
    "Bluetooth",
    "USB",
    "none",
]
COMMAND_TIMEOUT = 3.0
CONF_LAST_INPUT_SOURCE = "last_input_source"
CONF_POWERED = "powered"
