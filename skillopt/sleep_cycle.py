#!/usr/bin/env python3
"""X-domain SkillOpt sleep cycle (adapted from microsoft/skillopt).

harvest metrics -> reflect train vs val -> propose <=LR edits -> gate on held-out
-> adopt into best_skill.md or append rejected_edits.md

The reward is verifiable (RLVR-style): every score is computed only from X
counters logged in trajectories.jsonl (views, replies, bookmarks, likes),
normalized by post age and the operator's follower count (velocity, not raw
views), with penalties for near-duplicate posts, off-niche topics, and
risky parents. No model judges "quality".

The gate is machine-checked: an edit is accepted only if the held-out mean
improves AND the bootstrap 90% interval of the improvement is above zero,
with a minimum row count. Every epoch is logged with before/after scores
and the interval. `replay` runs the same math on two skill files offline,
so improvements are proven before they go live.

The operator (or Grok Bot) does the reflection. This file does the math and
the bookkeeping. No network calls.

Each skill file may carry one machine-readable policy comment; it is the
only part of a skill the scorer can see:

    <!-- skillopt-policy {"reply_bonus_ratio": 12, "niche_topics": ["ads"]} -->

Paths are relative to this file, or override with SKILLOPT_DIR / --root
(--root works before or after the subcommand).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import random
import re
import sys
from pathlib import Path

SCORE_VERSION = "v2-velocity-2026-11-08"

# (bucket name, hours since ship). First match wins, so this list is ordered
# newest-first: the most recent measurement of a post is its live state.
BUCKETS: list[tuple[str, float]] = [
    ("t_night", 24.0),
    ("t24h", 24.0),
    ("t6h", 6.0),
    ("t_plus_~1.5h", 1.5),
    ("t1h", 1.0),
    ("t_plus_~1h", 1.0),
    ("t20m", 1.0 / 3.0),
    ("t_plus_~20m", 1.0 / 3.0),
]
MIN_AGE_H = 1.0 / 3.0

# X weights replies/quotes/profile clicks far above likes, and bookmarks are
# the hardest counter to bait (see docs/analysis/RESEARCH.md). Bookmarks get
# the highest weight, likes the lowest.
W_LIKE, W_REPLY, W_BOOKMARK = 0.5, 1.5, 2.0

DUPLICATE_JACCARD = 0.8
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_LEVEL = 0.90
MAX_EDITS = 4

DEFAULT_POLICY: dict = {
    "reply_bonus_ratio": 12.0,        # reply on parent >= this ratio: bonus
    "reply_bonus_strong_ratio": 20.0, # reply on parent >= this ratio: bigger bonus
    "low_ratio_penalty_below": 5.0,   # reply on parent < this ratio: penalty (0 = off)
    "dead_diary_multiplier": 0.4,     # dead-diary posts
    "niche_topics": [],               # non-empty: off-niche topic penalty
    "penalize_risky_parents": True,   # replies under flagged risky parents
}
_POLICY_NUM = {
    "reply_bonus_ratio": float,
    "reply_bonus_strong_ratio": float,
    "low_ratio_penalty_below": float,
    "dead_diary_multiplier": float,
}
_POLICY_BOOL = {"penalize_risky_parents"}


class DataError(Exception):
    """A clear, user-facing input error. Printed, never a traceback."""


# ---------------------------------------------------------------- paths


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


# ---------------------------------------------------------------- loading


def load_traj(traj: Path) -> list[dict]:
    rows = []
    if not traj.exists():
        return rows
    for i, line in enumerate(traj.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise DataError(
                f"{traj.name} line {i}: not valid JSON ({e.msg}). Fix or remove that line."
            ) from None
        if not isinstance(obj, dict):
            raise DataError(f"{traj.name} line {i}: expected a JSON object")
        rows.append(obj)
    return rows


def validate_row(row: dict, where: str) -> None:
    rid = row.get("id")
    if not isinstance(rid, str) or not rid.strip():
        raise DataError(f"{where}: every row needs a non-empty string 'id'")
    where = f"{where} [{rid}]"
    if row.get("type") not in ("original", "reply"):
        raise DataError(f"{where}: 'type' must be \"original\" or \"reply\"")
    m = row.get("metrics")
    if m is not None and not isinstance(m, dict):
        raise DataError(f"{where}: 'metrics' must be an object of metric buckets")
    if isinstance(m, dict):
        for k, b in m.items():
            if not isinstance(b, dict):
                raise DataError(f"{where}: metrics.{k} must be an object")
            for f in ("views", "likes", "replies", "bookmarks"):
                v = b.get(f)
                if v is None:
                    continue
                if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
                    raise DataError(
                        f"{where}: metrics.{k}.{f} must be a number >= 0 (got {v!r})"
                    )
    feat = row.get("features")
    if feat is not None and not isinstance(feat, dict):
        raise DataError(f"{where}: 'features' must be an object")
    vr = (feat or {}).get("viral_ratio")
    if vr is not None and (isinstance(vr, bool) or not isinstance(vr, (int, float)) or vr < 0):
        raise DataError(f"{where}: features.viral_ratio must be a number >= 0 (got {vr!r})")


def has_metrics(row: dict) -> bool:
    """True once any metric bucket carries a measurement. Rows without
    metrics are pending, not zero - they are excluded from means."""
    for b in (row.get("metrics") or {}).values():
        if isinstance(b, dict) and any(
            b.get(f) is not None for f in ("views", "likes", "replies", "bookmarks")
        ):
            return True
    return False


# ---------------------------------------------------------------- policy


_POLICY_RE = re.compile(r"<!--\s*skillopt-policy\s*(\{.*?\})\s*-->", re.DOTALL)


def parse_policy(text: str, where: str) -> dict:
    policy = dict(DEFAULT_POLICY)
    m = _POLICY_RE.search(text)
    if not m:
        return policy
    try:
        obj = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise DataError(
            f"{where}: the skillopt-policy comment is not valid JSON ({e.msg})"
        ) from None
    if not isinstance(obj, dict):
        raise DataError(f"{where}: skillopt-policy must be a JSON object")
    for k, v in obj.items():
        if k not in DEFAULT_POLICY:
            raise DataError(
                f"{where}: unknown skillopt-policy key '{k}' "
                f"(known keys: {', '.join(sorted(DEFAULT_POLICY))})"
            )
        if k in _POLICY_NUM:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
                raise DataError(f"{where}: skillopt-policy '{k}' must be a number >= 0")
            policy[k] = float(v)
        elif k in _POLICY_BOOL:
            if not isinstance(v, bool):
                raise DataError(f"{where}: skillopt-policy '{k}' must be true or false")
            policy[k] = v
        else:  # niche_topics
            if not isinstance(v, list) or not all(isinstance(t, str) for t in v):
                raise DataError(
                    f"{where}: skillopt-policy 'niche_topics' must be a list of strings"
                )
            policy[k] = [t for t in v if t.strip()]
    return policy


def parse_policy_file(path: Path) -> dict:
    if not path.exists():
        raise DataError(f"{path}: file not found")
    return parse_policy(path.read_text(encoding="utf-8"), path.name)


# ---------------------------------------------------------------- scoring


def _num(v, default: float) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return default
    return float(v)


def latest_bucket(metrics: dict) -> tuple[str, dict]:
    """Newest measurement of a post: first matching bucket wins (BUCKETS is
    ordered newest-first); unknown bucket names fall back to file order."""
    for k, _age in BUCKETS:
        b = metrics.get(k)
        if isinstance(b, dict) and "views" in b:
            return k, b
    for k, b in metrics.items():
        if isinstance(b, dict) and "views" in b:
            return k, b
    return "", {}


def bucket_age_h(name: str) -> float:
    ages = dict(BUCKETS)
    return ages.get(name, 24.0)


def rescore(row: dict, policy: dict | None = None, duplicate: bool = False) -> float:
    """Verifiable reward: X counters only, normalized by post age and the
    operator's follower count (velocity), weighted toward replies and
    bookmarks, with Goodhart guards. Sets row["score"], returns it."""
    policy = policy or dict(DEFAULT_POLICY)
    metrics = row.get("metrics") or {}
    name, b = latest_bucket(metrics)
    views = _num(b.get("views"), 0.0)
    eng = (
        W_LIKE * _num(b.get("likes"), 0.0)
        + W_REPLY * _num(b.get("replies"), 0.0)
        + W_BOOKMARK * _num(b.get("bookmarks"), 0.0)
    )
    age_h = max(bucket_age_h(name) if name else 24.0, MIN_AGE_H)
    feat = row.get("features") or {}
    followers = max(_num(feat.get("author_followers"), 1.0), 1.0)
    norm = 1.0 / age_h / followers

    # x1000 keeps log1p readable: ~"views per 1000 followers per hour".
    base = math.log1p(1000.0 * views * norm) + 0.75 * math.log1p(1000.0 * eng * norm)

    ratio = _num(feat.get("viral_ratio"), 0.0)
    if row.get("type") == "reply":
        if ratio >= policy["reply_bonus_strong_ratio"]:
            base *= 1.35
        elif ratio >= policy["reply_bonus_ratio"]:
            base *= 1.15
        elif policy["low_ratio_penalty_below"] and ratio < policy["low_ratio_penalty_below"]:
            base *= 0.7
    if feat.get("viral_signal") == "weak_dead_diary":
        base *= policy["dead_diary_multiplier"]
    if feat.get("hard_open") is True:
        base *= 1.1
    if feat.get("author_replied") is True:
        base *= 1.5
    if (
        row.get("type") == "reply"
        and policy["penalize_risky_parents"]
        and feat.get("parent_risky") is True
    ):
        base *= 0.5
    topics = [t.lower() for t in policy["niche_topics"]]
    if topics:
        topic = str(feat.get("topic") or "").strip().lower()
        if topic and topic not in topics:
            base *= 0.5  # off-niche virality is not the goal
    if duplicate:
        base *= 0.5  # duplicative posts are also against X rules

    row["score"] = round(base / 10.0, 4)
    return row["score"]


def _text_tokens(text: str) -> frozenset:
    return frozenset(re.findall(r"[a-z0-9']+", text.lower()))


def duplicate_ids(rows: list[dict]) -> set[str]:
    """Ids of rows whose text is a near-duplicate of an earlier same-type
    row (token Jaccard >= DUPLICATE_JACCARD). The later row is the dupe."""
    seen: dict[str, list[frozenset]] = {}
    dups: set[str] = set()
    for r in sorted(rows, key=lambda r: str(r.get("ts") or "")):
        rtype = str(r.get("type") or "")
        tokens = _text_tokens(str(r.get("text") or ""))
        if not tokens:
            continue
        for prev in seen.get(rtype, []):
            union = len(tokens | prev)
            if union and len(tokens & prev) / union >= DUPLICATE_JACCARD:
                dups.add(str(r.get("id")))
                break
        seen.setdefault(rtype, []).append(tokens)
    return dups


# ---------------------------------------------------------------- stats


def bootstrap_ci(
    deltas: list[float],
    resamples: int = BOOTSTRAP_RESAMPLES,
    level: float = BOOTSTRAP_LEVEL,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean delta (stdlib only; see
    docs/analysis/RESEARCH.md for why percentile, not BCa)."""
    n = len(deltas)
    if n == 0:
        return 0.0, 0.0
    rng = random.Random(seed)
    means = []
    for _ in range(resamples):
        total = 0.0
        for _ in range(n):
            total += deltas[rng.randrange(n)]
        means.append(total / n)
    means.sort()
    lo_q = (1.0 - level) / 2.0
    lo = means[max(0, int(lo_q * (len(means) - 1)))]
    hi = means[min(len(means) - 1, int((1.0 - lo_q) * (len(means) - 1)))]
    return lo, hi


def seed_for(ids: list[str]) -> int:
    digest = hashlib.sha256(",".join(sorted(ids)).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- eval


def load_config(p: dict[str, Path]) -> dict:
    held = p["held"]
    if not held.exists():
        return {}
    try:
        cfg = json.loads(held.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DataError(f"{held.name}: not valid JSON ({e.msg})") from None
    if not isinstance(cfg, dict):
        raise DataError(f"{held.name}: expected a JSON object")
    ids = cfg.get("val_ids")
    if ids is not None and (not isinstance(ids, list) or not all(isinstance(x, str) for x in ids)):
        raise DataError(f"{held.name}: 'val_ids' must be a list of row ids (strings)")
    for k in ("min_trajectories_before_edit", "min_val_rows", "learning_rate_max_edits"):
        v = cfg.get(k)
        if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < 1):
            raise DataError(f"{held.name}: '{k}' must be a positive integer")
    return cfg


def split_rows(rows: list[dict], cfg: dict) -> tuple[list[dict], list[dict]]:
    val_ids = set(cfg.get("val_ids") or [])
    train = [r for r in rows if r.get("split") != "val" and str(r.get("id")) not in val_ids]
    val = [r for r in rows if r.get("split") == "val" or str(r.get("id")) in val_ids]
    return train, val


def mean_score(rows: list[dict], ids=None) -> float:
    if ids is not None:
        idset = set(ids)
        rows = [r for r in rows if r.get("id") in idset]
    rows = [r for r in rows if has_metrics(r)]
    if not rows:
        return 0.0
    return sum(float(r.get("score") or 0) for r in rows) / len(rows)


def evaluate_policies(rows: list[dict], policy_a: dict, policy_b: dict) -> dict:
    """Score every scored row under both policies; paired per-row deltas on
    the rows that have metrics. Returns means, delta, bootstrap CI, verdict."""
    dups = duplicate_ids(rows)
    pairs = []  # (id, type, score_a, score_b)
    for r in rows:
        if not has_metrics(r):
            continue
        ra, rb = dict(r), dict(r)
        dupe = str(r.get("id")) in dups
        sa = rescore(ra, policy_a, duplicate=dupe)
        sb = rescore(rb, policy_b, duplicate=dupe)
        pairs.append((str(r.get("id")), r.get("type"), sa, sb))

    by_type: dict[str, list[float]] = {}
    deltas = []
    for _rid, rtype, sa, sb in pairs:
        deltas.append(sb - sa)
        by_type.setdefault(str(rtype), []).append(sb - sa)

    mean_a = sum(p[2] for p in pairs) / len(pairs) if pairs else 0.0
    mean_b = sum(p[3] for p in pairs) / len(pairs) if pairs else 0.0
    delta = mean_b - mean_a
    lo, hi = bootstrap_ci(deltas, seed=seed_for([p[0] for p in pairs]))
    if delta > 0 and lo > 0:
        verdict = "b"
    elif delta < 0 and hi < 0:
        verdict = "a"
    else:
        verdict = "tie"
    per_type = {
        t: {"n": len(v), "delta_mean": round(sum(v) / len(v), 4)}
        for t, v in sorted(by_type.items())
    }
    return {
        "n_scored": len(pairs),
        "mean_a": round(mean_a, 4),
        "mean_b": round(mean_b, 4),
        "delta_mean": round(delta, 4),
        "ci90_low": round(lo, 4),
        "ci90_high": round(hi, 4),
        "verdict": verdict,
        "per_type": per_type,
        "rule": "accept b iff delta_mean > 0 and ci90_low > 0",
    }


# ---------------------------------------------------------------- commands


def _fmt_status(rows: list[dict], train: list[dict], val: list[dict]) -> dict:
    scored = [r for r in rows if has_metrics(r)]
    top = sorted(
        (
            {
                "id": r.get("id"),
                "score": r.get("score"),
                "type": r.get("type"),
                "notes": r.get("notes"),
            }
            for r in scored
        ),
        key=lambda x: -float(x["score"] or 0),
    )[:5]
    return {
        "n": len(rows),
        "n_scored": len(scored),
        "n_pending": len(rows) - len(scored),
        "train_mean": round(mean_score(train), 4),
        "val_mean": round(mean_score(val), 4),
        "reply_mean": round(mean_score([r for r in scored if r.get("type") == "reply"]), 4),
        "original_mean": round(mean_score([r for r in scored if r.get("type") == "original"]), 4),
        "top": top,
    }


def cmd_status(p: dict[str, Path]) -> int:
    cfg = load_config(p)
    rows = load_traj(p["traj"])
    for i, r in enumerate(rows, 1):
        validate_row(r, f"{p['traj'].name} line {i}")
    dups = duplicate_ids(rows)
    for r in rows:
        rescore(r, duplicate=str(r.get("id")) in dups)
    train, val = split_rows(rows, cfg)
    out = _fmt_status(rows, train, val)
    out["min_before_edit"] = cfg.get("min_trajectories_before_edit", 8)
    out["ready_for_edit"] = len(rows) >= int(cfg.get("min_trajectories_before_edit", 8))
    out["lr"] = cfg.get("learning_rate_max_edits", MAX_EDITS)
    out["score_version"] = SCORE_VERSION
    if not rows:
        out["hint"] = (
            "no trajectories yet; copy examples/trajectories.example.jsonl to "
            f"{p['traj'].name} for a dry run"
        )
    print(json.dumps(out, indent=2))
    return 0


def cmd_append(p: dict[str, Path], payload: str) -> int:
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError as e:
        raise DataError(f"append: payload is not valid JSON ({e.msg})") from None
    if not isinstance(obj, dict):
        raise DataError("append: payload must be a JSON object")
    validate_row(obj, "append payload")
    rows = load_traj(p["traj"])
    for i, r in enumerate(rows, 1):
        validate_row(r, f"{p['traj'].name} line {i}")
    if any(str(r.get("id")) == obj["id"] for r in rows):
        raise DataError(f"append: id '{obj['id']}' already exists in {p['traj'].name}")
    policy = (
        parse_policy(p["best"].read_text(encoding="utf-8"), p["best"].name)
        if p["best"].exists()
        else dict(DEFAULT_POLICY)
    )
    dupe = str(obj["id"]) in duplicate_ids(rows + [obj])
    score = rescore(obj, policy, duplicate=dupe)
    obj["score_version"] = SCORE_VERSION
    with p["traj"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(json.dumps({"appended": obj.get("id"), "score": score}, indent=2))
    return 0


def _unique_path(p: dict[str, Path], stamp: str, accepted: bool) -> Path:
    base = p["epochs"] / f"{stamp}_{'accept' if accepted else 'reject'}"
    path = base.with_suffix(".json")
    n = 1
    while path.exists():
        path = p["epochs"] / f"{stamp}-{n}_{'accept' if accepted else 'reject'}.json"
        n += 1
    return path


def cmd_gate(
    p: dict[str, Path], result: str, summary: str, edits: list[str], skill: str | None
) -> int:
    if len(edits) > MAX_EDITS:
        raise DataError(
            f"gate: {len(edits)} edits given; the learning rate is at most {MAX_EDITS} per epoch"
        )
    cfg = load_config(p)
    rows = load_traj(p["traj"])
    for i, r in enumerate(rows, 1):
        validate_row(r, f"{p['traj'].name} line {i}")

    min_rows = int(cfg.get("min_trajectories_before_edit", 8))
    if len(rows) < min_rows:
        print(
            json.dumps(
                {
                    "error": "too few rows to gate an edit",
                    "n_rows": len(rows),
                    "min_rows": min_rows,
                    "advice": "log more ships first; the gate refuses to learn from a tiny sample",
                },
                indent=2,
            )
        )
        return 3
    _, val = split_rows(rows, cfg)
    scored_val = [r for r in val if has_metrics(r)]
    min_val = int(cfg.get("min_val_rows", 5))
    if not scored_val:
        print(
            json.dumps(
                {
                    "error": "no scored val rows",
                    "advice": 'mark ~20% of rows "split": "val" (or list ids in held_out.json) '
                    "and fill their metrics",
                },
                indent=2,
            )
        )
        return 3
    if len(scored_val) < min_val:
        print(
            json.dumps(
                {
                    "error": "too few scored val rows for a bootstrap gate",
                    "n_val_scored": len(scored_val),
                    "min_val_rows": min_val,
                    "advice": "score more val rows first; a CI over fewer rows is noise",
                },
                indent=2,
            )
        )
        return 3

    receipt = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "accepted": False,
        "summary": summary,
        "edits": edits,
        "score_version": SCORE_VERSION,
        "n_rows": len(rows),
        "n_val_scored": len(scored_val),
        "min_val_rows": min_val,
    }
    accepted = False

    if result == "accept":
        if not skill:
            print(
                json.dumps(
                    {
                        "error": "accept requires --skill PROPOSED",
                        "advice": "the gate computes the decision from data; it no longer "
                        "accepts on the operator's word. Put the proposed skill in a file "
                        "(copy best_skill.md, edit it) and pass its path.",
                    },
                    indent=2,
                )
            )
            return 2
        proposed = Path(skill).expanduser()
        if not proposed.exists():
            raise DataError(f"{proposed}: proposed skill file not found")
        best_text = p["best"].read_text(encoding="utf-8") if p["best"].exists() else ""
        prop_text = proposed.read_text(encoding="utf-8")
        policy_a = parse_policy(best_text, p["best"].name)
        policy_b = parse_policy(prop_text, proposed.name)
        ev = evaluate_policies(rows, policy_a, policy_b)
        accepted = ev["verdict"] == "b"
        receipt.update(
            {
                "decision_basis": "computed",
                "skill_before": str(p["best"]),
                "skill_before_sha256": sha256_file(p["best"]) if p["best"].exists() else None,
                "skill_after": str(proposed.resolve()),
                "skill_after_sha256": sha256_file(proposed),
                "val_mean_before": ev["mean_a"],
                "val_mean_after": ev["mean_b"],
                "delta_mean": ev["delta_mean"],
                "ci90_low": ev["ci90_low"],
                "ci90_high": ev["ci90_high"],
                "per_type": ev["per_type"],
                "rule": ev["rule"],
            }
        )
        if accepted:
            tmp = p["best"].with_suffix(".md.tmp")
            tmp.write_text(prop_text, encoding="utf-8")
            os.replace(tmp, p["best"])
    else:
        receipt["decision_basis"] = "manual"

    p["epochs"].mkdir(parents=True, exist_ok=True)
    path = _unique_path(p, receipt["ts"], accepted)
    receipt["accepted"] = accepted
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if not accepted:
        with p["rej"].open("a", encoding="utf-8") as f:
            f.write(f"\n## {receipt['ts']}\n{summary}\n")
            for e in edits:
                f.write(f"- {e}\n")
    print(
        json.dumps(
            {
                "receipt": str(path),
                "accepted": accepted,
                "val_mean_before": receipt.get("val_mean_before"),
                "val_mean_after": receipt.get("val_mean_after"),
                "delta_mean": receipt.get("delta_mean"),
                "ci90": [receipt.get("ci90_low"), receipt.get("ci90_high")],
                "skill_updated": accepted,
            },
            indent=2,
        )
    )
    return 0


def cmd_replay(p: dict[str, Path], skill_a: str, skill_b: str) -> int:
    rows = load_traj(p["traj"])
    for i, r in enumerate(rows, 1):
        validate_row(r, f"{p['traj'].name} line {i}")
    cfg = load_config(p)
    _, val = split_rows(rows, cfg)
    scored_val = [r for r in val if has_metrics(r)]
    if not scored_val:
        raise DataError(
            "replay: no scored val rows in trajectories.jsonl; mark rows "
            '"split": "val" and fill their metrics first'
        )
    pa = parse_policy_file(Path(skill_a).expanduser())
    pb = parse_policy_file(Path(skill_b).expanduser())
    ev = evaluate_policies(scored_val, pa, pb)
    out = {
        "skill_a": str(Path(skill_a)),
        "skill_b": str(Path(skill_b)),
        "score_version": SCORE_VERSION,
        "n_val_scored": len(scored_val),
        **ev,
        "note": "replays the skillopt-policy block of each skill on held-out rows; "
        "prose-only edits replay as a tie",
    }
    print(json.dumps(out, indent=2))
    return 0


# ---------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS, help="SkillOpt directory")
    parser = argparse.ArgumentParser(
        description="SkillOpt sleep cycle for X growth", parents=[common]
    )
    sub = parser.add_subparsers(dest="cmd")

    def add(name: str, help_: str) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=help_, parents=[common])
        return sp

    add("status", "rescore trajectories and print train/val means")
    add("rescore", "alias for status")

    ap = add("append", "append one JSON trajectory from --json or stdin")
    ap.add_argument("--json", default=None, help="trajectory object as a JSON string")

    gp = add("gate", "book an epoch; 'accept' is computed from data, 'reject' is manual")
    gp.add_argument("result", choices=("accept", "reject"))
    gp.add_argument("--summary", required=True)
    gp.add_argument(
        "--edit", action="append", default=[], help="repeatable bounded edit note (max 4)"
    )
    gp.add_argument("--skill", default=None, help="proposed best_skill file (required for accept)")

    rp = add("replay", "offline eval: which skill policy wins on held-out rows?")
    rp.add_argument("--skill-a", required=True)
    rp.add_argument("--skill-b", required=True)

    args = parser.parse_args(argv)
    p = paths(root_dir(getattr(args, "root", None)))
    cmd = args.cmd or "status"

    try:
        if cmd in ("status", "rescore"):
            return cmd_status(p)
        if cmd == "append":
            payload = args.json if args.json else sys.stdin.read()
            if not payload.strip():
                raise DataError("append needs --json or stdin")
            return cmd_append(p, payload)
        if cmd == "gate":
            return cmd_gate(p, args.result, args.summary, args.edit, args.skill)
        if cmd == "replay":
            return cmd_replay(p, args.skill_a, args.skill_b)
    except DataError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
