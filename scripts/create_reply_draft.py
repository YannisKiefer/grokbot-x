#!/usr/bin/env python3
"""Create a Typefully reply draft. Do not set publish_at.

X blocks API reply publish. Open the returned private URL in the
Typefully UI and hit Publish NOW. made_with_ai stays false.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def require(name: str) -> str:
    val = (os.environ.get(name) or "").strip()
    if not val or val.startswith("YOUR_"):
        print(f"missing or placeholder env: {name}", file=sys.stderr)
        sys.exit(2)
    return val


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    parser = argparse.ArgumentParser(description="Create a Typefully reply draft")
    parser.add_argument("--text", required=True)
    parser.add_argument("--reply-to", required=True, help="parent tweet URL")
    args = parser.parse_args()

    key = require("YOUR_TYPEFULLY_API_KEY")
    sid = os.environ.get("YOUR_TYPEFULLY_SOCIAL_SET_ID") or os.environ.get("YOUR_SOCIAL_SET_ID")
    if not sid or str(sid).startswith("YOUR_"):
        print("missing YOUR_TYPEFULLY_SOCIAL_SET_ID", file=sys.stderr)
        return 2

    payload = {
        "platforms": {
            "x": {
                "enabled": True,
                "posts": [{"text": args.text}],
                "settings": {
                    "made_with_ai": False,
                    "reply_to_url": args.reply_to,
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
            created = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Typefully HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "draft_id": created.get("id"),
                "private_url": created.get("private_url") or created.get("url"),
                "next": "Open private_url in Typefully UI and Publish NOW. Do not schedule.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
