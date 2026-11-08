#!/usr/bin/env python3
"""Publish one original X post through Typefully.

Requires YOUR_TYPEFULLY_API_KEY and YOUR_TYPEFULLY_SOCIAL_SET_ID
(or YOUR_SOCIAL_SET_ID). Never automate x.com in a browser:
X's automation rules ban scripting the X website (risk of permanent
suspension), which is the reason this path exists.

AI disclosure is the operator's own choice: set X_MADE_WITH_AI=true in
.env to stamp Made with AI on the post. Default is off.

Exit codes: 0 ok/published, 1 API or network error, 2 bad input,
4 publish still unconfirmed after polling (check the Typefully UI).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

X_CHAR_LIMIT = 280
POLL_TRIES, POLL_SECS = 20, 2


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
    """Operator's choice, read from env. Default: off."""
    return (os.environ.get("X_MADE_WITH_AI", "").strip().lower()) in ("1", "true", "yes")


def validate_text(text: str, allow_long: bool) -> None:
    if not text.strip():
        print("error: --text is empty; refusing to publish an empty post", file=sys.stderr)
        sys.exit(2)
    if len(text) > X_CHAR_LIMIT and not allow_long:
        print(
            f"error: --text is {len(text)} chars; X standard limit is {X_CHAR_LIMIT}. "
            "Pass --allow-long if your account has longer posts.",
            file=sys.stderr,
        )
        sys.exit(2)


def api(method: str, url: str, key: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"error: Typefully HTTP {e.code}: {err}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"error: cannot reach Typefully ({e.reason}); check your connection", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"error: Typefully returned non-JSON: {raw[:200]}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    parser = argparse.ArgumentParser(description="Publish an original via Typefully")
    parser.add_argument("--text", required=True)
    parser.add_argument(
        "--allow-long", action="store_true", help=f"skip the {X_CHAR_LIMIT}-char check"
    )
    parser.add_argument("--no-wait", action="store_true", help="do not poll for x_published_url")
    args = parser.parse_args()

    validate_text(args.text, args.allow_long)
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
                "settings": {"made_with_ai": made_with_ai()},
            }
        },
        "publish_at": "now",
    }
    created = api(
        "POST",
        f"https://api.typefully.com/v2/social-sets/{sid}/drafts",
        key,
        payload,
    )
    draft_id = created.get("id")
    if not draft_id:
        print(
            "error: Typefully response has no draft id; keys: "
            + ", ".join(sorted(created.keys())),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps({"draft_id": draft_id, "publish_state": created.get("publish_state")}, indent=2)
    )
    if args.no_wait:
        return 0

    url = f"https://api.typefully.com/v2/social-sets/{sid}/drafts/{draft_id}"
    for _ in range(POLL_TRIES):
        time.sleep(POLL_SECS)
        d = api("GET", url, key)
        if d.get("publish_state") == "finished":
            print(
                json.dumps(
                    {"x_published_url": d.get("x_published_url"), "status": d.get("status")},
                    indent=2,
                )
            )
            return 0
        if d.get("publish_state") in ("failed", "error"):
            print(
                f"error: Typefully reports the draft failed (state={d.get('publish_state')}); "
                f"inspect draft {draft_id} in the UI",
                file=sys.stderr,
            )
            return 1
    print(
        f"publish not confirmed after {POLL_TRIES * POLL_SECS}s; publish_at=now is async. "
        f"Check draft {draft_id} in the Typefully UI before assuming anything.",
        file=sys.stderr,
    )
    return 4


if __name__ == "__main__":
    sys.exit(main())
