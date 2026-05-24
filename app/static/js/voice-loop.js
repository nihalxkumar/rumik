// Voice / answer loop for the practice screen.
//
// Phase 2 (current): typed answers only. POST { session_id, question_id,
// typed_answer } to /api/turn, render the tutor response, advance.
// Phase 3 will add MediaRecorder + multipart upload on the same endpoint.
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
    setStatus("Check kar raha hoon…");
    setMic("thinking");

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
      return;
    }

    if (!res.ok) {
      setStatus(`Error ${res.status}`);
      setMic("idle");
      return;
    }

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

    if (data.next_question) {
      state.questionId = data.next_question.id;
      promptEl.textContent = data.next_question.prompt;
      input.value = "";
      input.focus();
    } else {
      // Deck finished — phase 6 will route to /summary.
      setStatus("All done!");
      input.disabled = true;
    }

    setMic("idle");
  }

  // ---------- Wire up inputs ----------
  form?.addEventListener("submit", (e) => {
    e.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    submitTypedAnswer(value);
  });

  mic?.addEventListener("click", () => {
    // Phase 3 wires the real recorder here. For now nudge the user
    // toward the typed-answer path so the loop is still usable.
    setStatus("Type your answer for now");
    input.focus();
  });
})();
