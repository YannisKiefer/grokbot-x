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

1. Read `skillopt/best_skill.md` BEFORE drafting.
2. Ship via the locked Typefully paths in `docs/PUBLISH.md`.
3. Log it: `python3 skillopt/sleep_cycle.py append --json '{...}'` with id,
   ts, type, url, text, features (viral_ratio, viral_signal, topic,
   author_followers, source), metrics placeholder, split (train|val
   ~80/20), notes. During a live trial of `skillopt/proposed.md`, add
   `--skill skillopt/proposed.md` and use split val.
4. Refresh metrics later at +1h / +6h / +24h / next night
   (`views` / `likes` / `replies` / `bookmarks`).

## Nightly sleep (reflect -> edit -> gate)

1. Refresh metrics on posts older than 1h (read-only).
2. `python3 skillopt/sleep_cycle.py status`
3. If n < `min_trajectories_before_edit`: log an epoch skip. Do not edit.
4. Else: write <= 4 bounded add/delete/replace edits into a copy,
   `skillopt/proposed.md`, from train successes vs failures +
   `rejected_edits.md`. Targeting rules go in the skillopt-policy block.
5. GATE: `python3 skillopt/sleep_cycle.py gate accept --summary "..."
   --edit "..." --skill skillopt/proposed.md`. The gate decides on held-out
   rows (live trial if logged, else replay) and adopts only if the gain's
   90% interval is above zero. Prose-only edits need a live trial first.
   Never edit `best_skill.md` by hand.
6. Mirror accepted rules into the next day's hourly behavior.
7. Stay quiet unless a skill edit was accepted (one line) or a hard blocker.

## Score

Fixed in `skillopt/sleep_cycle.py`; see `docs/SKILLOPT.md`. Cold account: relative scores matter more than absolute
views until you have a real ICP graph.

## Reference

https://github.com/microsoft/SkillOpt
Rollout, reflect, bounded edits, held-out gate, rejected buffer, slow update.
