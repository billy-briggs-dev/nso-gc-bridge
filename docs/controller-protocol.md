# Controller protocol freeze

This document freezes the controller-facing protocol surface currently implemented in `main.py`. Use it as the reference when writing parser tests or porting the protocol layer.

## USB input report layout

Current USB parsing uses `NSODriver.parse_input()` with no report offset.

| Byte(s) | Meaning |
|---|---|
| 0-2 | ignored/reserved by the current parser |
| 3 | buttons: bit0 `B`, bit1 `A`, bit2 `Y`, bit3 `X`, bit4 `R`, bit5 `Z`, bit6 `Start` |
| 4 | buttons: bit0 `Dpad_Down`, bit1 `Dpad_Right`, bit2 `Dpad_Left`, bit3 `Dpad_Up`, bit4 `L`, bit5 `ZL` |
| 5 | buttons: bit0 `Home`, bit1 `Capture` |
| 6-8 | main stick, 12-bit Nintendo nibble packing |
| 9-11 | C-stick, 12-bit Nintendo nibble packing |
| 12 | ignored by the current parser |
| 13 | analogue `trigger_l` (`0-255`) |
| 14 | analogue `trigger_r` (`0-255`) |

Stick packing is `x = b0 | ((b1 & 0x0f) << 8)`, `y = (b1 >> 4) | (b2 << 4)`. Parsed stick output is raw value minus calibrated center, or raw value minus `2048` before calibration.

## BLE report variants currently supported

`main.py` currently accepts these BLE layouts:

| Variant | Selected by | Buttons | Sticks | Trigger semantics |
|---|---|---|---|---|
| NSO standard `0x30` | `_parse_ble_nso()` when byte 0 is `0x30`; also `parse_ble_input(..., ble_report_layout='standard')` | bytes 3-5 | bytes 6-8 and 9-11, 12-bit packed | `_parse_ble_nso()` uses bytes 14/15 when non-zero, else falls back to digital `ZL`/`Z`; `parse_ble_input()` always derives digital `0/255` from `ZL`/`Z` |
| NSO stripped report | `_parse_ble_nso()` when byte 0 is not `0x30` | bytes 2-4 | bytes 5-7 and 8-10, 12-bit packed | bytes 13/14 when non-zero, else digital fallback from `ZL`/`Z` |
| Reordered report | `parse_ble_input(..., ble_report_layout='reordered'/'auto')` | bytes 9-11 | bytes 3-5 and 6-8, 12-bit packed | digital `0/255` from `ZL`/`Z` |
| Simple `0x3f` | `parse_ble_input(..., ble_report_layout='0x3f'/'auto')` | byte 1 d-pad, byte 2 system/shoulders | bytes 4-11 as 16-bit little-endian axes | digital `0/255` from `L`/`Z` |
| 63-byte discovered layout | `_parse_ble_63_discovered()` | bytes 2-4 | bytes 5-7 and 8-10, 12-bit packed | bytes 12/13 when non-zero, else digital fallback from `ZL`/`Z` |
| BlueRetro 62+ byte layout | `_parse_ble_blueretro()` for reports `>= 62` bytes | bytes 4-7 as a 32-bit button mask | bytes 10-12 and 13-15, 12-bit packed | bytes 60/61 |

Notification handling prefers the 63-byte layout first, then BlueRetro (`>= 62` bytes), then NSO stripped/full reports.

## Analogue trigger semantics

- **USB:** `trigger_l` and `trigger_r` are raw analogue bytes from report bytes 13 and 14.
- **BLE standard/reordered:** current code treats triggers as digital and emits `0` or `255` from `ZL` and `Z`.
- **BLE stripped / 63-byte discovered:** current code uses trigger bytes if present and non-zero; otherwise it falls back to digital `0/255` from `ZL` and `Z`.
- **BLE `0x3f`:** current code derives `trigger_l` from `L` and `trigger_r` from `Z`, again as `0` or `255`.
- **BLE BlueRetro:** bytes 60 and 61 are treated as analogue trigger values.
- **Rumble:** output is only boolean on/off; any non-zero DSU motor value becomes rumble on.

## Canonical button naming used by the app

`A`, `B`, `X`, `Y`, `L`, `R`, `Z`, `ZL`, `Start`, `Home`, `Capture`, `Dpad_Up`, `Dpad_Down`, `Dpad_Left`, `Dpad_Right`

These are the button keys emitted by the Python parser and consumed by the GUI/DSU code.

## Player LED commands

Player LEDs use `LED_MAP = [0x01, 0x03, 0x05, 0x06, 0x07, 0x09, 0x0A, 0x0B]`.

For the normal four slots, the masks are:

| Slot index | Player | Mask |
|---|---|---|
| 0 | 1 | `0x01` |
| 1 | 2 | `0x03` |
| 2 | 3 | `0x05` |
| 3 | 4 | `0x06` |

Command format:

- USB: `09 91 00 07 00 08 00 00 <mask> 00 00 00 00 00 00 00`
- BLE: `09 91 01 07 00 08 00 00 <mask> 00 00 00 00 00 00 00`

BLE writes are intended for the discovered command characteristic (`0x0014` in the code comments), not the notification characteristic.

## Rumble commands

Command format:

- USB: `0A 91 00 02 00 04 00 00 <state> 00 00 00`
- BLE: `0A 91 01 02 00 04 00 00 <state> 00 00 00`

`<state>` is `0x01` for on and `0x00` for off.
