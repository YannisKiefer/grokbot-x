"""Offline replay eval: which skill policy wins on held-out rows."""
import json

from conftest import make_row, write_root

POLICY_NICHE_OPS = 'prose\n<!-- skillopt-policy {"niche_topics": ["ops"]} -->\n'
NO_POLICY = "prose only\n"


def rows():
    out = []
    for i in range(3):
        out.append(make_row(f"vc{i}", views=5000, split="val", topic="celebrity",
                            text=f"off-niche observation {i} about a viral celebrity post"))
    for i in range(3):
        out.append(make_row(f"vt{i}", views=3000, split="train", topic="ops",
                            text=f"train row {i} about checkout flows"))
    return out


def test_replay_reports_winner(sc, root, capsys):
    write_root(root, rows())
    a = root / "a.md"
    b = root / "b.md"
    a.write_text(POLICY_NICHE_OPS, encoding="utf-8")  # penalizes the val rows as off-niche
    b.write_text(NO_POLICY, encoding="utf-8")
    rc = sc.main(["--root", str(root), "replay", "--skill-a", str(a), "--skill-b", str(b)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "b"
    assert out["delta_mean"] > 0
    assert out["n_val_scored"] == 3
    assert "note" in out


def test_replay_identical_skills_tie(sc, root, capsys):
    write_root(root, rows())
    a = root / "a.md"
    a.write_text(NO_POLICY, encoding="utf-8")
    rc = sc.main(["--root", str(root), "replay", "--skill-a", str(a), "--skill-b", str(a)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "tie"
    assert out["delta_mean"] == 0.0


def test_replay_uses_only_val_rows(sc, root, capsys):
    write_root(root, rows())
    a = root / "a.md"
    b = root / "b.md"
    a.write_text(NO_POLICY, encoding="utf-8")
    b.write_text(POLICY_NICHE_OPS, encoding="utf-8")
    sc.main(["--root", str(root), "replay", "--skill-a", str(a), "--skill-b", str(b)])
    out = json.loads(capsys.readouterr().out)
    assert out["n_val_scored"] == 3


def test_replay_without_val_rows_fails_clean(sc, root, capsys):
    train_only = [make_row(f"t{i}") for i in range(5)]
    write_root(root, train_only)
    a = root / "a.md"
    a.write_text(NO_POLICY, encoding="utf-8")
    rc = sc.main(["--root", str(root), "replay", "--skill-a", str(a), "--skill-b", str(a)])
    assert rc == 2
    assert "val" in capsys.readouterr().err


def test_replay_missing_skill_file_clean_error(sc, root, capsys):
    write_root(root, rows())
    rc = sc.main(["--root", str(root), "replay", "--skill-a", "nope.md", "--skill-b", "also.md"])
    assert rc == 2
    assert "error:" in capsys.readouterr().err
