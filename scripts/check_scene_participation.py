#!/usr/bin/env python3
"""Synthetic cross-subject contract probes; never course approval or learner evidence."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from validate_scene_interaction_plan import validate_plan


ROOT = Path(__file__).resolve().parents[1]


def sample(beat, kind, action, evidence, reason):
    return {
        "beat_identifier": beat, "interaction_identifier": f"interaction_{beat}",
        "objective_identifiers": [f"objective_{beat}"], "event_class": "judgment",
        "knowledge_action": action, "evidence_to_notice": [evidence],
        "scene_anchor": {"object_identifier": f"object_{beat}",
                         "trigger_type": "npc_action",
                         "trigger_description": "主引导NPC把当前对象递向学习者，视频在对象稳定帧开放入口。",
                         "recognition_cue": "当前人物交到桌面的同一对象，进入前可辨认。",
                         "availability": "对象停稳后开放；手机保留全对象，退出恢复同一帧。"},
        "surface": {"kind": kind, "selection_reason": reason,
                    "simpler_representation": "已检查视频近景和二维控件能否支持相同判断与证据。"},
        "information_layers": {
            "before_action": [{"content": action, "purpose": "说明当前需要完成的知识动作。",
                               "delivery": "control_label"}],
            "on_demand": [{"content": "从当前对象查看完整材料、条件与来源，保留原顺序。",
                           "purpose": "为取证或核对提供可发现入口。", "delivery": "scene_object"}],
            "after_action": [{"content": "提交后定位所用依据与结果的关系，提供修订入口。",
                             "purpose": "解释当前关系，未提交任务不提前展示答案。",
                             "delivery": "scene_object"}],
            "source_access": "完整材料、规则和引用位置在当前对象的来源入口可访问。"},
        "attention": {"primary_focus": action, "pause_policy": "pause_on_entry",
                      "conflicting_narration": "pause", "initial_unit_limit": 1,
                      "budget_basis": "已在视频建立对象用途；首屏只补当前动作，必要材料取用后不限时查看。"},
        "feedback": {"visible_response": "当前对象显示学习者实际标注、输出或保存作品。",
                     "knowledge_response": "比较所选依据与目标关系；指出缺少的条件或联系。",
                     "repair_action": "回到原对象检查条件并修改，保留首次答案。",
                     "scene_connection": "交回同一对象，当前事务读取已保存结果。",
                     "story_consequence": "对象保留学习者的实际标注，主引导NPC据此改变回应和下一步条件。",
                     "branch_rejoin": f"在{beat}对应恢复秒回到主引导NPC面前的第一人称位置。"},
        "completion": {"mode": "practice_with_feedback", "evidence_required": True,
                       "evidence_fields": ["selection", "relationship_explanation"],
                       "decision_rule": "所选对象、条件与解释的关系成立后完成练习。",
                       "action_only_is_mastery": False, "close_behavior": "hold_pending"},
        "restoration": {"return_anchor_identifier": f"object_{beat}",
                        "resume_time_reference": f"video-event-map.json#{beat}",
                        "resume_interval_reason": None,
                        "state_fields": ["video_time", "viewpoint", "object_state", "learner_response",
                                         "focus", "audio", "captions", "completion"]},
        "accessibility": {"input_methods": ["keyboard", "touch", "pointer"],
                          "equivalent_action": "对象选择、定位或数值输入替代精细拖动和旋转。",
                          "equivalent_evidence": "仍判断同一关系并提交依据，额外提示单独登记。"}
    }


def main():
    events = [
        sample("B01", "object_inspection", "选出支持主张的原句，并说明原句与主张的联系。",
               "两封信的作者、日期、完整原文和引文位置。",
               "取证要求原文与主张对照；同一信件的正面阅读视图保留完整资料，视频近景不足以逐句选择。"),
        sample("B02", "simulation", "先预测，再调节流量并解释条件相同时的水位变化。",
               "初始水位、流入流出条件与确定性计算结果。",
               "二维仪器可改变变量并即时显示规则结果，无需3D；固定视频不能运行学习者的条件组合。"),
        sample("B03", "spatial_3d", "剖切后定位弯管的连接，并解释内外路径关系。",
               "同一对象的空间连接、内外表面和截面方向。",
               "任务要求自主比较连续视角与剖切面；已检验的固定二维图不能充分支持该操作。"),
        sample("B04", "scene_control", "标出两点高度，写出高度差和单位。",
               "测量基准、两个点的高度与共同单位。",
               "对象旁标记和数值输入足以表达关系，不需要深层模型或问答卡。"),
        sample("B05", "object_inspection", "为新材料写一句主张，并附上材料依据。",
               "尚未练习过的新材料和允许使用的来源。",
               "作品输入附着在同一稿件；写作是目标，需要正面阅读和输入空间，短卡不足以同时引用。")
    ]
    events[4]["completion"]["mode"] = "independent_submission"
    events[4]["completion"]["decision_rule"] = "先保存完整首次作品再显示量规；待审不记作掌握。"
    observation = sample("B06", "video_only", None, "镜头中的光照方向及其造成的影子变化。",
                         "视频清楚呈现变化，此时无需作答或操控。")
    observation.update(event_class="observation", interaction_identifier=None, feedback=None)
    observation["information_layers"]["before_action"][0]["content"] = "注意光照方向改变后影子怎样变化。"
    observation["attention"].update(primary_focus="观察光照方向与影子变化", pause_policy="continue",
                                    conflicting_narration="not_applicable")
    observation["completion"].update(mode="content_presented", evidence_required=False,
                                     evidence_fields=[], close_behavior="not_applicable",
                                     decision_rule="指定画面证据已呈现，仅推动叙事。")
    events.append(observation)
    optional = sample("B07", "scene_card", "按需查看当前仪器的单位说明。",
                      "仪器的单位和读数位置。",
                      "只有当前单位的短提示，场景辅助卡足够，无需进入实验视图。")
    optional["event_class"] = "exploration"
    optional["completion"].update(mode="optional_exploration", evidence_required=False,
                                  evidence_fields=[], close_behavior="return_optional",
                                  decision_rule="查看后可返回，开启帮助不作为掌握证据。")
    events.append(optional)
    plan = {"schema_version": "1.1", "experience_profile": "video_led_web",
            "continuity": {
                "primary_guide_identifier": "guide_lin",
                "primary_guide_role": "林老师贯穿开场到结课，交接对象、等待操作、回应结果并推进现场。",
                "primary_point_of_view": "learner_first_person",
                "point_of_view_return_rule": "短暂对象近景后沿同一物件和林老师的声音返回第一人称位置。",
                "branch_policy": "local_consequence_then_rejoin",
                "learner_language_policy": "只显示当前对象、动作、后果和下一步，不展示内部核查或待审状态。"
            },
            "coverage_scope": "full_course", "events": events}
    event_map = {"events": [
        {"beat_id": row["beat_identifier"], "interaction_id": row["interaction_identifier"],
         "event_class": row["event_class"], "evidence_required": row["completion"]["evidence_required"],
         "pause_seconds": i * 10, "resume_seconds": i * 10}
        for i, row in enumerate(events)]}
    results = []

    def check(name, changed, expected=None, mapped=event_map):
        errors = validate_plan(changed, mapped)
        assert (not errors if expected is None else any(expected in error for error in errors)), (name, errors)
        results.append(name)

    check("seven_cross_subject_and_event_cases", plan)
    macro = copy.deepcopy(plan)
    macro["continuity"].update(
        primary_guide_identifier=None,
        primary_guide_role=None,
        primary_point_of_view="macro_observational",
        continuity_anchor_identifier="system_map",
        continuity_anchor_role="同一时空关系图承接事件、证据与返回位置。",
        point_of_view_return_rule="始终回到同一系统时间线和已保存的关系状态。",
        branch_policy="linear_no_branch",
    )
    check("macro_observational_without_character", macro)
    for name, edit, message in [
        ("click_only_judgment", lambda p: p["events"][0]["completion"].update(evidence_fields=["click_count"]), "action-only"),
        ("close_bypasses_required_task", lambda p: p["events"][0]["completion"].update(close_behavior="return_optional"), "hold_pending"),
        ("missing_spatial_reason", lambda p: p["events"][2]["surface"].update(selection_reason=""), "selection_reason"),
        ("reading_competes_with_video", lambda p: p["events"][0]["attention"].update(pause_policy="continue"), "pause_policy"),
        ("local_reading_budget_exceeded", lambda p: p["events"][0]["attention"].update(initial_unit_limit=0), "local budget"),
        ("lost_draft_on_return", lambda p: p["events"][0]["restoration"]["state_fields"].remove("learner_response"), "learner_response"),
        ("missing_keyboard_equivalent", lambda p: p["events"][1]["accessibility"].update(input_methods=["touch"]), "keyboard"),
        ("duplicate_beat", lambda p: p["events"][1].update(beat_identifier="B01"), "unique"),
        ("unresolved_template", lambda p: p["events"][0].update(knowledge_action="{{action}}"), "unresolved"),
        ("broken_event_binding", lambda p: p["events"][0].update(interaction_identifier="wrong"), "identifier differs"),
        ("missing_full_course_beat", lambda p: p["events"].pop(), "exactly match"),
        ("reordered_events", lambda p: p["events"].reverse(), "exactly match"),
        ("malformed_nested_object", lambda p: p["events"][0].update(completion=[]), "must be an object"),
        ("malformed_event_class", lambda p: p["events"][0].update(event_class=[]), "event_class"),
        ("boolean_budget", lambda p: p["events"][0]["attention"].update(initial_unit_limit=True), "integer"),
        ("missing_primary_guide", lambda p: p["continuity"].update(primary_guide_identifier=""),
         "primary_guide_identifier"),
        ("detached_interaction_trigger",
         lambda p: p["events"][0]["scene_anchor"].update(trigger_type="task_sidebar"),
         "trigger_type"),
        ("missing_story_consequence",
         lambda p: p["events"][0]["feedback"].update(story_consequence=""),
         "story_consequence"),
        ("malformed_presentation_reference",
         lambda p: p["events"][0]["scene_anchor"].update(presentation_anchor_reference=[]),
         "presentation_reference#anchor_identifier"),
        ("empty_presentation_reference",
         lambda p: p["events"][0]["scene_anchor"].update(presentation_anchor_reference=""),
         "presentation_reference#anchor_identifier"),
        ("ambiguous_presentation_reference",
         lambda p: p["events"][0]["scene_anchor"].update(presentation_anchor_reference="ref#anchor#extra"),
         "presentation_reference#anchor_identifier"),
    ]:
        changed = copy.deepcopy(plan)
        edit(changed)
        check(name, changed, message)
    selected = copy.deepcopy(plan)
    selected.update(coverage_scope="selected_events", events=[selected["events"][1], selected["events"][4]])
    check("declared_partial_scope", selected)
    check("invalid_plan_root", [], "must be an object")
    check("invalid_event_map_shape", plan, "array of objects", mapped={"events": ["broken"]})
    legacy = copy.deepcopy(plan)
    legacy["schema_version"] = "1.0"
    legacy.pop("continuity")
    for row in legacy["events"]:
        row["scene_anchor"].pop("trigger_type", None)
        row["scene_anchor"].pop("trigger_description", None)
        if isinstance(row.get("feedback"), dict):
            row["feedback"].pop("story_consequence", None)
            row["feedback"].pop("branch_rejoin", None)
    check("legacy_one_zero_compatible", legacy)
    shifted = copy.deepcopy(event_map)
    shifted["events"][0]["resume_seconds"] = 4
    check("unexplained_skipped_video_interval", plan, "resume_interval_reason", mapped=shifted)
    changed = copy.deepcopy(plan)
    changed["events"][0]["restoration"]["resume_interval_reason"] = "略过已核对的重复停留帧，不省略教学证据。"
    check("explained_continuation_time", changed, mapped=shifted)
    with tempfile.TemporaryDirectory(prefix="scene-participation-check-") as directory:
        base = Path(directory)
        plan_path, map_path = base / "plan.json", base / "map.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        map_path.write_text(json.dumps(event_map), encoding="utf-8")
        command = [sys.executable, str(ROOT / "scripts/validate_scene_interaction_plan.py"), str(plan_path)]
        subprocess.run(command, check=True)
        subprocess.run(command + ["--event-map", str(map_path)], check=True)
    print(json.dumps({"status": "passed", "contract_probes": len(results),
                      "subject_and_event_examples": len(events), "cases": results,
                      "limits": "Synthetic contract checks, not content acceptance or teaching-effect evidence."},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
