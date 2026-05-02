from typing import Sequence, Tuple


def decode_12bit_pair(b0: int, b1: int, b2: int) -> Tuple[int, int]:
    """Decode Nintendo's nibble-packed 12-bit stick pair from 3 bytes."""
    x_raw = b0 | ((b1 & 0x0F) << 8)
    y_raw = (b1 >> 4) | (b2 << 4)
    return x_raw, y_raw


def decode_dual_stick_axes(main_bytes: Sequence[int], c_bytes: Sequence[int]) -> Tuple[int, int, int, int]:
    if len(main_bytes) != 3 or len(c_bytes) != 3:
        raise ValueError("main_bytes and c_bytes must both contain exactly 3 bytes")
    main_x_raw, main_y_raw = decode_12bit_pair(main_bytes[0], main_bytes[1], main_bytes[2])
    c_x_raw, c_y_raw = decode_12bit_pair(c_bytes[0], c_bytes[1], c_bytes[2])
    return main_x_raw, main_y_raw, c_x_raw, c_y_raw
