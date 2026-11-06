import copy
import json
import unittest
from pathlib import Path

from check_video_led_visual_gate import validate


ROOT = Path(__file__).resolve().parents[1]


class VideoLedVisualGateTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(
            (ROOT / "assets/video-led-visual-gate.template.json").read_text()
        )

    def test_planned_template_is_structurally_valid(self):
        self.assertEqual(validate(self.data), [])

    def test_passed_gate_requires_all_state_evidence(self):
        data = copy.deepcopy(self.data)
        data["status"] = "passed"
        self.assertIn("passed evidence", "\n".join(validate(data)))

    def test_rejects_decoration_without_learning_purpose(self):
        data = copy.deepcopy(self.data)
        data["decorations"][0]["teaching_purpose"] = ""
        self.assertIn("teaching_purpose is required", "\n".join(validate(data)))

    def test_rejects_decorative_only_role(self):
        data = copy.deepcopy(self.data)
        data["decorations"][0]["visual_role"] = "ornament"
        self.assertIn("learning-supporting role", "\n".join(validate(data)))


if __name__ == "__main__":
    unittest.main()
