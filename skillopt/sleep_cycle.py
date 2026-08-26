#!/usr/bin/env python3
"""X-domain SkillOpt sleep cycle (adapted from microsoft/skillopt).

harvest metrics -> reflect train vs val -> propose <=LR edits -> gate on held-out
-> adopt into best_skill.md or append rejected_edits.md

This script scores trajectories, prints status, and books accepted/rejected
epochs. The operator (or Grok Bot) does the reflection. Do not call an
external optimizer unless you wire one yourself.

Paths are relative to this file, or override with SKILLOPT_DIR / --root.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
from pathlib import Path


def root_dir(cli_root: str | None = None) -> Path:
    if cli_root:
        return Path(cli_root).expanduser().resolve()
    env = os.environ.get("SKILLOPT_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent


def paths(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "traj": root / "trajectories.jsonl",
        "held": root / "held_out.json",
        "best": root / "best_skill.md",
        "rej": root / "rejected_edits.md",
        "epochs": root / "epochs",
    }


def load_traj(traj: Path) -> list[dict]:
    rows = []
    if not traj.exists():
        return rows
    for line in traj.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def latest_bucket(m: dict) -> dict:
    if not m:
        return {}
    for k in (
        "t_night",
        "t24h",
        "t6h",
        "t1h",
        "t20m",
        "t_plus_~1.5h",
        "t_plus_~1h",
        "t_plus_~20m",
    ):
        if k in m and isinstance(m[k], dict) and "views" in m[k]:
            return m[k]
    for v in m.values():
        if isinstance(v, dict) and "views" in v:
            return v
    return {}


def rescore(row: dict) -> dict:
    metrics = row.get("metrics") or {}
    b = latest_bucket(metrics)
    views = int(b.get("views") or 0)
    eng = int(b.get("likes") or 0) + int(b.get("replies") or 0) + int(b.get("bookmarks") or 0)
    base = math.log1p(views) + 0.75 * math.log1p(eng)
    feat = row.get("features") or {}
    ratio = float(feat.get("viral_ratio") or 0)
    if row.get("type") == "reply" and ratio >= 20:
        base *= 1.35
    elif row.get("type") == "reply" and ratio >= 12:
        base *= 1.15
    if feat.get("viral_signal") == "weak_dead_diary":
        base *= 0.4
    if feat.get("hard_open") is True:
        base *= 1.1
    if feat.get("author_replied") is True:
        base *= 1.5
    if row.get("type") == "reply" and ratio and ratio < 5:
        base *= 0.7
    row["score"] = round(base / 10.0, 4)
    return row


def mean_score(rows: list[dict], ids=None) -> float:
    if ids is not None:
        idset = set(ids)
        rows = [r for r in rows if r.get("id") in idset]
    if not rows:
        return 0.0
    return sum(float(r.get("score") or 0) for r in rows) / len(rows)


def append_traj(traj: Path, obj: dict) -> dict:
    obj = rescore(obj)
    with traj.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return obj


def split_rows(rows: list[dict], cfg: dict) -> tuple[list[dict], list[dict]]:
    train = [r for r in rows if r.get("split") != "val"]
    val = [r for r in rows if r.get("split") == "val"]
    if not val:
        val = [r for r in rows if r.get("id") in set(cfg.get("val_ids") or [])]
    return train, val


def cmd_status(p: dict[str, Path]) -> None:
    cfg = json.loads(p["held"].read_text(encoding="utf-8")) if p["held"].exists() else {}
    rows = [rescore(r) for r in load_traj(p["traj"])]
    if rows:
        p["traj"].write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
            encoding="utf-8",
        )
    train, val = split_rows(rows, cfg)
    print(
        json.dumps(
            {
                "n": len(rows),
                "train_mean": round(mean_score(train), 4),
                "val_mean": round(mean_score(val), 4),
                "min_before_edit": cfg.get("min_trajectories_before_edit", 8),
                "ready_for_edit": len(rows) >= int(cfg.get("min_trajectories_before_edit", 8)),
                "lr": cfg.get("learning_rate_max_edits", 4),
                "top": sorted(
                    [
                        {
                            "id": r.get("id"),
                            "score": r.get("score"),
                            "type": r.get("type"),
                            "notes": r.get("notes"),
                        }
                        for r in rows
                    ],
                    key=lambda x: -float(x["score"] or 0),
                )[:5],
            },
            indent=2,
        )
    )


def cmd_append(p: dict[str, Path], payload: str) -> None:
    obj = json.loads(payload)
    out = append_traj(p["traj"], obj)
    print(json.dumps({"appended": out.get("id"), "score": out.get("score")}, indent=2))


def cmd_gate(p: dict[str, Path], accepted: bool, summary: str, edits: list[str]) -> None:
    p["epochs"].mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = p["epochs"] / f"{stamp}_{'accept' if accepted else 'reject'}.json"
    path.write_text(
        json.dumps(
            {"accepted": accepted, "summary": summary, "edits": edits, "ts": stamp},
            indent=2,
        ),
        encoding="utf-8",
    )
    if not accepted:
        with p["rej"].open("a", encoding="utf-8") as f:
            f.write(f"\n## {stamp}\n{summary}\n")
            for e in edits:
                f.write(f"- {e}\n")
    print(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SkillOpt sleep cycle for X growth")
    parser.add_argument(
        "--root",
        default=None,
        help="SkillOpt directory. Defaults to SKILLOPT_DIR or this file's folder.",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="rescore trajectories and print train/val means")
    sub.add_parser("rescore", help="alias for status")

    ap = sub.add_parser("append", help="append one JSON trajectory from --json or stdin")
    ap.add_argument("--json", default=None, help="trajectory object as a JSON string")

    gp = sub.add_parser("gate", help="book an accepted or rejected epoch")
    gp.add_argument("result", choices=("accept", "reject"))
    gp.add_argument("--summary", required=True)
    gp.add_argument("--edit", action="append", default=[], help="repeatable bounded edit note")

    args = parser.parse_args(argv)
    p = paths(root_dir(args.root))
    cmd = args.cmd or "status"

    if cmd in ("status", "rescore"):
        cmd_status(p)
        return 0
    if cmd == "append":
        payload = args.json if args.json else sys.stdin.read()
        if not payload.strip():
            print("append needs --json or stdin", file=sys.stderr)
            return 2
        cmd_append(p, payload)
        return 0
    if cmd == "gate":
        cmd_gate(p, args.result == "accept", args.summary, args.edit)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
