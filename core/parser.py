from dataclasses import dataclass, replace
from typing import Dict, Mapping, Optional, Sequence, Union

from .decoding import decode_12bit_pair
from .model import CalibrationState, ControllerState, StickState, TransportMetadata

DEFAULT_12BIT_CENTER = 2048
DEFAULT_16BIT_CENTER = 32768


USB_BUTTON_LAYOUT = {
    "B": (0x01, 0, 0),
    "A": (0x02, 0, 0),
    "Y": (0x04, 0, 0),
    "X": (0x08, 0, 0),
    "R": (0x10, 0, 0),
    "Z": (0x20, 0, 0),
    "Start": (0x40, 0, 0),
    "Dpad_Down": (0x01, 1, 0),
    "Dpad_Right": (0x02, 1, 0),
    "Dpad_Left": (0x04, 1, 0),
    "Dpad_Up": (0x08, 1, 0),
    "L": (0x10, 1, 0),
    "ZL": (0x20, 1, 0),
    "Home": (0x01, 2, 0),
    "Capture": (0x02, 2, 0),
}

BLE_STANDARD_BUTTON_LAYOUT = {
    "Y": (0x01, 0, 0),
    "X": (0x02, 0, 0),
    "B": (0x04, 0, 0),
    "A": (0x08, 0, 0),
    "R": (0x10, 0, 0),
    "Z": (0x20, 0, 0),
    "Start": (0x02, 1, 0),
    "Home": (0x10, 1, 0),
    "Capture": (0x20, 1, 0),
    "Dpad_Down": (0x01, 2, 0),
    "Dpad_Up": (0x02, 2, 0),
    "Dpad_Right": (0x04, 2, 0),
    "Dpad_Left": (0x08, 2, 0),
    "L": (0x40, 2, 0),
    "ZL": (0x80, 2, 0),
}

BLE_63_BUTTON_LAYOUT = {
    "B": (0x01, 0, 0),
    "A": (0x02, 0, 0),
    "Y": (0x04, 0, 0),
    "X": (0x08, 0, 0),
    "R": (0x10, 0, 0),
    "Z": (0x20, 0, 0),
    "Start": (0x40, 0, 0),
    "Dpad_Down": (0x01, 1, 0),
    "Dpad_Right": (0x02, 1, 0),
    "Dpad_Left": (0x04, 1, 0),
    "Dpad_Up": (0x08, 1, 0),
    "L": (0x10, 1, 0),
    "ZL": (0x20, 1, 0),
    "Home": (0x01, 2, 0),
    "Capture": (0x02, 2, 0),
}

BLE_0X3F_BUTTON_LAYOUT = {
    "Dpad_Down": (0x01, 0, 0),
    "Dpad_Right": (0x02, 0, 0),
    "Dpad_Left": (0x04, 0, 0),
    "Dpad_Up": (0x08, 0, 0),
    "Start": (0x02, 1, 0),
    "Home": (0x10, 1, 0),
    "Capture": (0x20, 1, 0),
    "L": (0x40, 1, 0),
    "Z": (0x80, 1, 0),
}

BLE_0X3F_DEFAULTS = {
    "Y": False,
    "X": False,
    "B": False,
    "A": False,
    "R": False,
    "ZL": False,
}

BLUERETRO_BUTTON_BITS = {
    "Dpad_Left": 8,
    "Dpad_Right": 9,
    "Dpad_Down": 10,
    "Dpad_Up": 11,
    "B": 16,
    "X": 17,
    "A": 18,
    "Y": 19,
    "Start": 20,
    "Home": 22,
    "Capture": 23,
    "ZL": 25,
    "L": 26,
    "Z": 29,
    "R": 30,
}


def _apply_calibration(
    calibration: Optional[CalibrationState],
    *,
    main_x_raw: int,
    main_y_raw: int,
    c_x_raw: int,
    c_y_raw: int,
    default_center: int,
):
    if calibration is not None:
        return calibration.apply(
            main_x_raw=main_x_raw,
            main_y_raw=main_y_raw,
            c_x_raw=c_x_raw,
            c_y_raw=c_y_raw,
            default_center=default_center,
        )
    return (
        main_x_raw - default_center,
        main_y_raw - default_center,
        c_x_raw - default_center,
        c_y_raw - default_center,
    )


def _decode_button_bytes(layout: Mapping[str, Sequence[int]], button_bytes: Sequence[int]) -> Dict[str, bool]:
    return {
        name: (button_bytes[byte_index] & mask) != 0
        for name, (mask, byte_index, _) in layout.items()
    }


def _build_stick_state(
    *,
    main_x_raw: int,
    main_y_raw: int,
    c_x_raw: int,
    c_y_raw: int,
    raw_bytes: Mapping[str, Sequence[int]],
    calibration: Optional[CalibrationState],
    default_center: int = DEFAULT_12BIT_CENTER,
) -> StickState:
    main_x, main_y, c_x, c_y = _apply_calibration(
        calibration,
        main_x_raw=main_x_raw,
        main_y_raw=main_y_raw,
        c_x_raw=c_x_raw,
        c_y_raw=c_y_raw,
        default_center=default_center,
    )
    return StickState(
        main_x=main_x,
        main_y=main_y,
        c_x=c_x,
        c_y=c_y,
        main_x_raw=main_x_raw,
        main_y_raw=main_y_raw,
        c_x_raw=c_x_raw,
        c_y_raw=c_y_raw,
        raw_bytes={name: list(values) for name, values in raw_bytes.items()},
    )


def _decode_nibble_sticks(
    data: Sequence[int],
    *,
    main_start: int,
    c_start: int,
    calibration: Optional[CalibrationState],
) -> Optional[StickState]:
    if len(data) < c_start + 3:
        return None
    main_bytes = list(data[main_start:main_start + 3])
    c_bytes = list(data[c_start:c_start + 3])
    main_x_raw, main_y_raw = decode_12bit_pair(*main_bytes)
    c_x_raw, c_y_raw = decode_12bit_pair(*c_bytes)
    return _build_stick_state(
        main_x_raw=main_x_raw,
        main_y_raw=main_y_raw,
        c_x_raw=c_x_raw,
        c_y_raw=c_y_raw,
        raw_bytes={"main": main_bytes, "c": c_bytes},
        calibration=calibration,
        default_center=DEFAULT_12BIT_CENTER,
    )


def _build_state(
    *,
    buttons: Mapping[str, bool],
    trigger_l: int,
    trigger_r: int,
    sticks: StickState,
    raw: Sequence[int],
) -> ControllerState:
    return ControllerState(
        buttons=dict(buttons),
        trigger_l=int(trigger_l),
        trigger_r=int(trigger_r),
        sticks=sticks,
        raw=list(raw),
    )


def _with_transport(
    state: ControllerState,
    *,
    transport: str,
    report_id_offset: int = 0,
    report_layout: Optional[str] = None,
) -> ControllerState:
    return replace(
        state,
        transport=TransportMetadata(
            transport=transport,
            report_id_offset=report_id_offset,
            report_layout=report_layout,
            command_interface=0x01 if transport.lower() == "ble" else 0x00,
        ),
    )


def _to_legacy_state(state: Optional[ControllerState]) -> Optional[Dict[str, object]]:
    if state is None:
        return None
    return state.to_legacy_dict()


def _parse_usb_state(
    data: Sequence[int],
    *,
    calibration: Optional[CalibrationState],
    report_id_offset: int,
    ble_layout: bool,
) -> Optional[ControllerState]:
    payload = list(data)
    offset = int(report_id_offset)
    if len(payload) < 12 + offset:
        return None

    button_bytes = payload[3 + offset:6 + offset]
    layout = BLE_STANDARD_BUTTON_LAYOUT if ble_layout else USB_BUTTON_LAYOUT
    buttons = _decode_button_bytes(layout, button_bytes)
    trigger_l = payload[13 + offset] if len(payload) > 13 + offset else 0
    trigger_r = payload[14 + offset] if len(payload) > 14 + offset else 0
    sticks = _decode_nibble_sticks(payload, main_start=6 + offset, c_start=9 + offset, calibration=calibration)
    if sticks is None:
        return None
    return _build_state(
        buttons=buttons,
        trigger_l=trigger_l,
        trigger_r=trigger_r,
        sticks=sticks,
        raw=payload,
    )


ParsedState = Union[ControllerState, Mapping[str, object]]


def extract_calibration_sample(parsed_state: Optional[ParsedState]) -> Optional[Dict[str, int]]:
    if not parsed_state:
        return None
    if isinstance(parsed_state, ControllerState):
        return {
            "main_x": int(parsed_state.sticks.main_x_raw),
            "main_y": int(parsed_state.sticks.main_y_raw),
            "c_x": int(parsed_state.sticks.c_x_raw),
            "c_y": int(parsed_state.sticks.c_y_raw),
        }
    sticks = parsed_state.get("sticks", {})
    keys = ("main_x_raw", "main_y_raw", "c_x_raw", "c_y_raw")
    if not all(key in sticks for key in keys):
        return None
    return {
        "main_x": int(sticks["main_x_raw"]),
        "main_y": int(sticks["main_y_raw"]),
        "c_x": int(sticks["c_x_raw"]),
        "c_y": int(sticks["c_y_raw"]),
    }


@dataclass(frozen=True)
class NSOReportParser:
    report_id_offset: int = 0
    ble_report_layout: str = "auto"

    def parse_usb_controller_state(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState] = None,
        report_id_offset: Optional[int] = None,
        ble_layout: bool = False,
    ) -> Optional[ControllerState]:
        offset = self.report_id_offset if report_id_offset is None else int(report_id_offset)
        state = _parse_usb_state(
            data,
            calibration=calibration,
            report_id_offset=offset,
            ble_layout=ble_layout,
        )
        if state is None:
            return None
        return _with_transport(
            state,
            transport="usb",
            report_id_offset=offset,
            report_layout="usb-ble-layout" if ble_layout else "usb",
        )

    def parse_usb_input(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState] = None,
        report_id_offset: Optional[int] = None,
        ble_layout: bool = False,
    ) -> Optional[Dict[str, object]]:
        return _to_legacy_state(
            self.parse_usb_controller_state(
                data,
                calibration=calibration,
                report_id_offset=report_id_offset,
                ble_layout=ble_layout,
            )
        )

    def parse_ble_controller_state(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState] = None,
    ) -> Optional[ControllerState]:
        payload = list(data)
        if len(payload) < 12:
            return None

        report_id = payload[0]
        report_layout = "standard"
        state: Optional[ControllerState] = None
        if report_id == 0x3F and self.ble_report_layout in ("auto", "0x3f"):
            report_layout = "0x3f"
            state = self._parse_ble_0x3f(payload)
        elif self.ble_report_layout in ("auto", "reordered"):
            state = self._parse_ble_reordered(payload, calibration=calibration)
            if state is not None:
                report_layout = "reordered"

        if state is None:
            state = self._parse_ble_standard(payload, calibration=calibration)

        if state is None:
            return None
        return _with_transport(
            state,
            transport="ble",
            report_id_offset=self.report_id_offset,
            report_layout=report_layout,
        )

    def parse_ble_input(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState] = None,
    ) -> Optional[Dict[str, object]]:
        return _to_legacy_state(self.parse_ble_controller_state(data, calibration=calibration))

    def parse_ble_notification_controller_state(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState] = None,
    ) -> Optional[ControllerState]:
        payload = list(data)
        if len(payload) == 63:
            state = self._parse_ble_63_discovered(payload, calibration=calibration)
            if state is not None:
                return _with_transport(
                    state,
                    transport="ble",
                    report_id_offset=self.report_id_offset,
                    report_layout="63-byte",
                )
        if len(payload) >= 62:
            state = self._parse_ble_blueretro(payload, calibration=calibration)
            if state is not None:
                return _with_transport(
                    state,
                    transport="ble",
                    report_id_offset=self.report_id_offset,
                    report_layout="blueretro",
                )

        state = self._parse_ble_nso(payload, calibration=calibration)
        if state is not None:
            return _with_transport(
                state,
                transport="ble",
                report_id_offset=self.report_id_offset,
                report_layout="nso",
            )

        state = _parse_usb_state(
            payload,
            calibration=calibration,
            report_id_offset=self.report_id_offset,
            ble_layout=False,
        )
        if state is None:
            return None
        return _with_transport(
            state,
            transport="ble",
            report_id_offset=self.report_id_offset,
            report_layout="usb-compatible",
        )

    def parse_ble_notification(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState] = None,
    ) -> Optional[Dict[str, object]]:
        return _to_legacy_state(self.parse_ble_notification_controller_state(data, calibration=calibration))

    def _parse_ble_standard(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState],
    ) -> Optional[Dict[str, object]]:
        offset = self.report_id_offset
        if len(data) < 12 + offset:
            return None
        buttons = _decode_button_bytes(BLE_STANDARD_BUTTON_LAYOUT, data[3 + offset:6 + offset])
        sticks = _decode_nibble_sticks(data, main_start=6 + offset, c_start=9 + offset, calibration=calibration)
        if sticks is None:
            return None
        return _build_state(
            buttons=buttons,
            trigger_l=255 if buttons.get("ZL") else 0,
            trigger_r=255 if buttons.get("Z") else 0,
            sticks=sticks,
            raw=data,
        )

    def _parse_ble_reordered(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState],
    ) -> Optional[Dict[str, object]]:
        if self.ble_report_layout not in ("auto", "reordered") or len(data) < 12:
            return None
        buttons = _decode_button_bytes(BLE_STANDARD_BUTTON_LAYOUT, data[9:12])
        sticks = _decode_nibble_sticks(data, main_start=3, c_start=6, calibration=calibration)
        if sticks is None:
            return None
        return _build_state(
            buttons=buttons,
            trigger_l=255 if buttons.get("ZL") else 0,
            trigger_r=255 if buttons.get("Z") else 0,
            sticks=sticks,
            raw=data,
        )

    def _parse_ble_0x3f(self, data: Sequence[int]) -> Optional[Dict[str, object]]:
        if len(data) < 12:
            return None
        buttons = _decode_button_bytes(BLE_0X3F_BUTTON_LAYOUT, data[1:3])
        buttons.update(BLE_0X3F_DEFAULTS)
        sticks = _build_stick_state(
            main_x_raw=data[4] | (data[5] << 8),
            main_y_raw=data[6] | (data[7] << 8),
            c_x_raw=data[8] | (data[9] << 8),
            c_y_raw=data[10] | (data[11] << 8),
            raw_bytes={"main": data[4:8], "c": data[8:12]},
            calibration=None,
            default_center=DEFAULT_16BIT_CENTER,
        )
        return _build_state(
            buttons=buttons,
            trigger_l=255 if buttons.get("L") else 0,
            trigger_r=255 if buttons.get("Z") else 0,
            sticks=sticks,
            raw=data,
        )

    def _parse_ble_nso(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState],
    ) -> Optional[Dict[str, object]]:
        if len(data) < 11:
            return None

        if data[0] != 0x30:
            button_slice = data[2:5]
            sticks = _decode_nibble_sticks(data, main_start=5, c_start=8, calibration=calibration)
            trigger_l = data[13] if len(data) > 13 else 0
            trigger_r = data[14] if len(data) > 14 else 0
        else:
            if len(data) < 12:
                return None
            button_slice = data[3:6]
            sticks = _decode_nibble_sticks(data, main_start=6, c_start=9, calibration=calibration)
            trigger_l = data[14] if len(data) > 14 else 0
            trigger_r = data[15] if len(data) > 15 else 0

        if sticks is None:
            return None
        buttons = _decode_button_bytes(BLE_STANDARD_BUTTON_LAYOUT, button_slice)
        if trigger_l == 0 and trigger_r == 0:
            trigger_l = 255 if buttons.get("ZL") else 0
            trigger_r = 255 if buttons.get("Z") else 0
        return _build_state(
            buttons=buttons,
            trigger_l=trigger_l,
            trigger_r=trigger_r,
            sticks=sticks,
            raw=data,
        )

    def _parse_ble_63_discovered(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState],
    ) -> Optional[Dict[str, object]]:
        if len(data) < 11:
            return None
        buttons = _decode_button_bytes(BLE_63_BUTTON_LAYOUT, data[2:5])
        sticks = _decode_nibble_sticks(data, main_start=5, c_start=8, calibration=calibration)
        if sticks is None:
            return None
        trigger_l = data[12] if len(data) > 12 else 0
        trigger_r = data[13] if len(data) > 13 else 0
        if trigger_l == 0 and trigger_r == 0:
            trigger_l = 255 if buttons.get("ZL") else 0
            trigger_r = 255 if buttons.get("Z") else 0
        return _build_state(
            buttons=buttons,
            trigger_l=trigger_l,
            trigger_r=trigger_r,
            sticks=sticks,
            raw=data,
        )

    def _parse_ble_blueretro(
        self,
        data: Sequence[int],
        *,
        calibration: Optional[CalibrationState],
    ) -> Optional[Dict[str, object]]:
        if len(data) < 62:
            return None
        buttons_u32 = data[4] | (data[5] << 8) | (data[6] << 16) | (data[7] << 24)
        buttons = {name: ((buttons_u32 >> bit) & 1) != 0 for name, bit in BLUERETRO_BUTTON_BITS.items()}
        sticks = _decode_nibble_sticks(data, main_start=10, c_start=13, calibration=calibration)
        if sticks is None:
            return None
        return _build_state(
            buttons=buttons,
            trigger_l=data[60] if len(data) > 60 else 0,
            trigger_r=data[61] if len(data) > 61 else 0,
            sticks=sticks,
            raw=data,
        )
