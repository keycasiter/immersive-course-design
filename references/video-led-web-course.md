# Video-led web course profile

This is the normative implementation profile for an immersive interactive browser classroom in this Skill. The video timeline is the authored course spine; direct controls, reading, simulation, spatial views, dialogue and other interactions attach to its events and return to its state. Learner actions may provide observation, choice, manipulation, expression, practice or immediate feedback without changing the authored course direction or creating durable evidence. Record the authored timeline before copying this profile's scaffolds. Do not assume a VR headset, headset tracking, or special hardware; define normal browser inputs such as click/tap, drag, keyboard, and accessible equivalents.

## Course-spine contract

Use this profile when all of the following are true:

- the learner benefits from a shared scene/event spine;
- video or timed audiovisual presentation carries the authored context, demonstration, pacing or continuity of the lesson;
- learner actions can produce a visible, audible, simulated or textual local response, even when the next course event remains fixed;
- pauses, returns and accessibility equivalents can preserve the same learning objective without hiding necessary evidence;
- the production team can validate the real media, runtime behavior and browser interaction before claiming completion.

If an attached interaction is unresolved, keep that interaction as a design question; do not remove the video spine or switch the whole classroom to a detached workbench. Do not generate the HTML or event-map scaffold before the authored timeline and event boundaries are known.

Choose the relationship and point-of-view model from the approved perspective decision. A participant route may use one continuous guide and learner first person. Macro-observational, documentary, system, object and explicitly transitioned multiple-viewpoint routes are equally valid and may have no character. In those routes, continuity is carried by a stable system, object, event, source set, sound or state transition. Do not add an NPC or force a return to first person solely because the profile is video-led.

## Precedence over shared page structure

The learner-facing playback/paused layout is owned by [video-surface-contract.md](video-surface-contract.md), which overrides the generic visual interpretation of `page-structure.md`. Keep semantic IDs needed for shared runtime compatibility; select the actual surface from the participation plan. A bounded judgment, current-source reading area or matched deeper view remains attached to the same event. This file owns the media clock, progression and exact return state; it does not impose a second layout contract.

The shared structural check permits an empty, hidden `task-layer` for this profile when no card is used. If a bounded card exists, give it a named region or a dialog with explicitly declared modality. Direct controls and matched deeper views do not need to be wrapped in a modal card. Shared semantic wrappers do not determine the learner-facing surface; actual controls, focus, evidence and returns require browser review.

Before detailed scene writing, the design outline must cover every required objective with at least one beat. Each interaction beat must declare a valid trigger, completion condition, and exact return state; beats with no interaction state why. Every proposed 360°/3D beat must pass the objective-based media decision below. The outline is review-ready only when these checks are complete and no unresolved coverage gap is hidden by a summary.

## Resource admission and failure policy

Video-led lessons use two resource checks:

1. **Course-entry admission**: before the learner enters the first scene, verify the main video is present and playable, required audio and caption resources are available, the runtime is ready, and the first scene dependencies pass their version and load checks.
2. **Event-entry admission**: immediately before opening a video event, verify that event's media, interaction dependencies, version, and runtime capability. Do not discover a missing 3D/360°/interaction asset only after the video has already entered the event.

Required media must be produced, loaded, and checked before the corresponding event is opened. A failed required resource may expose retry, reload, or re-enter actions only. Do not continue with a static image, text script, simplified interaction, or other degraded substitute. Repeated failure blocks entry or progression and records the failure reason, retry count, asset/version, event ID, and exact recovery position. An optional exploration asset that fails is hidden or disabled; never show an empty interaction layer.

## Runtime authority contract (mandatory for implementations)

The actual `HTMLVideoElement#course-video` is the sole course clock and source of truth for instructional progression. The active lesson state is derived from `video.currentTime` and stable event IDs in `video-event-map.json`. Required interactions open only when the declared media cue is reached; a required event pauses that same video at its declared pause time. Completing the learner action records its evidence, seeks to the declared resume time, restores the declared scene/audio/caption state, and resumes that video. A page button may start, pause, replay, answer, or close an interaction; it must never advance the instructional beat independently of video time. `setTimeout`, CSS animation duration, scrolling, or a sequence of page buttons must not act as a substitute course clock.

Every event map entry declares `beat_id`, `cue_seconds`, `pause_seconds`, `resume_seconds`, `interaction_id` (or null), `evidence_required`, and `resume_state`. Times are nonnegative, within the media duration, ordered, and map to the approved ordered beat IDs. The HTML contains one playable `<video id="course-video" data-media-clock="course">` inside `#scene-media`, with an actual local/approved `<source>` or `src` and a captions `<track>` when captions are supplied. Runtime listens to video `timeupdate` and `seeking` events, reads `currentTime`, and uses that time to open due events. Block forward seeking over unresolved required evidence; allow replay without erasing recorded responses. `ended` and elapsed time alone never mark a beat complete. For frame-accurate anchors, use `requestVideoFrameCallback`; otherwise declare cue tolerance and pause at the nearest supported boundary.

If playable video is unavailable, the deliverable must be labeled a design/static prototype and must not claim video-driven runtime behavior. Never fake a video clock by switching browser-drawn scenes on timers. Run `scripts/validate_video_led_runtime.py` on the event map, page, and runtime script; record its command/result in `verification.md`. This structural validator is not a substitute for browser playback and interaction review.

### Mandatory windows and presentation channels

Reserve `[cue_seconds,resume_seconds)` for each mandatory event (`evidence_required=true`, `interaction_required=true`, or judgment). The pause point is unique: two mandatory events cannot pause at the same instant, including zero-length windows. Later mandatory cues must be at or beyond the earlier resume boundary. Adjacent boundaries are valid when their pause points differ; conflicting windows must be merged or retimed before implementation. Optional exploration must stay closed while a mandatory work surface is unresolved; it cannot replace it. cue_tolerance is detection tolerance, never permission to overlap reservations.

Instructional position and presented-frame time are separate. Required events are managed by the runtime's video-position channel; exact anchors and synchronized atmosphere follow only the presented-frame channel when available. Before implementing either, read [video-presentation-contract.md](video-presentation-contract.md), use its bounded schema/module and register its evidence. It owns epochs, fallback, phase, occlusion and projection; this file owns progression and window conflicts.


Treat video as the learner-facing course spine. “Continuous” means the same event and point-of-view thread carries across clips and learning beats; it does not require one unbroken file. Every required instructional beat is tied to a stable `beat_identifier`, a video scene and a media-clock event. A beat advances only when its required instructional event is presented and any required learner evidence is complete. For a non-interactive explanation beat, reaching the specified media-clock event may count as content presentation so the narrative can continue; it does not count as evidence of mastery. Elapsed time, `ended`, or opening a hotspot alone do not count as learning evidence.

For each beat, record its previous and next beat, media time or event window, progress prerequisite, completion condition, pause behavior, interaction window, and exact resume time/state. Seeking or replaying must not silently skip required evidence. Resuming from interruption restores the same scene, time, point of view, audio/subtitle state, visible objects, learner response, and progress state.

## Event classes and interaction selection

Before choosing controls, read `scene-participation-design.md` and fill `scene-interaction-plan.json` from its template. Derive objective → visible evidence/object → knowledge action → surface → minimum information → visible response → completion and return. Prefer direct scene controls when sufficient; use a matched object-inspection, reading, simulation or spatial view when the action needs it. Cards support bounded questions/help and are not the default container for every beat.

Define the learner action before selecting an interaction technology. Use these event classes:

- **Observation event**: the learner must notice a visual, audio, spatial, or temporal change; the video may continue.
- **Exploration event**: the learner may inspect or manipulate a scene-anchored card, 3D object, 360° view, Three.js scene, comparison view, simulation, or other appropriate layer; it may be closed and returned to the same event.
- **Judgment event**: the learner must observe, choose, manipulate, explain, or create evidence; pause the video and resume only after the declared completion condition is met.

The class is not a media quota. For every event, record the learning action, why the video or a lower-cost representation is insufficient, the visible anchor, valid time window, payload, response, completion evidence, entry/exit transition, and exact resume state. Choose spatial media only when the objective requires spatial relations, object structure, manipulation, navigation, variable change, or dynamic spatial feedback. Use the lowest-complexity medium that preserves the required learning action.

Core interactions originate from the current video frame: a visible object, the NPC's gesture or handoff, an audio cue, or an event hotspot. A side task list, detached module launcher, persistent workbench, or global interaction catalog is not an equivalent entry. Global controls are limited to playback, captions, sound, accessibility and recovery. The default is a local, reversible response such as object highlighting, parameter preview, simulation output, reading position, dialogue feedback or temporary arrangement; the authored course direction remains unchanged. If a deliberate branch exists, it must declare a local consequence before rejoining the shared video spine. Long-running alternate plots require an explicit request, objective and production case.

Apply cognitive-load constraints instead of an interaction-per-minute quota: every continuous video segment has a clear information or action purpose; complex interactions are separated by observation, explanation, or feedback time; high-load 3D/360° entries are brief; one main task and at most one supporting layer are active at once; overlays do not cover required evidence, faces, or captions; every interaction has an explicit exit and recovery point.

## Interaction in the scene

Treat the browser page as the stage for a simulated immersive experience, not a course platform. The current video scene is the default surface and carries the course timeline. When a learning event needs 360° or 3D inspection, transition briefly into that in-scene view and return to the same video event afterward. Do not add a course outline, module navigation, separate workbench, document panel, persistent action toolbar, or verbose explanatory page chrome. Keep only essential playback and accessibility controls, available on demand.

At a video event, activate one primary task: direct controls attached to the object, a matched deeper view, or a bounded scene card. A card keeps the prompt, response and concise feedback near its anchor without covering required evidence. A reading, writing, simulation, 360° or 3D view may temporarily occupy the stage when that view is the learning action; it stays attached to the same object and event with a recognizable entry and return. Preserve source text, conditions and citation positions when reading is the objective. Use short instructions when needed to make the next action clear, with minimum prerequisites before acting, discoverable source/help on demand, and feedback after acting. Do not force all explanatory content into speech or hide necessary judgment evidence to reduce copy. Record anchor, window, action, response, transitions and exact resume state. On entry pause conflicting video/speech; after completion or optional exit restore time, view, audio, captions, object, response and focus. Closing an unresolved required task preserves its draft and keeps the video paused.

Avoid extra page buttons, persistent toolbars, decorative cards, and overlays that compete with the active subject, face, evidence, or captions. Define safe placement for desktop and phone; provide keyboard, touch, captions, reduced-motion, and mute behavior. Accessibility equivalents preserve the same learning objective and state, but required-media failure uses the resource retry/block policy above rather than a degraded learning path. If content cannot fit a card, re-derive the action and information layers; use a matched readable object or appropriate simulation when needed, rather than shrinking text, adding spatial media without purpose, or introducing a detached work surface.

## Low-disruption learning state

Do not add paragraphs about normal local-only storage, no upload/identity linkage, export/delete availability or browser cleanup to the entry, scene or record view. Keep governance in production materials; show actual progress and operations in the learner UI. Explain real failures or data-use decisions at the relevant action only.

The learner-facing scene shows only the current selection, entered state, or active object when that context needs to be visible. Keep recovery and evaluation state in a minimal system record. Do not make labels such as “first response”, “revision”, or “evidence record” persistent UI. Provide an in-scene “view my judgment” or equivalent contextual entry when the learner needs to revisit a choice; return to the original video event and object rather than a separate dashboard. The system may still store the minimum event ID, response, assistance, completion, and recovery fields required for reliable resume and assessment.

## Spatial media decision

Choose 360° only when the objective requires inspecting spatial relations, direction, or whole-scene layout. Choose 3D only when manipulating or magnifying an object, inspecting internal structure, navigating a simulated space, changing a variable, or observing a dynamic spatial relation teaches a stated objective and video, stills, diagrams, or a 360° image cannot support that action adequately. For each use, record the objective, relation or feature learned, why a video close-up/still/diagram is insufficient, the entry and return anchor, and an equivalent 2D path. Do not add a spatial mode to satisfy a media quota.

## First-person continuity

Choose narrative scale separately from POV using `narrative-scale-and-perspective.md`. A sustained global narrative can keep learner participation at the system/event level; a local narrative can stay local throughout. Observer, documentary, participant and explicitly transitioned multiple perspectives are valid choices. Do not impose first-person character scenes or global-to-local zooms merely because this profile is immersive.

Declare the point-of-view mode and its reason. For participant first person, maintain the guide's eyeline, address and spatial relationship. For observational or no-character routes, maintain the declared system/object/source anchor and return state. Keep movement, object state, camera direction, sound space and scene time coherent across clips, overlays, branches and returns. A historical reconstruction must not imply that the learner is a documented eyewitness; distinguish sourced evidence from dramatized staging. Every POV change needs an instructional or narrative reason, a visible transition and an explicit return to the declared continuity anchor.

## Learner-facing language

Read `experience-framing-and-learner-language.md`. Internal event maps and assessment records retain exact terms such as evidence, verification, pending review and completion conditions. The visible course does not expose them as course chrome, NPC dialogue, progress labels or buttons. Write the current object, action, consequence and next story move instead. Unless the domain itself is authentic inspection or review work, do not title the experience as an audit station, observation station, laboratory station, workbench, control room or command center. A generic place or job cannot substitute for a content-native world.

## Review outline and traceability

Create `design-outline.md` before detailed production artifacts. It is the reviewable index of the course and uses stable beat IDs. Each beat states the learning purpose, learner POV, video event and time, required visible evidence, action, interaction surface, response/branch, progress rule, exact return point, audio/visual continuity, assets and why they are needed, sources, success evidence, accessibility/failure path, and next beat. Include course audience, central question, observable final performance, overall route, estimated runtime, delivery profile, and known assumptions.

Repeat the same beat IDs in the course design, blueprint scene `beat_identifiers`, media plan, page design, and production manifest `experience_profile.beat_identifiers`; video production shots also identify their beat. The ordered beat-ID sets must reconcile exactly at review and be included in the applicable design confirmation fingerprint. Record the compared ordered lists in `verification.md`; missing, extra, or reordered IDs block review. The media plan binds each required beat to actual media-clock events and interaction windows. The blueprint binds beats to scenes and tasks; the video plan binds shots and timelines to beats; the manifest carries the exact ordered coverage list. The page design binds events and interactions to page states and visible controls. Keep a trace matrix in `page-design.md`:

`outline beat → objective/task → video scene/event/time → participation-plan event / chosen surface → page state → evidence/feedback → implementation locator`

Expand the interaction column with direct scene controls, object reading/inspection and simulation as applicable, and link each row to `scene-interaction-plan.json`. Check both planned information layers and actual longest-content states. The participation validator checks structure and event-map alignment, not teaching quality or browser behavior.

At design review, each row must be `same`, `justified adaptation`, or `unresolved`, with a reason for any adaptation. Unresolved coverage is a design gap. At functional acceptance, no row may remain unresolved; additions or omissions require a rationale, and the implemented locator and actual run evidence must be recorded. A workbench, document panel, detached navigation, verbose persistent copy, or unrequested module surface is a profile violation. Browser-based mouse/touch interaction is the default; headset behaviors must not be invented unless requested. A document-level cross-reference is necessary but does not replace visual and browser review.

## Review checklist

- [ ] The browser experience is specified as an immersive simulation without assuming VR hardware.
- [ ] One declared video-led progression spine exists; each required beat has a stable ID and media event.
- [ ] Progress conditions follow required actions/evidence rather than elapsed time or playback completion alone.
- [ ] Each interaction is anchored, time-bounded, low-friction, and returns to the exact event and state.
- [ ] Persistent and contextual controls do not compete with the scene; desktop and phone safe zones are specified.
- [ ] Each 360°/3D choice passes the objective-based decision test and has an equivalent path.
- [ ] POV, scene time, sound, captions, objects, and learner state remain coherent across outcomes and recovery.
- [ ] The ordered Beat ID set matches across outline, course design, blueprint, media plan, page design, verification, video plan, and manifest; a mismatch blocks design review.
- [ ] Accessibility and media-failure paths retain the same objective, evidence opportunity, and progress semantics.
- [ ] Course-entry and event-entry resource admission checks are defined and executed before required media is opened.
- [ ] Required resource failures retry or block progression; no degraded media path is presented.
- [ ] Every event is classified as observation, exploration, or judgment, with a learning-action reason for its chosen interaction technology.
- [ ] Interaction density follows cognitive-load constraints rather than a fixed quota.
- [ ] Learner-facing state is contextual and low-disruption while system recovery state remains available.
- [ ] Surface choice follows the actual knowledge action; cards are bounded support, deeper reading/simulation remains attached to its object, and observations do not need artificial hotspots.
- [ ] Before-action, on-demand and after-action information has a justified local budget; full source and necessary conditions remain available.
- [ ] Visible object response and knowledge feedback are separate from selection styling; required-task closure cannot bypass evidence.
- [ ] The approved character or no-character continuity anchor remains coherent from opening to conclusion.
- [ ] The approved POV/continuity model is coherent; first person is used only when the design decision requires it.
- [ ] Core interactions enter from the current scene object, NPC action, audio cue or event hotspot; no detached module launcher or permanent workbench.
- [ ] Interactions have a local response and exact return state; course branching is optional and never assumed.
- [ ] Learner-facing titles, dialogue, buttons and progress use scene language rather than internal review, evidence or status terminology.
