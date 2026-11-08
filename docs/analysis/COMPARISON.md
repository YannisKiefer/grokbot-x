# COMPARISON.md - grokbot-x vs the field (2026-11-08)

Nine projects profiled from their GitHub pages and READMEs (all checked
2026-11-08; full per-project notes in `_research_compare.md` working notes,
merged here). Categories scored 1-10, 10 best. "Cost" scores cheap-to-run
(10 = zero infra, no paid APIs). "Before" = grokbot-x at commit cade7d9,
"After" = this branch (glm/upgrade-1108).

## Score table

| Project | Setup | Docs | Loop rigor | Results | Safety | Privacy | Tests/CI | Quality | Extens. | Cost | Avg |
|---|---|---|---|---|---|---|---|---|---|---|---|
| grokbot-x (before) | 7 | 7 | 4 | 3 | 8 | 6 | 0 | 6 | 4 | 10 | 5.5 |
| grokbot-x (after) | 8 | 9 | 8 | 5 | 9 | 9 | 9 | 8 | 5 | 10 | 8.0 |
| microsoft/SkillOpt | 6 | 9 | 10 | 10 | 8 | 8 | 9 | 9 | 9 | 6 | 8.4 |
| stanfordnlp/dspy | 6 | 8 | 9 | 8 | 8 | 8 | 8 | 8 | 9 | 6 | 7.8 |
| gepa-ai/gepa | 7 | 8 | 9 | 9 | 8 | 7 | 7 | 8 | 8 | 6 | 7.7 |
| elizaos/eliza | 4 | 7 | 3 | 2 | 3 | 6 | 8 | 6 | 10 | 4 | 5.3 |
| gitroomhq/postiz-app | 5 | 9 | 1 | 6 | 8 | 8 | 8 | 7 | 7 | 5 | 6.4 |
| langchain-ai/social-media-agent | 3 | 8 | 2 | 2 | 7 | 4 | 5 | 6 | 6 | 3 | 4.6 |
| gkamradt/twitter-reply-bot | 5 | 3 | 1 | 1 | 4 | 6 | 1 | 3 | 2 | 5 | 3.1 |
| nirholas/XActions | 7 | 8 | 1 | 3 | 1 | 7 | 7 | 7 | 8 | 9 | 5.8 |
| tr4m0ryp/x-bot | 3 | 7 | 2 | 2 | 2 | 5 | 4 | 5 | 3 | 8 | 4.1 |

Score rationale highlights (details per project in the working notes):

- **Setup**: no pip install, no Docker, three env vars, one OAuth connect.
  XActions needs your session cookies; eliza needs pinned Bun/Node; postiz
  needs Postgres+Redis; langchain-ai needs 4+ SaaS keys.
- **Loop rigor**: only SkillOpt/dspy/gepa have real held-out gates. Every
  X-specific project has none; the closest twin (tr4m0ryp/x-bot) states in
  its own limitations that there is no engagement feedback loop.
- **Safety**: XActions runs Puppeteer against x.com (its own README warns of
  bans); x-bot scrapes with twikit; eliza targets full autonomy with no
  approval gate. grokbot-x: official API + human click on every reply.
- **Cost**: the X projects that use the official API still need a paid X API
  tier or OAuth client setup; grokbot-x needs only Typefully (free tier
  works, draft-only when capped).

## Where grokbot-x is not the best, and the smallest change that fixes it

1. **Loop rigor (8 vs SkillOpt 10).** SkillOpt has a 52-cell benchmark
   harness; nobody should out-harness Microsoft at their own game, and a
   social kit cannot - its metric is noisy and delayed. Smallest change that
   makes it best *in its own niche*: the Phase 5 verifiable gate + offline
   replay eval make grokbot-x the only X-domain kit that can prove or reject
   a skill edit at all. Done in this branch.
2. **Measurable results (5 vs SkillOpt 10, gepa 9, postiz 6).** The others
   publish benchmark or analytics numbers; grokbot-x publishes none and its
   README honestly says so. Smallest change: make the replay eval a tested,
   runnable command with published example-data results (done, Phase 5) and
   a README line stating the proven claim precisely (Phase 6). Real user
   numbers take months and cannot be faked.
3. **Docs (9 vs SkillOpt 9).** Tie at top; SkillOpt wins on rendered docs
   site. Smallest change to break the tie for this audience: a demo GIF at
   the top (Phase 7 ships the script), quickstart that works on a clean
   machine (Phase 6, verified by running it).
4. **Tests/CI (9 vs SkillOpt 9).** Tie after this branch (full pytest suite
   + ruff CI). Nothing further needed; a coverage badge would add noise.
5. **Extensibility (5 vs eliza 10, dspy 9).** Deliberately not chased. A
   plugin system is the opposite of "dumbed down on purpose". The honest
   extension points are: edit skills/*.md, add a script, or wire your own
   optimizer into the `gate` command. Documented in Phase 6 instead of
   adding a framework.
6. **Setup (8 vs XActions 7).** Best in class after Phase 6 verifies the
   quickstart on a fresh clone.

## Verdict

grokbot-x was a well-written kit with a missing spine: the learning loop it
marketed was unenforced (rigor 4) and untested (0). After this branch it is
the only project in its category with a verifiable, replayable,
platform-rules-compliant learning loop, at zero running cost - which is the
niche the README promises. SkillOpt remains the better optimizer library;
they are not competitors, one is a method, the other is an application
domain with a publish lane and human approval.
