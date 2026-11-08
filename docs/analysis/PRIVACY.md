# PRIVACY.md - scan results (2026-11-08)

Scope: full working tree plus all reachable git history
(`git log -p --all`, 6 commits incl. one on
`origin/cursor/github-discovery-metadata-3e0b`), gitleaks (installed,
scanned all commits: "no leaks found"), plus targeted greps for keys,
tokens, emails, phone numbers, real handles, social set IDs, Typefully
IDs, real names, private URLs, internal paths.

## Findings

### 1. Personal email in commit author metadata (history only)

The repo owner's personal Gmail address (redacted here on purpose; exact
address visible via `git log --format='%ae %an'`) is the author email on
commits `95584eb`, `65b11fa`, `9e51a92`, `cade7d9` (main line), in two
casings. Also present as `Co-authored-by` nowhere with the Gmail (those
use the GitHub noreply address).

- Exposure: anyone who clones the repo sees it.
- Fix without rewriting history (history rewrite is ruled out):
  1. GitHub -> Settings -> Emails: enable "Keep my email addresses
     private" and "Block command line pushes that expose my email".
  2. Local git config for this repo: `git config user.email
     "YannisKiefer@users.noreply.github.com"`.
- Nothing to rotate (an email cannot be revoked), but if the Gmail is
  used for password resets, treat the address as public from now on.

### 2. Strategy-level disclosure: docs/BRAND-BIBLE.template.md (user's call)

The "template" is a complete 25-section product doctrine for an
ecommerce-ops AI (category, enemy, specialist list, pricing structure,
objection handling, acquisition story) with `YOUR_*` placeholders. It
contains no secrets, IDs, or personal data, but it publishes the
operator's real product positioning in full. No action taken in this
branch; listed so the owner can decide whether to keep the depth,
shorten it to a fill-in skeleton, or genericize the category sections.

### 3. Clean otherwise

- gitleaks: no leaks across all commits.
- No `/Users/...` paths, no server names, no private URLs in any commit.
- No keys or tokens anywhere (`.env.example` holds only placeholders; the
  `YOUR_` placeholder convention is used consistently).
- Example data (`examples/trajectories.example.jsonl`) uses fake handles
  (`yourhandle`, `example_ops`, `example_diary`, `example_founder_fr`),
  fake IDs, and marks every row "FAKE example".
- No real names in file content (only commit metadata, finding 1).
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
