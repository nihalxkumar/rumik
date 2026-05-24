// Voice loop wiring — placeholder for Phase 3.
// Will own: mic permission, MediaRecorder lifecycle, upload to /api/turn,
// status chip + mic state transitions, audio playback, and typed-answer fallback.
//
// Keep this file dependency-free and under ~5 KB minified — kids' phones may
// be on slow networks.

(() => {
  const mic = document.querySelector(".mic");
  if (!mic) return;

  mic.addEventListener("click", () => {
    // Placeholder: cycle visible state so the design system is dogfooded.
    const cur = mic.dataset.state;
    mic.dataset.state = cur === "recording" ? "idle" : "recording";
  });
})();
