# Comparable open-source projects (research for COMPARISON.md)

All entries verified on their GitHub repo pages on 2026-11-08.

## microsoft/SkillOpt

- Name, URL, stars, language: microsoft/SkillOpt, https://github.com/microsoft/skillopt, about 18.9k stars, Python (checked 2026-11-08).
- What it does: a text-space optimizer that treats a skill document as the trainable state of a frozen LLM agent and accepts edits only when they strictly improve a held-out validation score.
- Setup to first output: pip install skillopt plus provider API keys (OpenAI, Azure, Claude, Qwen, MiniMax backends); optional Gradio WebUI on loopback; no Docker or cloud required.
- Docs: strong; versioned docs, rendered docs site, arXiv paper, changelog, guides for adding backends and benchmarks.
- Learning loop: true self-improvement with a held-out gate; rollout, reflect, aggregate, select, update, evaluate, with a rejected-edit buffer; SkillOpt-Sleep adds nightly offline evolution behind the same gate.
- Measurable results: best or tied-best on all 52 (model, benchmark, harness) cells across 6 benchmarks and 7 models; on GPT-5.5 about +23.5 points on direct chat; NeurIPS 2026 Spotlight.
- Safety and platform rules: no social platform interaction, no browser automation; WebUI loopback-only by default with optional auth.
- Privacy: keys via .env, local state, no telemetry noted.
- Tests and CI: tests directory and GitHub workflows present.
- Code quality: pip package, MIT, pyproject-based; WebUI extra uses Gradio; dependency count not enumerated on the page.
- Extensibility: custom chat backends (OpenAI-compatible), exec backends (Codex, Claude Code, Cursor, Copilot), new benchmark adapters.
- Running cost: paid LLM API calls for rollouts and the optimizer model.
- What it does 10x better: it is the direct ancestor of grokbot-x's gated nightly skill edits, with a multi-benchmark harness, published numbers, and heavy eval machinery.

## stanfordnlp/dspy

- Name, URL, stars, language: stanfordnlp/dspy, https://github.com/stanfordnlp/dspy, about 39k stars, Python (checked 2026-11-08).
- What it does: a framework for programming rather than prompting language models; optimizes prompts and weights for pipelines and agent loops.
- Setup to first output: pip install dspy plus provider API keys; quickstart lives on dspy.ai rather than the repo page.
- Docs: maintained docs site, migration guides for recent breaking LM changes; no quickstart in the README itself.
- Learning loop: explicit optimizer runs (GEPA and MIPROv2 lineage) over train and validation sets; not a runtime self-improvement loop.
- Measurable results: benchmark numbers live in the linked papers, not the README.
- Safety and platform rules: no platform interaction at all, no browser automation.
- Privacy: no telemetry mentioned in the README.
- Tests and CI: tests directory and GitHub Actions; 341 open issues, 431 open PRs.
- Code quality: MIT, large mature library; native lm15 engines bundled without a LiteLLM runtime dependency.
- Extensibility: compositional Python modules, custom LMs, large community ecosystem.
- Running cost: paid LLM APIs, mostly for optimization runs.
- What it does 10x better: a mature optimizer library; grokbot-x could borrow its GEPA optimizer instead of hand-rolling a skill editor.

## elizaos/eliza

- Name, URL, stars, language: elizaos/eliza, https://github.com/elizaos/eliza, about 19.8k stars, TypeScript (checked 2026-11-08).
- What it does: an open-source agentic operating system (runtime, app, CLI, cloud, plugins) for autonomous AI agents, with X support via its Twitter plugin.
- Setup to first output: git clone, bun install, bun run dev with pinned Bun and Node versions; dev:local mode runs without cloud sign-in; X posting needs X API v2 credentials.
- Docs: dedicated docs site with a per-package README rule; the docs Twitter guide targets the official plugin after the cookie-based agent-twitter-client was taken down in June 2025 following an X cease and desist, and X now effectively prices that style of access at about 5k dollars a month.
- Learning loop: memory, knowledge, and evaluators, but no documented gated self-improvement.
- Measurable results: none published.
- Safety and platform rules: built for full autonomy, no human approval gate; third-party plugin registry submissions are no longer accepted.
- Privacy: local-first runtime emphasized, optional Eliza Cloud; no telemetry notes in the README.
- Tests and CI: bun run verify, test, and test:e2e, plus a scenario runner and a Python benchmark suite.
- Code quality: MIT; heavy monorepo (Lerna, Turbo, patches directory, Biome).
- Extensibility: plugins register actions, providers, evaluators, services, model handlers, routes, and events.
- Running cost: paid LLM APIs plus the relevant X API tier.
- What it does 10x better: breadth (voice, wallets, messaging connectors); none of the trajectory logging and gated editing that grokbot-x centers on.

## gitroomhq/postiz-app

- Name, URL, stars, language: gitroomhq/postiz-app, https://github.com/gitroomhq/postiz-app, about 41.1k stars, TypeScript (checked 2026-11-08).
- What it does: open-source social media scheduling, automation, and analytics across about 14 platforms including X, with an AI copilot.
- Setup to first output: Docker, Coolify, Railway, or any VPS; self-host needs Postgres, Redis, storage, and env vars plus your own OAuth apps and LLM keys; a paid cloud exists.
- Docs: dedicated docs site, YouTube tutorials, public API docs, NodeJS SDK, N8N node.
- Learning loop: none; scheduling and analytics only, no eval framework.
- Measurable results: none published.
- Safety and platform rules: official platform OAuth apps, no browser automation; you manage your own developer app approvals.
- Privacy: states it does not collect, store, or proxy API keys or tokens; self-host can run air-gapped.
- Tests and CI: Jest, Sonar, Jenkins folder, GitHub Actions.
- Code quality: AGPL-3.0 plus CLA; heavy stack (Next.js, NestJS, Prisma, Temporal, Redis).
- Extensibility: fork and modify freely under AGPL; custom providers and integrations.
- Running cost: free self-host, paid cloud tiers; AI features need your own provider keys.
- What it does 10x better: mature multi-platform scheduling with a full UI, the surface grokbot-x deliberately replaces with the Typefully API and human approval.

## langchain-ai/social-media-agent

- Name, URL, stars, language: langchain-ai/social-media-agent, https://github.com/langchain-ai/social-media-agent, about 3k stars, TypeScript (checked 2026-11-08).
- What it does: an agent that takes a URL, curates it, drafts Twitter and LinkedIn posts, and schedules them with human-in-the-loop review.
- Setup to first output: clone, yarn install, .env with Anthropic, LangSmith, FireCrawl, and Arcade keys, then a LangGraph dev server; full mode adds Twitter and LinkedIn developer apps, Supabase, Vertex AI, and Slack.
- Docs: thorough quickstart and advanced setup, platform-by-platform auth guides, video tutorial, editable prompt variables.
- Learning loop: none; a memory-v2 experiment exists, no eval harness documented.
- Measurable results: none published.
- Safety and platform rules: official APIs via Arcade or your own OAuth apps; Agent Inbox for human review; no browser automation.
- Privacy: LangSmith tracing is on by default and its key is required even locally.
- Tests and CI: Jest configs and GitHub workflows, no badges shown.
- Code quality: MIT, LangGraph project template, four or more external SaaS dependencies to run at all.
- Extensibility: prompt-level business context, cron jobs, Slack ingestion.
- Running cost: at least four paid SaaS keys (Anthropic, LangSmith, FireCrawl, Arcade).
- What it does 10x better: a polished human-in-the-loop inbox that parallels grokbot-x's approval UI, at the cost of vendor lock-in.

## gepa-ai/gepa

- Name, URL, stars, language: gepa-ai/gepa, https://github.com/gepa-ai/gepa, about 7.3k stars, Python (checked 2026-11-08).
- What it does: optimizes any text parameter (prompts, code, configs) using LLM reflection plus Pareto-efficient evolutionary search on full execution traces.
- Setup to first output: pip install gepa plus LiteLLM-style provider keys; quickstart has a required valset separate from the trainset.
- Docs: dedicated site, quickstart, adapters guide, paper, blog, very long README with worked examples.
- Learning loop: true optimizer with held-out validation; candidates from the Pareto front are mutated and accepted only on improvement.
- Measurable results: GPT-4.1 Mini 46.6 to 56.6 percent on AIME 2025; claims 35x fewer rollouts than GRPO; Databricks and Nubank case numbers; 50+ production uses cited.
- Safety and platform rules: no platform interaction, no browser automation.
- Privacy: nothing mentioned.
- Tests and CI: tests directory and GitHub Actions, no visible badges.
- Code quality: MIT, modest dependency set with optional extras for confidence and LangChain.
- Extensibility: GEPAAdapter interface; built-in adapters for DSPy, MLflow, Opik, Pydantic AI, MCP, RAG stacks; ships as a Claude Code skill.
- Running cost: paid LLM APIs for task rollouts and the reflection model.
- What it does 10x better: an off-the-shelf reflective optimizer with a hard held-out gate that grokbot-x could plug a nightly loop into.

## gkamradt/twitter-reply-bot

- Name, URL, stars, language: gkamradt/twitter-reply-bot, https://github.com/gkamradt/twitter-reply-bot, about 67 stars, Python (checked 2026-11-08).
- What it does: a bot that auto replies to mentions using LLMs, demoed on the @SiliconOracle account.
- Setup to first output: create a bot account, get Twitter developer keys (basic or paid tier), optionally an Airtable token, deploy on Railway.
- Docs: hobby grade; deployment steps and a video, no architecture or test guidance.
- Learning loop: none.
- Measurable results: none.
- Safety and platform rules: official Twitter API; README suggests marking the account automated; no human approval gate.
- Privacy: Airtable logging is optional; nothing else documented.
- Tests and CI: none.
- Code quality: a single Python file with a requirements.txt, MIT, 11 commits, dormant since 2023.
- Extensibility: edit the file by hand.
- Running cost: a paid Twitter API tier plus an LLM API.
- What it does 10x better: nothing for grokbot-x; it shows the category baseline is a weekend script with no outcomes tracking, which strengthens grokbot-x's positioning.

## nirholas/XActions

- Name, URL, stars, language: nirholas/XActions, https://github.com/nirholas/XActions, about 648 stars, JavaScript (checked 2026-11-08).
- What it does: a Puppeteer-based X automation toolkit with scrapers, a 56-command CLI, browser console scripts, an extension, and an MCP server.
- Setup to first output: npm install xactions plus xactions quickstart and doctor; no X API key, it uses your x.com session auth_token and ct0 cookies; AI features need your own LLM keys.
- Docs: extensive tutorials, CLI and API references, llms.txt, and a docs:check CI job that fails on dead links.
- Learning loop: none; only snapshot diffs for unfollower detection.
- Measurable results: self-reported comparison tables only.
- Safety and platform rules: browser automation and GraphQL scraping on x.com; the README itself warns accounts may be restricted or banned and labels it educational use; this generally violates X terms.
- Privacy: claims everything runs locally with no telemetry.
- Tests and CI: Vitest offline suite, ESLint, CI on Node 22 and 24.
- Code quality: Apache-2.0, 547 commits, active through 2026, Node 22.19+ required.
- Extensibility: MCP server exposing about 152 tools to Claude, GPT, and Cursor.
- Running cost: free, plus optional LLM keys.
- What it does 10x better: raw reach into X data; for grokbot-x it is the counterexample that makes the official-API-only, human-approved stance a clear differentiator.

## tr4m0ryp/x-bot

- Name, URL, stars, language: tr4m0ryp/x-bot, https://github.com/tr4m0ryp/x-bot, 1 star, Python (checked 2026-11-08).
- What it does: autonomous reply drafting and posting for X; polls 84 target accounts and runs a 4-stage LLM pipeline (classifier, researcher, drafter, ranker) before posting or queueing.
- Setup to first output: pip install -e ".[dev]", .env with X_USERNAME and NVIDIA_API_KEY, sync Safari cookies, then x-bot track.
- Docs: unusually detailed for its size; architecture diagram, CLI and env tables, rubric, roadmap, limitations, disclaimer.
- Learning loop: none live; the ranker is calibrated once against a 229-reply historical corpus, and the limitations section admits there is no engagement feedback loop.
- Measurable results: corpus statistics only, no engagement outcomes.
- Safety and platform rules: unofficial twikit scraping on x.com with runtime patches for X's changed formats; optional AUTO_POST flag, or a queue-for-review mode.
- Privacy: all data local in SQLite plus cookies; cookie handling is the main sensitive area.
- Tests and CI: tests folder exists, no CI workflows shown.
- Code quality: Python 3.11+, small dependency set (twikit, OpenAI SDK, DuckDuckGo, Tenacity), license not shown on the page.
- Extensibility: config thresholds and target lists, no plugin surface.
- Running cost: free NVIDIA NIM tier plus an optional Moonshot fallback key.
- What it does 10x better: it is the closest architectural twin (scout accounts, score, draft, rank) but with no trajectory logging or gated skill edits, which is exactly grokbot-x's niche.
