# Subject Interaction Guidance

This file owns subject-specific interaction implementation guidance. It does not provide page templates or select a pedagogy from a subject label. Before selecting surfaces, use [subject pedagogy](subject-pedagogy.md) and its applicable knowledge-type guide to diagnose the difficulty, compare teaching mechanisms, map representations and design the key experience. This file then routes that choice to an object, learner action, interaction surface, feedback contract and acceptance evidence.

## Routing contract

For every target, resolve:

```text
subject context and knowledge difficulty
→ selected teaching mechanism and representation mapping
→ intended perceptual experience
→ knowledge object
→ required learner action
→ visible evidence
→ preferred surface
→ deterministic or rubric feedback
→ accessibility equivalent
→ acceptance evidence
```

Subject labels never select an interaction by themselves. The same subject may use reading, spatial judgment, comparison, simulation, ordering or structured editing.

## Guidance schema

```json
{
  "subject_context": "history|politics|society|geography|earth_science|mathematics|physics|chemistry|biology|medicine|language|reading|writing|computer_science|engineering|art|design|media|cross_subject",
  "knowledge_object": "what the learner is acting on",
  "knowledge_type": "fact|sequence|spatial|causal|procedural|evidence|pattern|decision|creation",
  "required_learner_actions": ["notice|classify|order|locate|compare|manipulate|trace|select|revise|construct"],
  "visible_evidence": "what the learner can inspect or change",
  "preferred_surfaces": ["surface_identifier"],
  "feedback_target": "object|relationship|condition|step|source|constraint",
  "minimum_acceptance_evidence": "what a reviewer can observe",
  "common_failure_mode": "what not to implement"
}
```

## Subject routes

| Subject context | Typical objects | Required design attention | Preferred surfaces | Feedback must identify |
|---|---|---|---|---|
| History / politics / society | dates, places, actors, institutions, primary sources, viewpoints | separate sourced fact, inference, teaching fiction and simulation | timeline, map hotspot, source annotation, comparison, constrained decision | date, source sentence, action, institutional relation or viewpoint |
| Geography / earth science | location, scale, direction, terrain, environmental variables, spatial distribution | preserve scale, legend, direction, layers and data source | map layer, profile, route trace, measurement, distribution comparison | location, distance, direction, layer, scale or distribution relation |
| Mathematics | symbols, quantities, figures, variables, invariants, proof steps | preserve intermediate states and mathematical constraints | parameter manipulation, graph transform, step completion, relation matching | variable, constraint, relation or invalid intermediate step |
| Physics | observable quantities, controls, conditions, model and result | declare controlled variables and model limits | experiment control, parameter comparison, prediction and result reading | input condition, observable result and causal relation |
| Chemistry | substances, properties, reagents, conditions, phenomena and safety boundaries | distinguish substance, condition and observed result; preserve safety state | condition combination, phenomenon matching, result prediction | ineffective combination, observed phenomenon or safety constraint |
| Biology / medicine | structures, stages, systems, samples, symptoms and risk boundaries | distinguish observation, inference, diagnosis and safety advice | structure locator, process ordering, layer view, mechanism comparison | observed fact, inferred mechanism, uncertainty or risk boundary |
| Language / reading / writing | context, words, syntax, meaning, evidence, discourse structure | keep feedback local to wording and structure | highlight, local replacement, evidence placement, ordering, structured editor | word, sentence, relation, rhetorical move or missing evidence |
| Computer science | input, state, output, constraint, logs, errors and recovery | make states reproducible and repairable | run/observe/debug loop, configuration, trace, state transition | input, state transition, error cause or corrected output |
| Engineering | materials, specifications, cost, safety, constraints and results | expose trade-offs and trace decisions to constraints | parameter selection, solution comparison, constraint check, result preview | satisfied/violated constraint and consequence |
| Art / design / media | composition, rhythm, layers, material, intent and revision | avoid pretending subjective judgment has one hidden answer | layer manipulation, local variant, before/after comparison, rubric check | design dimension, visible change and rubric criterion |

## Knowledge type to surface

| Knowledge type | Learner action | Preferred surface | Do not replace with |
|---|---|---|---|
| Fact / concept | identify, distinguish, classify, recall | object label, classification, matching, bounded choice | long explanation followed by one recall question |
| Sequence / process | order, locate stage, observe change | draggable timeline, segment playback, step view | static list with a single choice |
| Spatial / structural | locate, measure, compare relation, trace | map, profile, layer view, zoomable 2D object | decorative map plus prose |
| Causal / mechanism | change condition, compare result, inspect relation | parameter control, before/after, causal chain | generic “main reason” question |
| Procedure / skill | execute constraint, find error, revise step | step operation, simulation, error locator, preview | watch-only demonstration |
| Evidence / data | find, filter, compare, support judgment | source annotation, evidence layer, table/chart filter | letting a model summarize the conclusion |
| Pattern / language form | detect, transform, generate, correct | highlight, local replacement, matching, structured edit | large explanation followed by fill-in |
| Decision / trade-off | compare under constraints, inspect consequences | scenario choice, resource allocation, consequence preview | value judgment without conditions |
| Creation / argument | organize, support, revise | structured editor, ordering, evidence insertion, rubric | unrestricted long-form answer in a basic Demo |

## Interaction selection rules

1. Start with the action and evidence, not the subject label.
2. Optimize surface complexity only after preserving both the intended knowledge action and the explicit perceptual experience; text carrying the same facts is not automatically experience-equivalent.
3. Prefer scene-bound manipulation for spatial, procedural and causal knowledge.
4. Use bounded choices when the answer is deterministic and the evidence is visible.
5. Use structured editing when the learner must organize or revise a finite structure.
6. Open response requires a rubric, saving, review responsibility and an explicit evaluation state.
7. Do not introduce a second surface only to make the course appear varied.
8. Every surface must define entry, in-progress, success, error, help, revision, return and accessibility equivalent states.

## Observable evidence in science

When a science task asks learners to observe or infer a mechanism, inspect its actual materials before writing the answer or feedback:

- List the available modality and provenance: visible image feature, reported operation, instrument reading, real touch, sourced explanation or labeled simulation. A picture of an object provides no touch, smell or unrecorded measurement; blank image regions do not locate invisible substances.
- Keep the observation record separate from mechanism/model statements. An observed result can support several explanations. Identify which further observation or control weakens a competing explanation and which supports a condition relation; match the conclusion strength to that combined evidence.
- Mark illustrative arrows, generated scenes, assumed conditions and authored results as models or teaching simulations. They can support a task about reading records, but do not become real experimental findings.
- Check every correct answer, distractor, hint and feedback against the same evidence boundary. Define classification by meaning and provenance rather than a sentence pattern.

Completion: each claimed observation points to obtainable material, each inference names its supporting evidence and remaining limits, and the reviewer can inspect the actual task and feedback. A static contract cannot certify scientific reasoning.

## Subject-specific acceptance checks

- History: the learner can make one non-guessing judgment from at least two dated, sourced or spatially anchored pieces of evidence.
- Geography: an action changes or reveals a real map relationship; decorative proximity is not evidence.
- Mathematics: the action changes a mathematical object and preserves an inspectable intermediate state.
- Physics: the learner can reproduce a condition and observe the corresponding result.
- Chemistry: invalid combinations explain the observed or safety failure without hiding the condition.
- Biology/medicine: observation, inference and diagnosis are visibly separated; risk boundaries are explicit.
- Language/reading/writing: feedback points to a word, sentence or structure, not only a score.
- Computer science: the error is reproducible, the repair is observable and the state is recoverable.
- Engineering: the result can be traced to inputs, constraints and trade-offs.
- Art/design/media: the learner can see the before/after change and the criterion used for review.

If the relevant acceptance check cannot be demonstrated, keep the target in `design_draft` or mark the matrix row `blocked`; do not compensate with extra explanation or decorative interaction.
