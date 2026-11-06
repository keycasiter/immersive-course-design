#!/usr/bin/env python3
"""Headless checks of the generic deterministic storyboard carrier, not a real lesson."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import tempfile
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-channel")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--screenshot-directory", type=Path)
    args = parser.parse_args()
    for path in (args.report.parent if args.report else None, args.screenshot_directory):
        if path is not None and not path.is_dir():
            parser.error("Output parent directory must already exist")
    results = []
    with tempfile.TemporaryDirectory(prefix="storyboard-browser-") as directory:
        base = Path(directory)
        event_map = json.loads((ROOT / "assets/storyboard-event-map.template.json").read_text())
        second = {**event_map["events"][0], "beat_id": "beat_second", "return_event_identifier": "beat_second"}
        event_map["events"].append(second)
        event_map["approved_beat_ids"].append("beat_second")
        third = {**second, "beat_id": "beat_third", "return_event_identifier": "beat_third",
                 "event_class": "observation", "evidence_required": False, "interaction_id": None}
        event_map["events"].append(third)
        event_map["approved_beat_ids"].append("beat_third")
        html = (ROOT / "assets/storyboard-demo.template.html").read_text()
        html = html.replace("{{与独立文件相同的完整事件JSON}}", json.dumps(event_map))
        html = re.sub(r"\{\{.*?\}\}", "通用状态验证", html)
        (base / "index.html").write_text(html)
        (base / "runtime.js").write_text((ROOT / "assets/storyboard-runtime.template.js").read_text())
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(base)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, channel=args.browser_channel)
                try:
                    for width, height in ((1440, 900), (390, 844), (844, 390)):
                        page = browser.new_page(viewport={"width": width, "height": height})
                        console_errors = []
                        page.on("pageerror", lambda error: console_errors.append(str(error)))
                        page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
                        expect(page.locator("#task-surface")).to_be_hidden()
                        assert not page.locator("video").count()
                        page.locator("#open-interaction").click()
                        expect(page.locator("#task-surface")).to_be_visible()
                        expect(page.locator("#task-surface")).to_be_focused()
                        assert page.locator("[data-primary-action]:visible").count() == 1
                        page.locator("#response").fill("保留的首答")
                        if args.screenshot_directory:
                            page.screenshot(path=str(args.screenshot_directory / f"storyboard-paused-{width}.png"))
                        page.locator("#close-interaction").click()
                        expect(page.locator("#task-surface")).to_be_hidden()
                        assert page.evaluate("enterEvent('beat_second')") is False
                        assert page.evaluate("state.eventIdentifier") == "beat_practice"
                        page.locator("#open-interaction").click()
                        expect(page.locator("#response")).to_have_value("保留的首答")
                        page.reload()
                        expect(page.locator("#task-surface")).to_be_visible()
                        expect(page.locator("#response")).to_have_value("保留的首答")
                        expect(page.locator("#task-surface")).to_be_focused()
                        page.locator("#submit-interaction").click()
                        assert page.locator("[data-primary-action]:visible").count() == 1
                        assert page.evaluate("state.phase") == "feedback"
                        page.locator("#complete-interaction").click()
                        assert page.evaluate("state.phase") == "return"
                        assert page.evaluate("state.eventIdentifier") == "beat_practice"
                        assert page.evaluate("enterEvent('beat_third')") is False
                        assert page.evaluate("enterEvent('beat_second')") is True
                        page.reload()
                        assert page.evaluate("state.eventIdentifier") == "beat_second"
                        assert page.evaluate("enterEvent('beat_practice')") is False
                        page.locator("#open-interaction").click()
                        page.locator("#submit-interaction").click()
                        page.locator("#complete-interaction").click()
                        assert page.evaluate("enterEvent('beat_third')") is True
                        assert page.evaluate("enterEvent('beat_practice')") is True
                        assert page.evaluate("state.drafts.beat_practice") == "保留的首答"
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        assert not console_errors, console_errors
                        results.append({"case": f"storyboard_pause_close_feedback_return_recovery_{width}x{height}",
                                        "status": "passed", "no_real_video": True})
                        page.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    report = {"passed": len(results), "cases": results,
              "limits": "Generic headless carrier; real lesson content, teaching quality and video timing not assessed."}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
