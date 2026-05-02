import json
import unittest
from pathlib import Path

from core import (
    LED_MAP,
    CalibrationState,
    NSOReportParser,
    TransportMetadata,
    build_input_mode,
    build_rumble,
    build_set_player_led,
    extract_calibration_sample,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "protocol"


def load_fixture(name: str):
    with (FIXTURE_DIR / f"{name}.json").open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


class ProtocolFixtureTests(unittest.TestCase):
    def assert_parsed_matches_fixture(self, parsed, expected):
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["buttons"], expected["buttons"])
        self.assertEqual(parsed["trigger_l"], expected["trigger_l"])
        self.assertEqual(parsed["trigger_r"], expected["trigger_r"])
        for axis, value in expected["sticks"].items():
            self.assertEqual(parsed["sticks"][axis], value)
        pressed_buttons = sorted(name for name, pressed in parsed["buttons"].items() if pressed)
        self.assertEqual(pressed_buttons, sorted(expected["pressed_buttons"]))

    def test_usb_fixture_covers_button_mapping_and_stick_decoding(self):
        fixture = load_fixture("usb_neutral_report")

        parsed = NSOReportParser().parse_usb_input(fixture["raw_report"])

        self.assert_parsed_matches_fixture(parsed, fixture["expected"])

    def test_ble_standard_fixture_covers_button_mapping_sticks_and_digital_trigger_fallback(self):
        fixture = load_fixture("ble_standard_button_stick_report")

        parsed = NSOReportParser(ble_report_layout="standard").parse_ble_input(fixture["raw_report"])

        self.assert_parsed_matches_fixture(parsed, fixture["expected"])

    def test_ble_63_fixture_covers_analogue_triggers_and_notification_layout(self):
        fixture = load_fixture("ble_63_button_stick_report")

        parsed = NSOReportParser().parse_ble_notification(fixture["raw_report"])

        self.assert_parsed_matches_fixture(parsed, fixture["expected"])

    def test_ble_0x3f_fixture_covers_auto_variant_detection_and_16bit_sticks(self):
        fixture = load_fixture("ble_0x3f_neutral_report")

        parsed = NSOReportParser(ble_report_layout="auto").parse_ble_input(fixture["raw_report"])

        self.assert_parsed_matches_fixture(parsed, fixture["expected"])

    def test_usb_trigger_sweep_fixture_covers_analogue_trigger_decoding(self):
        fixture = load_fixture("usb_trigger_sweep")
        parser = NSOReportParser()

        for case in fixture["cases"]:
            with self.subTest(case=case["name"]):
                parsed = parser.parse_usb_input(case["raw_report"])
                self.assertIsNotNone(parsed)
                self.assertEqual(parsed["trigger_l"], case["expected_trigger_l"])
                self.assertEqual(parsed["trigger_r"], case["expected_trigger_r"])

    def test_ble_variant_detection_matches_current_paths(self):
        cases = (
            (
                "reordered-auto",
                load_fixture("ble_reordered_neutral_report"),
                lambda parser, raw: parser.parse_ble_input(raw),
                NSOReportParser(ble_report_layout="auto"),
            ),
            (
                "nso-stripped-notification",
                load_fixture("ble_nso_stripped_neutral_report"),
                lambda parser, raw: parser.parse_ble_notification(raw),
                NSOReportParser(),
            ),
            (
                "blueretro-notification",
                load_fixture("ble_blueretro_neutral_report"),
                lambda parser, raw: parser.parse_ble_notification(raw),
                NSOReportParser(),
            ),
        )

        for name, fixture, parse, parser in cases:
            with self.subTest(case=name):
                self.assert_parsed_matches_fixture(parse(parser, fixture["raw_report"]), fixture["expected"])

    def test_calibration_application_uses_fixture_samples(self):
        fixture = load_fixture("ble_standard_button_stick_report")
        parser = NSOReportParser(ble_report_layout="standard")
        baseline = parser.parse_ble_input(fixture["raw_report"])

        calibration = CalibrationState()
        self.assertTrue(calibration.update_from_samples([extract_calibration_sample(baseline)]))

        parsed = parser.parse_ble_input(fixture["raw_report"], calibration=calibration)

        self.assertEqual(parsed["sticks"]["main_x"], 0)
        self.assertEqual(parsed["sticks"]["main_y"], 0)
        self.assertEqual(parsed["sticks"]["c_x"], 0)
        self.assertEqual(parsed["sticks"]["c_y"], 0)
        self.assertEqual(parsed["sticks"]["main_x_raw"], baseline["sticks"]["main_x_raw"])
        self.assertEqual(parsed["sticks"]["main_y_raw"], baseline["sticks"]["main_y_raw"])
        self.assertEqual(parsed["sticks"]["c_x_raw"], baseline["sticks"]["c_x_raw"])
        self.assertEqual(parsed["sticks"]["c_y_raw"], baseline["sticks"]["c_y_raw"])

    def test_output_command_generation_matches_fixture_examples(self):
        fixture = load_fixture("output_command_examples")

        self.assertEqual(LED_MAP[:4], [fixture["player_led_masks"][str(index)] for index in range(4)])

        for transport in ("usb", "ble"):
            metadata = TransportMetadata(transport=transport)
            for slot_name, expected in fixture["player_led_commands"][transport].items():
                with self.subTest(command="player-led", transport=transport, slot=slot_name):
                    slot_index = int(slot_name.rsplit("_", 1)[-1])
                    command = build_set_player_led(slot_index, metadata)
                    self.assertEqual(list(command), expected["bytes"])
                    self.assertEqual(command.hex(" "), expected["hex"])

            for state_name, expected in fixture["rumble_commands"][transport].items():
                with self.subTest(command="rumble", transport=transport, state=state_name):
                    command = build_rumble(state_name == "on", metadata)
                    self.assertEqual(list(command), expected["bytes"])
                    self.assertEqual(command.hex(" "), expected["hex"])

        input_mode_command = build_input_mode()
        expected_input_mode = fixture["init_commands"]["set_input_mode_standard_full_reports"]
        self.assertEqual(list(input_mode_command), expected_input_mode["bytes"])
        self.assertEqual(input_mode_command.hex(" "), expected_input_mode["hex"])


if __name__ == "__main__":
    unittest.main()
