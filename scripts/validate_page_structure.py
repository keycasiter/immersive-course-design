#!/usr/bin/env python3
"""Check the shared immersive course page structure."""

import argparse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
from contract_checks import PLACEHOLDER


REGIONS = (
    "scene-media", "scene-shade", "course-header", "course-entry",
    "scene-objects", "course-caption", "course-actions", "task-layer", "course-status",
)
VIDEO_BODY_CHILD_TAGS = {"main", "script", "style"}
VIDEO_ROOT_CHILD_IDS = set(REGIONS) | {"course-atmosphere"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.nodes = []
        self.visible_text = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        node = {
            "tag": tag, "attrs": attrs,
            "parent_id": self.stack[-1]["attrs"].get("id") if self.stack else None,
            "parent_tag": self.stack[-1]["tag"] if self.stack else None,
            "ancestor_ids": {n["attrs"].get("id") for n in self.stack},
            "ancestor_classes": {c for n in self.stack for c in n["attrs"].get("class", "").split()},
        }
        self.nodes.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if not any(node["tag"] in ("script", "style") for node in self.stack):
            self.visible_text.append(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("page", type=Path)
    parser.add_argument("--mode", choices=("static_markup", "runtime_dom"), default="static_markup")
    parser.add_argument("--runtime-evidence", type=Path,
                        help="JSON receipt for a DOM captured by an actual browser")
    args = parser.parse_args()
    text = args.page.read_text(encoding="utf-8")
    html = PageParser()
    html.feed(text)
    errors = []
    video_profile = any(n["tag"] == "body" and
                        n["attrs"].get("data-experience-profile") == "video_led_web"
                        for n in html.nodes)
    placeholder_content = html.visible_text + [
        value for node in html.nodes for value in node["attrs"].values() if isinstance(value, str)]
    explicit_token = re.compile(r"\{\{(?:[A-Z][A-Z0-9_]*|[^{}]*[\u4e00-\u9fff][^{}]*)\}\}")
    if any(PLACEHOLDER.search(value) for value in placeholder_content) or explicit_token.search(text):
        errors.append("页面仍有未替换的模板内容")
    if args.mode == "runtime_dom":
        import hashlib
        import json
        try:
            if args.runtime_evidence is None:
                raise ValueError("runtime_dom 必须提供实际浏览器 DOM 的采集记录")
            receipt = json.loads(args.runtime_evidence.read_text(encoding="utf-8"))
            if not isinstance(receipt, dict):
                raise ValueError("DOM采集记录必须为对象")
            expected = hashlib.sha256(args.page.read_bytes()).hexdigest()
            if receipt.get("dom_sha256") != expected:
                errors.append("实际DOM与采集记录哈希不一致")
            for key in ("url", "captured_at", "browser", "application_version", "viewport"):
                if not receipt.get(key):
                    errors.append(f"DOM采集记录缺少 {key}")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    ids = Counter(n["attrs"]["id"] for n in html.nodes if n["attrs"].get("id"))
    if any(count != 1 for count in ids.values()):
        errors.append("页面标识重复")
    root = next((n for n in html.nodes if n["attrs"].get("id") == "course-stage"), None)
    if not root or root["tag"] != "main":
        errors.append("缺少 main#course-stage")
    if video_profile:
        body = next((n for n in html.nodes if n["tag"] == "body"), None)
        if body:
            body_children = [n for n in html.nodes if n["parent_tag"] == "body"]
            unexpected_body = [
                n for n in body_children
                if n["tag"] not in VIDEO_BODY_CHILD_TAGS and n["attrs"].get("id") != "course-stage"
            ]
            if unexpected_body:
                tags = ", ".join(sorted({node["tag"] for node in unexpected_body}))
                errors.append(f"video_led_web 的 body 不能包裹常驻布局区域：{tags}")
        root_children = [
            n for n in html.nodes
            if n["parent_id"] == "course-stage" and n["tag"] not in ("script", "style")
        ]
        unexpected_root = [
            n for n in root_children
            if n["attrs"].get("id") not in VIDEO_ROOT_CHILD_IDS
        ]
        if unexpected_root:
            labels = ", ".join(
                sorted({node["attrs"].get("id") or node["tag"] for node in unexpected_root})
            )
            errors.append(f"video_led_web 的唯一根舞台不能包含额外并行区域：{labels}")
        atmosphere = [n for n in html.nodes if n["attrs"].get("id") == "course-atmosphere"]
        if len(atmosphere) > 1:
            errors.append("course-atmosphere must be unique")
        for layer in atmosphere:
            if layer["attrs"].get("aria-hidden") != "true" or "inert" not in layer["attrs"]:
                errors.append("course-atmosphere must be aria-hidden and inert")
            descendants = [n for n in html.nodes if "course-atmosphere" in n["ancestor_ids"]]
            if any(n["tag"] not in {"img", "div", "span"} for n in descendants):
                errors.append("course-atmosphere may only contain silent noninteractive visual layers")
        media = next((n for n in html.nodes if n["attrs"].get("id") == "scene-media"), None)
        if media and not any(
                "scene-media" in node["ancestor_ids"] and node["tag"] in ("video", "img", "canvas")
                for node in html.nodes
        ):
            errors.append("video_led_web 的 scene-media 必须包含 video、img 或 canvas 主媒体")
    for region in REGIONS:
        nodes = [n for n in html.nodes if n["attrs"].get("id") == region]
        if len(nodes) != 1 or nodes[0]["parent_id"] != "course-stage":
            errors.append(f"{region} 必须是 course-stage 的唯一直接子区域")
    surfaces = [n for n in html.nodes if "task-surface" in n["attrs"].get("class", "").split()]
    for class_name in ("task-surface", "task-header", "task-body", "task-footer"):
        nodes = [n for n in html.nodes if class_name in n["attrs"].get("class", "").split()]
        if video_profile and not surfaces:
            if nodes:
                errors.append(f"{class_name} 不能脱离实际 task-surface")
            continue
        if len(nodes) != 1 or "task-layer" not in nodes[0]["ancestor_ids"]:
            errors.append(f"task-layer 内须有唯一的 {class_name}")
        elif class_name != "task-surface" and "task-surface" not in nodes[0]["ancestor_classes"]:
            errors.append(f"{class_name} 须位于 task-surface 内")
    if surfaces:
        attrs = surfaces[0]["attrs"]
        if video_profile:
            role = attrs.get("role")
            if role not in ("region", "dialog"):
                errors.append("视频场景辅助表面须声明 region 或 dialog")
            if not attrs.get("aria-label") and not (
                    attrs.get("aria-labelledby") and
                    all(ids.get(identifier) == 1 for identifier in attrs["aria-labelledby"].split())):
                errors.append("视频场景辅助表面须有可访问名称")
            if role == "dialog" and attrs.get("aria-modal") not in ("true", "false"):
                errors.append("场景 dialog 须显式声明是否模态")
        elif attrs.get("role") != "dialog" or attrs.get("aria-modal") != "true":
            errors.append("工作面须声明 dialog 和 aria-modal")
    styles = [n for n in html.nodes if n["tag"] == "link"
              and n["attrs"].get("rel") == "stylesheet"]
    if args.mode == "static_markup" and not any(
            Path(n["attrs"].get("href", "")).name == "course-page.css" for n in styles):
        errors.append("缺少共用样式 course-page.css")
    for node in styles:
        href = node["attrs"].get("href", "")
        if args.mode == "static_markup" and href and not href.startswith(("http:", "https:", "//")):
            if not (args.page.parent / href).is_file():
                errors.append(f"样式文件不存在：{href}")
    if errors:
        raise SystemExit("\n".join(errors))
    if video_profile:
        print(f"页面结构通过：{len(REGIONS)}个语义区域，{len(surfaces)}个辅助表面；视频场景控件另作实际验收。")
    else:
        print(f"页面结构通过：{len(REGIONS)}个固定区域，1个工作面，共用CSS。")


if __name__ == "__main__":
    main()
