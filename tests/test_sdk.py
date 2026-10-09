"""natlas-health SDK: client, safety layer, evaluation, fine-tuning data, playground and CLI. No Django or GPU needed."""

import base64
import io
import json
import os
import tempfile
import threading
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from unittest import TestCase

from natlas_health import (
    AuthenticationError,
    BadRequestError,
    FeatureNotEnabledError,
    HealthAssistant,
    NatlasClient,
    NotConfiguredError,
    UnavailableError,
    detect_danger,
)
from natlas_health import cli, dataset, evaluate
from natlas_health.assistant import DANGER_FACT
from natlas_health.playground import make_server
from natlas_health.testing import FakeGateway, MockClient

KEY = "sdk-key"
DOWN = "http://127.0.0.1:1"
GOOD_REPLY = "Tobi's next vaccines are Pentavalent 1, OPV 1, PCV 1 and Rotavirus 1, due on 14 Oct 2026. " \
             "They are free at Agodi PHC, 1.2 km away. Please take Tobi there this week."


class ClientTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gw = FakeGateway(api_key=KEY).start()

    @classmethod
    def tearDownClass(cls):
        cls.gw.stop()

    def setUp(self):
        self.gw.requests.clear()
        self.client = NatlasClient(self.gw.url, api_key=KEY, timeout=5)

    def test_base_url_forms(self):
        for base in (self.gw.url + "/", self.gw.url + "/v1", self.gw.url + "/v1/chat/completions"):
            self.assertEqual(NatlasClient(base).url("/health"), self.gw.url + "/health")

    def test_chat_sends_model_language_and_key(self):
        resp = self.client.chat("Sannu!", language="ha")
        self.assertEqual(resp.text, "N-ATLaS reply (ha)")
        path, headers, body = self.gw.requests[-1]
        payload = json.loads(body)
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(headers["Authorization"], f"Bearer {KEY}")
        self.assertEqual(payload["model"], "NCAIR1/N-ATLaS")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "Sannu!"}])
        self.assertEqual(payload["language"], "ha")

    def test_pidgin_uses_no_chat_template_and_english_asr(self):
        self.client.chat("How far?", language="pcm")
        self.assertNotIn("language", json.loads(self.gw.requests[-1][2]))
        t = self.client.transcribe(b"fake-audio", "note.ogg", "audio/ogg", "pcm")
        self.assertEqual((t.text, t.language), ("transcript-en", "en"))

    def test_transcribe_from_path(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "note.ogg")
            with open(path, "wb") as fh:
                fh.write(b"fake-audio")
            self.assertEqual(self.client.transcribe(path, language="yo").text, "transcript-yo")
        self.assertIn(b'filename="note.ogg"', self.gw.requests[-1][2])

    def test_speak(self):
        speech = self.client.speak("Ẹ kú àárọ̀", language="yo")
        self.assertEqual(speech.audio[:4], b"RIFF")
        self.assertEqual(speech.voice, "yo")
        self.assertEqual(self.client.speak("How far", language="pcm").voice, "en")  # Pidgin is read in English
        with self.assertRaises(BadRequestError):
            self.client.speak("  ")

    def test_errors_are_typed(self):
        with self.assertRaises(AuthenticationError):
            NatlasClient(self.gw.url, api_key="wrong").chat("hi")
        with self.assertRaises(UnavailableError):
            NatlasClient(DOWN, timeout=1, retries=1, retry_wait=0).chat("hi")
        with self.assertRaises(NotConfiguredError):
            NatlasClient().chat("hi")
        with FakeGateway(api_key=KEY, speech=False) as gw:
            with self.assertRaises(FeatureNotEnabledError):
                NatlasClient(gw.url, api_key=KEY).speak("hello")

    def test_error_messages_survive(self):
        """FastAPI {"detail"} (gateway), vLLM {"message"} and OpenAI {"error": {"message"}} bodies."""
        from natlas_health.client import _error_detail

        self.assertEqual(_error_detail({"detail": "Missing key"}), "Missing key")
        self.assertEqual(_error_detail({"object": "error", "message": "too long"}), "too long")
        self.assertEqual(_error_detail({"error": {"message": "bad"}}), "bad")
        self.assertIsNone(_error_detail([{"msg": "x"}]))
        with self.assertRaisesRegex(AuthenticationError, "Missing or invalid API key"):
            NatlasClient(self.gw.url, api_key="wrong").chat("hi")

    def test_health_never_raises(self):
        self.assertTrue(self.client.health())
        self.assertEqual(self.client.health().details["status"], "ok")
        self.assertFalse(NatlasClient(DOWN).health(timeout=1))
        self.assertFalse(NatlasClient().health())

    def test_from_env(self):
        env = {"NATLAS_BASE_URL": self.gw.url + "/v1", "NATLAS_API_KEY": KEY, "NATLAS_TIMEOUT": "7"}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            client = NatlasClient.from_env()
        finally:
            for k, v in old.items():
                os.environ.pop(k) if v is None else os.environ.__setitem__(k, v)
        self.assertEqual((client.base_url, client.api_key, client.timeout), (self.gw.url, KEY, 7))


class SafetyAndAssistantTests(TestCase):
    def test_danger_detection_is_multilingual_and_accent_insensitive(self):
        self.assertTrue(detect_danger("Mo lóyún, ẹ̀jẹ̀ ń jáde lára mi."))
        self.assertTrue(detect_danger("Ina da ciki kuma ina zubar jini"))
        self.assertTrue(detect_danger("My baby is having CONVULSIONS"))
        self.assertFalse(detect_danger("Which vaccine is next?"))
        self.assertTrue(detect_danger("he has a rash", extra_keywords=["rash"]))

    def test_every_built_in_emergency_case_is_detected(self):
        for case in evaluate.load_cases():
            self.assertEqual(detect_danger(case["question"]), bool(case.get("expect", {}).get("emergency")), case["id"])

    def test_emergency_notice_comes_first_whatever_the_model_says(self):
        client = MockClient(reply=lambda p: "**Rest** at home.")
        answer = HealthAssistant(client).answer("I am pregnant and bleeding", language="ha", facts=["30 weeks"])
        self.assertTrue(answer.emergency)
        self.assertTrue(answer.text.startswith("Wannan na iya zama alamar hadari"))
        self.assertIn("112", answer.text)
        self.assertTrue(answer.text.endswith("Rest at home."))  # markdown stripped
        system = json.loads(client.requests[-1][1])["messages"][0]["content"]
        self.assertIn(DANGER_FACT, system)

    def test_fallback_when_gateway_down(self):
        answer = HealthAssistant(NatlasClient(DOWN, timeout=1)).answer("Which vaccine?", fallback="Template reply.")
        self.assertEqual((answer.text, answer.generated_by, answer.emergency), ("Template reply.", "fallback", False))
        self.assertIn("Cannot reach", answer.error)

    def test_grounding_reaches_the_prompt(self):
        client = MockClient()
        answer = HealthAssistant(client, assistant_name="MamaBot").answer(
            "When is my next visit?", language="yo", facts=["Next ANC: 20 Oct 2026"], guidance=["8 contacts"])
        payload = json.loads(client.requests[-1][1])
        self.assertIn("You are MamaBot", payload["messages"][0]["content"])
        self.assertIn("Reply ONLY in Yoruba", payload["messages"][0]["content"])
        self.assertIn("- 8 contacts", payload["messages"][0]["content"])
        self.assertEqual(payload["language"], "yo")
        self.assertIn("Next ANC: 20 Oct 2026", answer.text)  # MockClient echoes the first fact


class EvaluateTests(TestCase):
    case = evaluate.load_cases()[0]  # vaccine-next-en

    def test_built_in_suite_covers_five_languages(self):
        cases = evaluate.load_cases()
        self.assertEqual(len(cases), 20)
        self.assertEqual({c["language"] for c in cases}, {"en", "yo", "ha", "ig", "pcm"})

    def test_good_reply_passes(self):
        checks = evaluate.check_reply(GOOD_REPLY, self.case)
        self.assertTrue(all(v[0] in (True, None) for v in checks.values()), checks)

    def test_bad_replies_are_caught(self):
        def failed(reply, case=self.case):
            return {k for k, v in evaluate.check_reply(reply, case).items() if v[0] is False}

        self.assertIn("plain_text", failed("**Pentavalent 1** is next for you.\n- Go to the clinic"))
        self.assertIn("grounded_numbers", failed("Pentavalent 1 is next. Call 08012345678 for the clinic."))
        self.assertIn("no_placeholders", failed("Pentavalent 1 is next. Go to [address] for the vaccine."))
        self.assertIn("safe_wording", failed("Pentavalent 1 is due. Take paracetamol 500 mg for the fever."))
        self.assertIn("includes_key_fact", failed("Please go to the clinic for your child."))
        yo = dict(self.case, language="yo")
        self.assertIn("language", failed(GOOD_REPLY, yo))
        self.assertNotIn("language", failed("Ẹ mú Tobi lọ sí Agodi PHC fun abẹ́rẹ́ Pentavalent 1 àti OPV 1 ni ọjọ́ 14.", yo))

    def test_run_eval_report(self):
        report = evaluate.run_eval(MockClient(reply=lambda p: GOOD_REPLY), [self.case] * 2)
        self.assertEqual(report["summary"]["pass_rate"], 1.0)
        self.assertEqual(report["summary"]["by_language"], {"en": 1.0})
        down = evaluate.run_eval(NatlasClient(DOWN, timeout=1), [self.case])
        self.assertEqual(down["summary"]["errors"], 1)
        self.assertIn("vaccine-next-en", evaluate.render_markdown(down))


class DatasetTests(TestCase):
    def cases(self):
        rows = []
        for lang in ("en", "yo", "ha"):
            for i in range(5):
                rows.append({"id": f"{lang}-{i}", "language": lang, "question": "Which vaccine next?",
                             "facts": ["Next: Pentavalent 1 on 14 Oct 2026."], "answer": GOOD_REPLY if lang == "en"
                             else "Ẹ mú ọmọ yín lọ fun abẹ́rẹ́ Pentavalent 1 ni ọjọ́ 14 Oct 2026." if lang == "yo"
                             else "Ku kai yaron asibiti don allurar Pentavalent 1 a ranar 14 Oct 2026."})
        rows.append({"language": "en", "question": "no answer yet"})
        return rows

    def test_build_validate_split(self):
        examples = dataset.build(self.cases())
        self.assertEqual(len(examples), 15)  # the case without an answer is skipped
        ex = examples[0]
        self.assertEqual([m["role"] for m in ex["messages"]], ["system", "user", "assistant"])
        self.assertIn("FACTS:", ex["messages"][0]["content"])
        self.assertEqual(dataset.validate(examples), {})
        train, held = dataset.split(examples, eval_fraction=0.2)
        self.assertEqual((len(train), len(held)), (12, 3))
        self.assertEqual({e["language"] for e in held}, {"en", "yo", "ha"})

    def test_validate_rejects_unsafe_targets(self):
        bad = dataset.make_example("en", ["Next: Pentavalent 1"], "Which vaccine?", "**Take** 500 mg paracetamol.")
        problems = " ".join(dataset.validate_example(bad))
        self.assertIn("plain_text", problems)
        self.assertIn("safe_wording", problems)


class PlaygroundAndCliTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(MockClient(api_key="secret-key"), port=0)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.url + path, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
            return raw if path == "/" else json.loads(raw)

    def test_page_and_config_never_expose_the_key(self):
        self.assertIn(b"N-ATLaS Playground", self.call("/"))
        config = self.call("/api/config")
        self.assertTrue(config["mock"])
        self.assertEqual(len(config["samples"]), 20)
        self.assertNotIn("secret-key", json.dumps(config))

    def test_answer_chat_voice(self):
        r = self.call("/api/answer", {"question": "I am bleeding", "language": "en", "facts": ["30 weeks pregnant"]})
        self.assertTrue(r["emergency"])
        self.assertIn("112", r["text"])
        self.assertIn(DANGER_FACT, r["request"]["messages"][0]["content"])
        self.assertIn("HealthAssistant", r["python"])
        self.assertIn("plain_text", r["checks"])
        r = self.call("/api/chat", {"messages": [{"role": "user", "content": "Bawo ni?"}], "language": "yo"})
        self.assertIn("mock N-ATLaS, yo", r["text"])
        r = self.call("/api/speak", {"text": "Sannu", "language": "ha"})
        self.assertEqual(base64.b64decode(r["audio_b64"])[:4], b"RIFF")
        r = self.call("/api/transcribe", {"audio_b64": base64.b64encode(b"x").decode(), "language": "ig"})
        self.assertIn("ig", r["text"])

    def test_cli(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["ask", "Which vaccine?", "-l", "ha", "--fact", "Due: Pentavalent 1", "--mock"])
        self.assertEqual(code, 0)
        self.assertIn("n-atlas", err.getvalue())

    def raw_post(self, path, data, headers):
        req = urllib.request.Request(self.url + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code

    def test_other_sites_cannot_use_the_key(self):
        body = json.dumps({"messages": [{"role": "user", "content": "x"}]}).encode()
        sent = len(self.server.RequestHandlerClass.client.requests)
        self.assertEqual(self.raw_post("/api/chat", body, {"Content-Type": "text/plain"}), 403)  # no-preflight post
        self.assertEqual(self.raw_post("/api/chat", body, {"Content-Type": "application/json",
                                                           "Origin": "https://evil.example"}), 403)
        self.assertEqual(self.raw_post("/api/chat", body, {"Content-Type": "application/json",
                                                           "Host": "evil.example"}), 403)  # DNS rebinding
        self.assertEqual(len(self.server.RequestHandlerClass.client.requests), sent)  # nothing reached N-ATLaS
        self.assertEqual(self.raw_post("/api/chat", body, {"Content-Type": "application/json"}), 200)

    def test_malformed_bodies_get_400(self):
        js = {"Content-Type": "application/json"}
        self.assertEqual(self.raw_post("/api/chat", b'{"messages": ["hi"]}', js), 400)
        self.assertEqual(self.raw_post("/api/answer", b'{"question": "q", "facts": [1]}', js), 400)
        self.assertEqual(self.raw_post("/api/chat", b"[1, 2]", js), 400)
        self.assertEqual(self.raw_post("/api/chat", b"{}", {**js, "Content-Length": "-1"}), 400)

    def test_checks_score_the_raw_model_reply(self):
        self.server.RequestHandlerClass.client.reply = lambda p: "## Next\n- **Pentavalent 1**"
        try:
            r = self.call("/api/answer", {"question": "Which vaccine?", "facts": ["Due: Pentavalent 1"]})
        finally:
            self.server.RequestHandlerClass.client.reply = None
        self.assertFalse(r["checks"]["plain_text"]["passed"])
        self.assertNotIn("**", r["text"])  # the user still gets clean text

    def test_eval_fails_when_gateway_unreachable(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = cli.main(["eval", "--limit", "1", "--base-url", DOWN, "--timeout", "1"])
        self.assertEqual(code, 1)


class ReviewRegressionTests(TestCase):
    case = evaluate.load_cases()[0]
    emergency = next(c for c in evaluate.load_cases() if c["expect"].get("emergency"))

    def failed(self, reply, case=None):
        return {k for k, v in evaluate.check_reply(reply, case or self.case).items() if v[0] is False}

    def test_dosing_and_curly_apostrophes(self):
        for reply in ("Take 2mg of Pentavalent 1.", "Take two paracetamol after Pentavalent 1.",
                      "Give Pentavalent 1 and 1 tablet daily.", "You don’t need to see a doctor about Pentavalent 1."):
            self.assertIn("safe_wording", self.failed(reply), reply)
        self.assertNotIn("safe_wording", self.failed("Please take Tobi for Pentavalent 1 this week."))

    def test_112_and_key_facts_are_whole_tokens(self):
        self.assertIn("emergency_escalation", self.failed("Go now and call 1122.", self.emergency))
        self.assertNotIn("emergency_escalation", self.failed("Go now and call 112.", self.emergency))
        self.assertIn("includes_key_fact", self.failed("Tobi needs OPV 1.", dict(self.case, expect={"include_any": ["OP"]})))

    def test_reformatted_dates_are_grounded(self):
        self.assertNotIn("grounded_numbers", self.failed("Pentavalent 1 is due on 2026-10-14."))
        self.assertIn("grounded_numbers", self.failed("Pentavalent 1 costs 2500 naira."))

    def test_split_edges(self):
        rows = [dataset.make_example("en", ["f"], "q", f"Answer {i}.") for i in range(3)]
        self.assertEqual(len(dataset.split(rows, eval_fraction=0)[1]), 0)
        train, held = dataset.split(rows, eval_fraction=0.9)
        self.assertEqual((len(train), len(held)), (1, 2))
