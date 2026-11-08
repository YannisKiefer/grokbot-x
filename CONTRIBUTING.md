# Contributing

Short version: small diffs, tests prove behavior, no secrets ever.

## Setup

```bash
python3 -m pip install ruff pytest
ruff check .
pytest
```

No runtime dependencies. If your change needs one, it is probably too big.

## Rules

1. Never commit real keys, tokens, handles, URLs, or trajectory data.
   Use `YOUR_*` placeholders and the fake rows in `examples/`.
2. Platform guardrails are load-bearing: official API clients only, no
   bot-browser compose on x.com, a human approves every reply, no bulk or
   unsolicited automated replies. PRs that weaken these will be rejected.
   The AI-disclosure setting stays the operator's choice.
3. Every bug fix ships with a test that fails on the old code.
4. Keep it simple: smallest change that fully solves the problem, delete
   before you add, no new dependency for a few lines.
5. `docs/analysis/*.md` are working documents - update, don't canonize.

## Commits

Small, imperative subject lines ("Fix gate row check", not "updates").
