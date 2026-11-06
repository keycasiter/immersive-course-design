/* Deterministic Demo carrier. Replace render callbacks with reviewed course content. */
const eventMap = JSON.parse(document.getElementById("video-event-map").textContent);
const storageKey = "storyboard:" + eventMap.event_graph_version;
let state = { eventIdentifier: eventMap.events[0].beat_id, phase: "playback", drafts: {}, completed: [] };
function persist() { localStorage.setItem(storageKey, JSON.stringify(state)); }
function render() {
  document.getElementById("course-stage").dataset.phase = state.phase;
  document.getElementById("task-surface").hidden = state.phase === "playback" || state.phase === "return";
  document.getElementById("submit-interaction").hidden = state.phase !== "paused";
  document.getElementById("complete-interaction").hidden = state.phase !== "feedback";
  document.dispatchEvent(new CustomEvent("course-event", { detail: structuredClone(state) }));
  persist();
}
function currentEvent() { return eventMap.events.find(row => row.beat_id === state.eventIdentifier); }
function enterEvent(identifier) {
  const event = currentEvent();
  if (event.evidence_required && !state.completed.includes(event.beat_id) && identifier !== event.beat_id) return false;
  const targetIndex = eventMap.events.findIndex(row => row.beat_id === identifier);
  if (targetIndex < 0 || eventMap.events.slice(0, targetIndex).some(
      row => row.evidence_required && !state.completed.includes(row.beat_id))) return false;
  state.eventIdentifier = identifier; state.phase = "playback"; render(); return true;
}
function openInteraction() {
  state.phase = "paused"; render(); document.getElementById("task-surface").focus();
}
function closeInteraction() {
  state.phase = "return"; render(); document.getElementById("open-interaction").focus();
}
function saveDraft(value) { state.drafts[state.eventIdentifier] = value; persist(); }
function showFeedback() { state.phase = "feedback"; render(); }
function completeInteraction() {
  if (state.phase !== "feedback") return false;
  if (!state.completed.includes(state.eventIdentifier)) state.completed.push(state.eventIdentifier);
  closeInteraction();
}
function restoreState() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved && ["playback", "paused", "feedback", "return"].includes(saved.phase) &&
        eventMap.events.some(row => row.beat_id === saved.eventIdentifier) &&
        Array.isArray(saved.completed) && saved.drafts && typeof saved.drafts === "object") state = saved;
  } catch { /* Invalid local data starts at the first event. */ }
  render();
  if (state.phase === "paused" || state.phase === "feedback") document.getElementById("task-surface").focus();
}
document.getElementById("open-interaction").addEventListener("click", openInteraction);
document.getElementById("close-interaction").addEventListener("click", closeInteraction);
document.getElementById("submit-interaction").addEventListener("click", showFeedback);
document.getElementById("complete-interaction").addEventListener("click", completeInteraction);
document.getElementById("response").addEventListener("input", event => saveDraft(event.target.value));
document.addEventListener("course-event", event => {
  document.getElementById("response").value = event.detail.drafts[event.detail.eventIdentifier] || "";
});
restoreState();
