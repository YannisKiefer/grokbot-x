#!/usr/bin/env python3
"""X-domain SkillOpt sleep cycle (adapted from microsoft/skillopt).

harvest metrics -> reflect train vs val -> propose <=LR edits -> gate on held-out
-> adopt into best_skill.md or append rejected_edits.md

The reward is verifiable (RLVR-style) and FIXED: every score is computed
only from X counters logged in trajectories.jsonl (views, replies,
bookmarks, likes), normalized by post age and the operator's follower count
(velocity, not raw views), with penalties for near-duplicate posts,
off-niche topics (niche list in held_out.json) and risky parents. No model
judges "quality", and no skill edit can change the reward.

The gate is machine-checked on held-out (val) rows only. An edit is
accepted only if the mean reward improves AND the bootstrap interval of the
improvement is above zero, with minimum row counts. The interval level
rises with every distinct proposal tried since the last accept (95% for
the first), so many tries on the same rows cannot find a lucky winner. Two kinds of
evidence count:

- trial: val rows logged while the proposed skill was live (their
  skill_sha256 matches it) against val rows logged under the current skill;
- replay: the proposed targeting policy, replayed on logged val rows, picks
  rows with a higher fixed reward than the current policy picks.

Every epoch is logged with before/after scores and the interval. `replay`
runs the replay math offline. The operator (or Grok Bot) does the
reflection. This file does the math and the bookkeeping. No network calls.

Each skill file may carry one machine-readable targeting policy comment:

    <!-- skillopt-policy {"min_parent_ratio": 12, "topics": ["ads"]} -->

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

SCORE_VERSION = "v3-fixed-reward-2026-11-08"

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
# Every distinct proposal tried against the val rows since the last accept
# is one more chance to win by luck. Alpha spending: attempt k gets
# 0.10/(k(k+1)) of the error budget, so all attempts together stay <= 0.10
# (attempt 1 needs a 95% interval, attempt 2 a 98.3% one, ...).
FAMILY_ALPHA = 0.10
MIN_VAL_ROWS_FLOOR = 5
MAX_EDITS = 4
# A proposed policy must keep at least this share of the rows the current
# policy takes, so "post only my 2 luckiest topics" cannot win on noise.
MIN_COVERAGE = 0.5

# The skill policy is a TARGETING rule (which posts to make), never a scoring
# rule. The reward is fixed and lives only in this file and held_out.json, so
# an edit cannot win by loosening its own penalties (Goodhart).
DEFAULT_POLICY: dict = {
    "min_parent_ratio": 0.0,      # replies only under parents with viral_ratio >= this
    "skip_dead_diary": False,     # skip rows flagged viral_signal = weak_dead_diary
    "skip_risky_parents": False,  # skip replies under parents flagged parent_risky
    "topics": [],                 # non-empty: only these topics
}
_POLICY_NUM = {"min_parent_ratio"}
_POLICY_BOOL = {"skip_dead_diary", "skip_risky_parents"}


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
        "attempts": root / "epochs" / "attempts.jsonl",
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
    fol = (feat or {}).get("author_followers")
    if fol is not None and (isinstance(fol, bool) or not isinstance(fol, (int, float)) or fol < 0):
        raise DataError(
            f"{where}: features.author_followers must be a number >= 0 (got {fol!r})"
        )


def has_metrics(row: dict) -> bool:
    """True once a metric bucket carries a views count (the measurement the
    scorer reads). Rows without one are pending, not zero - they are
    excluded from means and from the gate."""
    return any(
        isinstance(b, dict) and b.get("views") is not None
        for b in (row.get("metrics") or {}).values()
    )


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
        else:  # topics
            if not isinstance(v, list) or not all(isinstance(t, str) for t in v):
                raise DataError(f"{where}: skillopt-policy 'topics' must be a list of strings")
            policy[k] = [t.strip().lower() for t in v if t.strip()]
    return policy


def selects(row: dict, policy: dict) -> bool:
    """Would a skill with this targeting policy have made this post?"""
    feat = row.get("features") or {}
    is_reply = row.get("type") == "reply"
    if is_reply and policy["min_parent_ratio"] > 0:
        if _num(feat.get("viral_ratio"), 0.0) < policy["min_parent_ratio"]:
            return False
    if policy["skip_dead_diary"] and feat.get("viral_signal") == "weak_dead_diary":
        return False
    if is_reply and policy["skip_risky_parents"] and feat.get("parent_risky") is True:
        return False
    if policy["topics"]:
        if str(feat.get("topic") or "").strip().lower() not in policy["topics"]:
            return False
    return True


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
        if isinstance(b, dict) and b.get("views") is not None:
            return k, b
    for k, b in metrics.items():
        if isinstance(b, dict) and b.get("views") is not None:
            return k, b
    return "", {}


def bucket_age_h(name: str) -> float:
    ages = dict(BUCKETS)
    return ages.get(name, 24.0)


def rescore(row: dict, cfg: dict | None = None, duplicate: bool = False) -> float:
    """Fixed, verifiable reward: X counters only, normalized by post age and
    the operator's follower count (velocity), weighted toward replies and
    bookmarks, with Goodhart guards. Only outcomes count; how the post was
    targeted (parent ratio, dead diary, hard open) is the policy's job and
    is never rewarded directly. Sets row["score"], returns it.

    cfg (held_out.json) may set "author_followers" (default for rows that do
    not log it) and "niche_topics" (the brand's topics; others score x0.5)."""
    cfg = cfg or {}
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
    followers = _num(feat.get("author_followers"), _num(cfg.get("author_followers"), 1.0))
    norm = 1.0 / age_h / max(followers, 1.0)

    # x1000 keeps log1p readable: ~"views per 1000 followers per hour".
    base = math.log1p(1000.0 * views * norm) + 0.75 * math.log1p(1000.0 * eng * norm)

    if feat.get("author_replied") is True:
        base *= 1.5  # an outcome: the parent's author answered us
    if row.get("type") == "reply" and feat.get("parent_risky") is True:
        base *= 0.5  # reach under posts the operator would not want to be seen under
    topics = [str(t).strip().lower() for t in cfg.get("niche_topics") or []]
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
    row (token Jaccard >= DUPLICATE_JACCARD). The later row in the log (the
    log is append-only, so file order is ship order) is the dupe."""
    seen: dict[str, list[frozenset]] = {}
    dups: set[str] = set()
    for r in rows:
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


def _interval(stats: list[float], level: float) -> tuple[float, float]:
    if not stats:
        return 0.0, 0.0
    stats = sorted(stats)
    lo_q = (1.0 - level) / 2.0
    lo = stats[max(0, int(lo_q * (len(stats) - 1)))]
    hi = stats[min(len(stats) - 1, int((1.0 - lo_q) * (len(stats) - 1)))]
    return lo, hi


def _widen(lo: float, hi: float, center: float, n: int) -> tuple[float, float]:
    """Percentile bootstraps are too narrow on few rows (they use the n, not
    n-1, variance). Widen around the point estimate by sqrt(n/(n-1))."""
    f = math.sqrt(n / (n - 1)) if n > 1 else 1.0
    return center - (center - lo) * f, center + (hi - center) * f


def bootstrap_replay_ci(
    scores: list[float],
    take_a: list[bool],
    take_b: list[bool],
    resamples: int = BOOTSTRAP_RESAMPLES,
    level: float = BOOTSTRAP_LEVEL,
    seed: int = 0,
) -> tuple[float, float]:
    """CI of mean(reward | B takes) - mean(reward | A takes). Rows are
    resampled together, so both policies see the same resample."""
    n = len(scores)
    rng = random.Random(seed)
    diffs = []
    for _ in range(resamples):
        sa = sb = 0.0
        na = nb = 0
        for _ in range(n):
            i = rng.randrange(n)
            if take_a[i]:
                sa += scores[i]
                na += 1
            if take_b[i]:
                sb += scores[i]
                nb += 1
        if na and nb:
            diffs.append(sb / nb - sa / na)
    return _interval(diffs, level)


def bootstrap_two_sample_ci(
    a: list[float],
    b: list[float],
    resamples: int = BOOTSTRAP_RESAMPLES,
    level: float = BOOTSTRAP_LEVEL,
    seed: int = 0,
) -> tuple[float, float]:
    """CI of mean(b) - mean(a) for two independent groups of rows."""
    if not a or not b:
        return 0.0, 0.0
    rng = random.Random(seed)
    diffs = []
    for _ in range(resamples):
        mb = sum(b[rng.randrange(len(b))] for _ in b) / len(b)
        ma = sum(a[rng.randrange(len(a))] for _ in a) / len(a)
        diffs.append(mb - ma)
    return _interval(diffs, level)


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
    mv = cfg.get("min_val_rows")
    if mv is not None and mv < MIN_VAL_ROWS_FLOOR:
        raise DataError(
            f"{held.name}: 'min_val_rows' must be >= {MIN_VAL_ROWS_FLOOR}; "
            "an interval over fewer rows is noise"
        )
    topics = cfg.get("niche_topics")
    if topics is not None and (
        not isinstance(topics, list) or not all(isinstance(t, str) for t in topics)
    ):
        raise DataError(f"{held.name}: 'niche_topics' must be a list of strings")
    fol = cfg.get("author_followers")
    if fol is not None and (isinstance(fol, bool) or not isinstance(fol, (int, float)) or fol < 1):
        raise DataError(f"{held.name}: 'author_followers' must be a number >= 1")
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


def _verdict(delta: float, lo: float, hi: float) -> str:
    if delta > 0 and lo > 0:
        return "b"
    if delta < 0 and hi < 0:
        return "a"
    return "tie"


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def record_attempt(p: dict[str, Path], cmd: str, sha_b: str) -> int:
    """Log one try of a proposal against the val rows; return k, the number
    of distinct proposals tried since the last accept (this one included)."""
    shas: set[str] = set()
    if p["attempts"].exists():
        for line in p["attempts"].read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("reset"):
                shas = set()
            elif isinstance(obj.get("sha_b"), str):
                shas.add(obj["sha_b"])
    shas.add(sha_b)
    p["attempts"].parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with p["attempts"].open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": stamp, "cmd": cmd, "sha_b": sha_b}) + "\n")
    return len(shas)


def reset_attempts(p: dict[str, Path], ts: str) -> None:
    p["attempts"].parent.mkdir(parents=True, exist_ok=True)
    with p["attempts"].open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "reset": "accepted"}) + "\n")


def level_for(attempt: int) -> float:
    k = max(attempt, 1)
    return 1.0 - FAMILY_ALPHA / (k * (k + 1))


def score_rows(rows: list[dict], cfg: dict, all_rows: list[dict] | None = None) -> list[float]:
    """Fixed reward for each row; near-duplicates are judged against all rows."""
    dups = duplicate_ids(all_rows if all_rows is not None else rows)
    return [rescore(dict(r), cfg, duplicate=str(r.get("id")) in dups) for r in rows]


def evaluate_replay(
    val: list[dict],
    scores: list[float],
    policy_a: dict,
    policy_b: dict,
    min_rows: int,
    attempt: int = 1,
) -> dict:
    """Off-policy replay on logged val rows: mean fixed reward of the rows
    each targeting policy would have made. B must keep enough rows."""
    take_a = [selects(r, policy_a) for r in val]
    take_b = [selects(r, policy_b) for r in val]
    n_a, n_b = sum(take_a), sum(take_b)
    mean_a = _mean([s for s, t in zip(scores, take_a, strict=True) if t])
    mean_b = _mean([s for s, t in zip(scores, take_b, strict=True) if t])
    out = {
        "method": "replay",
        "n_a": n_a,
        "n_b": n_b,
        "mean_a": round(mean_a, 4),
        "mean_b": round(mean_b, 4),
        "delta_mean": round(mean_b - mean_a, 4),
        "attempt": attempt,
        "ci_level": round(level_for(attempt), 4),
        "ci_low": 0.0,
        "ci_high": 0.0,
        "rule": "accept b iff delta_mean > 0 and ci_low > 0 "
        "(ci_level = 1 - 0.10/(attempt*(attempt+1))), "
        f"and b keeps >= max(min_val_rows, {MIN_COVERAGE:.0%} of a's rows)",
    }
    need = max(min_rows, math.ceil(MIN_COVERAGE * n_a))
    if n_a < min_rows or n_b < need:
        out["verdict"] = "insufficient"
        out["reason"] = (
            f"a takes {n_a} and b takes {n_b} of {len(val)} val rows; "
            f"b needs >= {need} and a >= {min_rows}"
        )
        return out
    if take_a == take_b:
        out["verdict"] = "tie"
        out["reason"] = "both policies take the same rows (prose-only edits replay as a tie)"
        return out
    ids = [str(r.get("id")) for r in val]
    lo, hi = bootstrap_replay_ci(
        scores, take_a, take_b, level=level_for(attempt), seed=seed_for(ids)
    )
    lo, hi = _widen(lo, hi, mean_b - mean_a, n_b)
    out.update(ci_low=round(lo, 4), ci_high=round(hi, 4))
    out["verdict"] = _verdict(mean_b - mean_a, lo, hi)
    return out


def evaluate_trial(
    val: list[dict],
    scores: list[float],
    sha_a: str | None,
    sha_b: str,
    min_rows: int,
    attempt: int = 1,
) -> dict | None:
    """Live trial: val rows logged while the proposed skill was deployed
    (skill_sha256 == sha_b) against val rows logged under the current skill
    in the same window (ts at or after the first trial row), so account
    growth over time cannot pose as a skill effect. None when either side
    has fewer than min_rows scored rows."""
    if not sha_a or sha_a == sha_b:
        return None
    pairs = list(zip(val, scores, strict=True))
    b_rows = [(r, s) for r, s in pairs if r.get("skill_sha256") == sha_b]
    if not b_rows:
        return None
    start = min(str(r.get("ts") or "") for r, _ in b_rows)
    a = [s for r, s in pairs if r.get("skill_sha256") == sha_a and str(r.get("ts") or "") >= start]
    b = [s for _, s in b_rows]
    if len(a) < min_rows or len(b) < min_rows:
        return None
    ids = [str(r.get("id")) for r in val]
    delta = _mean(b) - _mean(a)
    lo, hi = bootstrap_two_sample_ci(a, b, level=level_for(attempt), seed=seed_for(ids))
    lo, hi = _widen(lo, hi, delta, min(len(a), len(b)))
    return {
        "method": "trial",
        "n_a": len(a),
        "n_b": len(b),
        "mean_a": round(_mean(a), 4),
        "mean_b": round(_mean(b), 4),
        "delta_mean": round(delta, 4),
        "attempt": attempt,
        "ci_level": round(level_for(attempt), 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "trial_start": start,
        "verdict": _verdict(delta, lo, hi),
        "rule": "accept b iff delta_mean > 0 and ci_low > 0 (two-sample bootstrap, "
        "ci_level = 1 - 0.10/(attempt*(attempt+1)), a = current-skill rows in the trial window)",
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
        rescore(r, cfg, duplicate=str(r.get("id")) in dups)
    train, val = split_rows(rows, cfg)
    out = _fmt_status(rows, train, val)
    out["min_before_edit"] = cfg.get("min_trajectories_before_edit", 8)
    out["ready_for_edit"] = out["n_scored"] >= int(cfg.get("min_trajectories_before_edit", 8))
    no_fol = sum(
        1 for r in rows if (r.get("features") or {}).get("author_followers") is None
    )
    if no_fol and cfg.get("author_followers") is None:
        out["warning"] = (
            f"{no_fol} rows have no features.author_followers and held_out.json sets no "
            "author_followers default; their velocity is per 1 follower, so they are not "
            "comparable with rows that log it"
        )
    out["lr"] = min(int(cfg.get("learning_rate_max_edits", MAX_EDITS)), MAX_EDITS)
    out["score_version"] = SCORE_VERSION
    if not rows:
        out["hint"] = (
            "no trajectories yet; copy examples/trajectories.example.jsonl to "
            f"{p['traj'].name} for a dry run"
        )
    print(json.dumps(out, indent=2))
    return 0


def cmd_append(p: dict[str, Path], payload: str, skill: str | None = None) -> int:
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
    sha = obj.get("skill_sha256")
    if sha is not None and not isinstance(sha, str):
        raise DataError("append: 'skill_sha256' must be a string")
    if skill:  # a live trial of a proposed skill
        sk = Path(skill).expanduser()
        if not sk.exists():
            raise DataError(f"{sk}: skill file not found")
        obj["skill_sha256"] = sha256_file(sk)
    elif sha is None and p["best"].exists():
        obj["skill_sha256"] = sha256_file(p["best"])  # which skill wrote this post
    dupe = str(obj["id"]) in duplicate_ids(rows + [obj])
    score = rescore(obj, load_config(p), duplicate=dupe)
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
    cfg = load_config(p)
    lr = min(int(cfg.get("learning_rate_max_edits", MAX_EDITS)), MAX_EDITS)
    if len(edits) > lr:
        raise DataError(
            f"gate: {len(edits)} edits given; the learning rate is at most {lr} per epoch"
        )
    rows = load_traj(p["traj"])
    for i, r in enumerate(rows, 1):
        validate_row(r, f"{p['traj'].name} line {i}")

    min_rows = int(cfg.get("min_trajectories_before_edit", 8))
    n_scored = sum(1 for r in rows if has_metrics(r))
    if n_scored < min_rows:
        print(
            json.dumps(
                {
                    "error": "too few rows to gate an edit",
                    "n_rows": n_scored,
                    "min_rows": min_rows,
                    "advice": "log more ships first; the gate refuses to learn from a tiny sample",
                },
                indent=2,
            )
        )
        return 3
    _, val = split_rows(rows, cfg)
    scored_val = [r for r in val if has_metrics(r)]
    min_val = int(cfg.get("min_val_rows", MIN_VAL_ROWS_FLOOR))
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
        sha_a = sha256_file(p["best"]) if p["best"].exists() else None
        sha_b = sha256_file(proposed)
        # held-out rows only; the operator reflected on train rows
        scores = score_rows(scored_val, cfg, all_rows=rows)
        attempt = record_attempt(p, "gate", sha_b)
        ev = evaluate_trial(
            scored_val, scores, sha_a, sha_b, min_val, attempt
        ) or evaluate_replay(scored_val, scores, policy_a, policy_b, min_val, attempt)
        accepted = ev["verdict"] == "b"
        receipt.update(
            {
                "decision_basis": "computed",
                "method": ev["method"],
                "skill_before": str(p["best"]),
                "skill_before_sha256": sha_a,
                "skill_after": str(proposed.resolve()),
                "skill_after_sha256": sha_b,
                "n_a": ev["n_a"],
                "n_b": ev["n_b"],
                "val_mean_before": ev["mean_a"],
                "val_mean_after": ev["mean_b"],
                "delta_mean": ev["delta_mean"],
                "attempt": ev["attempt"],
                "ci_level": ev["ci_level"],
                "ci_low": ev["ci_low"],
                "ci_high": ev["ci_high"],
                "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
                "verdict": ev["verdict"],
                "rule": ev["rule"],
            }
        )
        for k in ("reason", "trial_start"):
            if k in ev:
                receipt[k] = ev[k]
        if accepted:
            if p["best"].exists():  # keep the replaced skill so an accept can be rolled back
                p["epochs"].mkdir(parents=True, exist_ok=True)
                prev = p["epochs"] / f"{receipt['ts']}_best_before.md"
                n = 1
                while prev.exists():
                    prev = p["epochs"] / f"{receipt['ts']}-{n}_best_before.md"
                    n += 1
                prev.write_text(best_text, encoding="utf-8")
                receipt["skill_before_copy"] = str(prev)
            tmp = p["best"].with_suffix(".md.tmp")
            tmp.write_text(prop_text, encoding="utf-8")
            os.replace(tmp, p["best"])
            reset_attempts(p, receipt["ts"])
    else:
        receipt["decision_basis"] = "manual"

    p["epochs"].mkdir(parents=True, exist_ok=True)
    path = _unique_path(p, receipt["ts"], accepted)
    receipt["accepted"] = accepted
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if not accepted:
        verdict = receipt.get("verdict")
        status = {
            "a": "proven worse, do not retry",
            "tie": "not proven either way; retry only as a live trial",
            "insufficient": "not tested (too few rows); retry when there is data",
        }.get(verdict, "rejected by hand")
        with p["rej"].open("a", encoding="utf-8") as f:
            f.write(f"\n## {receipt['ts']} ({status})\n{summary}\n")
            if receipt.get("reason"):
                f.write(f"reason: {receipt['reason']}\n")
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
                "ci": [receipt.get("ci_low"), receipt.get("ci_high")],
                "ci_level": receipt.get("ci_level"),
                "attempt": receipt.get("attempt"),
                "method": receipt.get("method"),
                "verdict": receipt.get("verdict"),
                "reason": receipt.get("reason"),
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
    scores = score_rows(scored_val, cfg, all_rows=rows)
    # a replay is a look at the val rows too: it counts as an attempt
    attempt = record_attempt(p, "replay", sha256_file(Path(skill_b).expanduser()))
    ev = evaluate_replay(
        scored_val, scores, pa, pb, int(cfg.get("min_val_rows", MIN_VAL_ROWS_FLOOR)), attempt
    )
    out = {
        "skill_a": str(Path(skill_a)),
        "skill_b": str(Path(skill_b)),
        "score_version": SCORE_VERSION,
        "n_val_scored": len(scored_val),
        **ev,
        "note": "replays each skill's targeting policy on held-out rows against a fixed "
        "reward; prose-only edits replay as a tie (prove those with a live trial). "
        "Each distinct skill_b tried since the last accept raises the bar (attempt).",
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
    ap.add_argument(
        "--skill", default=None, help="skill file that wrote this post (live trial of a proposal)"
    )

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
            return cmd_append(p, payload, args.skill)
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
