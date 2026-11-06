/* Copy into the runtime bundle. Presentation never advances the lesson. */
export function attachPresentationClock(video, onPosition, onPresentation) {
  let epoch = 0, last = -Infinity, frameHandle, disposed = false, pendingFrame = null;
  const accurate = typeof video.requestVideoFrameCallback === "function";
  const emit = (seconds, kind, presentedMs) => {
    if (!Number.isFinite(seconds) || video.seeking || seconds < last) return;
    last = seconds;
    onPresentation({ seconds, kind, epoch, presentedMs, accurate });
  };
  const position = () => {
    onPosition(video.currentTime);
    if (!accurate) emit(video.currentTime, "approximate", performance.now());
  };
  const requestFrame = () => {
    const requestedEpoch = epoch;
    frameHandle = video.requestVideoFrameCallback((now, metadata) => {
      if (disposed || requestedEpoch !== epoch) return;
      if (video.seeking) pendingFrame = { seconds: metadata.mediaTime, presentedMs: now, epoch };
      else emit(metadata.mediaTime, "frame", now);
      requestFrame();
    });
  };
  const seeking = () => {
    epoch += 1; last = -Infinity; pendingFrame = null;
    onPresentation({ seconds: null, kind: "invalidate", epoch, accurate });
    if (accurate) { video.cancelVideoFrameCallback(frameHandle); requestFrame(); }
  };
  const seeked = () => {
    if (!accurate) position();
    else if (pendingFrame?.epoch === epoch) {
      emit(pendingFrame.seconds, "frame", pendingFrame.presentedMs);
      pendingFrame = null;
    }
  };
  video.addEventListener("timeupdate", position);
  video.addEventListener("seeking", seeking);
  video.addEventListener("seeked", seeked);
  if (accurate) requestFrame();
  return () => {
    disposed = true;
    video.removeEventListener("timeupdate", position);
    video.removeEventListener("seeking", seeking);
    video.removeEventListener("seeked", seeked);
    if (frameHandle !== undefined) video.cancelVideoFrameCallback(frameHandle);
  };
}

export function atmosphereAt(spec, seconds, worldState, reduced = false, failed = false, rebuild = false) {
  const t = Math.max(0, Math.min(seconds, spec.duration_seconds));
  const cues = spec.atmosphere.cues;
  const index = t === spec.duration_seconds ? cues.length - 1 :
    cues.findIndex(cue => cue.start_seconds <= t && t < cue.end_seconds);
  if (index < 0) throw new Error("Atmosphere timeline is not covered");
  const cue = cues[index], state = cue.states.find(row => row.world_state_identifier === worldState);
  if (!state) throw new Error("Atmosphere world-state variant is missing");
  const still = reduced || failed || cue.motion === "still";
  const phase = still ? 0 : (t - cue.start_seconds) % cue.cycle_seconds;
  const alpha = rebuild || still || !index || !cue.transition_seconds ? 1 :
    Math.min(1, (t - cue.start_seconds) / cue.transition_seconds);
  const priorCue = cues[index - 1];
  const previous = priorCue?.states.find(row => row.world_state_identifier === worldState);
  if (alpha < 1 && !previous) throw new Error("Transition world-state variant is missing");
  return { cueIdentifier: cue.identifier, sceneIdentifier: cue.scene_identifier,
    assetIdentifier: still ? state.still_asset_identifier : state.asset_identifier,
    previousAssetIdentifier: alpha < 1 ? previous.asset_identifier : null,
    previousPhase: priorCue ? (priorCue.end_seconds - priorCue.start_seconds) % priorCue.cycle_seconds : 0,
    previousCycleSeconds: priorCue?.cycle_seconds || 1,
    phase, alpha, cycleSeconds: cue.cycle_seconds, still };
}

export class AtmosphereController {
  constructor(root, spec, assets) {
    this.root = root; this.spec = spec; this.assets = assets;
    this.layers = [0, 1].map(() => {
      const node = document.createElement("img");
      node.alt = ""; node.draggable = false; root.append(node);
      const motion = node.animate(
        [{ transform: "scale(1)" }, { transform: "scale(1.04)" }, { transform: "scale(1)" }],
        { duration: 1000, iterations: Infinity });
      motion.pause();
      return { node, motion };
    });
    root.setAttribute("aria-hidden", "true"); root.inert = true;
    this.failedAssets = new Set(); this.epoch = null;
  }
  apply(sample, worldState, { reduced = false, rebuild = false } = {}) {
    if (sample.kind === "invalidate") { this.root.hidden = true; return null; }
    if (!Number.isFinite(sample.seconds)) throw new Error("Presentation time is required");
    const raw = atmosphereAt(this.spec, sample.seconds, worldState, reduced);
    const state = atmosphereAt(this.spec, sample.seconds, worldState, reduced,
      this.failedAssets.has(raw.assetIdentifier), rebuild || sample.epoch !== this.epoch);
    if (this.failedAssets.has(state.previousAssetIdentifier)) {
      state.previousAssetIdentifier = null; state.alpha = 1;
    }
    this.epoch = sample.epoch; this.root.hidden = false;
    this.last = [sample, worldState, { reduced, rebuild: true }];
    for (const [index, layer] of this.layers.entries()) {
      const identifier = index ? state.assetIdentifier : state.previousAssetIdentifier;
      layer.node.hidden = !identifier;
      if (!identifier) continue;
      if (this.failedAssets.has(identifier)) {
        if (index) this.root.hidden = true;
        continue;
      }
      const asset = this.assets[identifier];
      if (!asset) throw new Error(`Missing atmosphere asset: ${identifier}`);
      if (layer.node.dataset.assetIdentifier !== identifier) {
        layer.node.dataset.assetIdentifier = identifier;
        layer.node.onerror = () => {
          this.failedAssets.add(identifier);
          if (this.last) this.apply(...this.last);
        };
        layer.node.src = asset;
      }
      layer.node.style.opacity = index ? String(state.alpha) : String(1 - state.alpha);
      layer.motion.currentTime = index ? state.phase / state.cycleSeconds * 1000 :
        state.previousPhase / state.previousCycleSeconds * 1000;
    }
    this.root.dataset.cueIdentifier = state.cueIdentifier;
    this.root.dataset.assetIdentifier = state.assetIdentifier;
    this.root.dataset.phaseSeconds = String(state.phase);
    return state;
  }
  dispose() {
    for (const layer of this.layers) { layer.motion.cancel(); layer.node.remove(); }
    this.last = null;
  }
}

export function anchorAt(track, seconds) {
  if (seconds < track.start_seconds || seconds >= track.end_seconds ||
      track.occlusions.some(row => row.start_seconds <= seconds && seconds < row.end_seconds)) return null;
  const points = track.keyframes;
  const right = points.findIndex(row => row.presentation_seconds >= seconds);
  if (right <= 0) return points[right < 0 ? points.length - 1 : 0].rectangle;
  const a = points[right - 1], b = points[right];
  const f = (seconds - a.presentation_seconds) / (b.presentation_seconds - a.presentation_seconds);
  return Object.fromEntries(["x", "y", "width", "height"].map(
    key => [key, a.rectangle[key] + (b.rectangle[key] - a.rectangle[key]) * f]));
}

export function projectContain(rectangle, source, viewport) {
  const scale = Math.min(viewport.width / source.width, viewport.height / source.height);
  const left = viewport.x + (viewport.width - source.width * scale) / 2;
  const top = viewport.y + (viewport.height - source.height * scale) / 2;
  return { x: left + rectangle.x * source.width * scale,
    y: top + rectangle.y * source.height * scale,
    width: rectangle.width * source.width * scale,
    height: rectangle.height * source.height * scale };
}

export function placeAnchor(node, track, sample, source, videoBounds, overlayBounds) {
  const rectangle = sample.kind === "invalidate" || !sample.accurate ? null :
    anchorAt(track, sample.seconds);
  node.hidden = !rectangle; node.disabled = !rectangle;
  if (!rectangle) return null;
  const projected = projectContain(rectangle, source, {
    x: videoBounds.x - overlayBounds.x, y: videoBounds.y - overlayBounds.y,
    width: videoBounds.width, height: videoBounds.height });
  if (projected.width < 44 || projected.height < 44) {
    node.hidden = true; node.disabled = true;
    return { fallbackRequired: true };
  }
  Object.assign(node.style, { left: `${projected.x}px`, top: `${projected.y}px`,
    width: `${projected.width}px`, height: `${projected.height}px` });
  return projected;
}
