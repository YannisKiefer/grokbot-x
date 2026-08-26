#!/usr/bin/env python3
"""Publish one original X post through Typefully.

Requires YOUR_TYPEFULLY_API_KEY and YOUR_TYPEFULLY_SOCIAL_SET_ID
(or YOUR_SOCIAL_SET_ID). Never compose on x.com from a bot browser.
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
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"Typefully HTTP {e.code}: {err}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    parser = argparse.ArgumentParser(description="Publish an original via Typefully")
    parser.add_argument("--text", required=True)
    parser.add_argument("--no-wait", action="store_true", help="do not poll for x_published_url")
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
                "settings": {"made_with_ai": False},
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
    print(json.dumps({"draft_id": draft_id, "publish_state": created.get("publish_state")}, indent=2))
    if args.no_wait or not draft_id:
        return 0

    url = f"https://api.typefully.com/v2/social-sets/{sid}/drafts/{draft_id}"
    for _ in range(20):
        time.sleep(2)
        d = api("GET", url, key)
        if d.get("publish_state") == "finished":
            print(json.dumps({"x_published_url": d.get("x_published_url"), "status": d.get("status")}, indent=2))
            return 0
    print("timed out waiting for publish_state=finished", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
