"""Issue one gateway API key per beta tester, so usage can be counted per person without logging content.

The gateway logs every request with ``key = "k_" + sha256(key)[:12]`` and never the key, prompt or reply.
This script keeps the private roster (name -> key -> fingerprint) in beta_private/roster.csv, which is
git-ignored, and prints the command that installs the keys on the gateway.

    python scripts/beta/keys.py import testers.csv          # columns: name, contact (e.g. from Google Sheets)
    python scripts/beta/keys.py add "Ada Okafor" "Musa Bello" --contact ada@x.ng --contact musa@y.ng
    python scripts/beta/keys.py invites --form <form link> --session "Sat 10 Oct, 2 pm, <meet link>"
    python scripts/beta/keys.py list
    python scripts/beta/keys.py revoke "Musa Bello"
    python scripts/beta/keys.py secret        # prints the modal command with your key + every active tester key

Never commit beta_private/. Send each tester only their own key, through a private channel.
"""

import argparse
import csv
import datetime as dt
import hashlib
import os
import secrets
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROSTER = os.path.join(ROOT, "beta_private", "roster.csv")
FIELDS = ["tester_id", "name", "contact", "fingerprint", "key", "issued", "revoked"]


def fingerprint(key):
    """Same formula as natlas_serve.observability.key_fingerprint."""
    return "k_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def read_roster():
    if not os.path.exists(ROSTER):
        return []
    with open(ROSTER, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_roster(rows):
    os.makedirs(os.path.dirname(ROSTER), exist_ok=True)
    with open(ROSTER, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def owner_key():
    """Your own key from .env (kept active so Lafiya and your evaluation runs keep working)."""
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("NATLAS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def add_testers(people):
    """people: list of (name, contact). Skips names already in the roster."""
    rows = read_roster()
    known = {r["name"].strip().lower() for r in rows}
    for name, contact in people:
        if not name.strip() or name.strip().lower() in known:
            print(f"skipped {name!r} (empty or already in roster)")
            continue
        known.add(name.strip().lower())
        key = secrets.token_hex(32)
        tester_id = f"T{len(rows) + 1:02d}"
        rows.append({"tester_id": tester_id, "name": name, "contact": contact, "fingerprint": fingerprint(key),
                     "key": key, "issued": dt.date.today().isoformat(), "revoked": ""})
        print(f"{tester_id}  {name:<24} {fingerprint(key)}")
    write_roster(rows)
    print(f"\nSaved to {ROSTER}. Now run:  python scripts/beta/keys.py secret")


def cmd_add(args):
    contacts = args.contact + [""] * (len(args.names) - len(args.contact))
    add_testers(list(zip(args.names, contacts)))


def cmd_import(args):
    """CSV with a header row containing 'name' and optionally 'contact' (e.g. exported from Google Sheets)."""
    with open(args.csv, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        cols = {c.lower().strip(): c for c in reader.fieldnames or []}
        if "name" not in cols:
            sys.exit("The CSV needs a 'name' column (and optionally 'contact').")
        people = [((r[cols["name"]] or "").strip(), (r[cols["contact"]] or "").strip() if "contact" in cols else "")
                  for r in reader]
    add_testers(people)


def gateway_url():
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("NATLAS_BASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "<gateway URL>"


INVITE = """Hi {first},

Thank you for helping test natlas-health, the open developer kit for N-ATLaS.

Your tester ID:   {tester_id}
Gateway URL:      {url}
Your API key:     {key}

Keep the key private: it is yours alone and stops working after the beta.
Tester guide (about 30 minutes): https://github.com/onifade617/N-ATLAS-enhanced-apps/blob/main/docs/beta/TESTER_GUIDE.md
Feedback form (use your tester ID): {form}
Live session: {session}

Use made-up data only. The gateway never records your prompts, replies or audio.
"""


def cmd_invites(args):
    """Write one private invite per active tester to beta_private/invites/<id>.txt, ready to paste into email/DM."""
    out = os.path.join(ROOT, "beta_private", "invites")
    os.makedirs(out, exist_ok=True)
    url, n = gateway_url(), 0
    for r in read_roster():
        if r["revoked"]:
            continue
        first = r["name"].split()[0] if r["name"].split() else r["name"]
        text = INVITE.format(first=first, tester_id=r["tester_id"], url=url, key=r["key"],
                             form=args.form, session=args.session)
        with open(os.path.join(out, f"{r['tester_id']}.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"To: {r['contact'] or r['name']}\n\n{text}")
        n += 1
    print(f"Wrote {n} invites to {out}. Send each one privately (email or direct message), never in a group.")


def cmd_list(args):
    for r in read_roster():
        state = f"revoked {r['revoked']}" if r["revoked"] else "active"
        print(f"{r['tester_id']}  {r['name']:<24} {r['fingerprint']}  issued {r['issued']}  {state}")


def cmd_revoke(args):
    rows = read_roster()
    hit = [r for r in rows if r["name"] == args.name or r["tester_id"] == args.name]
    if not hit:
        sys.exit(f"No tester {args.name!r}")
    for r in hit:
        r["revoked"] = dt.date.today().isoformat()
    write_roster(rows)
    print("Revoked. Run `python scripts/beta/keys.py secret` and the printed commands to apply it.")


def cmd_secret(args):
    keys = [owner_key()] + [r["key"] for r in read_roster() if not r["revoked"]]
    keys = [k for k in keys if k]
    if not keys:
        sys.exit("No keys: add testers first, or set NATLAS_API_KEY in .env.")
    print("# Run these two commands (they contain secrets: do not paste them anywhere else).")
    print("# Neither starts a GPU; the next request picks up the new keys.")
    print(f'modal secret create natlas-api --force NATLAS_API_KEYS="{",".join(keys)}"')
    print("cd ../N-ATLAS-Kit && modal deploy serve/modal_app.py")


def main():
    p = argparse.ArgumentParser(description="Per-tester gateway keys for the natlas-health beta.")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("names", nargs="+")
    a.add_argument("--contact", action="append", default=[], help="email/phone, in the same order as names")
    a.set_defaults(func=cmd_add)
    i = sub.add_parser("import", help="add many testers from a CSV with 'name' and 'contact' columns")
    i.add_argument("csv")
    i.set_defaults(func=cmd_import)
    v = sub.add_parser("invites", help="write one private invite message per tester")
    v.add_argument("--form", default="<feedback form link>")
    v.add_argument("--session", default="<date, time and meeting link>")
    v.set_defaults(func=cmd_invites)
    sub.add_parser("list").set_defaults(func=cmd_list)
    r = sub.add_parser("revoke")
    r.add_argument("name", help="name or tester id")
    r.set_defaults(func=cmd_revoke)
    sub.add_parser("secret").set_defaults(func=cmd_secret)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
