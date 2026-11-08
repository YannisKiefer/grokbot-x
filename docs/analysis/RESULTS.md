# RESULTS.md - Phase 5 verification (2026-11-08)

## Test suite

94 tests, all passing on the new code. Run:

```
$ .tools-venv/bin/pytest
........................................................................ [ 76%]
......................                                                   [100%]
94 passed in 0.43s
```

Coverage by file:

| File | What it pins |
|---|---|
| tests/test_parsing.py (21) | trajectory parsing (bad JSON lines with file+line in the error, non-object lines), row validation (missing id, bad type, negative/string metrics, negative viral_ratio), pending-vs-zero metrics, `--root` after subcommand, status does NOT rewrite the log, empty-state hint, append duplicate-id and bad-JSON rejection, duplicate penalty on append, held_out.json validation |
| tests/test_scoring.py (25) | velocity (older bucket scores lower; 240 views at 1h vs 24h), follower normalization, zero/missing followers, bookmark > reply > like weights, reply bonus boundaries (12x/20x, <5x penalty), author-reply x1.5, dead-diary x0.4, hard-open, off-niche penalty only when the policy lists topics, risky-parent penalty, duplicate halving, duplicate detection (later row, same-type only), policy parse (defaults, overrides, unknown key, bad JSON, wrong types), bootstrap CI (degenerate at constant, excludes zero on clear effect), deterministic seed |
| tests/test_gate.py (11) | accept requires --skill, adoption only on strict improvement + CI, reject on falling mean, reject when mean up but CI straddles zero (the exact case the old code accepted), manual reject receipt + rejected_edits.md buffer, too-few-rows (exit 3), too-few-val-rows (exit 3), >4 edits rejected, receipt logs before/after/interval/sha256/score_version, tie does not touch best_skill.md, val_ids from config count as val |
| tests/test_replay.py (5) | replay reports the winner with delta + CI, identical skills tie, val-only scoring, clean errors without val rows or with missing files |
| tests/test_publish.py (32) | mocked Typefully (no network): happy path, made_with_ai operator choice on/off, empty/over-long text refused, --allow-long, missing/placeholder env exit 2, HTTP and network errors print clean messages (no tracebacks), poll timeout exits 4 "not confirmed" (was: exit 1 failure), failed state exit 1, --no-wait, response without draft id, non-JSON response, export-prefixed .env lines; reply drafts: reply_to_url present, no publish_at ever, twitter.com URLs accepted, 6 malformed reply-to URLs refused, missing private_url |

## Tests fail on the old code

Ran the same suite against the pre-change tree (worktree at cade7d9):

```
84 failed, 10 passed in 2.12s
```

The 10 passing are tests whose behavior the old code satisfied by accident
(e.g. identical-skill replay tie is trivially true when both files score the
same, some clean-error paths where old argparse also errored). Every fix
listed in docs/analysis/ANALYSIS.md is covered by at least one test that
fails on the old code, including: B1 (the old gate accepted on the
operator's word - test_gate proves the new one computes and can reject),
B2 (velocity/normalization - no such concept before), B3 (--root position),
B4 (validation), B5 (status rewrite), B6 (poll/network errors).

## Lint

```
$ .tools-venv/bin/ruff check .
All checks passed!
```

## Behavior checks (ran, not just tested)

- `python3 skillopt/sleep_cycle.py status` on the shipped example data:
  n=5, n_scored=5, train_mean/val_mean printed per split plus reply/original
  means, ready_for_edit=false (5 < 8), score_version v2-velocity-2026-11-08.
- `status --root /tmp/x` now works in both flag positions (old code: error).
- A replay of identical skills on the example data prints verdict "tie".
- Both publish scripts run to the "missing or placeholder env" error with
  exit 2 and no traceback when .env is absent.

## What is proven vs not

- Proven: the gate computes accept/reject from data with a bootstrap 90% CI
  and refuses small samples; the reward is velocity-normalized and
  duplicate/niche/risky-parent penalized; replay ranks two skill policies
  offline; publish inputs are validated; no test touches the network.
- Not proven (honest): that the new score formula correlates with real
  account growth better than the old one - that needs weeks of real
  trajectories; the weights (x1.35 bonus, 0.5/1.5/2.0 engagement weights)
  are directional choices from the research, not fitted to data. The
  `score_version` field exists exactly so a future refit is auditable.
