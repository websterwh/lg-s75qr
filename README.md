# LG S75QR Soundbar Bluetooth Control

Local control of the **LG S75QR Soundbar** over Bluetooth Classic RFCOMM/SPP. The repository contains a Home Assistant custom integration and the platform-neutral Python protocol client it uses.

The implementation is cloud-free: Home Assistant talks directly to the paired soundbar. It does not require the LG ThinQ app after initial Bluetooth pairing.

## Status

Tested and verified on the **LG S75QR(F5)** (40-step volume range, up-firing overhead speakers, hardware mute, and eARC / Dolby Audio active prefix `0xC4`).

Verified controls:

- Input function: Bluetooth, USB, HDMI In, and Optical / HDMI ARC / eARC
- Volume: Dynamic scaling (0–100 or 0–40 depending on soundbar model)
- Mute: Hardware mute toggle
- Sound mode: AI Sound Pro, Standard, Cinema, Clear Voice Pro, Sports, Music, Game, and Bass Blast
- Woofer level: -15…6
- Center level: -6…6
- Rear level: -6…6
- Overhead level: -6…6 (Atmos / up-firing speakers)
- Power-on / wake forced input source: configurable in options flow and via select entity
- Audio format stream detection (e.g. `DOLBY AUDIO`, `NO SIGNAL`)
- Night mode
- State refresh, pushed state changes, reconnect, availability, and privacy-safe diagnostics
- Automatic restoration of the last known input when a reconnect wakes the soundbar on Bluetooth

There is no separately captured HDMI-CEC function. The fourth function exposed by the soundbar and ThinQ is **Optical / HDMI ARC**.

## How it works

```mermaid
flowchart LR
    HA[Home Assistant entities] --> C[DataUpdateCoordinator]
    C --> P[Soundbar protocol client]
    P --> R[Linux RFCOMM socket]
    R --> S[LG soundbar SPP channel 1]
```

The control transport is Bluetooth Classic SPP, not BLE. The packet protocol and every exposed command are capture-backed; guessed power, reset, pairing, firmware, demo, and factory commands are intentionally absent.

## Requirements

- Home Assistant 2026.7.4 or newer
- A Linux Home Assistant host with a Bluetooth adapter that supports Classic RFCOMM (e.g. onboard Bluetooth or a USB dongle passed through to the VM)
- The soundbar paired and trusted by the host's BlueZ stack
- The soundbar's Bluetooth address

> **Note on ESPHome Bluetooth Proxies:** ESPHome Bluetooth Proxies only support Bluetooth Low Energy (BLE). LG soundbars use BLE strictly as a non-connectable discovery beacon and require Bluetooth Classic RFCOMM / SPP for all control. Therefore, an ESPHome Bluetooth proxy cannot be used for this integration; a local Bluetooth adapter on the Home Assistant host is required. Adding a USB Bluetooth adapter does not interfere with ESPHome proxies (Home Assistant supports both concurrently).

The integration tries RFCOMM channel 1 first, then channel 2 as a fallback, with an independent per-channel timeout to prevent hanging fallbacks. Channel order, total timeout, and per-channel timeout are fully configurable in the integration options. Only one ThinQ/SPP controller should be active during setup.

## Install with HACS

1. In HACS, open **Integrations**, select the menu, then **Custom repositories**.
2. Add `https://github.com/websterwh/lg-us60tr` with category **Integration**.
3. Install **LG S75QR Soundbar** and restart Home Assistant.
4. Pair the soundbar with the Home Assistant host as described below.
5. Open **Settings → Devices & services → Add integration**, search for **LG S75QR Soundbar**, and enter the Bluetooth address.

The repository layout and `hacs.json` are ready for HACS custom-repository installation. No Python package is downloaded at runtime; the complete protocol client and Linux transport are bundled under `custom_components/lg_us60tr/core`.

## Pair the soundbar with Home Assistant OS

Pairing is a one-time host operation. In the Terminal & SSH app, run:

```text
bluetoothctl
power on
agent NoInputNoOutput
default-agent
scan on
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
scan off
quit
```

> **Important Note for Home Assistant OS Users:**
> The official **Terminal & SSH** add-on runs in an isolated container that does not have kernel `AF_BLUETOOTH` socket privileges (`errno 97: Address family not supported by protocol`). Running Python scripts or standalone CLI commands directly inside Terminal & SSH will fail. Pair via `bluetoothctl` as shown above, then let the Home Assistant Core integration manage the connection. Monitor logs with `ha core logs --follow`.

Put the soundbar in Bluetooth pairing mode only for this initial pairing. Restore the desired HDMI/ARC input afterwards. Do not run `bluetoothctl connect` for normal use: the integration opens only its RFCOMM control channel and does not need an explicit A2DP connection.

List the saved address later with:

```sh
bluetoothctl devices Paired
```

## Home Assistant entities

| Entity | Capability |
|---|---|
| Media player | Source, volume, mute, sound mode, availability |
| Woofer level | Integer slider, -15…6 |
| Center level | Integer slider, -6…6 |
| Rear level | Integer slider, -6…6 |
| Overhead level | Integer slider, -6…6 (up-firing height speakers) |
| Night mode | On/off switch |
| Forced input | Select entity to configure or force power-on/wake input |
| Audio format | Sensor reporting audio stream format (e.g. `DOLBY AUDIO`) |
| RFCOMM channel | Sensor reporting active Bluetooth RFCOMM channel (`1` or `2`) |

All blocking Bluetooth work runs in Home Assistant's executor, while access to the single SPP session is serialized by the coordinator.

## Manual installation

Copy `custom_components/lg_us60tr` into the Home Assistant configuration directory:

```text
/config/custom_components/lg_us60tr
```

Restart Home Assistant, then add the integration through **Settings → Devices & services**.

## Standalone Python client

Python 3.11 or newer is required. Linux uses native `AF_BLUETOOTH` sockets; macOS installs PyObjC and uses `IOBluetooth`.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

lg-us60tr --address XX:XX:XX:XX:XX:XX state
lg-us60tr --address XX:XX:XX:XX:XX:XX volume 20
lg-us60tr --address XX:XX:XX:XX:XX:XX function "HDMI In"
lg-us60tr --address XX:XX:XX:XX:XX:XX mode Cinema
lg-us60tr --address XX:XX:XX:XX:XX:XX woofer 2
lg-us60tr --address XX:XX:XX:XX:XX:XX overhead 2
lg-us60tr --address XX:XX:XX:XX:XX:XX night off
lg-us60tr --address XX:XX:XX:XX:XX:XX mute on
lg-us60tr --address XX:XX:XX:XX:XX:XX mute off
```

On macOS, opening RFCOMM was observed to bring up A2DP as well, which can switch the soundbar to Bluetooth. Home Assistant/Linux is the recommended deployment target when preserving the current source matters.

## Documentation

- [Current status](docs/STATUS.md)
- [Protocol reference](docs/PROTOCOL.md)
- [Deployment and troubleshooting](docs/TROUBLESHOOTING.md)
- [Research evidence and capture index](research/README.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Safety and scope

The Home Assistant integration exposes only commands confirmed by ThinQ captures. The standalone CLI has a `raw` subcommand for protocol research; it is deliberately not exposed through Home Assistant or Assist. Do not send unknown commands to production hardware.

## License

[MIT](LICENSE)
