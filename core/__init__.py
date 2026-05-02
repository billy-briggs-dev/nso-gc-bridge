"""Shared protocol and controller model helpers."""

from .decoding import decode_12bit_pair, decode_dual_stick_axes
from .model import CalibrationState, ControllerState, StickState, TransportMetadata
from .parser import NSOReportParser, extract_calibration_sample
from .protocol import (
    DEFAULT_INPUT_MODE,
    LED_MAP,
    OutputCommand,
    build_input_mode,
    build_rumble,
    build_set_player_led,
    input_mode,
    rumble,
    set_player_led,
)

__all__ = [
    "CalibrationState",
    "ControllerState",
    "DEFAULT_INPUT_MODE",
    "LED_MAP",
    "NSOReportParser",
    "OutputCommand",
    "StickState",
    "TransportMetadata",
    "build_input_mode",
    "build_rumble",
    "build_set_player_led",
    "decode_12bit_pair",
    "decode_dual_stick_axes",
    "extract_calibration_sample",
    "input_mode",
    "rumble",
    "set_player_led",
]
