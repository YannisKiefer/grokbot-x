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
| `skillopt/held_out.json` | val ids, `learning_rate_max_edits` (4), row minimums. |
| `skillopt/rejected_edits.md` | negative buffer. Do not retry these. |
| `skillopt/epochs/` | accept/reject receipts with before/after scores. |
| `skillopt/sleep_cycle.py` | score, status, append, gate, replay. |

## Score (what "better" means)

`sleep_cycle.py` rescores every row from X counters only. The reward is
velocity, not raw views (score_version `v2-velocity-2026-11-08`):

- latest metrics bucket wins (buckets are ordered newest-first:
  `t_night`/`t24h` > `t6h` > `t1h`/`t20m`/`t_plus_*`),
- views and engagement are divided by post age and by your follower
  count (roughly "views per 1000 followers per hour", log-scaled),
- engagement weights: likes x0.5, replies x1.5, bookmarks x2.0
  (bookmarks are the hardest counter to bait),
- reply on a >= 20x parent: x1.35; >= 12x: x1.15; < 5x parent: x0.7,
- author replied: x1.5, hard open: x1.1, dead diary: x0.4,
- penalties: near-duplicate text x0.5, off-niche topic x0.5 (when the
  skill's policy lists `niche_topics`), risky parent x0.5,
- then divide by 10.

Rows with no metrics yet are pending, not zero; they do not drag means.

## The policy block

The scorer reads one machine-readable comment per skill file:

```
<!-- skillopt-policy {"reply_bonus_ratio": 12, "niche_topics": ["ads", "checkout"]} -->
```

Known keys: `reply_bonus_ratio`, `reply_bonus_strong_ratio`,
`low_ratio_penalty_below`, `dead_diary_multiplier`, `niche_topics`,
`penalize_risky_parents`. Everything else in the file is prose for the
bot. Prose-only edits replay as a tie: the gate can only measure what the
policy block encodes. When you change scoring-relevant behavior, encode it
here and put the reasoning in prose.

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

5. The gate refuses to run with too few rows (default 8 total, 5 scored
   val rows; both configurable in `held_out.json`). Otherwise it scores
   the val rows under both policy blocks and accepts only if the mean
   improves AND the bootstrap 90% interval of the improvement is above
   zero. On accept it replaces `best_skill.md` atomically and writes a
   receipt with before/after means, the interval, and both file hashes.
   On reject it books the receipt and appends to `rejected_edits.md`.
6. Rejecting an edit without proposing one is fine too:

```bash
python3 skillopt/sleep_cycle.py gate reject \
  --summary "val did not improve" --edit "tried: always post 3-line originals"
```

## Prove it before it goes live

Replay two skill versions against held-out rows, any time:

```bash
python3 skillopt/sleep_cycle.py replay --skill-a skillopt/best_skill.md --skill-b skillopt/proposed.md
```

Reports per-split means, delta, CI, and a verdict. Same math as the gate;
nothing is adopted.

## Why the controls exist

- **Bounded edits (lr=4):** a textual learning rate. Stops the bot from
  rewriting the whole doctrine every night.
- **Bootstrap gate:** reflection without a test set is fanfic; a val mean
  alone at n=20 is noise. The CI rule rejects edits whose gain is
  indistinguishable from zero. It does not prove causality (see
  docs/analysis/RESEARCH.md).
- **Min rows:** a gate over 5 rows is a coin flip with extra steps.
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
