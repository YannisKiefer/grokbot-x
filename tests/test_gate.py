"""The acceptance gate: min rows, bootstrap CI, receipts, skill adoption."""
import json

from conftest import make_row, write_root

POLICY_NICHE_OPS = 'prose\n<!-- skillopt-policy {"niche_topics": ["ops"]} -->\n'
POLICY_NICHE_X = 'prose\n<!-- skillopt-policy {"niche_topics": ["x"]} -->\n'
POLICY_NICHE_Y = 'prose\n<!-- skillopt-policy {"niche_topics": ["y"]} -->\n'
NO_POLICY = "prose only\n"


def val_rows():
    """8 scored val rows. Topic y rows score clearly above topic x rows."""
    rows = []
    for i in range(4):
        rows.append(make_row(f"vy{i}", views=5000, split="val", topic="y",
                             text=f"topic y observation number {i} about ads"))
    for i in range(4):
        rows.append(make_row(f"vx{i}", views=1000, split="val", topic="x",
                             text=f"topic x observation number {i} about checkout"))
    return rows


def receipts(root):
    return sorted((root / "epochs").glob("*.json"))


def test_gate_accept_requires_skill(sc, root, capsys):
    write_root(root, val_rows())
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "s"])
    assert rc == 2
    out = json.loads(capsys.readouterr().out)
    assert "--skill" in out["error"]


def test_gate_accept_only_on_strict_improvement(sc, root):
    # A penalizes every val row as off-niche; B (no niche list) does not -> B wins
    write_root(root, val_rows(), best_skill=POLICY_NICHE_OPS)
    proposed = root / "proposed.md"
    proposed.write_text(NO_POLICY, encoding="utf-8")
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "drop off-niche penalty",
                  "--skill", str(proposed), "--edit", "DO: keep scoring ops rows"])
    assert rc == 0
    assert (root / "best_skill.md").read_text(encoding="utf-8") == NO_POLICY


def test_gate_rejects_when_mean_falls(sc, root):
    # A (no policy) vs B (penalizes every val row as off-niche) -> B is worse
    write_root(root, val_rows(), best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(POLICY_NICHE_OPS, encoding="utf-8")
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "penalize everything",
                  "--skill", str(proposed)])
    assert rc == 0
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is False
    assert rec["delta_mean"] < 0
    assert (root / "best_skill.md").read_text(encoding="utf-8") == NO_POLICY


def test_gate_rejects_when_mean_up_but_ci_straddles_zero(sc, root):
    # A exempts topic x rows from the niche penalty, B exempts topic y rows.
    # The mean delta is slightly positive (y rows score higher), but per-row
    # deltas have both signs, so the 90% interval straddles zero. Old code
    # had no such check at all.
    write_root(root, val_rows(), best_skill=POLICY_NICHE_X)
    proposed = root / "proposed.md"
    proposed.write_text(POLICY_NICHE_Y, encoding="utf-8")
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "swap penalty",
                  "--skill", str(proposed)])
    assert rc == 0
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is False
    assert rec["delta_mean"] > 0
    assert rec["ci90_low"] <= 0


def test_gate_reject_books_manual_receipt_and_buffer(sc, root):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    rc = sc.main(["--root", str(root), "gate", "reject", "--summary", "tried 3-line originals",
                  "--edit", "tried: always post 3-line originals"])
    assert rc == 0
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is False
    assert rec["decision_basis"] == "manual"
    assert rec["score_version"] == sc.SCORE_VERSION
    buf = (root / "rejected_edits.md").read_text(encoding="utf-8")
    assert "tried 3-line originals" in buf


def test_gate_too_few_rows(sc, root, capsys):
    write_root(root, val_rows()[:3])
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "s", "--skill", "x.md"])
    assert rc == 3
    out = json.loads(capsys.readouterr().out)
    assert out["error"] == "too few rows to gate an edit"


def test_gate_too_few_val_rows(sc, root, capsys):
    rows = [make_row(f"t{i}", split="train") for i in range(10)]
    write_root(root, rows)  # all train: zero scored val rows
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "s", "--skill", "x.md"])
    assert rc == 3
    out = json.loads(capsys.readouterr().out)
    assert "val" in out["error"]


def test_gate_more_than_four_edits_rejected(sc, root):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    edits = [f"edit {i}" for i in range(5)]
    argv = ["--root", str(root), "gate", "reject", "--summary", "s"]
    for e in edits:
        argv += ["--edit", e]
    rc = sc.main(argv)
    assert rc == 2


def test_gate_receipt_logs_before_after_and_interval(sc, root):
    write_root(root, val_rows(), best_skill=POLICY_NICHE_OPS)
    proposed = root / "proposed.md"
    proposed.write_text(NO_POLICY, encoding="utf-8")
    sc.main(["--root", str(root), "gate", "accept", "--summary", "s", "--skill", str(proposed),
             "--edit", "DO: keep scoring ops rows"])
    rec = json.loads(receipts(root)[0].read_text())
    for key in ("val_mean_before", "val_mean_after", "delta_mean", "ci90_low", "ci90_high",
                "score_version", "skill_before_sha256", "skill_after_sha256", "n_val_scored",
                "edits", "rule", "ts"):
        assert key in rec, f"receipt missing {key}"
    assert rec["val_mean_after"] > rec["val_mean_before"]
    assert rec["ci90_low"] > 0
    assert rec["edits"] == ["DO: keep scoring ops rows"]


def test_gate_accept_without_improvement_does_not_touch_skill(sc, root):
    # same policy on both sides: delta 0, verdict tie -> no adoption
    write_root(root, val_rows(), best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(NO_POLICY, encoding="utf-8")
    sc.main(
        ["--root", str(root), "gate", "accept", "--summary", "no change", "--skill", str(proposed)]
    )
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is False
    assert rec["delta_mean"] == 0.0


def test_gate_val_ids_from_config_count_as_val(sc, root):
    rows = val_rows()
    for r in rows:
        r.pop("split")
    write_root(root, rows, cfg={"val_ids": [r["id"] for r in rows]}, best_skill=POLICY_NICHE_OPS)
    proposed = root / "proposed.md"
    proposed.write_text(NO_POLICY, encoding="utf-8")
    rc = sc.main(
        ["--root", str(root), "gate", "accept", "--summary", "s", "--skill", str(proposed)]
    )
    assert rc == 0
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is True


def test_gate_missing_proposed_file_is_clean_error(sc, root, capsys):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "s",
                  "--skill", str(root / "nope.md")])
    assert rc == 2
    assert "error:" in capsys.readouterr().err
