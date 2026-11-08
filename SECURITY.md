# Security policy

## Reporting

Use GitHub's "Report a vulnerability" on this repository (Security tab ->
Advisories). That keeps details private. Do not open a public issue for a
security report.

## Scope

- The two Typefully helper scripts and `skillopt/sleep_cycle.py`: input
  validation, credential handling, injection through JSON payloads.
- Anything that could leak operator data (handles, URLs, metrics) into the
  public repo.

## Out of scope

- X/Twitter or Typefully's own infrastructure.
- The kit's growth advice ("this got me views") - not a security claim.

## Handling secrets

`.env` is gitignored and must stay that way. If you pasted a real key into
an issue or commit, rotate it in Typefully immediately, then tell us so the
content can be removed from what we control (history cannot be rewritten).
