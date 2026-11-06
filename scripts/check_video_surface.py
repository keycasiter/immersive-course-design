#!/usr/bin/env python3
"""Headless probes of the generic video surface, with an isolated UI state harness.

Requires Python Playwright/Chromium and ffmpeg. Does not test a course runtime.
"""

import argparse
import base64
import json
from pathlib import Path
import re
import tempfile

from playwright.sync_api import sync_playwright, expect

from check_video_production import ROOT, make_media


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--screenshot-directory", type=Path)
    parser.add_argument("--browser-channel", help="Use an installed channel, for example chrome")
    args = parser.parse_args()
    if args.screenshot_directory and not args.screenshot_directory.is_dir():
        parser.error("Screenshot parent directory must already exist")
    if args.report and not args.report.parent.is_dir():
        parser.error("Report parent directory must already exist")
    results = []
    with tempfile.TemporaryDirectory(prefix="video-surface-") as temporary:
        media = make_media(Path(temporary), "surface.mp4", "testsrc2=size=320x180:rate=24:duration=4")
        content = (ROOT / "assets/video-led-course-page.template.html").read_text()
        content = re.sub(r'<link rel="stylesheet"[^>]+>', "", content)
        content = re.sub(r'<script type="module"[^>]+></script>', "", content)
        long_material = "<p>对照材料中的相同条件、不同结果和遗漏信息，说明哪些结论仍需要更多资料。</p>" * 18
        replacements = {
            "COURSE_TITLE": "通用布局验证",
            "COURSE_VIDEO_LABEL": "合成验证视频",
            "APPROVED_VIDEO_FILE": "data:video/mp4;base64," + base64.b64encode(media.read_bytes()).decode(),
            "CAPTIONS_VTT": "data:text/vtt,WEBVTT%0A%0A",
            "ONE_SHORT_START_CUE": '<button id="start">播放</button>',
            "ON_DEMAND_PLAYBACK_CAPTION_MUTE_CONTROLS_AND_CHAPTER_NAVIGATION":
                '<button id="hide-controls">收起控制</button><button id="chapter">回看开头</button>',
            "CURRENT_SCENE_HOTSPOTS_AND_DIRECT_CONTROLS":
                '<button class="scene-object" id="open" style="left:50%;top:30%">查看材料</button>',
            "READING_OR_COMPACT": "reading",
            "CURRENT_OBJECT_LABEL": "两份记录",
            "CLOSE_AND_RETURN": "回到画面",
            "ONE_CURRENT_JUDGMENT": "这两份记录能支持同一个结论吗？",
            "NECESSARY_SOURCE_EXCERPT_AND_CONTEXT": "<blockquote>甲、乙记录的结果相同，但条件记载不完整。</blockquote>" + long_material,
            "EVIDENCE_SELECTION_OR_INPUT_AND_LOCAL_FEEDBACK":
                '<label for="answer">你的理由</label><textarea id="answer"></textarea>',
            "ONE_PRIMARY_ACTION": '<button id="finish" class="primary">继续播放</button>',
            "EVENT_MAP_JSON": "{}",
        }
        content = re.sub(r"\{\{([^}]+)\}\}", lambda match: replacements.get(match[1], ""), content)
        styles = (ROOT / "assets/course-page.css").read_text() + (ROOT / "assets/video-led-course-page.css").read_text()
        content = content.replace("</head>", "<style>" + styles + "</style></head>")
        # This harness deliberately implements only the state transitions needed to
        # inspect the template. Production clock/recovery has separate acceptance.
        harness = """
<script>
const video=document.querySelector('video'), entry=document.querySelector('#course-entry');
const task=document.querySelector('#task-layer'), controls=document.querySelector('#course-header');
const objects=document.querySelector('#scene-objects');
video.muted=true;video.loop=true;
function hideControls(){controls.hidden=true;document.body.classList.remove('controls-visible');}
document.querySelector('#start').onclick=()=>{entry.hidden=true;objects.hidden=false;video.play();};
video.onclick=()=>{controls.hidden=false;document.body.classList.add('controls-visible');};
document.querySelector('#hide-controls').onclick=hideControls;
document.querySelector('#chapter').onclick=()=>{video.currentTime=0;task.hidden=true;objects.hidden=false;hideControls();};
document.querySelector('#open').onclick=()=>{video.pause();hideControls();task.hidden=false;objects.hidden=true;document.querySelector('#task-title').focus();};
document.querySelector('.task-header button').onclick=()=>{task.hidden=true;objects.hidden=false;document.querySelector('#open').focus();};
document.querySelector('#finish').onclick=()=>{task.hidden=true;objects.hidden=false;video.play();document.querySelector('#open').focus();};
</script>"""
        content = content.replace("</body>", harness + "</body>")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, channel=args.browser_channel)
            try:
                for width, height in ((1440, 900), (390, 844), (844, 390)):
                    page = browser.new_page(viewport={"width": width, "height": height},
                                            reduced_motion="reduce")
                    page.set_content(content)
                    page.locator("#start").click()
                    page.wait_for_function("!document.querySelector('video').paused")
                    geometry = page.locator("#course-stage").bounding_box()
                    assert geometry["width"] == width and geometry["height"] == height
                    assert page.locator("video").evaluate("(node)=>getComputedStyle(node).objectFit") == "contain"
                    expect(page.locator("#course-header")).to_be_hidden()
                    expect(page.locator("#task-layer")).to_be_hidden()
                    results.append({"case": f"video_dominates_{width}x{height}", "status": "passed"})
                    page.locator("video").click(position={"x": 20, "y": 20})
                    expect(page.locator("#course-header")).to_be_visible()
                    page.locator("#chapter").click()
                    expect(page.locator("#course-header")).to_be_hidden()
                    results.append({"case": f"on_demand_controls_and_chapter_{width}", "status": "passed"})
                    page.locator("#open").click()
                    assert page.locator("video").evaluate("(node)=>node.paused")
                    expect(page.locator("#task-layer")).to_be_visible()
                    expect(page.locator("#task-title")).to_be_in_viewport()
                    body = page.locator(".task-body")
                    assert body.evaluate("(node)=>node.scrollHeight>node.clientHeight")
                    assert body.evaluate("(node)=>node.scrollWidth<=node.clientWidth")
                    box = page.locator(".task-surface").bounding_box()
                    media_box = page.locator("#scene-media").bounding_box()
                    footer = page.locator("#finish").bounding_box()
                    assert box["y"] >= 0 and box["x"] >= 0 and box["x"] + box["width"] <= width
                    assert footer["y"] >= 0 and footer["y"] + footer["height"] <= height
                    assert (media_box["y"] + media_box["height"] <= box["y"] + 1 or
                            media_box["x"] + media_box["width"] <= box["x"] + 1)
                    if args.screenshot_directory:
                        page.screenshot(path=str(args.screenshot_directory / f"reading-{width}x{height}.png"))
                    results.append({"case": f"paused_reading_scroll_and_action_{width}", "status": "passed"})
                    page.locator("#answer").fill("保留的判断理由")
                    page.locator(".task-header button").click()
                    expect(page.locator("#task-layer")).to_be_hidden()
                    assert page.locator("video").evaluate("(node)=>node.paused")
                    expect(page.locator("#open")).to_be_focused()
                    page.locator("#open").click()
                    expect(page.locator("#answer")).to_have_value("保留的判断理由")
                    page.locator("#finish").click()
                    page.wait_for_function("!document.querySelector('video').paused")
                    expect(page.locator("#task-layer")).to_be_hidden()
                    results.append({"case": f"close_draft_reopen_complete_{width}", "status": "passed"})
                    page.close()
            finally:
                browser.close()
    report = {"passed": len(results), "cases": results,
              "limits": "Generic template/CSS and isolated state harness only. "
                        "No course runtime, character media or learning acceptance."}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
