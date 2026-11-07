# Contract Ownership and Source of Truth

This file defines which artifact owns each rule. `SKILL.md` is the orchestrator: it routes work, applies gates, and reports status. It must not introduce a second schema for a contract owned below.

## Ownership map

| Concern | Authoritative artifact | What it owns |
|---|---|---|
| Scope, authorization limit, inheritance and complete-course coverage | `work-scope.md` | `scope_type`, `work_scope.endpoint`, required content inventory, content-to-Beat coverage, video-only Demo delta and inherited/omitted artifacts |
| Formal course status and human gates | `orchestration-and-status.md` | `design_draft` through `effect_evaluated`, gate evidence and transitions |
| Manifest fields, delivery and acceptance | `production-manifest.md` | manifest schema, `delivery_endpoint` compatibility and minimum formal state, acceptance evidence, stable IDs, ordered coverage and revision checks |
| Clarification and independent Demo acceptance | `clarification-gate.md` | prerequisite decisions, sufficient explicit input reuse, actual user evidence and Demo reviewer conditions |
| Intake and decisions | `designer-intake-and-clarification.md` | question construction, decision records and assumption policy; gate closure points to clarification-gate.md |
| Skill and Agent maintenance | `skill-maintenance.md` | feedback generalization, active-target updates, routing/template/validator synchronization and isolated regression |
| Phase reading and persistent execution | `execution-flow.md` | draft checkpoints, early review reports, bounded delegation, recovery and real command-result capture; no change to endpoint or acceptance schemas |
| Knowledge-to-experience derivation | `knowledge-to-immersive-experience.md` | derivation chain from targets to world, perspective, video events and local interactions; candidate comparison, anti-copying and four release gates |
| Content design quality and Imagineering routing | `content-design-quality.md` | candidate divergence, disciplinary authenticity, problem tension, learner agency, evidence visibility, experience increment, quality scoring and content review state |
| Knowledge targets and instructional cycle | `knowledge-organization.md`, `instructional-design.md`, `course-evaluation.md` | objectives, evidence, practice, help, remediation, transfer and evaluation |
| Contextual knowledge weaving | `contextual-knowledge-weaving.md` | background, people, allusions, events, disciplinary lineage, milestones, impact and reception; contextual spine selection, reveal timing, return-to-core use and depth review |
| Transfer contrast and assessment integrity | `instructional-design.md`, `course-evaluation.md` | actual baseline/current material contrast in instructional design; assessment-integrity sidecar 1.0, shared first-response release, assistance and result provenance in course evaluation |
| Situated entry and world transition | `situated-entry-and-world-transition.md` | zero-background orientation, entry reason, continuity, identity, first action, persistent carrier and opening fields |
| Subject pedagogy and experience selection | `subject-pedagogy.md` and its routed subject guides | knowledge difficulty, conditional teaching mechanisms, representation bridges, perceptual experience, source applicability and uncovered-topic research; reuses existing content-quality fields |
| Subject interaction guidance | `subject-interaction-guidance.md` | implementation routes from selected pedagogy, knowledge-type surfaces, feedback targets and acceptance checks |
| Participation and interaction surfaces | `scene-participation-design.md`, `interaction-surface-implementation-matrix.md`, `course-contract.md` | event class, knowledge action, surface selection, input, feedback and accessibility equivalent |
| Knowledge-to-surface matrix | `knowledge-surface-and-demo-contract.md` | matrix schema, target/path/viewport browser coverage and Demo artifact blocking rules |
| Spatial teaching production | `spatial-learning-production.md` | teaching-to-rule-to-visual handoff, procedural/DCC/hybrid selection, structural/look quality and stage dependencies; technical implementation remains in threejs-anime-short |
| Spatial plan and scene-state runtime | `spatial-learning-contract.md` | optional plan 1.0, units/parameters/invariants, action consequences, clock/state ownership, native runtime binding and applicable evidence domains |
| Video-led runtime | `video-led-web-course.md`, `video-timeline-and-quality.md`, `implementation-playbook.md` | real video clock, event map, pause/resume, seeking, recovery and browser runtime |
| Presentation, synchronized atmosphere and exact anchors | `video-presentation-contract.md` | separate presented-frame clock, epoch reconstruction, cue/world-state/phase schema, optional static fallback, normalized rectangles, occlusion and centered contain projection |
| Video-led visual surface | `video-surface-contract.md` | video-dominant playback, on-demand controls/chapters, paused focused work surface and return behavior |
| Page semantics and UI quality | `page-structure.md`, `final-page-ui-quality.md` | semantic regions, layout, UI states and responsive content rules |
| UI design process | `final-page-ui-quality.md`, `ui-quality-evidence.md` | UICraft design/implementation, mandatory Web Design Guidelines review, optional Impeccable polish evidence and severity gates |
| Media production and asset substitution | `production-workflow.md`, `media-job-execution.md`, `asset-substitution-register` | jobs, attempts, costs, rights, substitutions and media admission |
| Supplied or inherited input media | `source-media-admission.md` | complete source inventory, not_supplied versus failed, file-bound content observation, decoding and per-source frame evidence |
| Selected output reuse | `media-job-execution.md` | reuse record 1.0, original accepted attempt, current request and authority identity, output integrity and non-overwriting recovery |
| Serialized submission and request identity | `media-job-execution.md` | Job 1.1 readback, canonical request_sha256, positional reference manifest, exact authority bindings and recovery; implemented by submission_contract.py |
| Actual seam state and media boundaries | `video-direction-and-continuity.md`, `video-timeline-and-quality.md` | semantic carryover and routes in direction; adopted source PTS/time_base, current hashes and inspection evidence in timeline |
| Video production plan and inspection | `video-production-system.md`, `video-timeline-and-quality.md` | provider capability, shot/unit compilation, timing, media inspection and file-bound review |
| Character references and first appearance | `character-reference-and-introduction.md` | source research, fixed appearance, shot identity, actual video introductions, schema 1.1 and output-bound evidence |
| Storyboard and interaction states | `experience-blueprint.md`, `storyboard-and-interaction-spec.md` | perceptual frames, captions, hotspot states and return states |
| Story causality and learner consequences | `narrative-storyboard-integration.md` | applicable narrative routes, actual actions/dialogue, participation-promise checks, material transitions and branch carryover |
| Isolated storyboard text review | `storyboard-review.md`, `../assets/storyboard-review.contract.json` | scoped text review process and interpretation in the reference; record 1.0 fields/enums in the contract, byte/line binding and case-comparison limits; no semantic acceptance |
| Complete design detail | `design-detail-standard.md` | required design modules, usable materials, recorded speech, feedback branches and exhaustive delivery review |
| Interaction information and effort | `interaction-and-atmosphere.md` | focused action, progressive reading, object-based operations and observable interface burden checks |
| Trial and effect evaluation | `course-evaluation.md`, `orchestration-and-status.md` | learner trial, sample, conditions, findings and supported/inconclusive outcomes |
| Immersion intent, review records and learner experience | `immersion-evaluation.md` | intent-to-decision-to-evidence mapping, bundled M13/M18 immersion subset, plan/packet v2, calibration and coverage reporting, whole journey and construct-specific trial/comparison protocol; no automatic semantic acceptance |

## Precedence

Resolve conflicts in this order:

1. User requirements and legal/safety constraints;
2. The authoritative artifact in this table;
3. Confirmed course decisions;
4. Project production profile;
5. `SKILL.md` routing guidance.

If an authoritative artifact conflicts with another authoritative artifact, stop production and record a `contract_conflict` decision. Do not silently merge or choose the more recent-looking wording.

## Duplication policy

- `SKILL.md` may summarize a rule and link to its owner, but must not redefine the owner's schema.
- Examples in `SKILL.md` are illustrative only. A field name or enum becomes contractual only in the owner file.
- A new field must be added to the owner first, then referenced from `SKILL.md`.
- A generated course may copy a contract into its local manifest only with a contract version and source path.
- Validators must read the owner schema, not a hand-maintained duplicate in the page or narrative document.

## Delivery and lifecycle pointers

For artifact completeness, endpoint/acceptance compatibility and minimum formal state, read [production-manifest.md](production-manifest.md). For authorization limits and inherited or local scope, read [work-scope.md](work-scope.md). For human gates, lifecycle transitions and evaluation status, read [orchestration-and-status.md](orchestration-and-status.md). This map routes those concerns; it does not define their tables again.
