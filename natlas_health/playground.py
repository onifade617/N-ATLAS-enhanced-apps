"""N-ATLaS Playground: try chat, grounded health answers, speech-to-text and voices in the browser.

    python -m natlas_health playground            # uses NATLAS_BASE_URL / NATLAS_API_KEY
    python -m natlas_health playground --mock     # no GPU: offline MockClient

The page talks only to this local server, which holds the API key and forwards to the gateway, so the key
never reaches the browser. Every response shows the exact request sent to N-ATLaS, the latency, the
evaluation checks, and the equivalent Python code.
"""

import base64
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources

from . import evaluate, prompts
from .assistant import HealthAssistant
from .errors import BadRequestError, NatlasError
from .languages import LANGUAGES

log = logging.getLogger(__name__)
MAX_BODY = 12 * 1024 * 1024


def python_snippet(mode, body):
    lang = body.get("language", "en")
    if mode == "chat":
        return (
            "from natlas_health import NatlasClient\n\n"
            "client = NatlasClient.from_env()\n"
            f"reply = client.chat({body.get('messages')!r},\n"
            f"                    language={lang!r}, temperature={body.get('temperature', 0.3)})\n"
            "print(reply.text)\n"
        )
    return (
        "from natlas_health import NatlasClient, HealthAssistant\n\n"
        "assistant = HealthAssistant(NatlasClient.from_env())\n"
        f"answer = assistant.answer(\n    {body.get('question', '')!r},\n    language={lang!r},\n"
        f"    facts={body.get('facts', [])!r},\n    guidance={body.get('guidance', [])!r},\n)\n"
        "print(answer.text, answer.generated_by, answer.emergency)\n"
    )


def _list(body, key, kind):
    value = body.get(key) or []
    if not isinstance(value, list) or not all(isinstance(v, kind) for v in value):
        raise ValueError(f"{key} must be a list of {kind.__name__}")
    return value


class PlaygroundHandler(BaseHTTPRequestHandler):
    client = None  # set by make_server

    def log_message(self, fmt, *args):
        log.debug(fmt, *args)

    def _json(self, code, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        try:
            size = int(self.headers.get("Content-Length", 0))
        except ValueError:
            raise ValueError("Bad Content-Length") from None
        if not 0 <= size <= MAX_BODY:
            self.close_connection = True  # the unread body can't be reused on this connection
            raise ValueError("Request too large")
        body = json.loads(self.rfile.read(size) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("Send a JSON object")
        return body

    def _discard_body(self):
        """Read (and drop) a small request body so a refusal reaches the client instead of a connection reset."""
        try:
            size = int(self.headers.get("Content-Length", 0))
        except ValueError:
            size = 0
        if 0 < size <= MAX_BODY:
            self.rfile.read(size)
        else:
            self.close_connection = True

    def _trusted(self):
        """Only this page may use the playground (it spends your API key).

        * Host must be this server: blocks DNS rebinding (attacker.com resolving to 127.0.0.1).
        * Origin, when sent, must be this server: blocks other sites' fetch/form posts.
        * POSTs must be application/json, which a cross-site page cannot send without a CORS preflight.
        """
        host, port = self.server.server_address[:2]
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}", f"{host}:{port}"}
        if self.headers.get("Host", "") not in allowed:
            return False
        origin = self.headers.get("Origin")
        if origin and origin.split("://", 1)[-1] not in allowed:
            return False
        if self.command == "POST" and not self.headers.get("Content-Type", "").startswith("application/json"):
            return False
        return True

    def do_GET(self):
        if not self._trusted():
            return self._json(403, {"error": "Forbidden: open the playground at http://127.0.0.1:<port>/"})
        if self.path in ("/", "/index.html"):
            page = resources.files("natlas_health").joinpath("static/playground.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        elif self.path == "/api/config":
            self._json(200, {
                "gateway": self.client.base_url, "model": self.client.model,
                "mock": self.client.base_url.startswith("mock://"), "languages": LANGUAGES,
                "system_prompt": prompts.SYSTEM_PROMPT, "samples": evaluate.load_cases(),
            })
        elif self.path == "/api/health":
            status = self.client.health(timeout=30)
            self._json(200, {"ok": status.ok, "details": status.details})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._trusted():
            self._discard_body()
            return self._json(403, {"error": "Forbidden: requests must come from the playground page as JSON"})
        try:
            body = self._body()
            route = {"/api/chat": self.chat, "/api/answer": self.answer,
                     "/api/transcribe": self.transcribe, "/api/speak": self.speak}.get(self.path)
            if route is None:
                return self._json(404, {"error": "not found"})
            route(body)
        except BadRequestError as exc:  # the gateway rejected the input (e.g. undecodable audio): the caller's fault
            self._json(400, {"error": f"{exc.__class__.__name__}: {exc}", "status": exc.status})
        except NatlasError as exc:
            self._json(502, {"error": f"{exc.__class__.__name__}: {exc}", "status": exc.status})
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self._json(400, {"error": str(exc) or exc.__class__.__name__})

    def chat(self, body):
        messages = [m for m in _list(body, "messages", dict) if str(m.get("content") or "").strip()]
        if not messages:
            raise ValueError("Add at least one message")
        language = body.get("language", "en")
        resp = self.client.chat(messages, language=language, temperature=float(body.get("temperature", 0.3)),
                                max_tokens=int(body.get("max_tokens", 500)))
        self._json(200, {"text": resp.text, "latency_ms": resp.latency_ms, "model": resp.model,
                         "request": {"messages": messages, "language": language},
                         "python": python_snippet("chat", body)})

    def answer(self, body):
        language = body.get("language", "en")
        question = (body.get("question") or "").strip()
        if not question:
            raise ValueError("Ask a question")
        facts = [f for f in _list(body, "facts", str) if f.strip()]
        guidance = [g for g in _list(body, "guidance", str) if g.strip()]
        assistant = HealthAssistant(self.client, temperature=float(body.get("temperature", 0.3)))
        result = assistant.answer(question, language=language, facts=facts, guidance=guidance)
        case = {"language": language, "question": question, "facts": facts, "guidance": guidance,
                "expect": {"emergency": result.emergency}}
        # Score what N-ATLaS actually wrote, before the safety layer strips markdown or adds the notice.
        checks = evaluate.check_reply(result.raw, case) if result.generated_by == "n-atlas" else {}
        self._json(200, {
            "text": result.text, "emergency": result.emergency, "generated_by": result.generated_by,
            "latency_ms": result.latency_ms, "error": result.error,
            "checks": {k: {"passed": v[0], "detail": v[1]} for k, v in checks.items()},
            "request": {"messages": assistant.messages(question, language, facts, guidance, emergency=result.emergency),
                        "language": language},
            "python": python_snippet("answer", {**body, "facts": facts, "guidance": guidance}),
        })

    def transcribe(self, body):
        audio = base64.b64decode(body["audio_b64"])
        result = self.client.transcribe(audio, body.get("filename", "voice.webm"), body.get("content_type"),
                                        body.get("language", "en"))
        self._json(200, {"text": result.text, "asr_language": result.language, "latency_ms": result.latency_ms})

    def speak(self, body):
        speech = self.client.speak(body.get("text", "")[:800], body.get("language", "en"))
        self._json(200, {"audio_b64": base64.b64encode(speech.audio).decode(), "content_type": speech.content_type,
                         "voice": speech.voice, "latency_ms": speech.latency_ms})


def make_server(client, host="127.0.0.1", port=8765):
    handler = type("Handler", (PlaygroundHandler,), {"client": client})
    return ThreadingHTTPServer((host, port), handler)


def serve(client, host="127.0.0.1", port=8765):
    server = make_server(client, host, port)
    print(f"N-ATLaS Playground on http://{host}:{server.server_port}  (gateway: {client.base_url or 'not set'})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
