# SkillOpt for X

This kit treats `skillopt/best_skill.md` as the trainable state of a
frozen Grok Bot. That is the [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt)
idea, pointed at tweets instead of office tasks.

You do not fine-tune a model. You edit one markdown file. Slowly.
Only when the held-out gate proves the edit is better.

## Loop

```
ship -> log trajectory -> later fill metrics
night: harvest -> score train vs val -> propose <= 4 edits -> gate
  proven better -> best_skill.md
  noise or worse -> rejected_edits.md
```

## Files

| File | Role |
|---|---|
| `skillopt/best_skill.md` | deployed skill. The bot follows this tomorrow. |
| `skillopt/trajectories.jsonl` | one line per ship. Your real data. Gitignored. |
| `examples/trajectories.example.jsonl` | fake rows so you can see the shape. |
| `skillopt/held_out.json` | val ids, row minimums, `learning_rate_max_edits` (4), `niche_topics`, `author_followers`. |
| `skillopt/rejected_edits.md` | negative buffer. Do not retry these. |
| `skillopt/epochs/` | accept/reject receipts, plus a copy of each replaced skill. |
| `skillopt/sleep_cycle.py` | score, status, append, gate, replay. |

## Score (what "better" means)

`sleep_cycle.py` rescores every row from X counters only. The reward is
fixed in code (score_version `v3-fixed-reward-2026-11-08`); no skill file
can change it, so an edit cannot win by rewriting its own reward:

- latest metrics bucket wins (buckets are ordered newest-first:
  `t_night`/`t24h` > `t6h` > `t1h`/`t20m`/`t_plus_*`),
- views and engagement are divided by post age and by your follower
  count (roughly "views per 1000 followers per hour", log-scaled),
- engagement weights: likes x0.5, replies x1.5, bookmarks x2.0
  (bookmarks are the hardest counter to bait),
- author replied to you: x1.5 (an outcome),
- guards: near-duplicate text x0.5, risky parent x0.5, off-niche topic
  x0.5 (when `held_out.json` lists `niche_topics`),
- then divide by 10.

Targeting features (parent ratio, dead diary, hard open) are not rewarded.
Where you reply is a choice; the reward only counts what happened.

Follower count is YOUR account's follower count at ship time (not the
parent author's): each row's `features.author_followers`, else
`author_followers` in `held_out.json`. Set one of them: `status` warns
when rows have neither, because their velocity is not comparable.

Features are frozen at ship time. A metrics refresh updates `metrics`
only; never rewrite `viral_ratio` or `viral_signal` later, or replay
would learn from facts you could not know when you replied.

The reward is a mean per post, so a policy that skips weak posts wins
even if total reach drops. That is intended (quality over volume), but
watch total views in `status` too.

Rows with no metrics yet are pending, not zero; they do not drag means
and do not count toward row minimums.

## The policy block

A skill file may carry one machine-readable targeting rule:

```
<!-- skillopt-policy {"min_parent_ratio": 12, "skip_dead_diary": true, "topics": ["ads", "checkout"]} -->
```

Known keys, all about which posts to make, none about scoring:

| Key | Effect |
|---|---|
| `min_parent_ratio` | skip replies whose parent `viral_ratio` is below this (or unknown) |
| `skip_dead_diary` | skip rows with `viral_signal: weak_dead_diary` |
| `skip_risky_parents` | skip replies under `parent_risky` parents |
| `topics` | only post on these topics (rows with another or no topic are skipped) |

Everything else in the file is prose for the bot.

## Two kinds of evidence

The gate judges held-out (val) rows only, and uses the strongest
evidence it has:

1. **Live trial** (any edit, including prose). Deploy the proposal for a
   while and log those ships with its hash:
   `sleep_cycle.py append --skill skillopt/proposed.md --json '{...}'`.
   Log trial rows with `"split": "val"`. Once both the current skill and
   the proposal have at least `min_val_rows` scored val rows, the gate
   compares the proposal's rows with the current skill's rows from the
   same window (logged at or after the first trial row), two-sample
   bootstrap. Alternate the two skills by day so time effects hit both,
   and draft from the file you log (see `skills/x-skillopt-learn`). A
   trial needs a current `best_skill.md` to compare against.
2. **Replay** (targeting edits). Each skill's policy block is applied to
   the logged val rows: which rows would it have posted? The gate compares
   the mean reward of the rows each one keeps. A proposal that keeps fewer
   than `min_val_rows` rows, or under half of what the current skill keeps,
   is `insufficient`, not a win: cherry-picking a few lucky rows proves
   nothing. Prose-only edits take the same rows and replay as a tie; they
   need a live trial.

Replay is off-policy: it only sees posts you actually made, so it can say
"skip weak parents" is better, never "reply under parents you never
tried". New targets need a live trial.

## Nightly gate

The gate computes the decision. It does not take your word.

1. Refresh metrics on anything older than an hour.
2. `python3 skillopt/sleep_cycle.py status`
3. Propose at most 4 bounded edits on a COPY of `best_skill.md`
   (e.g. `skillopt/proposed.md`), after reading `rejected_edits.md`.
4. Gate it:

```bash
python3 skillopt/sleep_cycle.py gate accept \
  --summary "replies-only on >=12x, bank zero-gold hours" \
  --edit "DO: no filler originals in empty hours" \
  --skill skillopt/proposed.md
```

5. The gate refuses to run with too few scored rows (default 8 total,
   5 val, never fewer than 5 val; both set in `held_out.json`). Otherwise
   it accepts only if the mean improves AND the bootstrap interval of the
   improvement is above zero.
6. Every look at the val rows is an attempt. Each distinct proposal tried
   since the last accept (by `gate accept` or `replay`; the same file
   twice counts once) raises the bar: attempt k needs a
   `1 - 0.10/(k(k+1))` interval (95%, 98.3%, 99.2%, ...), so all attempts
   together keep the false-accept rate near 5%. Without this, 20 tries on
   the same rows accepted a pure-noise edit 76% of the time in simulation;
   with it, 8% for log-scale rewards like ours. Attempts live in
   `epochs/attempts.jsonl`; an accept starts a new count.
7. The receipt in `skillopt/epochs/` records the method (trial or replay),
   attempt, interval level and bounds, row counts, means, the verdict and
   both file hashes. On accept it saves the old skill as
   `epochs/<ts>_best_before.md` and replaces `best_skill.md` atomically.
   On reject it appends to `rejected_edits.md` with the verdict: "proven
   worse, do not retry", "not proven either way; retry only as a live
   trial", or "not tested". Read the verdict before skipping an idea.
8. Rejecting an edit without proposing one is fine too:

```bash
python3 skillopt/sleep_cycle.py gate reject \
  --summary "val did not improve" --edit "tried: always post 3-line originals"
```

## Prove it before it goes live

Replay two skill versions against held-out rows, any time:

```bash
python3 skillopt/sleep_cycle.py replay --skill-a skillopt/best_skill.md --skill-b skillopt/proposed.md
```

Reports how many val rows each skill keeps, their means, the delta, the
interval and a verdict. Same replay math as the gate; nothing is adopted,
but it counts as an attempt (see step 6), so replay ideas you mean to
gate, not every variation you can think of.

## Why the controls exist

- **Bounded edits (lr=4):** a textual learning rate. Stops the bot from
  rewriting the whole doctrine every night.
- **Bootstrap gate:** reflection without a test set is fanfic; a val mean
  alone at n=20 is noise. The CI rule rejects edits whose gain is
  indistinguishable from zero. It does not prove causality (see
  docs/analysis/RESEARCH.md).
- **Fixed reward:** a skill that could edit its own reward would always
  find a way to score higher (Goodhart). The reward lives in code.
- **Held-out only, coverage guard:** train rows wrote the edit, so they
  cannot judge it; a policy that keeps 2 lucky rows proves nothing.
- **Min rows:** a gate over 5 rows is a coin flip with extra steps.
- **Attempt count:** testing many ideas on the same rows finds a lucky
  one. The bar rises with each attempt.
- **Rejected buffer:** the optimizer sees what already failed, so it does
  not loop.
- **score_version in every receipt:** when the formula changes, old and
  new epochs stay auditable.

## Start from the example

```bash
cp examples/trajectories.example.jsonl skillopt/trajectories.jsonl
cp skillopt/held_out.example.json skillopt/held_out.json
python3 skillopt/sleep_cycle.py status
```

Those rows are fake. The example dataset has 5 rows, below the gate's
minimum of 8, so it demonstrates `status` but can never pass a gate.
Replace them with your ships before you trust a gate.
