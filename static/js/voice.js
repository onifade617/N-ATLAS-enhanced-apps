/* Lafiya voice layer.
 *
 * Speech-to-text: when the N-ATLaS gateway is configured, voice notes are recorded
 * here and transcribed server-side by its Hausa/Igbo/Yoruba/English models
 * (record()); otherwise the browser's Web Speech API is used (listen()).
 * Text-to-speech: browser speech synthesis (the gateway has no TTS route).
 */
(function () {
  const LOCALES = {en: "en-NG", pcm: "en-NG", yo: "yo-NG", ha: "ha-NG", ig: "ig-NG"};
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  function pickVoice(lang) {
    const voices = window.speechSynthesis ? speechSynthesis.getVoices() : [];
    const want = (LOCALES[lang] || "en-NG").toLowerCase();
    const base = want.split("-")[0];
    return (
      voices.find(v => v.lang.toLowerCase() === want) ||
      voices.find(v => v.lang.toLowerCase().startsWith(base)) ||
      voices.find(v => v.lang.toLowerCase() === "en-ng") ||
      voices.find(v => v.lang.toLowerCase().startsWith("en"))
    );
  }

  window.LafiyaVoice = {
    canListen: !!Recognition,
    canSpeak: "speechSynthesis" in window,

    speak(text, lang) {
      if (!this.canSpeak || !text) return;
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text.replace(/[*_#]/g, ""));
      u.lang = LOCALES[lang] || "en-NG";
      const voice = pickVoice(lang);
      if (voice) u.voice = voice;
      u.rate = 0.95;
      speechSynthesis.speak(u);
    },

    stop() {
      if (this.canSpeak) speechSynthesis.cancel();
    },

    canRecord: !!(navigator.mediaDevices && window.MediaRecorder),

    /* Start recording a voice note. Returns {stop(): Promise<Blob>}; auto-stops after maxMs. */
    async record(maxMs = 45000) {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true});
      const rec = new MediaRecorder(stream);
      const chunks = [];
      rec.ondataavailable = e => e.data.size && chunks.push(e.data);
      const done = new Promise(resolve => {
        rec.onstop = () => {
          stream.getTracks().forEach(t => t.stop());
          resolve(new Blob(chunks, {type: rec.mimeType || "audio/webm"}));
        };
      });
      rec.start();
      const timer = setTimeout(() => rec.state !== "inactive" && rec.stop(), maxMs);
      return {
        stop() {
          clearTimeout(timer);
          if (rec.state !== "inactive") rec.stop();
          return done;
        },
        done,
      };
    },

    listen(lang, onResult, onEnd) {
      if (!Recognition) return null;
      const rec = new Recognition();
      rec.lang = LOCALES[lang] || "en-NG";
      rec.interimResults = true;
      rec.maxAlternatives = 1;
      rec.onresult = e => {
        const r = e.results[e.results.length - 1];
        onResult(r[0].transcript, r.isFinal);
      };
      rec.onerror = () => onEnd && onEnd(true);
      rec.onend = () => onEnd && onEnd(false);
      rec.start();
      return rec;
    },
  };
  if (window.speechSynthesis) speechSynthesis.onvoiceschanged = () => {};
})();
