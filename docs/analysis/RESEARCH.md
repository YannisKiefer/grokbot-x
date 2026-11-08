# RESEARCH.md - paper-level background for the nightly gate rework (2026-11-08)

One section per topic: canonical link, takeaway, and keep/change/add for this repo.
All numbers quoted were checked against the linked sources by three research passes.
The "Adopted in this branch" list at the end maps findings to the Phase 5 code.

## Prompt-optimization family

Seven methods that share this repo's loop shape: run, score, reflect in text, edit
text, gate on held-out data.

### 1. SkillOpt (microsoft/SkillOpt)

Canonical: https://github.com/microsoft/skillopt ; paper: https://arxiv.org/abs/2605.23904 (as linked from the repo README; project page https://microsoft.github.io/SkillOpt).

A text-space optimizer that treats a Markdown skill document as the trainable state
of a frozen LLM agent. Scored rollouts (trajectories) are converted by an optimizer
model into bounded add/delete/replace edits on a single skill doc, run like training
with epochs, mini-batches, and a textual learning-rate budget. A candidate edit is
accepted only when it strictly improves a held-out validation score; a buffer of
rejected edits plus a slow meta-update stabilize the loop. Output is a compact
best_skill.md (~300-2,000 tokens) adding zero inference-time model calls. The repo
reports best or tied-best results across 52 (model, benchmark, harness) cells over
six benchmarks and seven models, with ~20-25 point gains on strong models;
repo-reported numbers on QA-style benchmarks, not social growth. Limitation: it
needs a steady stream of scored trajectories and a clean numeric gate, and its
validation setups are far less noisy than engagement metrics.

For grokbot-x: keep - the repo already re-implements the paper-style path (single
md skill, bounded nightly edits, strict held-out gate, no auto-posting). Add the
one missing mechanism this branch adds for real: a rejected-edit buffer that logs
each rejected edit with its validation delta. The existing rejected_edits.md
becomes part of the receipts, not an honor-system file.

### 2. OPRO (Yang et al., 2023)

Canonical: https://arxiv.org/abs/2309.03409 ; code: https://github.com/google-deepmind/opro.

Optimization by PROmpting: the LLM itself is the optimizer. A meta-prompt contains
the task description plus an optimization trajectory of past candidates annotated
with scores, and the model proposes a new candidate told to balance exploration and
exploitation. Beats human prompts by up to 8% on GSM8K; also works on numeric
tasks. Limitation: a pure hill-climb over scored candidates with no held-out gate,
so it can oscillate or overfit the metric; each step costs many scored evaluations.

For grokbot-x: keep the trajectory-in-the-prompt idea. Change (docs-only, Phase 6):
make the nightly operator prompt an OPRO-style meta-prompt by appending a short
score history - last accepted edits with their val deltas plus the rejected buffer.
No code needed beyond formatting what `status` already prints.

### 3. DSPy / MIPROv2 (stanfordnlp/dspy)

Canonical: https://github.com/stanfordnlp/dspy ; paper: arXiv:2406.11695 (Opsahl-Ong et al., 2024).

DSPy compiles declarative multi-stage LM programs. MIPROv2 jointly searches
instructions and few-shot demonstrations: it bootstraps demos by running the
program on training inputs and keeping passing traces, proposes candidate
instructions grounded in dataset summaries, and uses a Bayesian surrogate over the
joint (instruction, demo) space to pick the next configuration to evaluate, scored
on held-out data. Limitation: needs a programmatic metric, many rollouts, and a
fixed pipeline; the surrogate assumes scores smooth enough to model, which noisy
engagement metrics are not.

For grokbot-x: keep the bootstrap-demos idea as an allowed edit class (Phase 6
docs): when val has plateaued, swap the worked examples inside best_skill.md for
the 2-3 highest-scoring recent posts pulled from trajectories. No dependency.

### 4. GEPA (arXiv 2507.19457)

Canonical: https://arxiv.org/abs/2507.19457 ; code: https://github.com/gepa-ai/gepa.

Reflective prompt evolution: sample execution trajectories, use an LLM to reflect
on them in natural language, evolve the instruction text. Maintains a Pareto
frontier of non-dominated candidates and merges complementary lessons from
frontier members. Reports beating GRPO by ~6% on average (up to 20%) using up to
35x fewer rollouts, and MIPROv2 by 10%+. Limitation: reflection quality depends on
a strong reflector and rich textual feedback; a growing frontier multiplies stored
candidates.

For grokbot-x: keep the strict acceptance rule. The Pareto idea shrinks to: don't
optimize a single global mean only - the Phase 5 scorer reports per-type (reply vs
original) means alongside the global one, and the receipt logs both, so an edit
that trades replies for originals is visible instead of hidden. That is the
smallest honest two-slot frontier.

### 5. TextGrad (zou-group/textgrad)

Canonical: https://github.com/zou-group/textgrad ; paper: https://arxiv.org/abs/2406.07496.

Automatic "differentiation" via text: build a DAG of LLM calls, let an LLM generate
natural-language critiques from an objective, apply the feedback to prompts or
solutions. Reports GPT-4o zero-shot GPQA 51% -> 55% and +20% relative on
LeetCode-Hard. Limitation: feedback is unbounded and iterative with no gate; each
step costs multiple strong-model calls; results depend on objective wording.

For grokbot-x: keep the critique-from-trajectories step (the nightly proposal).
Change: bound it - the skills already say "at most 4 bounded edits"; the Phase 5
gate now enforces a machine-checked count so the bound is real.

### 6. Reflexion (noahshinn/reflexion)

Canonical: https://arxiv.org/abs/2303.11366 ; code: https://github.com/noahshinn/reflexion.

Verbal RL: Actor tries, Evaluator scores, Self-Reflection writes a short lesson;
lessons are stored in an episodic buffer and prepended to the next attempt - no
weight updates. 91% pass@1 on HumanEval vs the 80% GPT-4 baseline of its time.
Limitation: per-task short-lived memory; self-reflection can invent causes when
feedback is sparse.

For grokbot-x: the nightly proposal already is the reflection step. Add the
smallest durable-memory piece: the epoch receipts (accepted and rejected, with
deltas) ARE the lesson file, and rejected_edits.md stays the do-not-retry list.
Read-before-propose stays in the skill instructions.

### 7. Voyager (MineDojo/Voyager)

Canonical: https://arxiv.org/abs/2305.16291 ; code: https://github.com/MineDojo/Voyager.

Open-ended Minecraft agent: automatic curriculum, iterative prompting with
environment feedback and self-verification, ever-growing skill library of
executable code retrieved by embedding. 3.3x unique items, up to 15.3x faster
tech-tree milestones vs prior SOTA. Limitation: skills are code with hard
executable verification; social posts have no such oracle until engagement days
later.

For grokbot-x: keep verify-before-storing - here the verification is the gate.
Change (Phase 6 docs): make trajectories retrievable by tagging rows with
`topic`/feature buckets they already carry, and have the nightly reflection pull
the top rows per bucket instead of scanning the log. A code skill library is not
warranted for prose.

### Family synthesis

All seven are one loop: score trajectories, turn scores into textual feedback,
edit text, gate on held-out data. grokbot-x is closest to SkillOpt and should
treat it as the reference spec. The other papers contribute single small pieces:
score history in the proposal prompt (OPRO), example-swapping from passing
trajectories (DSPy), a two-slot per-bucket view (GEPA), bounded ranked critiques
(TextGrad), a persistent lesson line (Reflexion), bucket-tagged retrieval
(Voyager). Nothing argues for loosening the strict gate, the single-file skill, or
human-in-the-loop. None solves the hardest problem, a delayed noisy metric, so the
gate stays conservative.

## RLVR: Reinforcement Learning with Verifiable Rewards

Canonical: [DeepSeek-R1, arXiv 2501.12948](https://arxiv.org/abs/2501.12948) (also
Nature 645:633, 2025); [Tulu 3, arXiv 2411.15124](https://arxiv.org/abs/2411.15124).

A reward is "verifiable" when correctness is computed from ground truth or a
constraint by code, not judged by a learned reward model, so there is no learned
model to game. DeepSeek-R1-Zero uses exactly two rule-based rewards: accuracy (is
the boxed answer right, do the tests pass) and format (reasoning inside `<think>`
tags); the authors picked rules over a neural reward model because in large-scale
RL a neural reward model "may suffer from reward hacking". Result: 71.0% pass@1 on
AIME 2024 from pure RL without SFT. Tulu 3 runs RLVR as its final stage on domains
with checkable outcomes: math against ground truth, instruction following scored
by heuristics over the IFEval constraint categories (8B: GSM8K 84.3 -> 87.6,
IFEval 81.1 -> 82.4 between DPO and final). Honest limitation: Tulu 3's own
appendix B.4 is titled "RLVR IFEval overoptimization" - a verifiable reward
removes reward-model gaming but not benchmark gaming.

What "verifiable" means for social metrics: views, replies, bookmarks are
objective in the RLVR sense (X's own counters, read over the API), but the
counter-to-goal mapping is a proxy, and proxies under optimization pressure get
gamed (Goodhart). [Manheim and Garrabrant, arXiv 1803.04585] split Goodhart
failures into four variants; [Lilian Weng's Reward Hacking post, 2024]
(https://lilianweng.github.io/posts/2024-11-28-reward-hacking/) documents the LLM
versions: agents editing the tests, sycophancy, the CoastRunners boat looping for
points. Here viewbait (views without bookmarks), engagement bait, off-niche
virality and near-duplicate recycling are exactly adversarial Goodhart: counters
stay honest while the composite diverges from the goal. Penalties are also
proxies; they shift the game rather than end it.

For grokbot-x: keep scores derived only from X counters, never an LLM judging
"quality". Add (Phase 5): bookmark-weighted composite, near-duplicate penalty,
off-niche penalty (topic match to the brand bible), and a `score_version` field
stamped into every epoch receipt so the reward definition is pinned and auditable
when the formula changes.

## Multi-armed bandits and Thompson sampling

Canonical: [Chapelle and Li, An Empirical Evaluation of Thompson Sampling, NeurIPS
2011](https://papers.nips.cc/paper_files/paper/2011/hash/e53a0a2978c28872a4505bdb51ab0662-Abstract.html).
Note: arXiv 1209.3353 is Agrawal and Goyal's theory paper (first near-optimal
problem-independent regret bound for TS), not Chapelle-Li.

Beta/Bernoulli Thompson sampling in three sentences: keep a Beta(a, b) posterior
per arm; each decision draws one sample from every arm's posterior and plays the
highest; update the played arm (a += 1 success, b += 1 failure). Sampling from the
posterior means uncertain arms still get picked, so exploration is automatic and
fades with evidence. Chapelle-Li found TS matched or beat UCB1/Bayes-UCB/
epsilon-greedy on Yahoo click data at tiny sample sizes. It fits "best posting
hour" and "best topic": each slot yields one Bernoulli-like observation (score
above the account median or not), the update is two integer increments. Honest
limitation: the analysis assumes stationary arms; X ranking shifts, follower
growth and content drift make arms non-stationary, so posteriors need decay or a
reset window.

For grokbot-x: keep the nightly gate untouched - a bandit chooses what to post,
never evaluates edits. Not added in this branch (smallest-change discipline);
documented as the follow-up: a stdlib `bandits.json` with Beta counts per
(hour, topic), updated on each logged post, surfaced as a suggestion in `status`.

## Statistics for small noisy samples

Canonical: [Efron 1979, Bootstrap Methods](https://projecteuclid.org/journals/annals-of-statistics/volume-7/issue-1/Bootstrap-Methods-Another-Look-at-the-Jackknife/10.1214/aos/1176344552.full);
[scipy.stats.bootstrap docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html);
[Bland and Altman, Regression towards the mean, BMJ 1994;308:1499](https://www.bmj.com/content/308/6942/1499);
[Evan Miller, How Not To Run An A/B Test](https://www.evanmiller.org/how-not-to-run-an-ab-test.html).

The bootstrap approximates the sampling distribution of a statistic by resampling
observed rows with replacement ~10,000 times and reading quantiles. Percentile
takes raw quantiles of resampled means; BCa corrects for bias/skew but can emit
NaN on degenerate resamples (small n), so plain percentile is the safer gate
primitive here. Sample-size intuition: at 80% power and alpha 0.05, comparing two
means needs roughly n = 16 sigma^2 / delta^2 rows per side - at n = 20 the
smallest detectable lift is ~0.9 standard deviations; typical skill-edit gains are
far below that. Regression to the mean (Bland-Altman: it "occurs unless r = 1, so
it always occurs in practice"; Kahneman's flight instructors): an edit made right
after a bad epoch inherits credit for the rebound. Why "strictly improves" alone
is meaningless at n = 20: noise flips the sign of small differences often; a 90%
CI > 0 rule bounds false accepts at 10% per epoch, but gating nightly, 1 - 0.9^20
~ 88% of truly-null sequences show a false accept within twenty epochs - the
peeking problem Miller describes. The CI rule also assumes exchangeable,
stationary rows; platform drift moves the val mean between epochs with no edit.

For grokbot-x (Phase 5 implements exactly this): keep the held-out val split
frozen across epochs so deltas compare like with like. Replace "val mean strictly
improves" with "bootstrap 90% percentile CI of the val-score delta has its lower
bound above zero", computed with a seeded stdlib bootstrap over paired per-row
deltas, minimum row floor enforced, both bounds logged in the receipt. And the
repo must not pretend a pass proves causality - see the last synthesis line.

## X platform: ranking signals and rules

### Ranking signals in the open-sourced algorithm

Canonical: https://github.com/twitter/the-algorithm (ML models incl. Heavy Ranker:
https://github.com/twitter/the-algorithm-ml). Write-ups:
https://solomonmg.github.io/post/twitter-the-algorithm/ and
https://github.com/igorbrigadir/awesome-twitter-algo.

The For You pipeline generates candidates, scores them, then applies heuristics.
Roughly half the ranked pool (~1,500 tweets/day/user) is in-network; the rest is
out-of-network via retrieval over engagement graphs - engagement on a post is
itself a candidate source. The Heavy Ranker predicts per-action probabilities and
sums weighted probabilities; community-annotated weights from the 2023 release:
like 0.5, repost 1.0, profile click ~12, reply 13.5-27, reply answered by the
author 75 - conversation actions outrank likes by ~20-150x. Negative feedback
dominates: block/mute ~ -74, report ~ -369. Author diversity discounts repeats
(~50% with a floor). Replies are ranked through the same scoring, which is why a
reply can be served to non-followers.

Is "viral ratio = parent views / parent followers" a reasonable proxy? Moderately.
Views far above follower count imply non-follower impressions (in-network supply
is bounded by followers), so the ratio is a proxy for how far a post escaped the
follow graph - and a reply under it reaches non-followers. Caveats: it conflates
recency, embed traffic, repeat views, and follower-growth timing; X documents none
of it. Treat it as a scout filter, not an official signal.

For grokbot-x: keep the gold filter. Change (Phase 5): the scorer's reply bonus
(already x1.35/x1.15 on 20x/12x parents) is directionally right per these weights;
add the author-reply x1.5 it already has is consistent with the "reply answered by
author = 75" signal. Bookmarks get extra weight (hardest to bait).

### Automation rules and Developer Agreement

Canonical: https://help.x.com/en/rules-and-policies/x-automation and
https://docs.x.com/developer-terms/policy.

The rules define automation as "accounts or apps that take repeated actions
without a person actively performing them." Key language: "Use non-API-based forms
of automation, such as scripting the X website. The use of these techniques may
result in the permanent suspension of your account." Duplicates: "You may not post
duplicative or substantially similar posts on one account or over multiple
accounts you operate." Unsolicited automated replies are an abuse ("sending
automated replies to posts based on keyword searches alone is not permitted");
automated replies are only allowed to opted-in recipients. And: "the deployment or
operation of any AI reply bot requires prior written and explicit approval from
X." The Developer Policy requires bot accounts to disclose that they are bots.

Nuance: no clause says "human review for each action" - but a human-approved
action is by definition not taken "without a person actively performing" it, so
the human-approved queue is what keeps this kit outside the "AI reply bot"
category. That is the compliance load wall: every reply goes through a human
clicking Publish NOW; auto-like/auto-follow stay out of scope entirely; the
duplicate-content penalty is not just reward hacking, it is a rule.

### "Made with AI" labels

Canonical: https://help.x.com/en/rules-and-policies/media-literacy-plan and
https://help.x.com/en/business-and-advertising/brand-safety/industry-leadership-and-partnerships.

Officially, labels target media (images/video/audio) via composer self-disclosure
and automatic detection tied to C2PA provenance. Text-only posts are not
auto-labeled and no official rule requires disclosure of AI-assisted writing.
Crucially: no official X documentation says automated-browser compose gets
fingerprinted and auto-labeled. The repo's PUBLISH docs must mark that claim
community-reported (fixed in Phase 6). The documented, verifiable reason to stay
API-only is stronger anyway: scripting the X website risks permanent suspension
under the automation rules.

## Adopted in this branch (Phase 5 mapping)

1. Velocity normalization: views/hour divided by follower count, so account size
   and post age stop dominating the reward (fixes ANALYSIS B2).
2. Verifiable gate: min row floor, paired per-row deltas on frozen val rows,
   bootstrap 90% percentile CI lower bound above zero, `score_version` + before/
   after + interval in every receipt (fixes B1 for real).
3. Goodhart guards: near-duplicate penalty, off-niche penalty, bookmarks weighted
   above likes.
4. Docs changes (Phase 6): fingerprinting claim marked community-reported,
   scripting-suspension rule cited as the API-only rationale, disclosure framed as
   the operator's choice.
5. Deliberately NOT added: Thompson bandit (right idea, wrong branch), LLM-judge
   scores (breaks verifiability), Pareto frontier of skills (two-metric reporting
   instead), embedding skill library (no oracle for prose).

## What this repo must not pretend

A strictly better val mean at n = 20 does not prove the edit caused anything. It
is one noisy draw from a drifting platform. The bootstrap CI rule lowers false
accepts per epoch without eliminating them (and nightly peeking accumulates them);
it establishes nothing about causality. The honest claim: the gate rejects edits
whose improvement is indistinguishable from noise, which is the best a stdlib-only,
no-orm, human-in-the-loop kit can do - and better than what most comparable
projects do, which is nothing.
