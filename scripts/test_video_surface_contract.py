#!/usr/bin/env python3
"""Regression checks for the video-led page hard boundary."""

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_page_structure import main


class VideoSurfaceContractTests(unittest.TestCase):
    def validate(self, html):
        with tempfile.TemporaryDirectory(prefix="video-surface-contract-") as directory:
            page = Path(directory) / "index.html"
            page.write_text(html, encoding="utf-8")
            with self.assertRaises(SystemExit) as result:
                # validate_page_structure.main reads argv, so invoke the script
                # through its public CLI contract in a subprocess-like way below.
                import sys
                original = sys.argv
                try:
                    sys.argv = ["validate_page_structure.py", str(page)]
                    main()
                finally:
                    sys.argv = original
            return str(result.exception)

    def test_rejects_persistent_layout_wrapper(self):
        html = """<!doctype html><html><head><link rel="stylesheet" href="course-page.css"></head>
        <body data-experience-profile="video_led_web"><aside>目录</aside><main id="course-stage">
        <div id="scene-media"><video></video></div><div id="scene-shade"></div>
        <header id="course-header"></header><section id="course-entry"></section>
        <div id="scene-objects"></div><div id="course-caption"></div><div id="course-actions"></div>
        <div id="task-layer"><section class="task-surface" role="region" aria-label="任务">
        <header class="task-header"></header><div class="task-body"></div><footer class="task-footer"></footer>
        </section></div><div id="course-status"></div></main></body></html>"""
        self.assertIn("不能包裹常驻布局区域", self.validate(html))

    def test_rejects_parallel_root_panel(self):
        html = """<!doctype html><html><head><link rel="stylesheet" href="course-page.css"></head>
        <body data-experience-profile="video_led_web"><main id="course-stage">
        <div id="scene-media"><video></video></div><div id="scene-shade"></div>
        <header id="course-header"></header><section id="course-entry"></section>
        <div id="scene-objects"></div><div id="course-caption"></div><div id="course-actions"></div>
        <div id="task-layer"><section class="task-surface" role="region" aria-label="任务">
        <header class="task-header"></header><div class="task-body"></div><footer class="task-footer"></footer>
        </section></div><div id="course-status"></div><aside>证据卡</aside></main></body></html>"""
        self.assertIn("不能包含额外并行区域", self.validate(html))


if __name__ == "__main__":
    unittest.main()
