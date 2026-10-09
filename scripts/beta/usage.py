"""Per-tester usage from the N-ATLaS gateway's request logs: the beta's hard evidence.

The gateway logs one JSON line per request (feature, language, status, latency, tokens, key fingerprint) and
never the prompt, reply, audio or key. Modal keeps logs for only 1 day on the Starter plan, so save them
every day of the beta (fetching logs does not start a GPU):

    modal app logs natlas-serve --since 1d --search '"event":"request"' --tail 20000 \
        > beta_private/logs/$(date +%F).jsonl

Then:

    python scripts/beta/usage.py beta_private/logs/ --since 2026-10-09T12:31 -o docs/beta/usage_report.md

Testers appear by tester id (T01, T02...) from beta_private/roster.csv; pass --names for a private view.
Requests made with your own key (.env) are reported separately, not counted as beta usage.
"""

import argparse
import datetime as dt
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keys import fingerprint, owner_key, read_roster  # noqa: E402

FEATURES = ("chat", "transcription", "speech")
LANGS = ("en", "ha", "yo", "ig", "pcm", "-")


def read_requests(paths):
    """Request records from log files or folders, de-duplicated by request_id (daily exports overlap)."""
    files = []
    for p in paths:
        files += sorted(glob.glob(os.path.join(p, "*"))) if os.path.isdir(p) else [p]
    seen = {}
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                start = line.find("{")  # tolerate --timestamps / container-id prefixes
                if start < 0:
                    continue
                try:
                    rec = json.loads(line[start:])
                except ValueError:
                    continue
                if rec.get("event") == "request" and rec.get("request_id"):
                    seen[rec["request_id"]] = rec
    return sorted(seen.values(), key=lambda r: r.get("ts", 0))


def summarize(records, roster, owner_fp, names=False):
    label = {r["fingerprint"]: (r["name"] if names else r["tester_id"]) for r in roster}
    per = defaultdict(list)
    for rec in records:
        fp = rec.get("key")
        who = "owner" if fp == owner_fp else label.get(fp, "unknown")
        per[who].append(rec)
    rows = []
    for who, recs in per.items():
        days = {dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc).date() for r in recs if r.get("ts")}
        ok = sum(1 for r in recs if 200 <= int(r.get("status", 0)) < 300)
        lat = sorted(r["latency_ms"] for r in recs if r.get("latency_ms") and r.get("feature") == "chat")
        rows.append({
            "who": who, "requests": len(recs), "ok": ok,
            "features": Counter(r.get("feature", "?") for r in recs),
            "languages": Counter(r.get("language") or "-" for r in recs),
            "audio_seconds": round(sum(r.get("audio_seconds") or 0 for r in recs), 1),
            "tokens": sum(r.get("total_tokens") or 0 for r in recs),
            "days": len(days), "first": min(days) if days else None, "last": max(days) if days else None,
            "chat_p50_ms": int(lat[len(lat) // 2]) if lat else None,
        })
    order = {"owner": 2, "unknown": 1}
    rows.sort(key=lambda r: (order.get(r["who"], 0), r["who"]))
    return rows


def render(rows, roster, sources):
    beta = [r for r in rows if r["who"] not in ("owner", "unknown")]
    total = sum(r["requests"] for r in beta)
    ok = sum(r["ok"] for r in beta)
    active = len(beta)
    feats = sum((r["features"] for r in beta), Counter())
    langs = sum((r["languages"] for r in beta), Counter())
    issued = len(roster)
    lines = [
        "# natlas-health beta: usage from gateway logs",
        "",
        f"Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC from {len(sources)} log file(s). "
        "Source: N-ATLAS-Kit gateway request logs (no prompts, replies, audio or keys are ever logged).",
        "",
        f"**{active} of {issued} invited testers made real N-ATLaS calls · {total} requests · "
        f"{(ok / total * 100 if total else 0):.0f}% succeeded**",
        "",
        "| Feature | Requests |", "|---|---|",
        *[f"| {f} | {feats.get(f, 0)} |" for f in FEATURES],
        "",
        "| Language | Requests |", "|---|---|",
        *[f"| {lang} | {langs.get(lang, 0)} |" for lang in LANGS if langs.get(lang)],
        "",
        "| Tester | Requests | OK | Chat | ASR | TTS | Languages | Audio s | Days active | First | Last | Chat p50 ms |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        f = r["features"]
        lang = ", ".join(f"{k} {v}" for k, v in r["languages"].most_common())
        lines.append(f"| {r['who']} | {r['requests']} | {r['ok']} | {f.get('chat', 0)} | {f.get('transcription', 0)} | "
                     f"{f.get('speech', 0)} | {lang} | {r['audio_seconds']} | {r['days']} | {r['first']} | {r['last']} | "
                     f"{r['chat_p50_ms'] or '-'} |")
    lines += ["", "`owner` = the project's own key (evaluation runs, demos); `unknown` = a key not in the roster. "
              "Neither counts as beta usage. Pidgin requests appear as `-` because the kit sends no language hint "
              "for Pidgin."]
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("logs", nargs="+", help="log files or folders")
    p.add_argument("-o", "--output", help="write the Markdown report here")
    p.add_argument("--names", action="store_true", help="show tester names (private use only; do not publish)")
    p.add_argument("--since", help="ignore requests before this UTC time, e.g. 2026-10-09T12:31 (excludes setup tests)")
    args = p.parse_args()
    roster = read_roster()
    records = read_requests(args.logs)
    if args.since:
        cutoff = dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc).timestamp()
        records = [r for r in records if r.get("ts", 0) >= cutoff]
    if not records:
        sys.exit("No gateway request records found in those files.")
    key = owner_key()
    rows = summarize(records, roster, fingerprint(key) if key else None, names=args.names)
    report = render(rows, roster, args.logs)
    if args.output:
        if args.names:
            sys.exit("Refusing to write a report with names; drop --names to publish.")
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"Wrote {args.output}")
    sys.stdout.buffer.write(report.encode("utf-8"))


if __name__ == "__main__":
    main()
