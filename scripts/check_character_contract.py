#!/usr/bin/env python3
"""Isolated character-contract probes; synthetic reviews are not human approval."""

import argparse
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from check_video_production import ROOT, fixture, make_media
from validate_video_production import digest, validate_delivery, validate_plan
from video_character_contract import validate_character_reviews


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    results = []

    def passed(name):
        results.append({"case": name, "status": "passed"})

    with tempfile.TemporaryDirectory(prefix="character-contract-") as temporary:
        base = Path(temporary)
        media = make_media(base, "moving.mp4", "testsrc2=size=320x180:rate=24:duration=4")
        plan, environment, evidence = fixture(base, media)
        legacy = copy.deepcopy(plan)
        plan["schema_version"] = "1.1"
        plan["character_sources"] = [{
            "source_identifier": "source", "source_type": "primary_text",
            "title": "Synthetic text", "locator": "Synthetic page 1",
            "research_file": evidence.name, "research_sha256": digest(evidence),
        }]
        plan["characters"] = [{
            "character_identifier": "speaker", "display_name": "人物甲", "current_identity": "当时身份",
            "reference_status": "referenced", "source_identifiers": ["source"],
            "reference_search": "Synthetic search result", "creative_fallback_reason": None,
            "appearance_constraints": "Synthetic stable eyebrows and beard; unknown features invented",
            "visual_reference_identifiers": [],
        }]
        plan["shots"][0]["character_identifiers"] = ["speaker"]
        plan["character_introductions"] = [{
            "introduction_identifier": "intro", "character_identifier": "speaker",
            "timeline_identifier": "mainline", "branch_identifier": "mainline",
            "shot_identifier": "shot", "display_name": "人物甲", "current_identity": "当时身份",
            "start_seconds": 0, "end_seconds": 2, "render_mode": "burned_in_video",
            "placement": "Synthetic shoulder-side safe area",
        }]
        for check in ("character_appearance", "character_introduction"):
            review = {
                "timeline_identifier": "mainline", "check": check, "status": "passed",
                "character_identifiers": ["speaker"], "reviewer": "Synthetic fixture only",
                "bound_sha256": digest(media), "evidence_file": evidence.name,
                "evidence_sha256": digest(evidence),
            }
            if check == "character_introduction":
                review["introduction_identifiers"] = ["intro"]
            plan["manual_reviews"].append(review)

        def inspect(name, candidate, expected=None, delivery=False, reviews=False):
            audit = validate_plan(candidate, environment, base, delivery)
            if not audit.errors and delivery:
                validate_delivery(candidate, environment, audit)
            elif not audit.errors and reviews:
                validate_character_reviews(candidate, candidate["timelines"][0], audit)
            if expected:
                assert any(expected in error for error in audit.errors), (name, audit.errors)
            else:
                assert not audit.errors, (name, audit.errors)
            passed(name)
            return audit

        inspect("referenced_character_plan", plan)
        inspect("encoded_delivery_with_file_bound_character_records", plan, delivery=True)
        good = copy.deepcopy(plan)
        good["characters"][0].update(reference_status="no_suitable_reference",
                                     source_identifiers=[], creative_fallback_reason="Synthetic no usable reference")
        inspect("documented_free_design", good)
        good = copy.deepcopy(plan)
        good.update(characters=[], character_sources=[], character_introductions=[])
        good["shots"][0]["character_identifiers"] = []
        good["sound_events"][0].update(kind="narration", on_screen=False,
                                       synchronization_method="off_screen")
        good["manual_reviews"] = [row for row in good["manual_reviews"]
                                  if row["check"] not in ("character_appearance", "character_introduction")]
        inspect("explicit_characterless_course", good, delivery=True)
        good = copy.deepcopy(plan)
        good["shots"][0]["character_identifiers"] = []
        good["character_introductions"] = []
        good["sound_events"][0].update(on_screen=False, synchronization_method="off_screen")
        inspect("off_screen_dialogue_without_visible_actor", good)
        good = copy.deepcopy(plan)
        good["sound_events"][0]["kind"] = "narration"
        inspect("registered_on_screen_narrator", good)

        # Sound declarations must not bypass identity/introduction by clearing shot actors.
        for kind in ("dialogue", "narration"):
            bad = copy.deepcopy(plan)
            bad["shots"][0]["character_identifiers"] = []
            bad["character_introductions"] = []
            bad["sound_events"][0]["kind"] = kind
            inspect("on_screen_" + kind + "_omitted_from_shot", bad, "remain visible")
        bad = copy.deepcopy(plan)
        bad["sound_events"][0].update(kind="narration", speaker_identifier="unknown")
        inspect("unregistered_on_screen_narrator", bad, "registered character")

        mutations = [
            ("missing_character_registry", lambda p: p.pop("characters"), "characters must be an array"),
            ("missing_shot_character_list", lambda p: p["shots"][0].pop("character_identifiers"), "registered identifiers"),
            ("unknown_shot_character", lambda p: p["shots"][0].update(character_identifiers=["unknown"]), "registered identifiers"),
            ("duplicate_shot_character", lambda p: p["shots"][0].update(character_identifiers=["speaker", "speaker"]), "duplicate identifiers"),
            ("missing_source", lambda p: p["characters"][0].update(source_identifiers=[]), "lacks sources"),
            ("unknown_source", lambda p: p["characters"][0].update(source_identifiers=["unknown"]), "registered identifiers"),
            ("missing_search_record", lambda p: p["characters"][0].update(reference_search=""), "reference_search"),
            ("missing_source_locator", lambda p: p["character_sources"][0].update(locator=""), "locator"),
            ("source_hash_changed", lambda p: p["character_sources"][0].update(research_sha256="0" * 64), "fingerprint differs"),
            ("free_design_without_reason", lambda p: p["characters"][0].update(reference_status="no_suitable_reference"), "fallback reason"),
            ("voice_file_used_as_visual_reference", lambda p: p["characters"][0].update(visual_reference_identifiers=["voice"]), "image or video"),
            ("missing_introduction", lambda p: p.update(character_introductions=[]), "exactly one"),
            ("wrong_introduction_name", lambda p: p["character_introductions"][0].update(display_name="人物乙"), "display_name differs"),
            ("future_identity_mismatch", lambda p: p["character_introductions"][0].update(current_identity="未来头衔"), "current_identity differs"),
            ("web_overlay_is_insufficient", lambda p: p["character_introductions"][0].update(render_mode="web_overlay"), "inside actual video"),
            ("late_introduction", lambda p: p["character_introductions"][0].update(start_seconds=0.4), "first visibility"),
            ("introduction_outlasts_shot", lambda p: p["character_introductions"][0].update(end_seconds=5), "within its shot"),
            ("boolean_time", lambda p: p["character_introductions"][0].update(start_seconds=False), "invalid introduction"),
            ("nonfinite_time", lambda p: p["character_introductions"][0].update(end_seconds=float("inf")), "invalid introduction"),
            ("wrong_branch", lambda p: p["character_introductions"][0].update(branch_identifier="other"), "no registered first"),
            ("invalid_appearance_time", lambda p: p["shots"][0].update(character_appearances=[
                {"character_identifier": "speaker", "first_visible_seconds": 4}]), "within shot"),
            ("empty_appearance_mapping", lambda p: p["shots"][0].update(character_appearances=[]), "must match shot"),
            ("unregistered_dialogue_speaker", lambda p: p["sound_events"][0].update(speaker_identifier="unknown"), "registered character"),
            ("malformed_identifier_value", lambda p: p["characters"][0].update(source_identifiers=[{}]), "registered identifiers"),
            ("malformed_introduction_reference", lambda p: p["character_introductions"][0].update(character_identifier={}), "registered first"),
        ]
        for name, mutate, expected in mutations:
            bad = copy.deepcopy(plan)
            mutate(bad)
            inspect(name, bad, expected)
        bad = copy.deepcopy(plan)
        bad["character_introductions"].append(dict(bad["character_introductions"][0],
                                                   introduction_identifier="duplicate"))
        inspect("duplicate_introduction", bad, "exactly one")

        # An actor enters after the shot starts; introduction uses first visibility.
        good = copy.deepcopy(plan)
        good["shots"][0]["character_appearances"] = [
            {"character_identifier": "speaker", "first_visible_seconds": 1},
        ]
        good["sound_events"][0].update(start_seconds=1.2, speech_spans=[[1.2, 3.7]])
        good["generation_units"][0]["sound_event_offsets"][0]["start_seconds"] = 1.2
        good["character_introductions"][0].update(start_seconds=1, end_seconds=3)
        inspect("delayed_visible_appearance", good)
        bad = copy.deepcopy(good)
        bad["character_introductions"][0].update(start_seconds=0)
        inspect("introduction_before_delayed_appearance", bad, "first visibility")
        bad = copy.deepcopy(good)
        bad["sound_events"][0].update(start_seconds=0.3, speech_spans=[[0.3, 3.7]])
        bad["generation_units"][0]["sound_event_offsets"][0]["start_seconds"] = 0.3
        inspect("speech_before_first_visibility", bad, "remain visible")

        # One voice event may span contiguous shots, but not a visibility gap or branch merge.
        good = copy.deepcopy(plan)
        good["shots"][0]["end_seconds"] = 2
        good["shots"].append(dict(good["shots"][0], shot_identifier="second_shot",
                                  start_seconds=2, end_seconds=4))
        good["generation_units"][0]["shot_identifiers"].append("second_shot")
        good["generation_units"][0]["required_capabilities"].append("multi_shot")
        inspect("continuous_speaker_across_shots", good)
        bad = copy.deepcopy(good)
        bad["shots"][1]["character_appearances"] = [
            {"character_identifier": "speaker", "first_visible_seconds": 2.5},
        ]
        inspect("speaker_visibility_gap", bad, "remain visible")
        bad = copy.deepcopy(good)
        bad["shots"][1]["branch_identifier"] = "alternate"
        bad["character_introductions"].append(dict(bad["character_introductions"][0],
            introduction_identifier="alternate_intro", branch_identifier="alternate",
            shot_identifier="second_shot", start_seconds=2, end_seconds=3))
        inspect("separate_branches_cannot_fill_speech_gap", bad, "remain visible")
        bad = copy.deepcopy(plan)
        bad["shots"][0]["end_seconds"] = 2
        inspect("speech_outlasts_visible_shot", bad, "remain visible")

        # Independent branches and separate exported timelines each need orientation.
        for separate_timeline in (False, True):
            good = copy.deepcopy(plan)
            if separate_timeline:
                good["timelines"].append(dict(good["timelines"][0], timeline_identifier="alternate",
                                               asset_identifier="video_alternate"))
                good["clips"].append(dict(good["clips"][0], clip_identifier="alternate_clip",
                                          timeline_identifier="alternate"))
            timeline = "alternate" if separate_timeline else "mainline"
            good["shots"].append(dict(good["shots"][0], shot_identifier="alternate_shot",
                                      branch_identifier="alternate", timeline_identifier=timeline))
            unit = good["generation_units"][0]
            unit["shot_identifiers"].append("alternate_shot")
            unit["required_capabilities"].append("multi_shot")
            good["character_introductions"].append(dict(good["character_introductions"][0],
                introduction_identifier="alternate_intro", branch_identifier="alternate",
                timeline_identifier=timeline, shot_identifier="alternate_shot"))
            inspect("separate_timeline_covered" if separate_timeline else "separate_branch_covered", good)
            good["character_introductions"].pop()
            inspect("missing_timeline_introduction" if separate_timeline else "missing_branch_introduction",
                    good, "exactly one")

        for check in ("character_appearance", "character_introduction"):
            bad = copy.deepcopy(plan)
            bad["manual_reviews"] = [row for row in bad["manual_reviews"] if row["check"] != check]
            inspect("missing_" + check + "_review", bad, "requires one file-bound", reviews=True)
            bad = copy.deepcopy(plan)
            row = next(row for row in bad["manual_reviews"] if row["check"] == check)
            row["bound_sha256"] = "0" * 64
            inspect("stale_" + check + "_review", bad, "another file", reviews=True)
            row["bound_sha256"] = digest(media)
            row["character_identifiers"] = []
            inspect("incomplete_" + check + "_review", bad, "omits visible", reviews=True)
        bad = copy.deepcopy(plan)
        next(row for row in bad["manual_reviews"] if row["check"] == "character_introduction")[
            "introduction_identifiers"] = []
        inspect("review_omits_introduction_ids", bad, "omits introductions", reviews=True)

        audit = inspect("legacy_plan_remains_readable", legacy)
        assert audit.warnings and "have not been validated" in audit.warnings[0]
        passed("legacy_warning_explicit")
        (base / "environment.json").write_text(json.dumps(environment))
        for candidate, expected in ((plan, "delivery_records_checked"), (legacy, "not_validated_legacy")):
            candidate["environment_sha256"] = digest(base / "environment.json")
            path = base / "plan.json"
            path.write_text(json.dumps(candidate))
            report_path = base / "report.json"
            subprocess.run([sys.executable, str(ROOT / "scripts/validate_video_production.py"),
                            str(path), "--delivery", "--report", str(report_path)],
                           check=True, capture_output=True, timeout=60)
            report = json.loads(report_path.read_text())
            assert report["character_contract_status"] == expected and report["status"] == "passed"
            passed("cli_" + expected)
        template = ROOT / "assets/video-production-plan.template.json"
        instantiated = json.loads(re.sub(r"\{\{.*?\}\}", "synthetic", template.read_text()))
        # This fixture isolates the unchanged character contract. Submission and
        # source-PTS contracts have their own schema 1.2 regressions.
        instantiated["schema_version"] = "1.1"
        for reference in instantiated["references"]:
            reference.update(path=media.name, content_sha256=digest(media))
        instantiated["character_sources"][0].update(research_file=evidence.name,
                                                    research_sha256=digest(evidence))
        for binding in instantiated["generation_units"][0]["reference_bindings"]:
            binding["slot"] = "audio_1" if binding["purpose"] == "voice" else "image_1"
        template_environment = copy.deepcopy(environment)
        template_environment["providers"][0]["duration_seconds"] = {
            "minimum": 1, "maximum": 10, "allowed_values": [10],
        }
        audit = validate_plan(instantiated, template_environment, base)
        assert not audit.errors, audit.errors
        passed("instantiated_template_reference_bindings")
        bad = copy.deepcopy(instantiated)
        bad["generation_units"][0]["reference_bindings"] = [
            binding for binding in bad["generation_units"][0]["reference_bindings"]
            if binding["purpose"] != "voice"
        ]
        audit = validate_plan(bad, template_environment, base)
        assert any("lacks actual reference binding" in error for error in audit.errors), audit.errors
        passed("instantiated_template_missing_voice_binding")
        template_environment["providers"][0]["capabilities"]["image_reference"] = {
            "status": "unknown", "evidence": [],
        }
        audit = validate_plan(instantiated, template_environment, base)
        assert any("image_reference is not verified" in error for error in audit.errors), audit.errors
        passed("instantiated_template_unknown_capability_blocks_plan")
        subprocess.run([sys.executable, str(ROOT / "scripts/validate_video_production.py"),
                        str(template), "--template"], check=True, capture_output=True)
        passed("new_template_syntax")
        failed = subprocess.run([sys.executable, str(ROOT / "scripts/validate_video_production.py"),
                                 str(template), "--template", "--delivery"], capture_output=True)
        assert failed.returncode == 1
        passed("template_cannot_claim_delivery")
        malformed = base / "malformed.json"
        malformed.write_text("{")
        failed = subprocess.run([sys.executable, str(ROOT / "scripts/validate_video_production.py"),
                                 str(malformed), "--report", str(base / "malformed-report.json")],
                                capture_output=True)
        assert failed.returncode == 1 and json.loads((base / "malformed-report.json").read_text())[
            "character_contract_status"] == "failed"
        passed("malformed_json_has_diagnostic_report")

    report = {
        "passed": len(results), "cases": results,
        "limits": "Synthetic identity declarations, encoded test patterns and review records. "
                  "No actual character likeness, visible titles, human approval or learner effect is established.",
    }
    if args.report:
        if not args.report.parent.is_dir():
            parser.error("Report parent directory must already exist")
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
