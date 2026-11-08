# ANALYSIS.md - grokbot-x, full read (2026-11-08)

Repo read end to end: README, docs/* (7), skills/*/SKILL.md (5), scripts/*.py (2),
skillopt/sleep_cycle.py, skillopt/best_skill.md, skillopt/held_out.example.json,
skillopt/rejected_edits.md, examples/*, .env.example, .gitignore, LICENSE.
Verified behavior by running `sleep_cycle.py status` and probing error paths.

## 1. End-to-end flow (exact file and function per step)

| Step | Where | Exact entry point |
|---|---|---|
| Scout gold | `docs/PLAYBOOK.md` step 1 + `docs/OPERATOR.md` "Gold targeting" + `skillopt/best_skill.md` DO/DONT | Manual: operator computes `viral_ratio = parent_views / parent_followers`, keep >= 12x (ideal >= 20x), climbable replies |
| Draft unslop | `skills/x-unslop-humanizer/SKILL.md` + `skills/x-unslop-humanizer-2/SKILL.md` (second pass) | Agent loads skill, writes reply/original, spoken test |
| Publish original | `scripts/publish_original.py` -> `main()` -> `api("POST", .../social-sets/{sid}/drafts)` with `publish_at: "now"`, then polls `GET .../drafts/{id}` until `publish_state == "finished"` | `python3 scripts/publish_original.py --text "..."` |
| Draft reply (human publishes) | `scripts/create_reply_draft.py` -> POST draft with `reply_to_url`, no `publish_at`; human opens `private_url` and clicks Publish NOW in Typefully UI | `python3 scripts/create_reply_draft.py --text "..." --reply-to URL` |
| Log trajectory | `skillopt/sleep_cycle.py` `cmd_append()` -> `append_traj()` -> `rescore()` | `python3 skillopt/sleep_cycle.py append --json '{...}'` appends one line to `skillopt/trajectories.jsonl` |
| Fill metrics later | Operator/agent edits the row's `metrics` buckets (`t20m`, `t1h`, `t6h`, `t24h`, `t_night`) | Manual or agent |
| Score / status | `sleep_cycle.py` `cmd_status()` -> `load_traj()`, `rescore()`, `split_rows()`, `mean_score()` | `python3 skillopt/sleep_cycle.py status` |
| Nightly gate | `skills/x-skillopt-learn/SKILL.md` nightly routine; booking in `sleep_cycle.py` `cmd_gate()` -> writes `skillopt/epochs/<stamp>_accept|reject.json`, rejects also appended to `rejected_edits.md` | Reflection is done by the operator/agent; the script only books the receipt |
| Deployed skill | `skillopt/best_skill.md` | Edited only when the gate accepts; starter copy in `examples/best_skill.starter.md` |

The loop is honest about being human-in-the-loop: the script scores and books,
the human/agent reflects. The gate, however, is enforced nowhere (see B1).

## 2. Bugs, ranked by impact

### B1. The acceptance gate verifies nothing (high)
`cmd_gate()` (sleep_cycle.py:166) books "accept" or "reject" purely on the
operator's word. Nothing computes before/after val means, nothing requires a
minimum row count at gate time (`min_trajectories_before_edit` is only printed
by `status`), nothing prevents a skill rewrite going live unmeasured. The
README promises "held-out val must strictly improve"; code enforces nothing.
Fix in Phase 5: gate command must take the two skill files, score val rows,
require min rows, require mean improvement AND bootstrap 90% CI > 0, log both.

### B2. Score ignores post age and follower normalization (high)
`rescore()` (sleep_cycle.py:76) uses raw `log1p(views)` of the latest bucket.
A post measured 20 minutes after publish competes against one measured at
24h. Docs claim "Early velocity for post age" is a scouting criterion but the
reward never sees age. Also no normalization by the operator's own follower
count, so raw views reward accounts that got big, not skills that work.
Phase 5: views/hour velocity, normalized by follower count.

### B3. `--root` rejected after the subcommand (medium)
`sleep_cycle.py status --root X` -> `argparse` error "unrecognized arguments".
Verified. It only works as `sleep_cycle.py --root X status`. Docs never state
the order. Fix: accept both.

### B4. Malformed input crashes with raw tracebacks (medium, several sites)
Verified crashes:
- `status` with one bad line in trajectories.jsonl -> `json.JSONDecodeError`
  traceback, exit 1, no filename/line number, whole run dies.
- `append` with bad JSON -> same raw traceback (also crashes on valid JSON
  missing required keys like `id`, and silently accepts duplicate `id`s).
- `rescore()` on `views: "1,000"` or a negative number -> ValueError /
  math domain error, uncaught.
No input validation at any trust boundary (JSON files, CLI args, API
responses below).

### B5. `cmd_status` silently rewrites trajectories.jsonl (medium)
`cmd_status` (sleep_cycle.py:127) rewrites the whole log file in place after
rescoring. A crash mid-write corrupts the operator's only dataset; the file
is documented as "one line per ship. Your real data." Rewriting a log file
from a read command is wrong. Fix: write to temp + atomic replace, or don't
rewrite at all (scores can live in memory / a sidecar).

### B6. Publish scripts: network errors uncaught, polling lies (medium)
- `api()` in publish_original.py catches only `HTTPError`; `URLError`
  (DNS fail, timeout) escapes as a traceback. Same POST path in
  create_reply_draft.py:75.
- Poll loop gives up after 20 x 2 s and exits 1 with "timed out" although
  Typefully `publish_at: "now"` is async and the post usually goes live
  later. Reads as failure when the post is fine. Should report "still
  pending, check Typefully" and exit 0 (or distinct code), and stop early
  on an explicit failure state if the API returns one.

### B7. No validation on publish inputs (medium)
- `--text` length never checked; X rejects > 280 chars for standard
  accounts with an opaque Typefully error.
- `--reply-to` never checked; a typo ("x.com/status/123" missing scheme,
  or a tweet URL pasted twice) produces a draft that can never be
  published as a reply.

### B8. `gate` timestamp collisions overwrite receipts (low)
Epoch files are named `%Y%m%dT%H%M%SZ`; two gates in the same second
silently overwrite. Add an `-HHMMSS` suffix uniquifier or include the
summary slug.

### B9. `latest_bucket` fallback order is insertion order (low)
If none of the known bucket keys match, the fallback `for v in m.values()`
returns whatever dict happens to be first, not the newest. Known keys cover
real usage; a comment or explicit order fix makes it deterministic.

### B10. `--root` before subcommand only, plus dead config keys (low)
`held_out.json` declares `metric` and `gate` keys that no code reads. Either
read them or document them as inert.

## 3. Docs that disagree with code or reality

1. README "GitHub topics" section: says topics "are already set on the GitHub
   repository". They are not set (confirmed via API 2026-11-08). Stale claim.
2. `docs/SKILLOPT.md` says "Latest metrics bucket wins: t_night > t24h > t6h
   > t1h" - code also honors `t20m` and `t_plus_*` buckets.
3. README sells "Publish without the AI badge" as a benefit. Ground rules for
   this repo: official clients, disclosure is the operator's choice. The
   framing should be "official API, no bot-browser compose", with
   `made_with_ai` operator-configurable instead of hardcoded false.
4. `docs/PUBLISH.md` "If the AI label appears: Delete the post" - deleting a
   labeled post is label-avoidance, not compliance. Reframe: the label means
   the session looked automated; stop that path; keep/delete is the
   operator's call.
5. `held_out.example.json` has `min_trajectories_before_edit: 8` but the
   example dataset has 5 rows, so the shipped example can never pass its own
   gate. Intentional-looking, but say so in the doc.
6. `.env.example` documents `YOUR_TIMEZONE` as "Used only for human-cadence
   notes, not by the scorer" - true; but nothing reads YOUR_TIMEZONE or
   YOUR_HANDLE at all in scripts. They are agent-context variables. Fine, but
   say so (already half-said).
7. README setup copies examples to `skillopt/` paths that are gitignored -
   correct, but `status` on a fresh clone without the copy prints n=0 with no
   hint that examples exist. Add the hint to the empty-state output.

## 4. Missing error handling / validation (trust boundaries)

- Env vars: `require()` checks placeholder/empty - good; but social set id
  check duplicates that logic inline in both scripts instead of reusing it.
- JSON files: no validation anywhere (B4).
- API responses: `created.get("id")` etc. never checked for None/shape; a
  Typefully schema change prints `None` instead of an error.
- CLI: `--text` empty string accepted and publishes an empty post.

## 5. Untested paths

Everything. Zero tests, zero CI, zero lint config. Highest-value tests:
trajectory parsing (bad lines/missing metrics), scoring, the acceptance gate
(accept/reject/too-few-rows), replay eval, publish scripts with mocked
Typefully, input validation. Done in Phase 5.

## 6. Safety / platform-rules posture

Good bones: official API only, no bot-browser compose, human clicks Publish
NOW for every reply, anti-burst cadence, explicit "never bulk replies". Gaps
per current ground rules:
- `made_with_ai: false` is hardcoded; should be the operator's choice (flag).
- "Delete the post if labeled" reads as evasion; reframe as fix-the-path.
- Reply flow's human approval step is implicit (UI click). Make it explicit
  in the checklist: a human reads and approves the text before the click.

## 7. What "status" printed on the example data

Fresh clone: `python3 skillopt/sleep_cycle.py status` -> n=0, means 0.0,
ready_for_edit false, no error and no hint. After copying the example files
(README quickstart): n=5, train_mean 0.227, val_mean 0.765, ready_for_edit
false (5 < 8). The example data can never satisfy its own gate - fine for a
demo, worth a sentence in docs.

## 8. Code quality notes

- Stdlib only, no dependencies - a real strength, keep it.
- `load_dotenv`/`require` duplicated across both scripts (~30 lines). For a
  copy-first kit, self-contained scripts are defensible; do not extract a
  shared module just for DRY.
- `load_dotenv` mishandles `export KEY=...` lines (parses key as
  "export KEY"). Minor; .env.example shows plain form.
- Type hints + `from __future__ import annotations` present, clean.
- `skillopt/epochs/` uses `.gitkeep` + gitignore for receipts - correct.
- No pyproject/ruff/CI (Phase 2 adds).

## 9. Plan carried into later phases

- Phase 5 fixes B1-B8 (verifiable reward, bootstrap gate, replay eval,
  validation, tests).
- Phase 2 adds CONTRIBUTING/SECURITY/templates/CHANGELOG/pyproject(ruff)/CI
  workflow + badge.
- Phase 6 rewrites README top (quickstart, flow, file map, what NOT to do),
  removes the stale topics claim.
- Framing changes from section 6 land in Phase 5/6 alongside the script
  changes (made_with_ai flag, label-reframe, explicit human approval line).
