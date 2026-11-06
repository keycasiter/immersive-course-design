#!/usr/bin/env python3
"""Synthetic regressions for learner-facing framing and language lint."""

import copy

from validate_learner_experience import validate, validate_page


BASE = {
    "course_title": "为什么抛出的球会再次落地",
    "opening": {
        "course_introduction": "林老师接住球，问你愿不愿意一起看看它的运动。",
        "background_input": "你站在操场边，球刚从林老师手中抛出。",
        "motivating_problem": "球在什么时候到达最高点？",
        "learner_role": "你负责观察轨迹并调整下一次抛球条件。",
        "first_action": "在球经过标线时按下标记。",
        "transition": "林老师把标记结果叠到同一段轨迹上。",
        "understanding_check": "你能指出现在观察的是球的高度变化。",
        "orientation_bootstrap": {
            "host_welcome": "林老师转向你，把球递过来，并说明今天一起研究这次抛球。",
            "minimal_world_model": "球离手后高度会随时间变化。",
            "key_objects_and_terms": "球、标线和计时器在画面中逐一出现。",
            "learning_journey_preview": "先观察，再改变条件，最后解释轨迹。",
            "role_and_collaboration": "林老师抛球并回应，你负责观察、预测和操作。",
            "first_action_handoff": "林老师说“球过线时就按这里”。",
            "comprehension_safeguard": "不要求预先知道函数，可先看一次慢速轨迹。"
        }
    },
    "scenes": [
        {
            "title": "第一次抛球",
            "narration": "林老师抛球并等待你的标记。",
            "task": {
                "prompt": "标出球经过最高点前后的两个位置。",
                "feedback": {
                    "success": "两处位置已经留在轨迹上，林老师请你比较高度。",
                    "needs_help": "回看球开始下降的瞬间，再移动第二个标记。"
                },
                "recovery": {
                    "hints": ["注意球从上升变成下降的瞬间。"],
                    "explanation": "修改标记后，林老师会用同一段轨迹继续。"
                }
            }
        }
    ]
}


def main():
    assert not validate(BASE, {})

    leaked = copy.deepcopy(BASE)
    leaked["scenes"][0]["task"]["feedback"]["success"] = "核查完成，继续核查下一项。"
    errors = validate(leaked, {})
    assert any("internal workflow phrase" in error for error in errors), errors

    generic = copy.deepcopy(BASE)
    generic["course_title"] = "抛物线观察台"
    errors = validate(generic, {})
    assert any("generic framing term" in error for error in errors), errors
    assert not validate(generic, {"观察台": "真实天文观测课程中的原生设备名称"})
    wireframe = """```text
[根 待核查] [继续核查]
```"""
    errors = validate_page(wireframe, {})
    assert any("wireframe leaks internal workflow phrase" in error for error in errors), errors
    scientific = copy.deepcopy(BASE)
    scientific["scenes"][0]["narration"] = "这是一个待验证的猜想，需要比较两次观测。"
    assert not validate(scientific, {})
    visible_table = """## 状态与自然文案
| 状态 | 学习者可见文案 |
|---|---|
| current | 进入核查 |
"""
    errors = validate_page(visible_table, {})
    assert any("line_4" in error for error in errors), errors
    assert not validate_page("设计说明提到进入核查，但不在学习者可见区。", {})

    print("PASS: learner-experience framing and language regressions")


if __name__ == "__main__":
    main()
