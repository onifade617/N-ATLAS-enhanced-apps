"""natlas-health command line: talk to N-ATLaS, evaluate it, prepare fine-tuning data, open the playground.

    natlas-health health
    natlas-health chat "Sannu! Yaya kake?" --language ha
    natlas-health ask "Which vaccine next?" --language yo --fact "Child: Tobi, 6 weeks" --fact "Due: Pentavalent 1"
    natlas-health transcribe note.ogg --language yo
    natlas-health speak "Ẹ kú àárọ̀" --language yo -o hello.wav
    natlas-health eval [cases.jsonl] --report report.md --json report.json
    natlas-health dataset build|validate|split ...
    natlas-health playground [--port 8765]

Every command reads NATLAS_BASE_URL / NATLAS_API_KEY / NATLAS_MODEL / NATLAS_TIMEOUT (or --base-url, --api-key);
add --mock to run offline with no GPU.
"""

import argparse
import json
import mimetypes
import os
import sys

from . import __version__, dataset, evaluate
from .assistant import HealthAssistant
from .client import NatlasClient
from .errors import NatlasError
from .languages import LANGUAGES

LANG_CHOICES = list(LANGUAGES)


def load_dotenv(path=".env"):
    """Minimal .env support so the CLI picks up the same settings as your app."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def make_client(args):
    if args.mock:
        from .testing import MockClient

        return MockClient()
    overrides = {k: v for k, v in (("base_url", args.base_url), ("api_key", args.api_key)) if v}
    if args.timeout:
        overrides["timeout"] = args.timeout
    client = NatlasClient.from_env(**overrides)
    if not client.configured:
        sys.exit("No gateway: set NATLAS_BASE_URL (and NATLAS_API_KEY), pass --base-url, or use --mock.")
    return client


def out(text):
    """Print as UTF-8 even on a Windows console (Yoruba and Igbo tone marks)."""
    stream = getattr(sys.stdout, "buffer", None)
    if stream is None:
        print(text)
        return
    stream.write((text + "\n").encode("utf-8"))
    sys.stdout.flush()


def cmd_health(args):
    status = make_client(args).health(timeout=max(30, args.timeout or 0))
    out(("OK " if status.ok else "NOT READY ") + json.dumps(status.details, ensure_ascii=False))
    return 0 if status.ok else 1


def cmd_chat(args):
    messages = ([{"role": "system", "content": args.system}] if args.system else []) + [
        {"role": "user", "content": args.message}]
    resp = make_client(args).chat(messages, language=args.language, temperature=args.temperature,
                                  max_tokens=args.max_tokens)
    out(resp.text)
    print(f"[{resp.model} · {resp.latency_ms} ms]", file=sys.stderr)


def cmd_ask(args):
    answer = HealthAssistant(make_client(args), assistant_name=args.assistant).answer(
        args.question, language=args.language, facts=args.fact, guidance=args.guidance, fallback=args.fallback)
    out(answer.text)
    print(f"[{answer.generated_by} · emergency={answer.emergency} · {answer.latency_ms} ms]"
          + (f" {answer.error}" if answer.error else ""), file=sys.stderr)


def cmd_transcribe(args):
    result = make_client(args).transcribe(args.audio, os.path.basename(args.audio),
                                          mimetypes.guess_type(args.audio)[0], args.language)
    out(result.text)
    print(f"[ASR {result.language} · {result.latency_ms} ms]", file=sys.stderr)


def cmd_speak(args):
    speech = make_client(args).speak(args.text, args.language)
    audio = speech.audio
    if args.output.lower().endswith(".mp3"):
        from .audio import wav_to_mp3

        audio = wav_to_mp3(audio) or sys.exit("MP3 needs: pip install 'natlas-health[audio]'")
    with open(args.output, "wb") as fh:
        fh.write(audio)
    print(f"Wrote {args.output} ({len(audio)} bytes, voice {speech.voice or '-'}, {speech.latency_ms} ms)", file=sys.stderr)


def cmd_eval(args):
    cases = evaluate.load_cases(args.cases)
    if args.language:
        cases = [c for c in cases if c.get("language") in args.language]
    if args.limit:
        cases = cases[: args.limit]
    client = make_client(args)
    print(f"Evaluating {len(cases)} cases on {client.model} at {client.base_url} ...", file=sys.stderr)

    def progress(i, n, row):
        mark = "ERR " if row["error"] else ("pass" if row["passed"] else "FAIL")
        print(f"  [{i}/{n}] {mark} {row['id']}", file=sys.stderr)

    report = evaluate.run_eval(client, cases, assistant_name=args.assistant, progress=progress)
    md = evaluate.render_markdown(report)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(md)
    out(md)
    summary = report["summary"]
    if summary["errors"]:
        print(f"{summary['errors']} of {summary['cases']} cases could not reach N-ATLaS.", file=sys.stderr)
        return 1  # an unreachable or unauthorised gateway must never look like a pass in CI
    return 0 if (summary["pass_rate"] or 0) >= args.min_pass_rate else 1


def cmd_dataset(args):
    if args.output is None:
        args.output = "data/all.jsonl" if args.action == "build" else "data"
    if args.action == "build":
        if not args.output.endswith(".jsonl"):
            sys.exit("dataset build writes a file: pass -o something.jsonl")
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        examples = dataset.build(dataset.read_jsonl(args.input), assistant=args.assistant)
        dataset.write_jsonl(args.output, examples)
        out(f"Wrote {len(examples)} examples to {args.output}: {json.dumps(dataset.stats(examples))}")
    elif args.action == "validate":
        examples = dataset.read_jsonl(args.input)
        problems = dataset.validate(examples)
        for i, p in problems.items():
            out(f"line {i + 1} ({examples[i].get('id', '-')}): {'; '.join(p)}")
        out(f"{len(examples) - len(problems)}/{len(examples)} examples OK. {json.dumps(dataset.stats(examples))}")
        return 1 if problems else 0
    elif args.action == "split":
        train, held = dataset.split(dataset.read_jsonl(args.input), args.eval_fraction, args.seed)
        os.makedirs(args.output, exist_ok=True)
        dataset.write_jsonl(os.path.join(args.output, "train.jsonl"), train)
        dataset.write_jsonl(os.path.join(args.output, "eval.jsonl"), held)
        out(f"train: {len(train)}  eval: {len(held)}  -> {args.output}")


def cmd_playground(args):
    from .playground import serve

    serve(make_client(args), args.host, args.port)


def build_parser():
    p = argparse.ArgumentParser(prog="natlas-health", description="Developer kit for N-ATLaS health applications.")
    p.add_argument("--version", action="version", version=f"natlas-health {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base-url", help="gateway URL (default: NATLAS_BASE_URL)")
    common.add_argument("--api-key", help="gateway key (default: NATLAS_API_KEY)")
    common.add_argument("--timeout", type=int, help="seconds per request (default: NATLAS_TIMEOUT or 60)")
    common.add_argument("--mock", action="store_true", help="offline MockClient, no GPU")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("health", parents=[common], help="GET /health")
    s.set_defaults(func=cmd_health)

    s = sub.add_parser("chat", parents=[common], help="one chat completion")
    s.add_argument("message")
    s.add_argument("--language", "-l", choices=LANG_CHOICES)
    s.add_argument("--system")
    s.add_argument("--temperature", type=float, default=0.3)
    s.add_argument("--max-tokens", type=int, default=300)
    s.set_defaults(func=cmd_chat)

    s = sub.add_parser("ask", parents=[common], help="grounded health answer with the safety layer")
    s.add_argument("question")
    s.add_argument("--language", "-l", choices=LANG_CHOICES, default="en")
    s.add_argument("--fact", action="append", default=[], help="repeatable")
    s.add_argument("--guidance", action="append", default=[], help="repeatable")
    s.add_argument("--fallback", help="text to use if N-ATLaS is unavailable")
    s.add_argument("--assistant", default="Lafiya", help="assistant name in the system prompt")
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("transcribe", parents=[common], help="speech-to-text")
    s.add_argument("audio")
    s.add_argument("--language", "-l", choices=LANG_CHOICES, default="en")
    s.set_defaults(func=cmd_transcribe)

    s = sub.add_parser("speak", parents=[common], help="text-to-speech")
    s.add_argument("text")
    s.add_argument("--language", "-l", choices=LANG_CHOICES, default="en")
    s.add_argument("--output", "-o", default="speech.wav", help=".wav or .mp3")
    s.set_defaults(func=cmd_speak)

    s = sub.add_parser("eval", parents=[common], help="run the health evaluation suite")
    s.add_argument("cases", nargs="?", help="JSONL cases (default: built-in 5-language suite)")
    s.add_argument("--language", "-l", action="append", choices=LANG_CHOICES, help="only these languages")
    s.add_argument("--limit", type=int)
    s.add_argument("--report", help="write the Markdown report here")
    s.add_argument("--json", help="write the full JSON report here")
    s.add_argument("--assistant", default="Lafiya")
    s.add_argument("--min-pass-rate", type=float, default=0.0, help="exit 1 below this (use in CI)")
    s.set_defaults(func=cmd_eval)

    s = sub.add_parser("dataset", help="fine-tuning data: build, validate, split")
    s.add_argument("action", choices=["build", "validate", "split"])
    s.add_argument("input")
    s.add_argument("--output", "-o", default=None, help="build: output .jsonl (default data/all.jsonl); split: directory (default data)")
    s.add_argument("--assistant", default="Lafiya")
    s.add_argument("--eval-fraction", type=float, default=0.1)
    s.add_argument("--seed", type=int, default=13)
    s.set_defaults(func=cmd_dataset)

    s = sub.add_parser("playground", parents=[common], help="browser playground")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(func=cmd_playground)
    return p


def main(argv=None):
    load_dotenv()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args) or 0
    except NatlasError as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
