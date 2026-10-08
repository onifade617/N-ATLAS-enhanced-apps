(function () {
  const chat = document.getElementById("chat");
  const form = document.getElementById("ask");
  const input = document.getElementById("text");
  const langSel = document.getElementById("lang");
  const micBtn = document.getElementById("mic");
  const autospeak = document.getElementById("autospeak");
  const facilitiesBox = document.getElementById("facilities");
  const suggestionsBox = document.getElementById("suggestions");
  const voiceNote = document.getElementById("voice-note");
  const suggestions = JSON.parse(document.getElementById("suggestions-data").textContent);
  let conversationId = window.conversationId;
  let recognition = null;

  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const scroll = () => { chat.scrollTop = chat.scrollHeight; };
  scroll();

  function renderSuggestions() {
    suggestionsBox.innerHTML = "";
    (suggestions[langSel.value] || suggestions.en).forEach(s => {
      const b = el("button", "btn btn-sm btn-outline-teal", s);
      b.type = "button";
      b.onclick = () => send(s);
      suggestionsBox.appendChild(b);
    });
  }
  langSel.addEventListener("change", renderSuggestions);
  renderSuggestions();

  const serverAsr = window.natlasAsr && LafiyaVoice.canRecord;
  // Challenge mode: voice input must go through the official N-ATLaS ASR — no browser fallback.
  const browserAsrAllowed = LafiyaVoice.canListen && !window.challengeMode;
  if (serverAsr) {
    voiceNote.textContent = "Tap the mic, speak, then tap again. Speech is recognised by N-ATLaS (Hausa, Igbo, Yoruba, English).";
  } else if (window.challengeMode) {
    micBtn.disabled = true;
    voiceNote.textContent = "Voice input needs the N-ATLaS gateway (challenge mode). Please type for now.";
  } else if (!LafiyaVoice.canListen) {
    voiceNote.textContent = "Voice input isn't supported in this browser — try Chrome or Edge, or type your question.";
  }
  let recording = null;
  let currentAudio = null;

  function stopAudio() {
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    LafiyaVoice.stop();
  }

  /* Read an answer aloud in its own language: N-ATLaS gateway voices (Hausa, Igbo, Yoruba, English),
     falling back to the browser's voice when the gateway is not connected. */
  async function playAnswer(data) {
    stopAudio();
    if (window.natlasAsr && data.message_id) {
      try {
        const res = await fetch("/navigator/api/speak/", {
          method: "POST",
          headers: {"Content-Type": "application/json", "X-CSRFToken": window.csrfToken},
          body: JSON.stringify({message_id: data.message_id}),
        });
        if (res.ok) {
          const {url} = await res.json();
          currentAudio = new Audio(url);
          await currentAudio.play();
          return;
        }
      } catch (e) { /* fall back to the browser voice */ }
    }
    LafiyaVoice.speak(data.reply, data.language);
  }

  async function transcribe(blob) {
    const ext = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
    const body = new FormData();
    body.append("audio", blob, `voice.${ext}`);
    body.append("language", langSel.value);
    voiceNote.textContent = "Listening to your voice note…";
    const res = await fetch("/navigator/api/transcribe/", {method: "POST", headers: {"X-CSRFToken": window.csrfToken}, body});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not transcribe");
    voiceNote.textContent = "";
    return data.text;
  }

  async function toggleRecording() {
    if (recording) {
      const rec = recording;
      recording = null;
      micBtn.classList.remove("listening");
      try {
        const text = await transcribe(await rec.stop());
        input.value = text;
        send(text, "n-atlas");
      } catch (e) {
        voiceNote.textContent = e.message + " You can also type your question.";
      }
      return;
    }
    try {
      stopAudio();
      recording = await LafiyaVoice.record();
      micBtn.classList.add("listening");
      voiceNote.textContent = "Recording… tap the mic again when you finish.";
      recording.done.then(() => { if (recording) toggleRecording(); });  // auto-stop at the time limit
    } catch (e) {
      voiceNote.textContent = "Microphone permission is needed to speak to Lafiya.";
    }
  }

  async function refer(facility, referralId, button) {
    const res = await fetch("/navigator/api/refer/", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRFToken": window.csrfToken},
      body: JSON.stringify({facility_id: facility.id, referral_id: referralId}),
    });
    if (res.ok) {
      button.textContent = "✓ Referral saved";
      button.disabled = true;
    }
  }

  function facilityCard(f, referralId) {
    const card = el("div", "facility-chip");
    card.appendChild(el("div", "fw-semibold", f.name));
    card.appendChild(el("div", "text-muted", `${f.type} · ${f.distance_km} km · ${f.hours}`));
    const verified = f.hours_verified !== false;
    card.appendChild(el("div", f.open_now ? "text-success" : "text-danger",
      (verified ? "" : "Usually ") + (f.open_now ? (verified ? "Open now" : "open now") : (verified ? "Closed now" : "closed now"))));
    const actions = el("div", "d-flex gap-2 mt-1");
    const go = el("button", "btn btn-sm btn-teal", "I'll go here");
    go.type = "button";
    go.onclick = () => refer(f, referralId, go);
    const dir = el("a", "btn btn-sm btn-outline-teal", "Directions");
    dir.href = f.map_url;
    dir.target = "_blank";
    actions.append(go, dir);
    if (f.phone) {
      const call = el("a", "btn btn-sm btn-outline-secondary", "Call");
      call.href = "tel:" + f.phone.replace(/\s/g, "");
      actions.append(call);
    }
    card.appendChild(actions);
    return card;
  }

  function renderReply(data) {
    const b = el("div", "bubble assistant" + (data.emergency ? " emergency" : ""));
    b.appendChild(el("div", "", data.reply));
    if (data.reminder) {
      b.appendChild(el("div", "mt-2 small text-success", `🔔 ${data.reminder.title} (reminder on ${data.reminder.date})`));
    }
    if (data.risk) {
      const r = el("div", "mt-2 small");
      r.appendChild(el("span", `risk-pill risk-${data.risk.level_code}`, `${data.risk.hazard} · ${data.risk.level} · ${data.risk.trend}`));
      r.appendChild(el("div", "text-muted mt-1", "Why: " + data.risk.why));
      b.appendChild(r);
    }
    if (data.topic && data.generated_by !== "n-atlas") {
      const t = el("div", "mt-2 small");
      t.appendChild(el("div", "fw-semibold", data.topic.title));
      const ul = el("ul", "mb-0");
      data.topic.points.forEach(p => ul.appendChild(el("li", "", p)));
      t.appendChild(ul);
      b.appendChild(t);
    }
    const meta = el("div", "meta");
    const speakBtn = el("button", "btn btn-link btn-sm p-0 me-2", "🔊 Listen");
    speakBtn.type = "button";
    speakBtn.onclick = () => playAnswer(data);
    meta.appendChild(speakBtn);
    meta.appendChild(document.createTextNode(
      (data.generated_by === "n-atlas" ? "N-ATLAS" : "Grounded template") +
      (data.sources.length ? " · Sources: " + data.sources.join("; ") : "")
    ));
    b.appendChild(meta);
    chat.appendChild(b);

    if (data.facilities && data.facilities.length) {
      facilitiesBox.innerHTML = "";
      data.facilities.forEach(f => facilitiesBox.appendChild(facilityCard(f, data.referral_id)));
      const inline = el("div", "bubble assistant");
      inline.appendChild(facilityCard(data.facilities[0], data.referral_id));
      chat.appendChild(inline);
    }
    scroll();
    if (autospeak.checked) playAnswer(data);
  }

  async function send(text, voice) {
    text = (text || input.value).trim();
    if (!text) return;
    input.value = "";
    chat.appendChild(el("div", "bubble user", text));
    const typing = el("div", "bubble assistant text-muted", "Lafiya is thinking…");
    chat.appendChild(typing);
    scroll();
    try {
      const res = await fetch("/navigator/api/ask/", {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRFToken": window.csrfToken},
        body: JSON.stringify({
          text, language: langSel.value, conversation_id: conversationId,
          input_mode: voice ? "voice" : "text", asr: voice || "",
        }),
      });
      const data = await res.json();
      typing.remove();
      if (!res.ok) {
        chat.appendChild(el("div", "bubble assistant", data.error || "Something went wrong."));
        return;
      }
      conversationId = data.conversation_id;
      renderReply(data);
    } catch (e) {
      typing.textContent = "Network problem — please try again.";
    }
  }

  form.addEventListener("submit", e => { e.preventDefault(); send(); });

  micBtn.addEventListener("click", () => {
    if (serverAsr) { toggleRecording(); return; }
    if (!browserAsrAllowed) return;
    if (recognition) { recognition.stop(); return; }
    LafiyaVoice.stop();
    micBtn.classList.add("listening");
    recognition = LafiyaVoice.listen(
      langSel.value,
      (transcript, isFinal) => {
        input.value = transcript;
        if (isFinal) send(transcript, "browser");
      },
      () => { micBtn.classList.remove("listening"); recognition = null; }
    );
  });
})();
