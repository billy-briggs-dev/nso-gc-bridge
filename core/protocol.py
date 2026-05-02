from dataclasses import dataclass
from typing import Optional, Union

from .model import TransportMetadata

DEFAULT_INPUT_MODE = 0x30

# Player 1=0x01, 2=0x03, 3=0x05, 4=0x06
LED_MAP = [0x01, 0x03, 0x05, 0x06, 0x07, 0x09, 0x0A, 0x0B]


def _normalize_transport(transport: Optional[Union[str, TransportMetadata]]) -> Optional[str]:
    if transport is None:
        return None
    if isinstance(transport, TransportMetadata):
        return transport.transport.lower()
    return str(transport).lower()


def _command_interface(transport: Optional[Union[str, TransportMetadata]]) -> int:
    normalized = _normalize_transport(transport)
    if normalized == "ble":
        return 0x01
    return 0x00


@dataclass(frozen=True)
class OutputCommand:
    name: str
    slot_index: Optional[int] = None
    enabled: Optional[bool] = None
    mode: int = DEFAULT_INPUT_MODE

    def to_bytes(self, transport: Optional[Union[str, TransportMetadata]] = None) -> bytes:
        if self.name == "set-player-led":
            led_mask = LED_MAP[min(int(self.slot_index or 0), len(LED_MAP) - 1)]
            return bytes([
                0x09,
                0x91,
                _command_interface(transport),
                0x07,
                0x00,
                0x08,
                0x00,
                0x00,
                led_mask,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ])
        if self.name == "rumble":
            return bytes([
                0x0A,
                0x91,
                _command_interface(transport),
                0x02,
                0x00,
                0x04,
                0x00,
                0x00,
                0x01 if self.enabled else 0x00,
                0x00,
                0x00,
                0x00,
            ])
        if self.name == "input-mode":
            return bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, self.mode])
        raise ValueError(f"Unsupported output command: {self.name}")


def set_player_led(slot_index: int) -> OutputCommand:
    return OutputCommand(name="set-player-led", slot_index=slot_index)


def rumble(enabled: bool) -> OutputCommand:
    return OutputCommand(name="rumble", enabled=enabled)


def input_mode(mode: int = DEFAULT_INPUT_MODE) -> OutputCommand:
    return OutputCommand(name="input-mode", mode=mode)


def build_set_player_led(slot_index: int, transport: Optional[Union[str, TransportMetadata]]) -> bytes:
    return set_player_led(slot_index).to_bytes(transport)


def build_rumble(enabled: bool, transport: Optional[Union[str, TransportMetadata]]) -> bytes:
    return rumble(enabled).to_bytes(transport)


def build_input_mode(mode: int = DEFAULT_INPUT_MODE) -> bytes:
    return input_mode(mode).to_bytes()
