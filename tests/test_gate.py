"""The acceptance gate: held-out only, fixed reward, trial or replay evidence,
bootstrap CI, coverage, receipts, skill adoption and rollback copy."""
import hashlib
import json

from conftest import make_row, write_root

NO_POLICY = "prose only\n"
GOLD_ONLY = 'prose\n<!-- skillopt-policy {"min_parent_ratio": 12} -->\n'
GOLD_ONLY_SAME_ROWS = 'other prose\n<!-- skillopt-policy {"min_parent_ratio": 11} -->\n'


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def val_rows():
    """10 scored val replies: 6 under gold parents (ratio >= 12) that did
    well, 4 under weak parents (ratio 2) that did badly."""
    rows = []
    for i in range(6):
        rows.append(make_row(f"vg{i}", views=4000 + 100 * i, ratio=20, split="val",
                             text=f"gold parent reply number {i} about ad spend"))
    for i in range(4):
        rows.append(make_row(f"vw{i}", views=200 + 10 * i, ratio=2, split="val",
                             text=f"weak parent reply number {i} about restock"))
    return rows


def receipts(root):
    return sorted((root / "epochs").glob("*.json"))


def gate(sc, root, skill, *extra):
    return sc.main(["--root", str(root), "gate", "accept", "--summary", "s",
                    "--skill", str(skill), *extra])


def test_gate_accept_requires_skill(sc, root, capsys):
    write_root(root, val_rows())
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "s"])
    assert rc == 2
    out = json.loads(capsys.readouterr().out)
    assert "--skill" in out["error"]


def test_replay_accepts_a_better_targeting_rule(sc, root):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY, encoding="utf-8")
    assert gate(sc, root, proposed, "--edit", "DO: reply only under >=12x parents") == 0
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is True
    assert rec["method"] == "replay"
    assert (rec["n_a"], rec["n_b"]) == (10, 6)
    assert rec["ci_low"] > 0
    assert (root / "best_skill.md").read_text(encoding="utf-8") == GOLD_ONLY


def test_accept_keeps_a_copy_of_the_replaced_skill(sc, root):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY, encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    copy = root / "epochs" / f"{rec['ts']}_best_before.md"
    assert rec["skill_before_copy"] == str(copy)
    assert copy.read_text(encoding="utf-8") == NO_POLICY


def test_replay_rejects_a_worse_targeting_rule(sc, root):
    write_root(root, val_rows(), best_skill=GOLD_ONLY)
    proposed = root / "proposed.md"
    proposed.write_text(NO_POLICY, encoding="utf-8")
    assert gate(sc, root, proposed) == 0
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is False
    assert rec["delta_mean"] < 0
    assert (root / "best_skill.md").read_text(encoding="utf-8") == GOLD_ONLY


def test_edit_cannot_win_by_rewriting_the_reward(sc, root, capsys):
    # The old gate let a skill carry scoring knobs (e.g. drop the dead-diary
    # penalty) and accepted whatever scored itself higher. Scoring knobs are
    # no longer part of a skill at all.
    write_root(root, val_rows(), best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text('<!-- skillopt-policy {"dead_diary_multiplier": 1} -->', encoding="utf-8")
    assert gate(sc, root, proposed) == 2
    assert "unknown skillopt-policy key" in capsys.readouterr().err
    assert (root / "best_skill.md").read_text(encoding="utf-8") == NO_POLICY


def test_policy_that_takes_the_same_rows_is_a_tie(sc, root):
    write_root(root, val_rows(), best_skill=GOLD_ONLY)
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY_SAME_ROWS, encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is False
    assert rec["verdict"] == "tie"
    assert rec["delta_mean"] == 0.0


def test_gate_judges_held_out_rows_only(sc, root):
    # Train rows would make the gold-only rule look great; val rows are all
    # gold, so on held-out data both policies take the same rows: a tie.
    rows = [make_row(f"tw{i}", views=10, ratio=2, split="train", text=f"weak train {i}")
            for i in range(10)]
    rows += [make_row(f"vg{i}", views=4000, ratio=20, split="val", text=f"gold val {i} ads")
             for i in range(6)]
    write_root(root, rows, best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY, encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is False
    assert (rec["n_a"], rec["n_b"]) == (6, 6)
    assert rec["verdict"] == "tie"


def test_too_narrow_a_policy_is_insufficient_not_a_win(sc, root):
    # b keeps 2 lucky rows out of 10: below min_val_rows and below 50% coverage
    rows = val_rows()
    rows[0]["features"]["topic"] = "lucky"
    rows[1]["features"]["topic"] = "lucky"
    write_root(root, rows, best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text('<!-- skillopt-policy {"topics": ["lucky"]} -->', encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is False
    assert rec["verdict"] == "insufficient"
    assert "b needs" in rec["reason"]


def test_noisy_improvement_with_ci_across_zero_is_rejected(sc, root):
    # The rows b keeps are, on average, slightly better than all rows, but
    # their rewards swing widely, so the 90% interval straddles zero.
    rows = []
    for i in range(8):
        views = 5000 if i % 2 == 0 else 0
        rows.append(make_row(f"vs{i}", views=views, ratio=20, split="val", text=f"swing {i} ads"))
    for i in range(6):
        rows.append(make_row(f"vm{i}", views=5, ratio=2, split="val", text=f"steady {i} ops"))
    write_root(root, rows, best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY, encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["delta_mean"] > 0
    assert rec["ci_low"] <= 0 < rec["ci_high"]
    assert rec["accepted"] is False


def test_live_trial_proves_a_prose_only_edit(sc, root):
    # Prose edits cannot replay; a live trial (rows logged while the proposal
    # was deployed) can prove them.
    proposed_text = "rewritten hooks, same targeting\n"
    rows = []
    for i in range(6):
        r = make_row(f"va{i}", views=300 + i, split="val", text=f"old skill post {i} ads")
        r["skill_sha256"] = sha(NO_POLICY)
        rows.append(r)
    for i in range(6):
        r = make_row(f"vb{i}", views=3000 + i, split="val", text=f"new skill post {i} ops")
        r["skill_sha256"] = sha(proposed_text)
        rows.append(r)
    write_root(root, rows, best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(proposed_text, encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["method"] == "trial"
    assert (rec["n_a"], rec["n_b"]) == (6, 6)
    assert rec["accepted"] is True


def test_too_few_trial_rows_falls_back_to_replay(sc, root):
    rows = val_rows()
    rows[0]["skill_sha256"] = sha(GOLD_ONLY)  # one trial row is not evidence
    write_root(root, rows, best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY, encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["method"] == "replay"


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


def test_pending_rows_do_not_count_toward_the_minimum(sc, root, capsys):
    rows = val_rows()[:3]
    for i in range(10):
        r = make_row(f"p{i}", split="val")
        r["metrics"] = {}
        rows.append(r)
    write_root(root, rows)
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "s", "--skill", "x.md"])
    assert rc == 3
    assert json.loads(capsys.readouterr().out)["n_rows"] == 3


def test_gate_too_few_val_rows(sc, root, capsys):
    rows = [make_row(f"t{i}", split="train") for i in range(10)]
    write_root(root, rows)  # all train: zero scored val rows
    rc = sc.main(["--root", str(root), "gate", "accept", "--summary", "s", "--skill", "x.md"])
    assert rc == 3
    out = json.loads(capsys.readouterr().out)
    assert "val" in out["error"]


def test_gate_more_than_four_edits_rejected(sc, root):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    argv = ["--root", str(root), "gate", "reject", "--summary", "s"]
    for i in range(5):
        argv += ["--edit", f"edit {i}"]
    assert sc.main(argv) == 2


def test_gate_receipt_logs_before_after_and_interval(sc, root):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY, encoding="utf-8")
    gate(sc, root, proposed, "--edit", "DO: reply only under >=12x parents")
    rec = json.loads(receipts(root)[0].read_text())
    for key in ("val_mean_before", "val_mean_after", "delta_mean", "ci_low", "ci_high",
                "score_version", "skill_before_sha256", "skill_after_sha256", "n_val_scored",
                "n_a", "n_b", "method", "verdict", "edits", "rule", "ts"):
        assert key in rec, f"receipt missing {key}"
    assert rec["val_mean_after"] > rec["val_mean_before"]
    assert rec["edits"] == ["DO: reply only under >=12x parents"]


def test_gate_val_ids_from_config_count_as_val(sc, root):
    rows = val_rows()
    for r in rows:
        r.pop("split")
    write_root(root, rows, cfg={"val_ids": [r["id"] for r in rows]}, best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY, encoding="utf-8")
    assert gate(sc, root, proposed) == 0
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["accepted"] is True


def test_gate_missing_proposed_file_is_clean_error(sc, root, capsys):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    rc = gate(sc, root, root / "nope.md")
    assert rc == 2
    assert "error:" in capsys.readouterr().err


def test_each_new_proposal_raises_the_bar(sc, root):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    for i, text in enumerate(("p1", "p2", "p2")):
        f = root / f"try{i}.md"
        policy = '<!-- skillopt-policy {"min_parent_ratio": 30} -->'
        f.write_text(f"{text}\n{policy}", encoding="utf-8")
        gate(sc, root, f)
    recs = [json.loads(r.read_text()) for r in receipts(root)]
    # the same file tried twice is one attempt, not two
    assert sorted(r["attempt"] for r in recs) == [1, 2, 2]
    assert min(r["ci_level"] for r in recs) == 0.95


def test_accept_resets_the_attempt_count(sc, root):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    bad = root / "bad.md"
    bad.write_text('<!-- skillopt-policy {"min_parent_ratio": 30} -->', encoding="utf-8")
    gate(sc, root, bad)
    good = root / "good.md"
    good.write_text(GOLD_ONLY, encoding="utf-8")
    gate(sc, root, good)  # attempt 2, accepted
    nxt = root / "next.md"
    nxt.write_text(GOLD_ONLY_SAME_ROWS, encoding="utf-8")
    gate(sc, root, nxt)
    recs = sorted((json.loads(r.read_text()) for r in receipts(root)), key=lambda r: r["attempt"])
    assert [r["accepted"] for r in recs if r["attempt"] == 2] == [True]
    assert sum(1 for r in recs if r["attempt"] == 1) == 2  # bad.md, then next.md after reset


def test_replay_counts_as_an_attempt(sc, root, capsys):
    write_root(root, val_rows(), best_skill=NO_POLICY)
    peek = root / "peek.md"
    peek.write_text('<!-- skillopt-policy {"topics": ["ads"]} -->', encoding="utf-8")
    sc.main(["--root", str(root), "replay", "--skill-a", str(root / "best_skill.md"),
             "--skill-b", str(peek)])
    capsys.readouterr()
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY, encoding="utf-8")
    gate(sc, root, proposed)
    assert json.loads(receipts(root)[0].read_text())["attempt"] == 2


def trial_rows(a_views, b_views, a_ts="2026-09-02T10:00:00Z", b_ts="2026-09-01T10:00:00Z",
               split="val", proposed="rewritten hooks\n"):
    rows = []
    for i, v in enumerate(a_views):
        r = make_row(f"va{i}", views=v, split="val", text=f"old skill post {i} ads")
        r["skill_sha256"], r["ts"] = sha(NO_POLICY), a_ts
        rows.append(r)
    for i, v in enumerate(b_views):
        r = make_row(f"vb{i}", views=v, split=split, text=f"new skill post {i} ops")
        r["skill_sha256"], r["ts"] = sha(proposed), b_ts
        rows.append(r)
    return rows


def test_live_trial_rejects_a_worse_prose_edit(sc, root):
    write_root(root, trial_rows([3000 + i for i in range(6)], [300 + i for i in range(6)]),
               best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text("rewritten hooks\n", encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["method"] == "trial"
    assert rec["verdict"] == "a" and rec["accepted"] is False


def test_trial_ignores_current_skill_rows_from_before_the_trial(sc, root):
    # weak current-skill rows from months ago must not make the trial look good
    rows = trial_rows([3000] * 6, [3000] * 6)
    for i in range(6):
        r = make_row(f"old{i}", views=10, split="val", text=f"ancient post {i} pdp")
        r["skill_sha256"], r["ts"] = sha(NO_POLICY), "2026-01-01T00:00:00Z"
        rows.append(r)
    write_root(root, rows, best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text("rewritten hooks\n", encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["method"] == "trial"
    assert rec["n_a"] == 6
    assert rec["accepted"] is False


def test_trial_rows_marked_train_are_ignored(sc, root):
    write_root(root, trial_rows([300] * 6, [3000] * 6, split="train"), best_skill=NO_POLICY)
    proposed = root / "proposed.md"
    proposed.write_text("rewritten hooks\n", encoding="utf-8")
    gate(sc, root, proposed)
    assert json.loads(receipts(root)[0].read_text())["method"] == "replay"


def test_no_current_skill_means_no_trial(sc, root):
    rows = trial_rows([300] * 6, [3000] * 6)
    write_root(root, rows)  # no best_skill.md
    proposed = root / "proposed.md"
    proposed.write_text("rewritten hooks\n", encoding="utf-8")
    gate(sc, root, proposed)
    rec = json.loads(receipts(root)[0].read_text())
    assert rec["method"] == "replay" and rec["accepted"] is False


def test_backup_names_never_collide(sc, root, monkeypatch):
    import datetime as real_dt

    class Frozen(real_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_dt.datetime(2026, 11, 8, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(sc.dt, "datetime", Frozen)
    write_root(root, val_rows(), best_skill=NO_POLICY)
    first = root / "first.md"
    first.write_text(GOLD_ONLY, encoding="utf-8")
    gate(sc, root, first)
    second = root / "second.md"
    second.write_text('x\n<!-- skillopt-policy {"min_parent_ratio": 12, "topics": []} -->\n',
                      encoding="utf-8")
    write_root(root, val_rows())
    (root / "best_skill.md").write_text(NO_POLICY, encoding="utf-8")
    gate(sc, root, second)
    backups = sorted((root / "epochs").glob("*_best_before.md"))
    assert len(backups) == 2


def test_learning_rate_from_config_is_enforced(sc, root):
    write_root(root, val_rows(), cfg={"learning_rate_max_edits": 2}, best_skill=NO_POLICY)
    argv = ["--root", str(root), "gate", "reject", "--summary", "s",
            "--edit", "a", "--edit", "b", "--edit", "c"]
    assert sc.main(argv) == 2


def test_min_val_rows_below_floor_rejected(sc, root, capsys):
    write_root(root, val_rows(), cfg={"min_val_rows": 1})
    assert sc.main(["--root", str(root), "status"]) == 2
    assert "min_val_rows" in capsys.readouterr().err


def test_rejected_buffer_records_the_verdict(sc, root):
    write_root(root, val_rows(), best_skill=GOLD_ONLY)
    proposed = root / "proposed.md"
    proposed.write_text(GOLD_ONLY_SAME_ROWS, encoding="utf-8")
    gate(sc, root, proposed)
    assert "retry only as a live trial" in (root / "rejected_edits.md").read_text()
