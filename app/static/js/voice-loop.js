// Voice / answer loop for the practice screen.
//
// Keep dependency-free and small — slow Android phones are the target.

(() => {
  const seedEl = document.getElementById("lesson-seed");
  if (!seedEl) return;
  const seed = JSON.parse(seedEl.textContent);

  // Persist session_id across reloads so a refresh resumes the lesson.
  const SID_KEY = "rumik:sid";
  const sessionId = () => localStorage.getItem(SID_KEY);
  const rememberSession = (id) => id && localStorage.setItem(SID_KEY, id);

  const state = {
    questionId: seed.questionId,
    deckTotal: seed.deckTotal,
    completed: 0,
    recorder: null,
    chunks: [],
    busy: false,
  };

  // ---------- DOM handles ----------
  const promptEl   = document.querySelector("[data-question-prompt]");
  const bubbleEl   = document.querySelector("[data-tutor-bubble]");
  const youSaidEl  = document.querySelector("[data-you-said]");
  const streakEl   = document.querySelector("[data-streak]");
  const feedback   = document.getElementById("feedback");
  const progressEl = document.querySelector(".progress__fill");
  const statusLbl  = document.querySelector("[data-status-label]");
  const mic        = document.querySelector(".mic");
  const form       = document.getElementById("typed-answer-form");
  const input      = document.getElementById("typed-answer");

  // ---------- UI helpers ----------
  function setStatus(text) { if (statusLbl) statusLbl.textContent = text; }
  function setMic(s)       { if (mic) mic.dataset.state = s; }
  function setBusy(v) {
    state.busy = v;
    if (input) input.disabled = v;
  }
  function renderProgress(done) {
    if (!progressEl) return;
    progressEl.style.width = `${Math.min(100, (done / state.deckTotal) * 100)}%`;
  }
  function showFeedback({ tutor, said, streak, isCorrect }) {
    bubbleEl.textContent  = stripToneTag(tutor);
    youSaidEl.textContent = said ? `You said: ${said}` : "";
    streakEl.textContent  = streak > 0 ? `${streak} correct in a row` : "";
    feedback.hidden = false;
    feedback.classList.remove("anim-pop-in");
    void feedback.offsetWidth;            // restart animation
    feedback.classList.add("anim-pop-in");
    setStatus(isCorrect ? "Sahi jawab" : "Try again");
  }
  function stripToneTag(s) {
    // The bubble shows the human-readable text; the tone tag is for Silk.
    return s.replace(/^\[(neutral|happy|whisper|excited|sad)\]\s*/i, "");
  }

  // ---------- Turn submission ----------
  async function submitTypedAnswer(typed) {
    if (state.busy) return;
    setStatus("Check kar raha hoon…");
    setMic("thinking");
    setBusy(true);

    let res;
    try {
      res = await fetch("/api/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId(),
          question_id: state.questionId,
          typed_answer: typed,
        }),
      });
    } catch (err) {
      setStatus("Network error — try again");
      setMic("idle");
      setBusy(false);
      return;
    }

    if (!res.ok) {
      setStatus(`Error ${res.status}`);
      setMic("idle");
      setBusy(false);
      return;
    }

    await handleTurnResponse(res);
  }

  async function submitAudio(blob) {
    if (state.busy) return;
    setStatus("Sun raha hoon…");
    setMic("uploading");
    setBusy(true);

    const body = new FormData();
    const sid = sessionId();
    if (sid) body.append("session_id", sid);
    body.append("question_id", state.questionId);
    body.append("audio", blob, "answer.webm");

    let res;
    try {
      res = await fetch("/api/turn", { method: "POST", body });
    } catch (err) {
      setStatus("Network error — type instead");
      setMic("idle");
      setBusy(false);
      input?.focus();
      return;
    }

    if (!res.ok) {
      setStatus(`Error ${res.status} — type instead`);
      setMic("idle");
      setBusy(false);
      input?.focus();
      return;
    }

    await handleTurnResponse(res);
  }

  async function handleTurnResponse(res) {
    setStatus("Soch raha hoon…");
    setMic("thinking");
    const data = await res.json();
    rememberSession(data.session_id);
    showFeedback({
      tutor: data.tutor_text,
      said:  data.transcript ?? "",
      streak: data.streak,
      isCorrect: data.is_correct,
    });

    if (data.is_correct) {
      state.completed += 1;
      renderProgress(state.completed);
    }

    const lessonDone = !data.next_question;
    if (data.next_question) {
      state.questionId = data.next_question.id;
      promptEl.textContent = data.next_question.prompt;
      input.value = "";
    } else {
      // Deck finished — phase 6 will route to /summary.
      setStatus("All done!");
      input.disabled = true;
    }

    setMic("idle");
    if (!lessonDone) setBusy(false);
    if (data.error) setStatus(data.error === "no_number_parsed" ? "Please repeat or type" : "Type instead");
  }

  // ---------- Wire up inputs ----------
  form?.addEventListener("submit", (e) => {
    e.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    submitTypedAnswer(value);
  });

  mic?.addEventListener("click", async () => {
    if (state.busy) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setStatus("Mic not supported — type instead");
      input?.focus();
      return;
    }

    if (state.recorder?.state === "recording") {
      state.recorder.stop();
      setStatus("Upload kar raha hoon…");
      setMic("uploading");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      state.recorder = recorder;
      state.chunks = [];

      recorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) state.chunks.push(event.data);
      });
      recorder.addEventListener("stop", () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(state.chunks, { type: recorder.mimeType || "audio/webm" });
        state.recorder = null;
        submitAudio(blob);
      });

      recorder.start();
      setStatus("Bol ke dobara tap karo");
      setMic("recording");
    } catch (err) {
      setStatus("Mic denied — type instead");
      setMic("idle");
      input?.focus();
    }
  });

  function pickMimeType() {
    const preferred = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
    return preferred.find((type) => MediaRecorder.isTypeSupported(type)) || "";
  }
})();
