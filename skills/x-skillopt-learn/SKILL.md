---
name: X SkillOpt learn
description: >-
  use this when running the X SkillOpt learn loop: log every post trajectory,
  refresh metrics, and nightly gated-edit best_skill.md so the bot only
  doubles down on what works
---
# X SkillOpt learn loop

Use this whenever shipping X posts/replies for the operator, and on the
nightly sleep routine. Treat `skillopt/best_skill.md` as the trainable skill
(Microsoft SkillOpt method adapted to X).

## Decide, then ship

Do not ask the operator for strategy permission. Report live URLs or real
blockers only. No "want me to" questions.

## After EVERY ship (rollout)

1. Read `skillopt/best_skill.md` BEFORE drafting (during a live trial on a
   trial day: `skillopt/proposed.md`).
2. Ship via the locked Typefully paths in `docs/PUBLISH.md`.
3. Log it: `python3 skillopt/sleep_cycle.py append --json '{...}'` with id,
   ts, type, url, text, features (viral_ratio, viral_signal, topic,
   author_followers = YOUR own follower count now, source), metrics
   placeholder, split (train|val ~80/20), notes. Features are frozen at
   ship time; later refreshes touch `metrics` only. On a trial day, add
   `--skill skillopt/proposed.md` and use split val.
4. Refresh metrics later at +1h / +6h / +24h / next night
   (`views` / `likes` / `replies` / `bookmarks`).

## Nightly sleep (reflect -> edit -> gate)

1. Refresh metrics on posts older than 1h (read-only).
2. `python3 skillopt/sleep_cycle.py status`
3. If `ready_for_edit` is false (scored rows < `min_trajectories_before_edit`):
   log an epoch skip. Do not edit.
4. Else: write <= 4 bounded add/delete/replace edits into a copy,
   `skillopt/proposed.md`, from train successes vs failures +
   `rejected_edits.md`. Targeting rules go in the skillopt-policy block.
5. GATE: `python3 skillopt/sleep_cycle.py gate accept --summary "..."
   --edit "..." --skill skillopt/proposed.md`. The gate decides on held-out
   rows (live trial if logged, else replay) and adopts only if the gain's
   interval is above zero. Every distinct proposal tried (gate or replay)
   since the last accept raises the bar, so try few, well-reasoned edits.
   Prose-only edits need a live trial first.
   Never edit `best_skill.md` by hand.

## Live trial (prose edits)

1. Start: copy `best_skill.md` to `skillopt/proposed.md` and edit it.
2. Alternate days: odd days draft from `proposed.md` and log with
   `--skill skillopt/proposed.md`; even days draft from `best_skill.md`
   and log normally. All trial rows use split val.
3. Stop: once both sides have >= `min_val_rows` scored rows, run the gate
   with `--skill skillopt/proposed.md`. Accepted or not, the trial ends.
6. Mirror accepted rules into the next day's hourly behavior.
7. Stay quiet unless a skill edit was accepted (one line) or a hard blocker.

## Score

Fixed in `skillopt/sleep_cycle.py`; see `docs/SKILLOPT.md`. Cold account: relative scores matter more than absolute
views until you have a real ICP graph.

## Reference

https://github.com/microsoft/SkillOpt
Rollout, reflect, bounded edits, held-out gate, rejected buffer, slow update.
