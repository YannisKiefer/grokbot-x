# Changelog

## Unreleased - 2026-11-08

### Changed
- Reward is now verifiable (RLVR-style): score uses view velocity
  (views normalized by follower count and post age) plus replies and
  bookmarks; niche-match and near-duplicate penalties guard against
  reward hacking.
- The nightly gate now computes the decision itself: minimum row count,
  held-out mean improvement AND bootstrap 90% interval above zero,
  before/after logged to `skillopt/epochs/`.
- New offline replay eval: `python3 skillopt/sleep_cycle.py replay --skill-a A --skill-b B`
  reports which skill wins on held-out rows before anything goes live.
- `made_with_ai` is the operator's choice (`X_MADE_WITH_AI` env, default off).
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
