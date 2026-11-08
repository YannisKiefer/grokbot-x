"""Offline replay eval: which targeting policy picks better held-out rows."""
import json

from conftest import make_row, write_root

NO_POLICY = "prose only\n"
GOLD_ONLY = 'prose\n<!-- skillopt-policy {"min_parent_ratio": 12} -->\n'


def rows():
    out = []
    for i in range(6):
        out.append(make_row(f"vg{i}", views=4000, ratio=20, split="val", text=f"gold {i} ads"))
    for i in range(4):
        out.append(make_row(f"vw{i}", views=200, ratio=2, split="val", text=f"weak {i} ops"))
    for i in range(3):
        out.append(make_row(f"vt{i}", views=9000, ratio=2, split="train", text=f"train {i} pdp"))
    return out


def replay(sc, root, a, b):
    return sc.main(["--root", str(root), "replay", "--skill-a", str(a), "--skill-b", str(b)])


def test_replay_reports_winner(sc, root, capsys):
    write_root(root, rows())
    a, b = root / "a.md", root / "b.md"
    a.write_text(NO_POLICY, encoding="utf-8")
    b.write_text(GOLD_ONLY, encoding="utf-8")
    assert replay(sc, root, a, b) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "b"
    assert out["delta_mean"] > 0
    assert out["n_val_scored"] == 10
    assert (out["n_a"], out["n_b"]) == (10, 6)
    assert "note" in out


def test_replay_identical_skills_tie(sc, root, capsys):
    write_root(root, rows())
    a = root / "a.md"
    a.write_text(NO_POLICY, encoding="utf-8")
    assert replay(sc, root, a, a) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "tie"
    assert out["delta_mean"] == 0.0


def test_replay_uses_only_val_rows(sc, root, capsys):
    write_root(root, rows())
    a, b = root / "a.md", root / "b.md"
    a.write_text(NO_POLICY, encoding="utf-8")
    b.write_text(GOLD_ONLY, encoding="utf-8")
    replay(sc, root, a, b)
    out = json.loads(capsys.readouterr().out)
    assert out["n_val_scored"] == 10  # the 3 strong train rows are not used


def test_replay_without_val_rows_fails_clean(sc, root, capsys):
    write_root(root, [make_row(f"t{i}") for i in range(5)])
    a = root / "a.md"
    a.write_text(NO_POLICY, encoding="utf-8")
    assert replay(sc, root, a, a) == 2
    assert "val" in capsys.readouterr().err


def test_replay_missing_skill_file_clean_error(sc, root, capsys):
    write_root(root, rows())
    assert replay(sc, root, "nope.md", "also.md") == 2
    assert "error:" in capsys.readouterr().err
