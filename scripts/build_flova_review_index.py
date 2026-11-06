#!/usr/bin/env python3
"""Build a sanitized coverage index from a retained public catalogue screen."""

import argparse
import json
from pathlib import Path
import re

# Reading depth is an explicit research record, not inferred from keyword counts.
COMPLETE = {
    1: ("production_units", "区分实际shot与生成单元；能力决定自然分段，输出按源区间装配"),
    6: ("reference_pack", "固定角色身份、区分共通风格与各人面部、状态和服装变体"),
    16: ("direction", "场地调度地图、机位与人物朝向、首尾状态、接触释放和光向"),
    18: ("performance", "可观察目标、倾听与反应、触发微动作及状态延续；不继承输赢压力公式"),
    21: ("sound_timeline", "真实声音作为时序依据；身份/时序/配乐参考分开，绝对与相对时间对应"),
    26: ("previsualization", "独立镜头与同镜时刻分开；板不是首帧，格数不是秒数"),
    111: ("production_system", "实体/风格/分镜/模型编译分层；不采纳夸大模型参数和预算降档"),
    113: ("direction", "焦点、机位、运动动机和剪辑连续性；拒绝焦段情绪铁律"),
    115: ("graphics", "统一图形运动语汇、线宽与色板，按教学事件组织动作"),
    116: ("animation", "角色与动态图形分路线，准备/动作/收势和局部修复"),
    124: ("instructional_visuals", "定义、组成、逻辑、参数和应用；准确文字和数值用确定性呈现"),
    153: ("reference_pack", "可见内容和遮挡补全分开、对象边界与唯一归属；不接受100%生成保真承诺"),
    160: ("audio_postproduction", "尾声检测和波形可辅助；正常台词/尾字结束后才处理杂音"),
    161: ("assembly", "拼接先核编码、帧率、音轨与顺序；转场需真实区间和事件核对"),
    180: ("storyboard", "可拍行为、具体相机位置、接缝卡与首镜核对；不继承80/15/5或镜头配额"),
    201: ("transitions", "首尾状态、视线、焦点、动作与声音的转场承接"),
    211: ("scene_reference", "空间骨架、材质/光影/时间痕迹和局部视图；不继承固定版式"),
    235: ("instructional_video", "主干/条件/例外、依赖/并行/反馈与局部下钻；不继承课件和字数配额"),
    237: ("transcript_driven", "逐字稿观点来源、出现时间、视觉参数和动效对应"),
    282: ("reference_pack", "角色/场景/道具/声线与多视角参考包；按风险选素材，不机械量产"),
    286: ("lighting", "光源/光向/曝光与连戏；不继承段落光型、善恶冷暖和百分比"),
    304: ("point_of_view", "视线链、局部身体、可见物证和参考职责；严格POV仅按课程视点采用"),
    330: ("multiple_speakers", "独立声线、话轮、倾听反应、音频驱动口型；不统一静音正确原声"),
    331: ("observational_video", "真实劳作、自然微动、空气层次与克制镜头；合成不能冒充实拍"),
}
TARGETED = {
    8: "自然话轮、多人固定声线与分段衔接",
    9: "来源正文、专名发音、估计和实际长度分开",
    27: "声音节奏与表演/镜头对应，音乐驱动仅按教学需要",
    45: "角色音色锚点与参考用途",
    61: "动作预演板、动作节拍和物理接续",
    89: "文献→工艺流程→动作声；发现总时长45秒与3×30秒冲突，不采纳规格",
    90: "来源事实保持、图形语汇与旁白/字幕对应",
    162: "翻译、自动字幕和逆向分析分别处理，重配后重对齐",
    238: "组件层级和组装次序；精确结构须权威制作验证",
    279: "形态锚点、生长顺序和科学依据核对",
    293: "线条/动作风格一致及旁白停顿",
    296: "UI状态与动作/音效对应；确定性运行与实际录制优先",
    326: "参考面板与内部切镜；多镜合单元必须实测支持",
}
REFERENCE_READS = {
    1: ["media-generation"],
    21: ["媒体生成", "提示词写作", "剪辑交付"],
}


def retained_read_log(path=None):
    """Index reading claims by source identity and body hash, never catalogue position."""
    path = path or Path(__file__).resolve().parents[1] / "assets/flova-skill-review-index.json"
    try:
        previous = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return {
        (row.get("public_skill_identifier"), row.get("body_sha256")): {
            key: row.get(key) for key in (
                "main_read_depth", "reference_contents_read", "capability",
                "disposition", "decision",
            )
        }
        for row in previous.get("items", [])
        if isinstance(row, dict) and
        row.get("main_read_depth") in {
            "complete_main_body_read", "selected_main_body_paragraphs_read"
        }
    }


def build(screen, read_log=None):
    source_items = screen.get("items", [])
    identifiers = [row.get("public_skill_identifier") for row in source_items]
    if len(source_items) != 332 or len(set(identifiers)) != 332:
        raise ValueError("This research record requires the verified 332-item snapshot")
    read_log = retained_read_log() if read_log is None else read_log
    output = []
    for row in source_items:
        reference_reads = []
        position = row["catalogue_position"]
        title = row["title"]
        source_key = (row["public_skill_identifier"], row["body_sha256"])
        if source_key in read_log:
            retained = read_log[source_key]
            capability = retained["capability"]
            decision = retained["decision"]
            depth = retained["main_read_depth"]
            disposition = retained["disposition"]
            reference_reads = retained.get("reference_contents_read") or []
        elif re.search(r"视频|短片|短剧|MV|电影|导演|动画|分镜|运镜|故事|播客|音频|视觉|风格|三视|角色|服装|建模|素材", title, re.I):
            capability, decision = "style_scenario_or_repeated_method", (
                "全正文关键词筛查；共通流程归入已精读模块。专属题材、审美与模型参数"
                "不设为课程默认；课程需要此路线时再精读适用正文及附件。")
            depth, disposition = "full_main_body_keyword_screen", "conditional_source_not_default"
        else:
            capability, decision = "adjacent_or_outside_video_environment", (
                "全正文关键词筛查；图像/营销/文案/设计等邻接用途按需选用，"
                "不将单场景模板或平台约束加入通用视频环境。")
            depth, disposition = "full_main_body_keyword_screen", "not_added_to_video_defaults"
            reference_reads = []
        output.append({
            "catalogue_position": position,
            "public_skill_identifier": row["public_skill_identifier"],
            "title": title, "catalogue_url": screen["catalogue_url"],
            "body_character_count": row["body_character_count"],
            "body_sha256": row["body_sha256"],
            "reference_names": row["reference_names"],
            "main_read_depth": depth,
            "reference_contents_read": reference_reads,
            "capability": capability, "disposition": disposition, "decision": decision,
        })
    return {
        "retrieved_on": screen["retrieved_on"], "catalogue_url": screen["catalogue_url"],
        "retrieval_method": screen["retrieval_method"],
        "coverage": {
            "unique_main_bodies_retrieved_and_screened": len(output),
            "main_body_characters": sum(row["body_character_count"] for row in output),
            "complete_main_bodies_read": sum(
                row["main_read_depth"] == "complete_main_body_read" for row in output),
            "additional_targeted_main_bodies": sum(
                row["main_read_depth"] == "selected_main_body_paragraphs_read" for row in output),
            "advertised_reference_documents": sum(len(row["reference_names"]) for row in output),
            "reference_contents_read": sum(len(row["reference_contents_read"]) for row in output),
        },
        "limits": (
            "全目录正文已取得并做关键词筛查，不等于逐字精读全部正文。只对明确列出的正文与附属"
            "内容记录精读；未读附属不作为采纳依据。来源是平台工作流范例，不是科学或当前模型能力证明。"
            "索引仅保留公开来源标识、文本哈希和独立采纳摘要，不含完整正文、签名媒体URL或账户字段。"),
        "items": output,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screen", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.output.parent.is_dir():
        raise ValueError("Output parent directory must already exist")
    result = build(json.loads(args.screen.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["coverage"], ensure_ascii=False))


if __name__ == "__main__":
    main()
