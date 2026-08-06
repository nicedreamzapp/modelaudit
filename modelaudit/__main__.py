"""modelaudit — find the license landmines in a local AI stack.

    python3 -m modelaudit ~/MyProject --ship service

Ordinary license scanners read your dependency manifests. That misses the two things
that actually catch people building with AI:

  1. Model *weights* carry their own license, separate from the code that runs them.
     FLUX is Apache-2.0 code with non-commercial weights. Manifest scanners say fine.
  2. Whether a license bites depends on how you ship. GPL on your own server is fine.
     AGPL on your own server means every user can demand your source.

So this reads weights licenses too, and asks how you ship before deciding anything.
"""

import argparse
import json
import os
import sys

from .detect import scan
from .licenses import SEVERITY_ORDER, SHIP_MODES, classify

COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
C = {
    "blocker": "\033[1;31m", "obligation": "\033[1;33m", "review": "\033[1;36m",
    "attribution": "\033[0;32m", "ok": "\033[0;32m",
    "dim": "\033[2m", "bold": "\033[1m", "off": "\033[0m",
}
if not COLOR:
    C = {k: "" for k in C}

MARK = {"blocker": "✗", "obligation": "!", "review": "?", "attribution": "·", "ok": "·"}


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="modelaudit",
        description="Audit a local AI stack for license obligations you actually have.")
    p.add_argument("path", nargs="?", default=".", help="directory to audit")
    p.add_argument("--ship", choices=sorted(SHIP_MODES), default="service",
                   help="how this reaches other people (default: service)")
    p.add_argument("--offline", action="store_true",
                   help="don't look anything up; use only what's on disk")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--all", action="store_true", help="show clean results too")
    p.add_argument("--depth", type=int, default=6, help="how deep to walk (default 6)")
    a = p.parse_args(argv)

    if not os.path.isdir(os.path.expanduser(a.path)):
        p.error(f"not a directory: {a.path}")

    found = scan(a.path, use_network=not a.offline, max_depth=a.depth)

    rows = []
    for f in found:
        sev, headline, detail = classify(f["license"], a.ship, f["kind"],
                                         published=f.get("published", False))
        rows.append({**f, "severity": sev, "headline": headline, "detail": detail})
    rows.sort(key=lambda r: (SEVERITY_ORDER.get(r["severity"], 9), r["name"]))

    if a.json:
        print(json.dumps({"ship_mode": a.ship, "root": os.path.abspath(a.path),
                          "findings": rows}, indent=2))
        return 1 if any(r["severity"] == "blocker" for r in rows) else 0

    counts = {}
    for r in rows:
        counts[r["severity"]] = counts.get(r["severity"], 0) + 1

    print(f"\n{C['bold']}modelaudit{C['off']}  {os.path.abspath(a.path)}")
    print(f"{C['dim']}shipping as: {a.ship} — {SHIP_MODES[a.ship]}{C['off']}")
    print(f"{C['dim']}{len(rows)} dependencies found"
          f"{'' if not a.offline else ', offline mode'}{C['off']}\n")

    shown = 0
    for r in rows:
        if r["severity"] in ("ok", "attribution") and not a.all:
            continue
        shown += 1
        col = C[r["severity"]]
        print(f"{col}{MARK[r['severity']]} {r['severity'].upper():<11}{C['off']}"
              f"{C['bold']}{r['name']}{C['off']}  {C['dim']}({r['license']}, {r['kind']}){C['off']}")
        print(f"  {r['headline']}")
        for line in _wrap(r["detail"], 76):
            print(f"  {C['dim']}{line}{C['off']}")
        print(f"  {C['dim']}↳ {r['path']}{C['off']}")
        if r.get("source"):
            print(f"  {C['dim']}↳ license from: {r['source']}{C['off']}")
        print()

    if shown == 0:
        print(f"{C['ok']}Nothing to worry about in this mode.{C['off']}")
        if not a.all:
            print(f"{C['dim']}Run with --all to see everything that was checked.{C['off']}")

    summary = "  ".join(f"{C.get(k,'')}{v} {k}{C['off']}"
                        for k, v in sorted(counts.items(),
                                           key=lambda kv: SEVERITY_ORDER.get(kv[0], 9)))
    print(f"{C['dim']}{'─'*70}{C['off']}\n{summary}\n")

    if counts.get("review"):
        print(f"{C['dim']}Anything marked REVIEW is a license I can't safely interpret. "
              f"That's not a pass — it means read it yourself.{C['off']}\n")

    return 1 if counts.get("blocker") else 0


def _wrap(text, width):
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main())
