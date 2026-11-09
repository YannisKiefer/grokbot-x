# Changelog

## Unreleased - 2026-11-09

### Changed
- The kit is niche-agnostic. One profile drives everything: copy
  `profile.example.md` to `profile.md` (gitignored) and fill it; skills,
  docs, prompts and the starter skill read niche, audience, topics and
  voice from there instead of assuming an ecommerce niche.
- `docs/BRAND-BIBLE.template.md` rewritten as a short generic worksheet
  (questions only, no positioning).
- Example trajectories and scorer examples are niche-neutral; three
  clearly fictional example profiles (indie SaaS, fitness coach,
  ecommerce brand) live under `examples/profiles/`.
- `held_out.example.json` tells you to copy `niche_topics` from
  `profile.md`. Scorer/gate math unchanged.

### Added
- `tests/test_generic.py`: guard test that fails on real company/person
  mentions outside the branding surfaces (README, site and docs/brand
  keep their existing owner-approved branding) and on ecommerce
  vocabulary outside `examples/profiles/`, with a small reasoned
  allowlist.

## 2026-11-08

### Changed

### Changed
- Reward is now verifiable and fixed in code (RLVR-style): view velocity
  (views normalized by follower count and post age) plus weighted
  engagement, with niche, risky-parent and near-duplicate guards. Skill
  files can no longer change their own reward.
- Skill files carry a targeting policy (`min_parent_ratio`,
  `skip_dead_diary`, `skip_risky_parents`, `topics`) instead of scoring
  knobs.
- The nightly gate computes the decision itself on held-out rows only:
  live trial (rows stamped with the proposal's hash via `append --skill`)
  or off-policy replay with a coverage guard; accept only when the
  bootstrap interval of the gain is above zero. Receipts go to
  `skillopt/epochs/`, with a copy of the replaced skill.
- Each look at the val rows since the last accept (a new proposal, or
  the same one after the val data changed) raises the gate's interval
  level (alpha spending), so many tries or nightly re-runs cannot find a
  lucky winner; `status` lists top rows from train only; trials compare against current-skill rows
  from the same time window; small-sample interval correction;
  `min_val_rows` >= 5; `learning_rate_max_edits` is enforced; rejected
  edits record their verdict.
- New offline replay eval: `python3 skillopt/sleep_cycle.py replay --skill-a A --skill-b B`
  reports which targeting rule wins on held-out rows before anything goes live.
- `made_with_ai` is the operator's choice (`X_MADE_WITH_AI` env, default off).
- Publish skill renamed `x-publish`; likes, bookmarks and follows are the
  operator's own clicks, never automated (X automation rules).
- Every trust boundary validates input: trajectory lines, append JSON,
  publish text length, reply-to URL, env placeholders - clear errors,
  no raw tracebacks.

### Fixed
- `--root` now works after the subcommand (`status --root DIR`).
- One bad line no longer kills the whole trajectory file read.
- `status` no longer rewrites the trajectory log in place.
- Publish poll timeout no longer reports failure while the post is still
  publishing; network errors are handled, not tracebacks.

### Added
- pytest suite (parsing, scoring, gate, replay, mocked Typefully publish),
  ruff config, CI workflow (Python 3.10/3.14), CONTRIBUTING, SECURITY,
  issue/PR templates, changelog, README quickstart rewrite.

## 2026-08 - initial public release

Docs-first kit: scout, draft, publish via Typefully, log trajectories,
nightly SkillOpt gate, five Grok Bot skills.
