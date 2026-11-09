import {geometry} from './rules.mjs';
const initialPaper = () => ({phase: 'uncut', offset: 0});

// paint is implemented by the course: mesh, matrices, DOM labels and description.
// This adapter is the testable state/model seam, not a Three.js scene.
export function createPaperAdapter(paint) {
  if (typeof paint !== 'function') throw new TypeError('paint callback required');
  return {
    act(action, payload, state) {
      const current = state.objects.paper ?? initialPaper();
      let paper;
      if (action.interaction_identifier === 'cut_paper') {
        paper = current.phase === 'uncut' ? {phase: 'split', offset: 0} : current;
      } else if (action.interaction_identifier === 'slide_corner') {
        if (current.phase === 'uncut') throw new Error('Split paper first');
        if (!Number.isFinite(payload.offset)) throw new TypeError('Finite offset required');
        const offset = Math.max(0, Math.min(6, payload.offset));
        paper = {phase: offset === 6 ? 'rectangle' : 'split', offset};
      } else if (action.interaction_identifier === 'reset_paper') {
        paper = initialPaper();
      } else throw new Error('Unknown paper action');
      return {objects: {...state.objects, paper}};
    },
    evaluate(state) {
      const paper = state.objects.paper ?? initialPaper();
      paint(geometry({offset: paper.offset}), paper, state);
    }
  };
}
