import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def sc():
    return load_module("grokbotx_sleep_cycle", "skillopt/sleep_cycle.py")


@pytest.fixture(scope="session")
def pub():
    return load_module("grokbotx_publish_original", "scripts/publish_original.py")


@pytest.fixture(scope="session")
def rep():
    return load_module("grokbotx_create_reply_draft", "scripts/create_reply_draft.py")


@pytest.fixture()
def root(tmp_path):
    """A skillopt root dir with no data yet."""
    return tmp_path


def make_row(rid, rtype="reply", views=100, likes=0, replies=0, bookmarks=0,
             ratio=None, split="train", followers=None, bucket="t_night",
             topic=None, text="a plain sentence about ops", **extra):
    row = {
        "id": rid,
        "ts": "2026-08-20T10:12:00Z",
        "type": rtype,
        "url": f"https://x.com/yourhandle/status/{rid}",
        "text": text,
        "features": {},
        "metrics": {bucket: {"views": views, "likes": likes, "replies": replies,
                             "bookmarks": bookmarks}},
        "split": split,
        "notes": "test row",
    }
    feat = row["features"]
    if ratio is not None:
        feat["viral_ratio"] = ratio
    if followers is not None:
        feat["author_followers"] = followers
    if topic is not None:
        feat["topic"] = topic
    row["features"].update(extra.get("features", {}))
    return row


def write_root(root, rows, cfg=None, best_skill=None):
    (root / "trajectories.jsonl").write_text(
        "".join(__import__("json").dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    if cfg is not None:
        import json as j
        (root / "held_out.json").write_text(j.dumps(cfg), encoding="utf-8")
    if best_skill is not None:
        (root / "best_skill.md").write_text(best_skill, encoding="utf-8")
