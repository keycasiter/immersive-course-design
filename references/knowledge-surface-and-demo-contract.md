# Knowledge Surface and Demo Contract

This file owns the `knowledge-surface-matrix` schema and the rules for an `interaction_complete_prototype`.

Machine files use a root object with `matrix_version=1.1`, `course_version` and `rows`; copy [the matrix template](../assets/knowledge-surface-matrix.template.json). Each row adds `objective_identifier`, and `knowledge_object_id` maps to blueprint `knowledge_identifier`. Multiple Beat rows may share a knowledge target. `browser_test_identifiers` replaces the former single `browser_test_id`.

## Matrix row

Each knowledge target has one or more Beat rows:

```json
{
  "knowledge_object_id": "stable_english_identifier",
  "objective_identifier": "stable_objective_identifier",
  "beat_id": "stable_beat_identifier",
  "interaction_id": "stable_interaction_identifier",
  "subject_context": "history|geography|mathematics|science|language|engineering|art|cross_subject",
  "knowledge_type": "fact|sequence|spatial|causal|procedural|evidence|pattern|decision|creation",
  "learner_action": "notice|classify|order|locate|compare|manipulate|trace|select|revise|construct",
  "visible_evidence": "object, text, data, relationship or change",
  "scene_context": "scene, media event or content entry",
  "source_ids": ["source_identifier"],
  "event_class": "observation|exploration|judgment",
  "surface": "direct_scene_control|hotspot|timeline|map|comparison|reading|simulation|choice|ordering|matching|structured_editor",
  "media_cue_or_scene_window": {
    "entry": "media time or scene condition",
    "pause": "pause condition",
    "resume": "return time or scene state"
  },
  "input_contract": "allowed learner action",
  "in_progress_state": "visible state during action",
  "success_criteria": "observable completion rule",
  "incorrect_response_mapping": [
    {
      "response_id": "stable_response_identifier",
      "misconception": "incorrect relationship, condition or step",
      "feedback": "specific feedback",
      "revision_action": "allowed correction"
    }
  ],
  "attempt_policy": {
    "max_attempts": "number_or_unlimited",
    "allow_replay": true,
    "preserve_draft": true,
    "on_exhausted": "retry|show_help|block_progression|manual_review"
  },
  "feedback_contract": "judgment basis and target object",
  "help_contract": "help that narrows the search without replacing judgment",
  "assist_levels": [],
  "revision_contract": "retain, revise and recheck behavior",
  "return_state": "media time, captions, focus and local state",
  "accessibility_equivalent": "keyboard, touch, text or 2D equivalent",
  "evaluator": "deterministic_rule|teacher_rubric|self_check|manual_review",
  "content_review": {
    "owner": "review_owner_identifier",
    "status": "pending|approved|rejected",
    "reviewed_version": "content_version"
  },
  "runtime_locator": {
    "page": "page_or_scene_identifier",
    "selector_or_component": "stable_runtime_locator",
    "state_key": "state_store_key"
  },
  "browser_test_identifiers": ["stable_browser_test_identifier"],
  "demo_status": "implemented|blocked|review_pending"
}
```

## Coverage rule

Do not impose an interaction-count quota. For each knowledge target:

```text
required_knowledge_actions ⊆ implemented_knowledge_actions
```

Use `observation` when the learner must notice a change or evidence, `exploration` when the learner must inspect/manipulate/compare an object, and `judgment` when the learner must make a deterministically checkable decision. Reuse a surface when the knowledge action is the same; do not add a surface solely to make a Demo look varied.

## Derived coverage report

`knowledge-action-coverage-report` is derived from `knowledge-surface-matrix`. It is not a second design matrix and does not count interaction types.

```json
{
  "report_version": "1.0",
  "course_version": "course_version",
  "matrix_version": "matrix_version",
  "rows": [
    {
      "knowledge_object_id": "stable_english_identifier",
      "beat_id": "stable_beat_identifier",
      "required_knowledge_actions": ["notice", "compare"],
      "implemented_knowledge_actions": ["notice", "compare"],
      "missing_knowledge_actions": [],
      "evidence": [
        {
          "interaction_id": "stable_interaction_identifier",
          "browser_test_id": "stable_browser_test_identifier",
          "result": "passed|failed|not_run"
        }
      ],
      "status": "covered|partial|missing|blocked"
    }
  ],
  "summary": {
    "required_action_count": 0,
    "implemented_action_count": 0,
    "missing_action_count": 0,
    "blocked_row_count": 0,
    "overall_status": "covered|partial|blocked"
  }
}
```

Generation rules:

- `required_knowledge_actions` comes from the learning goal and matrix `learner_action/event_class`, not from the selected UI surface;
- `implemented_knowledge_actions` comes from the actual interaction state and browser evidence, not from design intention;
- a row is `covered` only when every required action has implementation evidence and its linked browser test passes;
- a row is `partial` when some required actions exist but one or more are missing or unverified;
- a row is `blocked` when a required source, accessibility equivalent, runtime locator or acceptance evidence is missing;
- do not report “more interactive” or “more diverse” as a success criterion;
- the report cannot modify the source matrix and must record the matrix version it used.

## Demo endpoint

`interaction_complete_prototype` requires all low-cost content and interactions to be runnable:

- scene entry and first action;
- object-bound interaction entry;
- in-progress, correct, incorrect, help and revision states;
- deterministic feedback;
- close/complete return state;
- keyboard/touch and accessible equivalent;
- refresh/replay/recovery behavior;
- UI decision, UI review and browser evidence.

For `full_course + interactive_web + video_led_web`, it may substitute only the formal video body. Images, diagrams, documents, runtime code and other required non-video assets must already be final and accepted. It may not defer page structure, content, scenes, Beats, knowledge actions, feedback, recovery, responsive behavior or accessibility paths.

The Demo must cover the complete `required_content_inventory`; a representative interaction sample is only a test selection and cannot define course scope. The production manifest must pass the `video_only_delta` contract in [工作范围](work-scope.md).

## Blocking conditions

Block the endpoint if a row lacks `success_criteria`, applicable `incorrect_response_mapping`, `media_cue_or_scene_window`, `runtime_locator`, `browser_test_identifiers`, approved `source_ids/content_review`, or `accessibility_equivalent`.

Also block a full-course endpoint when:

- `scope_coverage` is missing, partial or contains deferred content;
- any required content item, objective, knowledge unit, required scene or Beat lacks a coverage mapping;
- `demo_completion` is missing or allows work outside the video-only delta;
- a required non-video formal asset or storyboard substitute is not accepted;
- the browser-verified student path is only a representative subset of the course.

## Executable browser coverage

Register the matrix as `knowledge_surface_matrix` and the [browser JSON](../assets/browser-execution.template.json) as `browser_execution`. Each implemented row has a current approved `content_review`, actual `content_review` file evidence, verified blueprint `source_ids`, a runtime locator and linked test identifiers. Tests bind the same objective, knowledge target, Beat and locator.

Every target covers `normal`, `close_return`, `refresh_recovery`, `replay`, `keyboard`, `touch` and `accessible_equivalent` in both desktop and narrow viewports. Exploration and judgment additionally cover `incorrect`, `help` and `revision`; observation can omit these three. Every required Beat, including orientation and summary, has a normal path in both viewports.

Each test records browser, actual time, numeric viewport, entry steps, expected/observed result, `status=passed`, and at least one current SHA256-bound screenshot, trace or operation log. The package binds current runtime/matrix/asset fingerprints; plain `verification` files and completion strings cannot substitute for execution records. `non_video_completion` summarizes these checks and is not independent acceptance evidence.

`validate_production.py --joint` reads the matrix and tests rather than accepting a precomputed coverage summary. It checks complete objective/knowledge/Beat coverage, source identity and all linked path results. Human reviewers still assess whether the recorded knowledge action demonstrates the intended understanding.
