import json
import struct
import unittest
from pathlib import Path

from core import ControllerState, NSOReportParser, StickState, TransportMetadata
from dsu_server import DSUServer


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "protocol"


def _load_fixture(name: str):
    with (FIXTURES_DIR / name).open() as fixture_file:
        return json.load(fixture_file)


class CanonicalStateRoutingTests(unittest.TestCase):
    def test_parser_emits_canonical_controller_state_with_transport_metadata(self):
        fixture = _load_fixture("usb_neutral_report.json")

        controller_state = NSOReportParser().parse_usb_controller_state(fixture["raw_report"])

        self.assertIsInstance(controller_state, ControllerState)
        self.assertEqual("usb", controller_state.transport.transport)
        self.assertEqual("usb", controller_state.transport.report_layout)
        self.assertEqual(fixture["expected"]["buttons"], controller_state.buttons)
        self.assertEqual(fixture["expected"]["trigger_l"], controller_state.trigger_l)
        self.assertEqual(fixture["expected"]["trigger_r"], controller_state.trigger_r)

    def test_dsu_server_consumes_canonical_state_and_preserves_mapping(self):
        server = DSUServer()
        controller_state = ControllerState(
            buttons={
                "A": True,
                "B": False,
                "X": False,
                "Y": False,
                "L": True,
                "R": False,
                "Z": True,
                "ZL": True,
                "Start": True,
                "Home": True,
                "Capture": True,
                "Dpad_Up": False,
                "Dpad_Down": False,
                "Dpad_Left": True,
                "Dpad_Right": False,
            },
            trigger_l=123,
            trigger_r=231,
            sticks=StickState(
                main_x=512,
                main_y=-256,
                c_x=-128,
                c_y=64,
                main_x_raw=2560,
                main_y_raw=1792,
                c_x_raw=1920,
                c_y_raw=2112,
            ),
            transport=TransportMetadata(transport="ble", report_layout="nso", command_interface=0x01),
        )

        server.update(controller_state, pad_id=2)

        self.assertEqual(0x02, server._get_connection_type_for_slot(2))

        packet = server._create_pad_data_packet(
            server.last_state_by_slot[2],
            pad_id=2,
            connection_type=server._get_connection_type_for_slot(2),
        )

        self.assertEqual(0x02, packet[23])
        self.assertEqual(0b10001100, packet[36])  # Left, Start->Options, Z->R3
        self.assertEqual(0b01000101, packet[37])  # A->Cross, L->L1, ZL->L2
        self.assertEqual(1, packet[38])  # Home->PS
        self.assertEqual(1, packet[39])  # Capture->Touchpad click
        self.assertEqual(123, packet[54])
        self.assertEqual(231, packet[55])

    def test_dsu_rumble_callback_flow_is_preserved(self):
        server = DSUServer()
        observed = []
        server.register_rumble_callback(1, lambda large, small: observed.append((large, small)))

        packet = bytearray(30)
        packet[0:4] = b"DSUC"
        struct.pack_into("<I", packet, 16, server.PACKET_TYPE_RUMBLE)
        packet[20] = 1
        packet[21] = 1
        packet[28] = 0
        packet[29] = 200

        server._handle_rumble(bytes(packet))

        self.assertEqual([(200, 0)], observed)


if __name__ == "__main__":
    unittest.main()
