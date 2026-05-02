from dataclasses import dataclass, field
from statistics import median
from typing import Dict, Iterable, List, Mapping, Optional, Sequence


def _coerce_sample_values(samples: Iterable[Mapping[str, int]], axis: str) -> List[int]:
    return [int(sample[axis]) for sample in samples]


@dataclass(frozen=True)
class TransportMetadata:
    transport: str
    report_id_offset: int = 0
    report_layout: Optional[str] = None
    command_interface: Optional[int] = None


@dataclass(frozen=True)
class StickState:
    main_x: int
    main_y: int
    c_x: int
    c_y: int
    main_x_raw: int
    main_y_raw: int
    c_x_raw: int
    c_y_raw: int
    raw_bytes: Dict[str, Sequence[int]] = field(default_factory=dict)

    def to_legacy_dict(self) -> Dict[str, object]:
        return {
            "main_x": self.main_x,
            "main_y": self.main_y,
            "c_x": self.c_x,
            "c_y": self.c_y,
            "main_x_raw": self.main_x_raw,
            "main_y_raw": self.main_y_raw,
            "c_x_raw": self.c_x_raw,
            "c_y_raw": self.c_y_raw,
            "main_x_offset": self.main_x,
            "main_y_offset": self.main_y,
            "c_x_offset": self.c_x,
            "c_y_offset": self.c_y,
            "raw_bytes": self.raw_bytes,
        }


@dataclass(frozen=True)
class ControllerState:
    buttons: Dict[str, bool]
    trigger_l: int
    trigger_r: int
    sticks: StickState
    raw: Sequence[int] = field(default_factory=list)
    transport: Optional[TransportMetadata] = None

    def to_legacy_dict(self) -> Dict[str, object]:
        payload = {
            "buttons": dict(self.buttons),
            "trigger_l": self.trigger_l,
            "trigger_r": self.trigger_r,
            "sticks": self.sticks.to_legacy_dict(),
            "raw": list(self.raw),
        }
        if self.transport is not None:
            payload["transport"] = self.transport
        return payload


@dataclass
class CalibrationState:
    main_x_center: Optional[int] = None
    main_y_center: Optional[int] = None
    c_x_center: Optional[int] = None
    c_y_center: Optional[int] = None
    calibrated: bool = False

    def __getitem__(self, key: str):
        return getattr(self, key)

    def __setitem__(self, key: str, value):
        setattr(self, key, value)

    def apply(
        self,
        *,
        main_x_raw: int,
        main_y_raw: int,
        c_x_raw: int,
        c_y_raw: int,
        default_center: int = 2048,
    ):
        if self.calibrated:
            return (
                main_x_raw - int(self.main_x_center),
                main_y_raw - int(self.main_y_center),
                c_x_raw - int(self.c_x_center),
                c_y_raw - int(self.c_y_center),
            )
        return (
            main_x_raw - default_center,
            main_y_raw - default_center,
            c_x_raw - default_center,
            c_y_raw - default_center,
        )

    def update_from_samples(self, samples: Iterable[Mapping[str, int]], reducer: str = "mean") -> bool:
        sample_list = list(samples)
        if not sample_list:
            return False

        def reduce_axis(axis: str) -> int:
            values = _coerce_sample_values(sample_list, axis)
            if reducer == "median":
                return int(median(values))
            return int(sum(values) / len(values))

        self.main_x_center = reduce_axis("main_x")
        self.main_y_center = reduce_axis("main_y")
        self.c_x_center = reduce_axis("c_x")
        self.c_y_center = reduce_axis("c_y")
        self.calibrated = True
        return True

    def to_legacy_dict(self) -> Dict[str, Optional[int]]:
        return {
            "main_x_center": self.main_x_center,
            "main_y_center": self.main_y_center,
            "c_x_center": self.c_x_center,
            "c_y_center": self.c_y_center,
            "calibrated": self.calibrated,
        }
