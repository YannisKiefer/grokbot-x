#!/usr/bin/env python3
"""Create a Typefully reply draft. Do not set publish_at.

X blocks API reply publish. Open the returned private URL in the
Typefully UI, read the reply once more, and hit Publish NOW: that human
click is the approval step required by X's automation rules. made_with_ai
is the operator's choice (X_MADE_WITH_AI=true to disclose), default off.

Exit codes: 0 ok, 1 API or network error, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

X_CHAR_LIMIT = 280
REPLY_URL_RE = re.compile(
    r"^https?://(www\.)?(x|twitter)\.com/(?P<user>[A-Za-z0-9_]{1,15})/status/(?P<id>\d+)/?$"
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def require(name: str) -> str:
    val = (os.environ.get(name) or "").strip()
    if not val or val.startswith("YOUR_"):
        print(
            f"error: missing or placeholder env {name}; copy .env.example to .env "
            "and fill it (Typefully Settings -> API)",
            file=sys.stderr,
        )
        sys.exit(2)
    return val


def made_with_ai() -> bool:
    return (os.environ.get("X_MADE_WITH_AI", "").strip().lower()) in ("1", "true", "yes")


def validate_inputs(text: str, reply_to: str) -> None:
    if not text.strip():
        print("error: --text is empty; refusing to draft an empty reply", file=sys.stderr)
        sys.exit(2)
    if len(text) > X_CHAR_LIMIT:
        print(
            f"error: --text is {len(text)} chars; X standard limit is {X_CHAR_LIMIT}. "
            "Trim the reply; long replies under a parent read like essays.",
            file=sys.stderr,
        )
        sys.exit(2)
    if not REPLY_URL_RE.match(reply_to.strip()):
        print(
            f"error: --reply-to is not an X post URL: {reply_to!r}. "
            "Expected https://x.com/<user>/status/<numbers>",
            file=sys.stderr,
        )
        sys.exit(2)


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    parser = argparse.ArgumentParser(description="Create a Typefully reply draft")
    parser.add_argument("--text", required=True)
    parser.add_argument("--reply-to", required=True, help="parent tweet URL")
    args = parser.parse_args()

    validate_inputs(args.text, args.reply_to)
    key = require("YOUR_TYPEFULLY_API_KEY")
    sid = os.environ.get("YOUR_TYPEFULLY_SOCIAL_SET_ID") or os.environ.get("YOUR_SOCIAL_SET_ID")
    if not sid or str(sid).startswith("YOUR_"):
        print(
            "error: missing YOUR_TYPEFULLY_SOCIAL_SET_ID (Typefully -> Development mode)",
            file=sys.stderr,
        )
        return 2

    payload = {
        "platforms": {
            "x": {
                "enabled": True,
                "posts": [{"text": args.text}],
                "settings": {
                    "made_with_ai": made_with_ai(),
                    "reply_to_url": args.reply_to.strip(),
                },
            }
        }
    }
    req = urllib.request.Request(
        f"https://api.typefully.com/v2/social-sets/{sid}/drafts",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(
            f"error: Typefully HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}",
            file=sys.stderr,
        )
        return 1
    except urllib.error.URLError as e:
        print(f"error: cannot reach Typefully ({e.reason}); check your connection", file=sys.stderr)
        return 1
    try:
        created = json.loads(raw)
    except json.JSONDecodeError:
        created = None
    if not isinstance(created, dict):
        print(f"error: Typefully returned non-JSON: {raw[:200]}", file=sys.stderr)
        return 1

    private_url = created.get("private_url") or created.get("url")
    if not private_url:
        print(
            "error: Typefully response has no draft URL; keys: "
            + ", ".join(sorted(created.keys())),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "draft_id": created.get("id"),
                "private_url": private_url,
                "next": "Open private_url, read the reply once more, then Publish NOW by hand. "
                "That click is the human approval; do not schedule.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
