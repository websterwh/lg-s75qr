# Deployment and troubleshooting

## Installation checklist

1. Install the repository through HACS or copy `custom_components/lg_us60tr` manually.
2. Restart Home Assistant.
3. Pair and trust the soundbar in the host's BlueZ database.
4. Restore the soundbar to the desired HDMI/ARC input after initial pairing.
5. Add **LG S75QR Soundbar** from **Settings → Devices & services** using its Bluetooth address.

The config flow performs a real RFCOMM probe. A successful form submission therefore proves that pairing, channel access, protocol handshake, and initial state retrieval all worked at that moment.

## Pairing on Home Assistant OS

Use the official Terminal & SSH app:

```text
bluetoothctl
power on
agent NoInputNoOutput
default-agent
scan on
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
scan off
devices Paired
quit
```

Initial pairing normally requires the soundbar's Bluetooth pairing function. Normal control does not. Avoid a later `bluetoothctl connect`: it may request audio profiles in addition to SPP. Let the integration open its RFCOMM socket directly.

## `cannot_connect` during setup

Check, in order:

1. The soundbar is powered on.
2. The address is the soundbar's Classic Bluetooth address (`54:15:89:...`), not an unrelated BLE advertisement.
3. `bluetoothctl devices Paired` lists that address.
4. The device is trusted (`bluetoothctl info XX:XX:XX:XX:XX:XX`).
5. ThinQ, a phone, or another controller is not holding the SPP session.
6. The Home Assistant Bluetooth adapter supports Classic Bluetooth/RFCOMM (e.g. USB dongle passed through to the VM), not BLE only.
7. Restart the soundbar once after a failed or interrupted pairing attempt.

### Channel Order and Per-Channel Timeouts
On the LG S75QR, RFCOMM control is on **channel 1**. The integration tries channel 1 first and channel 2 second by default. Each channel has an independent timeout budget (default: 5.0s per channel), preventing an unresponsive channel from starving subsequent fallbacks. Both channel attempts and their failure reasons are detailed in debug logs and config flow error dialogs.

### Testing from HAOS Terminal & SSH (Errno 97)
> **Important Note:** In Home Assistant OS, the official **Terminal & SSH** add-on runs inside an isolated Docker container that does **not** have `AF_BLUETOOTH` kernel socket privileges (`errno 97: Address family not supported by protocol`). Therefore, attempting to run Python scripts or standalone CLI tests with `AF_BLUETOOTH` directly inside the Terminal & SSH shell will fail with errno 97.
>
> All RFCOMM connection testing must be performed by the Home Assistant Core process itself. To monitor connection attempts, follow the core logs:
> ```sh
> ha core logs --follow | grep -iE "lg_us60tr|rfcomm"
> ```
## Entity becomes unavailable

The coordinator closes a failed session and reconnects on the next refresh. If it remains unavailable:

1. Close ThinQ on nearby phones.
2. Confirm the pairing still exists.
3. Reload the integration entry from **Settings → Devices & services**.
4. Power-cycle the soundbar only if the RFCOMM service remains wedged.
5. Collect diagnostics and debug logs before deleting/re-pairing the device.

## Enable debug logging

In **Developer tools → Actions**, run `logger.set_level` with:

```yaml
action: logger.set_level
data:
  custom_components.lg_us60tr: debug
```

Follow Core logs from the Terminal & SSH app:

```sh
ha core logs --follow
```

Useful messages include:

- RFCOMM channel attempts and selected channel
- Raw TX/RX bytes at debug level
- Decoded protocol major/minor/payload values
- State changes and pushed updates
- Command timeouts, disconnects, and reconnect attempts

Return logging to normal after diagnosis:

```yaml
action: logger.set_level
data:
  custom_components.lg_us60tr: warning
```

## Download diagnostics

Open the integration entry, select the menu, and download diagnostics. The report includes the selected RFCOMM channel and decoded state. The configured Bluetooth address is redacted.

## A command times out

- Same-value setters are handled as no-ops, but a changed value must still be confirmed by state traffic.
- A timeout usually means the soundbar closed the session, another controller took it, or the protocol handshake was interrupted.
- Do not increase the timeout first. Capture debug logs and verify the actual TX/RX sequence.
- Reloading the integration cleanly closes the old client before opening a new one.

## Source changes unexpectedly or forcing an input

On Linux/Home Assistant, the integration opens an RFCOMM socket for control. When Bluetooth connects, the soundbar naturally wakes up and switches its input to Bluetooth.

### Power-on / Wake Forced Input Source
To prevent the soundbar from staying on Bluetooth, the integration includes a **Power-on / wake forced input** option (available in integration options and via `select.forced_input_source`):
- **`restore_previous` (default)**: Automatically restores the input source (e.g. Optical / HDMI ARC) that was active before the soundbar woke on Bluetooth.
- **`Optical / HDMI ARC`**: Always forces the soundbar to Optical / HDMI ARC / eARC on every connection.
- **`HDMI In`**: Always forces the soundbar to HDMI In on connection.
- **`Bluetooth`**: Leaves the soundbar on Bluetooth.
- **`none` / `disabled`**: Disables automatic input switching.
## HACS does not show the integration

- Confirm the custom repository category is **Integration**.
- Confirm `hacs.json` and `custom_components/lg_us60tr/manifest.json` are present on the selected branch.
- Update/redownload the repository in HACS, then restart Home Assistant.
- Search for the display name **LG S75QR Soundbar**, not the domain name.

## Safe data to attach to an issue

- Home Assistant and HAOS versions
- Soundbar model and firmware version
- Whether pairing and trust succeed
- Redacted diagnostics
- Debug logs covering one connection or one isolated command
- A description of the physical display/source before and after the action

Remove Bluetooth addresses, phone serials, account identifiers, tokens, and full Android bugreports before publishing.
