# SkillOpt for X

This kit treats `skillopt/best_skill.md` as the trainable state of a
frozen Grok Bot. That is the [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt)
idea, pointed at tweets instead of office tasks.

You do not fine-tune a model. You edit one markdown file. Slowly.
Only when a held-out score says the edit is better.

## Loop

```
ship -> log trajectory -> later fill metrics
night: harvest -> score train vs val -> propose <= 4 edits -> gate
  accept -> best_skill.md
  reject -> rejected_edits.md
```

## Files

| File | Role |
|---|---|
| `skillopt/best_skill.md` | deployed skill. The bot follows this tomorrow. |
| `skillopt/trajectories.jsonl` | one line per ship. Your real data. Gitignored. |
| `examples/trajectories.example.jsonl` | fake rows so you can see the shape. |
| `skillopt/held_out.json` | val ids + `learning_rate_max_edits` (4) + min n. |
| `skillopt/rejected_edits.md` | negative buffer. Do not retry these. |
| `skillopt/epochs/` | accept/reject receipts. |
| `skillopt/sleep_cycle.py` | score, status, append, gate bookkeeping. |

## Score (what "better" means)

`sleep_cycle.py` rescores every row:

- `log1p(views) + 0.75 * log1p(likes+replies+bookmarks)`
- reply on a >= 20x parent: x1.35
- reply on a >= 12x parent: x1.15
- author replied: x1.5
- hard open: x1.1
- dead diary: x0.4
- reply on < 5x parent: x0.7
- then divide by 10

Latest metrics bucket wins: `t_night` > `t24h` > `t6h` > `t1h`.

Cold account: relative rank matters more than the raw view count.
A gold reply that earns an author reply should beat a 5-view original
every time.

## Nightly gate

1. Refresh metrics on anything older than an hour.
2. `python3 skillopt/sleep_cycle.py status`
3. If `n` < `min_trajectories_before_edit` (default 8): skip. No edit.
4. Reflect on train rows only. Propose at most 4 bounded
   add / delete / replace edits.
5. Mentally (or actually) apply them to a copy. Recompute **val** mean.
6. Adopt only if val mean **strictly** improves. Else:

```bash
python3 skillopt/sleep_cycle.py gate reject \
  --summary "val did not improve" \
  --edit "tried: always post 3-line originals"
```

7. If it did improve:

```bash
python3 skillopt/sleep_cycle.py gate accept \
  --summary "replies-only on >=12x, bank zero-gold hours" \
  --edit "DO: no filler originals in empty hours"
```

Then write those edits into `best_skill.md`.

## Why the controls exist

- **Bounded edits (lr=4):** a textual learning rate. Stops the bot from
  rewriting the whole doctrine every night.
- **Held-out gate:** reflection without a test set is fanfic.
- **Rejected buffer:** the optimizer (you, or the bot) sees what already
  failed, so it does not loop.

Read the SkillOpt paper / repo if you want the general method. This
folder is the X adaptation only.

## Start from the example

```bash
cp examples/trajectories.example.jsonl skillopt/trajectories.jsonl
cp skillopt/held_out.example.json skillopt/held_out.json
python3 skillopt/sleep_cycle.py status
```

Those rows are fake. Replace them with your ships before you trust a gate.
