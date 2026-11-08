# PRIVACY.md - scan results (2026-11-08)

Scope: full working tree plus all reachable git history
(`git log -p --all`, 6 commits incl. one on
`origin/cursor/github-discovery-metadata-3e0b`), gitleaks (installed,
scanned all commits: "no leaks found"), plus targeted greps for keys,
tokens, emails, phone numbers, real handles, social set IDs, Typefully
IDs, real names, private URLs, internal paths.

## Findings

### 1. Owner-only items

Two non-secret items need a decision by the repo owner (commit author
metadata settings, and how much product positioning the brand-bible
template should carry). They were reported to the owner privately and
are deliberately not detailed in this public file.

### 2. Clean otherwise

- gitleaks: no leaks across all commits.
- No `/Users/...` paths, no server names, no private URLs in any commit.
- No keys or tokens anywhere (`.env.example` holds only placeholders; the
  `YOUR_` placeholder convention is used consistently).
- Example data (`examples/trajectories.example.jsonl`) uses fake handles
  (`yourhandle`, `example_ops`, `example_diary`, `example_founder_fr`),
  fake IDs, and marks every row "FAKE example".
- No real names in file content.
- No phone numbers (one grep false positive on a commit hash).
- `skillopt/trajectories.jsonl`, `held_out.json`, `epochs/*.json` are
  gitignored so real operator data cannot be committed by accident.

## Repo hygiene added in this branch

- `CONTRIBUTING.md` - how to run tests/lint, PR rules (placeholders only,
  no secrets, platform-rules guardrails).
- `SECURITY.md` - private disclosure via GitHub Security Advisories.
- `.github/ISSUE_TEMPLATE/bug_report.md`, `feature_request.md`,
  `.github/PULL_REQUEST_TEMPLATE.md` - short forms.
- `CHANGELOG.md` - Keep-a-Changelog format, starts at this release.
- `pyproject.toml` - ruff + pytest config (no packaging, stdlib only).
- `.github/workflows/ci.yml` - ruff + pytest on push and PR, Python
  3.10 and 3.14.
- README: CI + license badges.
- `.gitignore`: adds `growth/` (local growth analysis, deliberately not
  published) and `.gitleaks.toml` exceptions if ever needed.
