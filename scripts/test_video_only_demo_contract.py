#!/usr/bin/env python3
"""Regression tests for the final-except-video Demo contract."""

import copy
import unittest

from production_contract import validate_video_only_demo_contract


def asset(kind, status="accepted", required=True):
    return {
        "kind": kind,
        "status": status,
        "required": required,
        "delivery_class": "formal",
    }


class VideoOnlyDemoContractTests(unittest.TestCase):
    def setUp(self):
        self.assets = {
            "video_main": asset("linear_video", "planned"),
            "storyboard_main": asset("image"),
            "runtime_main": asset("runtime"),
        }
        self.data = {
            "delivery_endpoint": "interaction_complete_prototype",
            "acceptance_status": "browser_verified",
            "work_scope": {
                "scope_type": "full_course",
                "learner_delivery_type": "interactive_web",
            },
            "experience_profile": {"profile_identifier": "video_led_web"},
            "demo_completion": {
                "contract_version": "1.0",
                "completion_policy": "video_only_delta",
                "non_video_completion": {
                    "course_content": "complete",
                    "scene_and_beat_sequence": "complete",
                    "page_and_responsive_layout": "complete",
                    "interactions_and_feedback": "complete",
                    "state_and_recovery": "complete",
                    "accessibility_equivalents": "complete",
                    "non_video_assets": "complete",
                    "browser_verification": "complete",
                },
                "deferred_items": [
                    {
                        "deferred_identifier": "deferred_video",
                        "kind": "formal_video_generation",
                        "asset_identifiers": ["video_main"],
                        "reason": "Formal video is not generated yet",
                    }
                ],
                "video_replacement_contract": {
                    "substitute_asset_identifiers": ["storyboard_main"],
                    "formal_video_asset_identifiers": ["video_main"],
                    "preserved_contracts": [
                        "course_content", "layout", "interactions",
                        "feedback", "state_and_recovery", "accessibility",
                    ],
                    "post_replacement_checks": [
                        "media_timing", "hotspot_timing", "caption_sync",
                        "return_state", "responsive_layout", "accessibility",
                    ],
                },
            },
        }

    def check(self, expected=None):
        errors = validate_video_only_demo_contract(self.data, self.assets)
        if expected is None:
            self.assertEqual(errors, [])
        else:
            self.assertTrue(any(expected in error for error in errors), errors)

    def test_complete_video_only_demo(self):
        self.check()

    def test_rejects_non_video_deferred_work(self):
        self.data["demo_completion"]["deferred_items"][0]["kind"] = "interaction_implementation"
        self.check("video-only deferred work")

    def test_rejects_unaccepted_non_video_asset(self):
        self.assets["runtime_main"]["status"] = "ready"
        self.check("requires accepted non-video asset")

    def test_rejects_accepted_video_as_generation_delta(self):
        self.assets["video_main"]["status"] = "accepted"
        self.check("cannot defer generation of an accepted formal video")

    def test_rejects_unaccepted_storyboard_substitute(self):
        self.assets["storyboard_main"]["status"] = "ready"
        self.check("Storyboard substitute must be accepted")

    def test_rejects_missing_browser_verification(self):
        self.data["acceptance_status"] = "structure_checked"
        self.check("requires browser verification")

    def test_non_applicable_scope_is_ignored(self):
        self.data["work_scope"]["scope_type"] = "local_design"
        del self.data["demo_completion"]
        self.check()


if __name__ == "__main__":
    unittest.main()
