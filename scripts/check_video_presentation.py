#!/usr/bin/env python3
"""Bounded presentation regressions with actual decoded synthetic video in headless Chrome."""
import argparse
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright
from check_video_production import make_media
from validate_video_presentation import validate, validate_bound_video
from validate_content_quality import file_fingerprint
from validate_video_led_runtime import validate_required_windows

ROOT = Path(__file__).resolve().parents[1]


def check_joint_binding(base, media, spec, check):
    """Only synthetic records: exercise joint binding, never assert real course acceptance."""
    from check_workflow_and_demo import fixture
    from check_scene_participation import sample
    from demo_regression_fixtures import install_runtime
    from demo_contract import runtime_fingerprints, validate_runtime_delivery

    data = fixture(base)
    data["assets"][0]["status"] = "accepted"
    runtime = install_runtime(data, base, formal=True)
    evidence = {row["reference_identifier"]: row for row in data["evidence_files"]}

    def read(reference):
        return json.loads((base / evidence[reference]["path"]).read_text())
    def write(reference, value):
        path = base / evidence[reference]["path"]
        path.write_text(json.dumps(value))
        evidence[reference]["content_sha256"] = file_fingerprint(path)
    def refresh():
        fingerprints = runtime_fingerprints(data, base, runtime)
        browser = read(runtime["browser_evidence_reference"])
        browser["runtime_fingerprints"] = fingerprints
        write(runtime["browser_evidence_reference"], browser)
        gate = read(runtime["visual_gate_reference"])
        gate["runtime_fingerprints"] = fingerprints
        gate["runtime_file_snapshots"] = [
            {"reference_identifier": reference, "path": evidence[reference]["path"], "content_sha256": digest}
            for reference, digest in fingerprints["evidence"].items()]
        for row in gate["evidence"]:
            row["runtime_fingerprints"] = fingerprints
        write(runtime["visual_gate_reference"], gate)

    (base / "sound.mp4").write_bytes(media.read_bytes())
    video_asset = data["assets"][0]
    video_asset["acceptance"]["file_snapshots"][0]["content_sha256"] = file_fingerprint(media)
    presentation = copy.deepcopy(spec)
    presentation["main_video_asset_identifier"] = video_asset["asset_identifier"]
    runtime["presentation_reference"] = "formal_presentation"
    evidence["formal_presentation"] = {
        "reference_identifier": "formal_presentation", "kind": "video_presentation_contract",
        "path": "formal-presentation.json", "course_version": data["course_version"],
        "bound_identifiers": ["objective_core"]}
    data["evidence_files"].append(evidence["formal_presentation"])
    write("formal_presentation", presentation)
    event_map = read(runtime["event_map_reference"])
    event_map["duration_seconds"] = presentation["duration_seconds"]
    for i, row in enumerate(event_map["events"]):
        row.update(cue_seconds=1 + i * .5, pause_seconds=1 + i * .5, resume_seconds=1 + i * .5)
    write(runtime["event_map_reference"], event_map)
    entry = base / evidence[runtime["entry_reference"]]["path"]
    import re
    html = re.sub(r'(<script id="video-event-map" type="application/json">).*?(</script>)',
                  lambda match: match[1] + json.dumps(event_map) + match[2], entry.read_text())
    html = html.replace('id="course-stage"', 'id="course-stage" data-atmosphere="synchronized"')
    html = html.replace("</main>", '<button data-presentation-anchor="anchor_object_01">Synthetic object</button></main>')
    entry.write_text(html)
    evidence[runtime["entry_reference"]]["content_sha256"] = file_fingerprint(entry)
    source = base / evidence[runtime["source_reference"]]["path"]
    source.write_text(source.read_text() + "\n" +
                      (ROOT / "assets/video-presentation-runtime.js").read_text().replace("export ", ""))
    evidence[runtime["source_reference"]]["content_sha256"] = file_fingerprint(source)
    runtime_asset = next(row for row in data["assets"] if row["asset_identifier"] == "formal_runtime")
    for row in runtime_asset["acceptance"]["file_snapshots"]:
        row["content_sha256"] = file_fingerprint(base / row["path"])
    background_ids = {state[key] for cue in presentation["atmosphere"]["cues"]
                      for state in cue["states"] for key in ("asset_identifier", "still_asset_identifier")}
    for identifier in sorted(background_ids):
        asset = copy.deepcopy(data["assets"][1])
        path = base / (identifier + ".svg")
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" fill="#135"/></svg>')
        asset.update(asset_identifier=identifier, kind="image", required=False, files=[{"path": path.name}])
        asset["acceptance"]["file_snapshots"] = [{"path": path.name, "content_sha256": file_fingerprint(path)}]
        data["assets"].append(asset)
        runtime["bound_asset_identifiers"].append(identifier)
    track = presentation["anchors"][0]
    participant = sample(track["beat_identifier"], "scene_control", "Synthetic knowledge action",
                         "Synthetic observed object", "Synthetic representation selection")
    participant["interaction_identifier"] = next(row["interaction_id"] for row in event_map["events"]
                                                 if row["beat_id"] == track["beat_identifier"])
    participant["objective_identifiers"] = ["objective_core"]
    participant["scene_anchor"].update(object_identifier=track["object_identifier"],
                                       presentation_anchor_reference="formal_presentation#" + track["identifier"])
    plan = {"schema_version": "1.1", "experience_profile": "video_led_web", "coverage_scope": "selected_events",
            "continuity": {"primary_point_of_view": "macro_observational",
                           "continuity_anchor_identifier": "synthetic_system",
                           "continuity_anchor_role": "Synthetic object continuity",
                           "point_of_view_return_rule": "Synthetic same-state return",
                           "learner_language_policy": "Synthetic current action",
                           "branch_policy": "linear_no_branch"},
            "events": [participant]}
    write("scene_interaction_plan", plan)
    browser = read(runtime["browser_evidence_reference"])
    for viewport in ("desktop", "narrow"):
        prototype = next(row for row in browser["tests"] if row["viewport_class"] == viewport)
        anchor = copy.deepcopy(prototype)
        anchor.update(test_identifier=f"anchor_{viewport}", path_category="anchor_projection")
        browser["tests"].append(anchor)
        for motion in ("normal", "reduced"):
            row = copy.deepcopy(prototype)
            row.update(test_identifier=f"atmosphere_{viewport}_{motion}", path_category="atmosphere_sync",
                       motion_preference=motion, event_kinds=[
                           "pause", "interaction", "seek", "replay", "restore", "rate_change", "background_failure"])
            browser["tests"].append(row)
    write(runtime["browser_evidence_reference"], browser)
    refresh()
    errors = validate_runtime_delivery(data, base, formal=True)
    assert not errors, errors
    check("joint_presentation_valid", True)
    original_data = copy.deepcopy(data)
    originals = {path: path.read_bytes() for path in base.iterdir() if path.is_file()}
    for name, edit, diagnostic in (
        ("missing_reference", lambda: runtime.pop("presentation_reference"), "requires presentation_reference"),
        ("malformed_reference", lambda: runtime.update(presentation_reference=["wrong"]), "requires text"),
        ("wrong_video_hash", lambda: write("formal_presentation", dict(presentation, main_video_sha256="0" * 64)), "video hash differs"),
        ("malformed_video_identifier", lambda: write("formal_presentation", dict(presentation, main_video_asset_identifier=[])), "main_video_asset_identifier must be text"),
        ("wrong_video_dimensions", lambda: write("formal_presentation", dict(presentation, source_dimensions={"width": 640, "height": 360})), "dimensions differ"),
        ("unbound_background", lambda: runtime["bound_asset_identifiers"].remove(sorted(background_ids)[0]), "omit presentation dependencies"),
        ("missing_motion_coverage", lambda: write(runtime["browser_evidence_reference"], dict(browser,
             tests=[row for row in browser["tests"] if not (row.get("path_category") == "atmosphere_sync" and
                    row.get("viewport_class") == "narrow" and row.get("motion_preference") == "reduced")])), "omits viewport/motion"),
        ("missing_anchor_coverage", lambda: write(runtime["browser_evidence_reference"], dict(browser,
             tests=[row for row in browser["tests"] if row.get("path_category") != "anchor_projection"])), "anchor_projection"),
        ("wrong_anchor_object", lambda: write("scene_interaction_plan", dict(plan, events=[
             dict(participant, scene_anchor=dict(participant["scene_anchor"], object_identifier="wrong"))])), "Beat/object differs"),
        ("wrong_anchor_reference", lambda: write("scene_interaction_plan", dict(plan, events=[
             dict(participant, scene_anchor=dict(participant["scene_anchor"], presentation_anchor_reference="wrong#anchor_object_01"))])), "reference differs"),
        ("unknown_anchor_reference", lambda: write("scene_interaction_plan", dict(plan, events=[
             dict(participant, scene_anchor=dict(participant["scene_anchor"], presentation_anchor_reference="formal_presentation#unknown"))])), "anchor is absent"),
        ("missing_plan_anchor", lambda: write("scene_interaction_plan", dict(plan, events=[
             dict(participant, scene_anchor=dict(participant["scene_anchor"], presentation_anchor_reference=None))])), "lack participation-plan"),
        ("stale_presentation_fingerprints", lambda: write("formal_presentation",
             dict(presentation, anchors=[dict(track, keyframes=[
                 dict(point, rectangle=dict(point["rectangle"], x=.25)) for point in track["keyframes"]])])), "browser evidence is stale"),
        ("stale_background_fingerprints", lambda: (base / (sorted(background_ids)[0] + ".svg")).write_text(
             '<svg xmlns="http://www.w3.org/2000/svg"/>'), "browser evidence is stale"),
    ):
        edit()
        errors = validate_runtime_delivery(data, base, formal=True)
        check("joint_" + name, any(diagnostic in error for error in errors))
        for path, content in originals.items():
            path.write_bytes(content)
        data = copy.deepcopy(original_data)
        runtime = data["runtime_delivery"]
        evidence = {row["reference_identifier"]: row for row in data["evidence_files"]}
    check("joint_valid_after_probes", not validate_runtime_delivery(data, base, formal=True))
    command = [sys.executable, str(ROOT / "scripts/validate_scene_interaction_plan.py"),
               str(base / evidence["scene_interaction_plan"]["path"]), "--event-map",
               str(base / evidence[runtime["event_map_reference"]]["path"]), "--presentation",
               str(base / evidence["formal_presentation"]["path"]), "--presentation-reference", "formal_presentation"]
    check("actual_participation_presentation_CLI", subprocess.run(command, capture_output=True).returncode == 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--browser-channel", default="chrome")
    args = parser.parse_args()
    results = []
    def check(name, ok):
        assert ok, name
        results.append({"case": name, "status": "passed"})
    def seek(page, seconds):
        page.evaluate("(t)=>video.currentTime=t", seconds)
        try:
            page.wait_for_function("t=>last.seconds!==null && Math.abs(last.seconds-t)<.05", arg=seconds, timeout=8000)
        except Exception:
            print(json.dumps(page.evaluate("({last, samples:samples.slice(-8), currentTime:video.currentTime,seeking:video.seeking,paused:video.paused})")))
            raise
    with tempfile.TemporaryDirectory(prefix="presentation-regression-") as temporary:
        base = Path(temporary)
        media = make_media(base, "main.mp4", "testsrc2=size=320x180:rate=24:duration=4")
        spec = json.loads((ROOT / "assets/video-presentation.template.json").read_text())
        spec.update(duration_seconds=4, main_video_sha256=file_fingerprint(media),
                    source_dimensions={"width": 320, "height": 180})
        cue = spec["atmosphere"]["cues"][0]
        cue.update(end_seconds=2, cycle_seconds=1)
        second = copy.deepcopy(cue)
        second.update(identifier="second", scene_identifier="scene_second", start_seconds=2,
                      end_seconds=4, transition_seconds=1)
        second["states"][0].update(asset_identifier="bg_second", still_asset_identifier="still_second")
        spec["atmosphere"]["cues"].append(second)
        check("valid_specification", not validate(spec))
        for name, edit, diagnostic in (
            ("gap", lambda s: s["atmosphere"]["cues"][1].update(start_seconds=2.1), "partition"),
            ("cover_rejected", lambda s: s.update(projection="cover"), "centered_contain"),
            ("missing_hash", lambda s: s.pop("main_video_sha256"), "sha256"),
            ("learning_background_rejected", lambda s: s["atmosphere"].update(required_for_learning=True), "optional"),
            ("outside_rectangle", lambda s: s["anchors"][0]["keyframes"][0]["rectangle"].update(x=.95), "fit normalized"),
            ("missing_keyframe", lambda s: s["anchors"][0].update(keyframes=[]), "two keyframes"),
            ("unordered_occlusion", lambda s: s["anchors"][0]["occlusions"][0].update(end_seconds=2.5), "interval"),
        ):
            bad = copy.deepcopy(spec)
            edit(bad)
            check(name, any(diagnostic in error for error in validate(bad)))
        contract = base / "presentation.json"
        contract.write_text(json.dumps(spec))
        cli = subprocess.run([sys.executable, str(ROOT / "scripts/validate_video_presentation.py"),
                              str(contract), "--video", str(media)], capture_output=True, text=True)
        check("actual_presentation_CLI", cli.returncode == 0)
        for name, edit, diagnostic in (
            ("actual_duration_mismatch", lambda s: s.update(duration_seconds=10), "duration differs"),
            ("actual_dimensions_mismatch", lambda s: s.update(source_dimensions={"width": 1920, "height": 1080}), "dimensions differ"),
        ):
            bad = copy.deepcopy(spec)
            edit(bad)
            check(name, any(diagnostic in error for error in validate_bound_video(bad, media)))
        check_joint_binding(base, media, spec, check)
        import re
        markup = re.sub(r"\{\{.*?\}\}", "Synthetic content",
                        (ROOT / "assets/video-led-course-page.template.html").read_text())
        markup_path = base / "synthetic-markup.html"
        for name in ("course-page.css", "video-led-course-page.css"):
            (base / name).write_text((ROOT / "assets" / name).read_text())
        for name, changed, diagnostic in (
            ("atmosphere_markup", markup, None),
            ("atmosphere_markup_no_inert", markup.replace('aria-hidden="true" inert', 'aria-hidden="true"'), "aria-hidden and inert"),
            ("atmosphere_markup_audio", re.sub(r'(<div id="course-atmosphere"[^>]*>)(</div>)',
                 r'\1<audio></audio>\2', markup), "silent noninteractive"),
            ("atmosphere_markup_input", re.sub(r'(<div id="course-atmosphere"[^>]*>)(</div>)',
                 r'\1<button>Input</button>\2', markup), "silent noninteractive"),
        ):
            assert diagnostic is None or changed != markup, "negative markup probe must change input"
            markup_path.write_text(changed)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_page_structure.py"),
                                     str(markup_path)], capture_output=True, text=True)
            check(name, result.returncode == 0 if diagnostic is None else
                  result.returncode != 0 and diagnostic in result.stdout + result.stderr)
        a = {"beat_id": "A", "cue_seconds": 1, "pause_seconds": 2, "resume_seconds": 4, "evidence_required": True}
        b = {"beat_id": "B", "cue_seconds": 1.5, "pause_seconds": 2.5, "resume_seconds": 2.5, "evidence_required": True}
        check("overlapping_required_windows_rejected", bool(validate_required_windows([a, b])))
        b.update(cue_seconds=4, pause_seconds=4, resume_seconds=4)
        check("adjacent_windows_allowed", not validate_required_windows([a, b]))
        a.update(cue_seconds=4, pause_seconds=4, resume_seconds=4)
        check("same_point_required_events_rejected", bool(validate_required_windows([a, b])))
        module = (ROOT / "assets/video-presentation-runtime.js").read_text().replace("export ", "")
        module += "\nwindow.API={attachPresentationClock,atmosphereAt,AtmosphereController,anchorAt,projectContain,placeAnchor};"
        styles = (ROOT / "assets/course-page.css").read_text() + (ROOT / "assets/video-led-course-page.css").read_text()
        url = "data:video/mp4;base64," + base64.b64encode(media.read_bytes()).decode()
        def image(color):
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" fill="{color}"/></svg>'
            return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
        assets = {"atmosphere_01": image("#135"), "atmosphere_01_still": image("#135"),
                  "bg_second": image("#531"), "still_second": image("#531")}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, channel=args.browser_channel)
            try:
                for width, height in ((1440, 900), (390, 844)):
                    for preference in ("normal", "reduced"):
                        page = browser.new_page(viewport={"width": width, "height": height},
                            reduced_motion="reduce" if preference == "reduced" else "no-preference")
                        page.set_content(f'<style>{styles}</style><body data-experience-profile="video_led_web">'
                            '<main id="course-stage" data-atmosphere="synchronized">'
                            '<div id="course-atmosphere" aria-hidden="true" inert></div>'
                            f'<div id="scene-media"><video id="course-video" muted playsinline src="{url}"></video></div>'
                            '<div id="scene-objects"><button class="scene-object" data-presentation-anchor="anchor_object_01">Object</button></div>'
                            '</main></body>')
                        page.add_script_tag(content=module)
                        page.evaluate("""({spec,assets})=>{
                          window.spec=spec;window.video=document.querySelector('video');
                          window.root=document.querySelector('#course-atmosphere');window.samples=[];window.positions=[];
                          window.controller=new API.AtmosphereController(root,spec,assets);
                          window.red=matchMedia('(prefers-reduced-motion:reduce)').matches;
                          window.dispose=API.attachPresentationClock(video,t=>positions.push(t),sample=>{
                            window.last=sample;
                            window.atmosphere=controller.apply(sample,'initial',{reduced:red});
                            API.placeAnchor(document.querySelector('button'),spec.anchors[0],sample,spec.source_dimensions,
                              video.getBoundingClientRect(),document.querySelector('#scene-objects').getBoundingClientRect());
                            if(sample.seconds!==null)samples.push(sample);
                          });
                        }""", {"spec": spec, "assets": assets})
                        page.evaluate("video.play()")
                        page.wait_for_function("window.last && last.seconds > 0.25")
                        label = f"{width}_{preference}"
                        state = page.evaluate("({accurate:last.accurate,epoch:last.epoch,asset:atmosphere.assetIdentifier})")
                        check("real_presented_frames_" + label, state["accurate"] and state["epoch"] == 0)
                        check("motion_variant_" + label, state["asset"] ==
                              ("atmosphere_01_still" if preference == "reduced" else "atmosphere_01"))
                        page.evaluate("video.pause()")
                        frozen = page.evaluate("""async()=>{
                          for(let i=0;i<3;i++)await new Promise(requestAnimationFrame);
                          const before=root.dataset.phaseSeconds;
                          for(let i=0;i<8;i++)await new Promise(requestAnimationFrame);
                          return before===root.dataset.phaseSeconds &&
                            root.getAnimations({subtree:true}).every(a=>a.playState==='paused');
                        }""")
                        check("pause_and_interaction_freeze_" + label, frozen)
                        seek(page, 2.5)
                        check("seek_rebuild_" + label, page.evaluate(
                            "last.epoch>0 && atmosphere.cueIdentifier==='second' && atmosphere.alpha===1"))
                        seek(page, 3.1)
                        check("occlusion_hides_and_disables_" + label, page.evaluate(
                            "document.querySelector('button').hidden && document.querySelector('button').disabled"))
                        seek(page, 3.5)
                        projection = page.evaluate("""()=>{
                          const node=document.querySelector('button'), v=video.getBoundingClientRect(), actual=node.getBoundingClientRect();
                          const expected=API.projectContain(API.anchorAt(spec.anchors[0],last.seconds),spec.source_dimensions,v);
                          return !node.hidden && ['x','y','width','height'].every(k=>Math.abs(actual[k]-expected[k])<1);
                        }""")
                        check("actual_DOM_contain_projection_" + label, projection)
                        resized = page.evaluate("""async()=>{
                          const container=document.querySelector('#scene-media'),node=document.querySelector('button');
                          container.style.bottom='55%';
                          await new Promise(requestAnimationFrame);
                          const result=API.placeAnchor(node,spec.anchors[0],last,spec.source_dimensions,
                            video.getBoundingClientRect(),document.querySelector('#scene-objects').getBoundingClientRect());
                          const expected=API.projectContain(API.anchorAt(spec.anchors[0],last.seconds),
                            spec.source_dimensions,video.getBoundingClientRect()),actual=node.getBoundingClientRect();
                          const ok=result?.fallbackRequired ? node.hidden&&node.disabled :
                            !node.hidden&&['x','y','width','height'].every(k=>Math.abs(actual[k]-expected[k])<1);
                          container.style.bottom=''; return ok;
                        }""")
                        check("paused_shrunk_stage_reprojection_" + label, resized)
                        small = page.evaluate("""()=>{
                          const node=document.querySelector('button'),small=structuredClone(spec.anchors[0]);
                          for(const point of small.keyframes)point.rectangle={x:.2,y:.3,width:.01,height:.01};
                          const result=API.placeAnchor(node,small,last,spec.source_dimensions,
                            video.getBoundingClientRect(),document.querySelector('#scene-objects').getBoundingClientRect());
                          return result?.fallbackRequired && node.hidden && node.disabled;
                        }""")
                        check("small_target_requests_same_object_fallback_" + label, small)
                        deterministic = page.evaluate("""()=>{
                          const sample={seconds:2.4,kind:'frame',epoch:100,accurate:true};
                          controller.apply({...sample,seconds:2.1},'initial',{reduced:red});
                          const state=controller.apply(sample,'initial',{reduced:red}),layer=controller.layers[1];
                          return red ? state.phase===0&&state.alpha===1&&layer.motion.currentTime===0 :
                            Math.abs(state.phase-.4)<1e-9&&Math.abs(state.alpha-.4)<1e-9&&
                            Math.abs(layer.motion.currentTime-400)<1e-6&&Math.abs(+layer.node.style.opacity-.4)<1e-9;
                        }""")
                        check("actual_phase_and_crossfade_" + label, deterministic)
                        page.evaluate("video.playbackRate=2")
                        seek(page, .5)
                        check("replay_rate_and_restore_" + label, page.evaluate(
                            "video.playbackRate===2 && atmosphere.cueIdentifier==='atmosphere_scene_01' && atmosphere.alpha===1"))
                        page.evaluate("controller.layers[1].node.src='data:image/png;base64,invalid'")
                        if preference == "normal":
                            page.wait_for_function("root.dataset.assetIdentifier==='atmosphere_01_still'")
                            check("actual_image_failure_static_fallback_" + label, True)
                        else:
                            page.wait_for_function("root.hidden")
                            check("static_failure_neutral_stage_" + label, True)
                        check("silent_noninteractive_background_" + label, page.evaluate(
                            "root.inert && root.getAttribute('aria-hidden')==='true' && getComputedStyle(root).pointerEvents==='none' && !root.querySelector('audio,video,button,input')"))
                        check("single_epoch_monotonic_" + label, page.evaluate(
                            "samples.every((s,i)=>!i || s.epoch!==samples[i-1].epoch || s.seconds>=samples[i-1].seconds)"))
                        page.close()
                page = browser.new_page()
                page.add_script_tag(content=module)
                clock = page.evaluate("""()=>{
                  const listeners={}, callbacks=new Map(); let token=0;const frames=[],positions=[];
                  const fake={currentTime:2.04,seeking:false,
                    addEventListener:(k,f)=>listeners[k]=f,removeEventListener:()=>{},
                    requestVideoFrameCallback:f=>{callbacks.set(++token,f);return token},
                    cancelVideoFrameCallback:id=>callbacks.delete(id)};
                  const close=API.attachPresentationClock(fake,t=>positions.push(t),s=>frames.push(s));
                  listeners.timeupdate();callbacks.get(token)(0,{mediaTime:2});
                  const old=callbacks.get(token);listeners.seeking();const afterSeek=token;old(0,{mediaTime:1});
                  close();
                  return positions[0]===2.04 && frames.filter(s=>s.kind==='frame').map(s=>s.seconds).join(',')==='2'
                    && frames.some(s=>s.kind==='invalidate') && token===afterSeek;
                }""")
                check("mixed_clock_and_stale_epoch_regression", clock)
                approximate = page.evaluate("""spec=>{
                  const listeners={}, samples=[],positions=[];
                  const fake={currentTime:2.5,seeking:false,
                    addEventListener:(key,fn)=>listeners[key]=fn,removeEventListener:()=>{}};
                  const close=API.attachPresentationClock(fake,t=>positions.push(t),s=>samples.push(s));
                  listeners.timeupdate(); const sample=samples[0],node=document.createElement('button');
                  const result=API.placeAnchor(node,spec.anchors[0],sample,spec.source_dimensions,
                    {x:0,y:0,width:1440,height:900},{x:0,y:0});
                  close();
                  return positions[0]===2.5&&sample.kind==='approximate'&&!sample.accurate&&
                    result===null&&node.hidden&&node.disabled;
                }""", spec)
                check("frame_API_absent_approximate_background_and_hidden_anchor", approximate)
                page.close()
            finally:
                browser.close()
    report = {"passed": len(results), "cases": results,
              "limits": "Actual browser/decoder with synthetic video and visual fixtures. No real object recognition, GPU budget, teacher/learner or experience outcome."}
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
