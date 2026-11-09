"""Trajectory parsing and input validation at the trust boundary."""
import json

import pytest
from conftest import make_row, write_root


def test_bad_json_line_names_file_and_line(sc, tmp_path):
    p = tmp_path / "trajectories.jsonl"
    p.write_text('{"id": "a"}\nnot json at all\n', encoding="utf-8")
    with pytest.raises(sc.DataError) as e:
        sc.load_traj(p)
    assert "line 2" in str(e.value)


def test_empty_lines_are_skipped(sc, tmp_path):
    p = tmp_path / "trajectories.jsonl"
    p.write_text('{"id": "a", "type": "reply"}\n\n  \n', encoding="utf-8")
    assert len(sc.load_traj(p)) == 1


def test_non_object_line_rejected(sc, tmp_path):
    p = tmp_path / "trajectories.jsonl"
    p.write_text('[1, 2]\n', encoding="utf-8")
    with pytest.raises(sc.DataError):
        sc.load_traj(p)


def test_validate_row_rejects_missing_id(sc):
    with pytest.raises(sc.DataError, match="id"):
        sc.validate_row({"type": "reply"}, "t")


def test_validate_row_rejects_bad_type(sc):
    with pytest.raises(sc.DataError, match="type"):
        sc.validate_row({"id": "x", "type": "tweet"}, "t")


def test_validate_row_rejects_negative_views(sc):
    row = make_row("x", views=-5)
    with pytest.raises(sc.DataError, match="views"):
        sc.validate_row(row, "t")


def test_validate_row_rejects_non_numeric_views(sc):
    row = make_row("x", views="1,000")
    with pytest.raises(sc.DataError, match="views"):
        sc.validate_row(row, "t")


def test_validate_row_rejects_negative_viral_ratio(sc):
    row = make_row("x", ratio=-2)
    with pytest.raises(sc.DataError, match="viral_ratio"):
        sc.validate_row(row, "t")


def test_has_metrics_distinguishes_pending_from_zero(sc):
    pending = {"id": "a", "type": "reply", "metrics": {}}
    zeroed = {"id": "b", "type": "reply", "metrics": {"t1h": {"views": 0}}}
    assert sc.has_metrics(pending) is False
    assert sc.has_metrics(zeroed) is True
    assert sc.has_metrics({"id": "c", "type": "reply"}) is False


def test_status_gives_clean_error_on_bad_line(sc, root, capsys):
    (root / "trajectories.jsonl").write_text('{"id": "a"}\nnope\n', encoding="utf-8")
    rc = sc.main(["--root", str(root), "status"])
    assert rc == 2
    assert "line 2" in capsys.readouterr().err


def test_status_does_not_rewrite_the_log(sc, root):
    # old code rewrote trajectories.jsonl on every status; the log must not move
    rows = [make_row("a"), make_row("b")]
    write_root(root, rows)
    before = (root / "trajectories.jsonl").read_text(encoding="utf-8")
    assert sc.main(["--root", str(root), "status"]) == 0
    assert (root / "trajectories.jsonl").read_text(encoding="utf-8") == before


def test_status_empty_gives_hint_not_silence(sc, root, capsys):
    rc = sc.main(["--root", str(root), "status"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["n"] == 0
    assert "hint" in out


def test_root_flag_after_subcommand(sc, root, capsys):
    # old argparse rejected "status --root"; both positions must work
    (root / "trajectories.jsonl").write_text("", encoding="utf-8")
    rc = sc.main(["status", "--root", str(root)])
    assert rc == 0


def test_root_flag_before_subcommand(sc, root, capsys):
    (root / "trajectories.jsonl").write_text("", encoding="utf-8")
    assert sc.main(["--root", str(root), "status"]) == 0


def test_append_rejects_bad_json(sc, root, capsys):
    rc = sc.main(["--root", str(root), "append", "--json", "{oops"])
    assert rc == 2
    assert "error:" in capsys.readouterr().err


def test_append_rejects_row_without_id(sc, root, capsys):
    rc = sc.main(["--root", str(root), "append", "--json", '{"type": "reply"}'])
    assert rc == 2
    assert "id" in capsys.readouterr().err


def test_append_rejects_duplicate_id(sc, root, capsys):
    write_root(root, [make_row("dup")])
    rc = sc.main(["--root", str(root), "append", "--json", json.dumps(make_row("dup"))])
    assert rc == 2
    assert "already exists" in capsys.readouterr().err


def test_append_stamps_score_and_version(sc, root, capsys):
    rc = sc.main(["--root", str(root), "append", "--json", json.dumps(make_row("new1"))])
    assert rc == 0
    line = json.loads((root / "trajectories.jsonl").read_text().splitlines()[0])
    assert line["score_version"] == sc.SCORE_VERSION
    assert line["score"] >= 0


def test_append_reports_duplicate_penalty(sc, root):
    write_root(root, [make_row("a1", text="the checkout drop kills paid conversion")])
    rc = sc.main(
        [
            "--root", str(root), "append",
            "--json", json.dumps(make_row("a2", text="the checkout drop kills paid conversion")),
        ]
    )
    assert rc == 0
    line = json.loads((root / "trajectories.jsonl").read_text().splitlines()[1])
    lone = make_row("lone", views=100)
    sc.rescore(lone)
    assert line["score"] == pytest.approx(lone["score"] / 2, abs=1e-3)


def test_held_out_bad_val_ids_rejected(sc, root, capsys):
    (root / "held_out.json").write_text('{"val_ids": "not-a-list"}', encoding="utf-8")
    rc = sc.main(["--root", str(root), "status"])
    assert rc == 2
    assert "val_ids" in capsys.readouterr().err


def test_held_out_bad_min_rows_rejected(sc, root, capsys):
    (root / "held_out.json").write_text('{"min_trajectories_before_edit": 0}', encoding="utf-8")
    rc = sc.main(["--root", str(root), "status"])
    assert rc == 2
    assert "min_trajectories_before_edit" in capsys.readouterr().err


def test_append_stamps_best_skill_sha(sc, root):
    write_root(root, [], best_skill="current skill\n")
    sc.main(["--root", str(root), "append", "--json", json.dumps(make_row("n1"))])
    line = json.loads((root / "trajectories.jsonl").read_text().splitlines()[0])
    assert line["skill_sha256"] == sc.sha256_file(root / "best_skill.md")


def test_append_skill_flag_stamps_trial_skill_sha(sc, root):
    write_root(root, [], best_skill="current skill\n")
    trial = root / "proposed.md"
    trial.write_text("proposed skill\n", encoding="utf-8")
    rc = sc.main(["--root", str(root), "append", "--skill", str(trial),
                  "--json", json.dumps(make_row("n1"))])
    assert rc == 0
    line = json.loads((root / "trajectories.jsonl").read_text().splitlines()[0])
    assert line["skill_sha256"] == sc.sha256_file(trial)


def test_append_rejects_non_string_skill_sha(sc, root, capsys):
    row = make_row("n1")
    row["skill_sha256"] = 5
    rc = sc.main(["--root", str(root), "append", "--json", json.dumps(row)])
    assert rc == 2
    assert "skill_sha256" in capsys.readouterr().err


def test_held_out_bad_reward_config_rejected(sc, root, capsys):
    for body, key in (('{"niche_topics": "ads"}', "niche_topics"),
                      ('{"author_followers": 0}', "author_followers")):
        (root / "held_out.json").write_text(body, encoding="utf-8")
        assert sc.main(["--root", str(root), "status"]) == 2
        assert key in capsys.readouterr().err


def test_status_warns_when_followers_are_missing(sc, root, capsys):
    write_root(root, [make_row("a"), make_row("b", followers=300)])
    sc.main(["--root", str(root), "status"])
    assert "author_followers" in json.loads(capsys.readouterr().out)["warning"]
    write_root(root, [make_row("a")], cfg={"author_followers": 300})
    sc.main(["--root", str(root), "status"])
    assert "warning" not in json.loads(capsys.readouterr().out)


def test_status_ready_counts_scored_rows_only(sc, root, capsys):
    rows = [make_row(f"s{i}") for i in range(3)]
    for i in range(10):
        r = make_row(f"p{i}")
        r["metrics"] = {}
        rows.append(r)
    write_root(root, rows)
    sc.main(["--root", str(root), "status"])
    out = json.loads(capsys.readouterr().out)
    assert out["n_scored"] == 3
    assert out["ready_for_edit"] is False


def test_non_numeric_followers_rejected(sc, root, capsys):
    row = make_row("a")
    row["features"]["author_followers"] = "1,200"
    write_root(root, [row])
    assert sc.main(["--root", str(root), "status"]) == 2
    assert "author_followers" in capsys.readouterr().err


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_validate_row_rejects_non_finite_numbers(sc, bad):
    with pytest.raises(sc.DataError, match="views"):
        sc.validate_row(make_row("x", views=bad), "t")
    with pytest.raises(sc.DataError, match="viral_ratio"):
        sc.validate_row(make_row("x", ratio=bad), "t")


def test_non_finite_literals_in_jsonl_and_policy_rejected(sc, tmp_path):
    p = tmp_path / "trajectories.jsonl"
    p.write_text(
        '{"id": "a", "type": "reply", "metrics": {"t1h": {"views": 1e999}}}\n', encoding="utf-8"
    )
    (row,) = sc.load_traj(p)
    with pytest.raises(sc.DataError, match="finite"):
        sc.validate_row(row, "t")
    with pytest.raises(sc.DataError, match="min_parent_ratio"):
        sc.parse_policy('<!-- skillopt-policy {"min_parent_ratio": NaN} -->', "t")
    assert sc._num(float("nan"), 1.0) == 1.0
