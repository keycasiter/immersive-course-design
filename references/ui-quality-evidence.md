# UI Quality Evidence

This file owns the UI evidence required for `interactive_web` endpoints.

## Skill routing

- UICraft is mandatory for webpage design and implementation.
- Web Design Guidelines is mandatory for semantic, accessibility, responsive and interaction review.
- Impeccable Design Polish is conditional: use it only after a runnable page exists and the review identifies visual convergence, template residue or share-pass polish work.
- Do not run overlapping UICraft and Impeccable checks twice. Record which tool performed each review.

## Required records

### `ui-design-decision.md`

Record the design context, visual direction, layout contract, type scale, color tokens, interaction states, responsive contract, motion contract, content density and asset-substitution effect.

### `ui-review.md`

Each finding records:

```json
{
  "finding_id": "stable_ui_finding_identifier",
  "category": "accessibility|layout|typography|contrast|interaction|responsive|motion|content|performance",
  "severity": "blocker|high|medium|low",
  "evidence": "viewport, state, element or browser evidence",
  "impact": "impact on task completion or comprehension",
  "fix": "specific correction",
  "verification": "recheck method and result",
  "status": "open|fixed|accepted_with_reason"
}
```

### `polish-log.md`

Record before/after states, hierarchy and spacing changes, removed template decoration, motion changes, remaining assumptions and final browser/screenshots.

## Severity gates

`blocker` includes an unusable core control, keyboard dead end, mobile overflow, unreadable critical text, missing feedback/return state, false media control, detached task entry or an interaction that conflicts with the learning contract.

`high` includes unclear primary task, hotspot/object mismatch, generic error feedback, unstable touch interaction, caption/overlay collision, color-only meaning or a media substitution that changes the learning action.

`medium` and `low` may remain only with a recorded reason and follow-up; they cannot hide an interaction or accessibility defect.
