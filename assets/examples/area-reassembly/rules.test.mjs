import test from 'node:test';
import assert from 'node:assert/strict';
import {geometry, polygonArea} from './rules.mjs';
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-8, `${a} != ${b}`);

test('translation preserves both pieces and their total area across valid shapes', () => {
  for (const base of [1, 6, 12]) for (const height of [0.5, 4, 9])
    for (const fraction of [0.01, 0.3, 0.99]) for (const progress of [0, 0.5, 1]) {
      const g = geometry({base, height, shear: base * fraction, offset: base * progress});
      near(polygonArea(g.original), g.area);
      near(polygonArea(g.remaining) + polygonArea(g.moved), g.area);
    }
});

test('at final offset horizontal sections meet without gap or overlap', () => {
  // At y=t*h, remaining=[s,b+s*t], moved=[b+s*t,b+s].
  for (const base of [1, 6]) for (const shear of [base * 0.1, base * 0.9]) {
    const height = 4, g = geometry({base, height, shear, offset: base});
    for (const t of [0, 0.01, 0.5, 0.99, 1]) {
      const remainingRight = g.remaining[1][0] + (g.remaining[2][0] - g.remaining[1][0]) * t;
      const movedLeft = g.moved[0][0] + (g.moved[2][0] - g.moved[0][0]) * t;
      near(remainingRight, movedLeft);
      near(g.moved[1][0] - g.remaining[0][0], base);
    }
  }
});

test('labels share model values and remain on their intended world anchors', () => {
  const before = geometry(), after = geometry({offset: 6});
  assert.deepEqual(before.heightAnchor, after.heightAnchor);
  assert.deepEqual(after.heightAnchor, [2, 2]);
  assert.equal(after.area, 24);
  assert.equal(after.width, 6);
  assert.equal(after.height, 4);
});

test('invalid or unsupported models are rejected rather than drawn as valid facts', () => {
  for (const params of [{base: 0}, {height: -1}, {shear: 0}, {shear: 6}, {offset: 7}, {height: NaN}])
    assert.throws(() => geometry(params), RangeError);
});

import {readFileSync} from 'node:fs';
import {createPaperAdapter} from './adapter.mjs';
import {createExperienceController} from '../../scene-runtime.mjs';
const plan = JSON.parse(readFileSync(new URL('./scene-plan.json', import.meta.url)));

test('actual controller and adapter share the model; actions do not invent presented events', () => {
  let frame;
  const controller = createExperienceController(plan, createPaperAdapter((model, paper) => {frame = {model, paper};}));
  assert.throws(() => controller.act('slide_corner', {offset: 6}), /Split paper/);
  controller.act('cut_paper');
  controller.act('slide_corner', {offset: 3});
  assert.equal(frame.paper.phase, 'split');
  controller.act('slide_corner', {offset: 6});
  assert.equal(frame.paper.phase, 'rectangle');
  assert.deepEqual(frame.model.moved[0], [6, 0]);
  assert.deepEqual(controller.getState().events, {});
  // Host calls this only after real presentation; here it tests controller plumbing.
  controller.markEvent('event_rectangle');
  const snapshot = controller.snapshot();
  controller.act('reset_paper');
  assert.equal(frame.paper.phase, 'uncut');
  controller.restore(snapshot);
  assert.equal(frame.paper.offset, 6);
  assert.equal(controller.getState().paused, true);
  assert.deepEqual(frame.model.heightAnchor, [2, 2]);
});

test('adapter preserves other objects when returning a top-level objects patch', () => {
  const adapter = createPaperAdapter(() => {});
  const state = {objects: {other: {visible: true}}};
  const patch = adapter.act({interaction_identifier: 'cut_paper'}, {}, state);
  assert.deepEqual(patch.objects.other, state.objects.other);
  assert.equal(state.objects.paper, undefined);
});
