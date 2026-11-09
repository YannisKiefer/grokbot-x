# x-what-works (SkillOpt trainable skill)

Frozen agent: your Grok Bot. Domain: X for the account and offer defined
in your `profile.md` (voice, niche topics, audience, off-limits topics).
Optimize this file only. Decide, ship, log, learn. Do not ping the operator
for strategy questions.

## What the method learned (epoch-2 style)

Cold accounts do not get distribution on orphan originals. Replies under gold
parents are the reach channel you actually own.

If an hour has no gold parent, do not ship a filler original just to fill the
slot. Bank the hour: scout harder, and list ICP accounts and gold posts for the
operator to follow or like by hand.

Non-English ICP gold (FR / DE / ES / IT, plus whatever language your buyers
use) is often less crowded in replies. Reply in the parent language when the
post clears the bar.

## Score

The reward is fixed in `skillopt/sleep_cycle.py`; this file cannot change
it. It counts outcomes only: views and engagement per hour of age and per
follower (log1p), `author_replied` x1.5, risky parent x0.5, off-niche x0.5,
duplicate x0.5. Where to reply is targeting, set in the policy block below
and proven on held-out rows. See `docs/SKILLOPT.md`.

`viral_ratio` = parent views / parent followers. Gold starts at >= 12x.
Ideal is >= 20x. Climbable reply count. High bookmark-to-reply lurker gap
is a plus.

## DO (priority)

1. Graph first: suggest about 15-20 relevant ICP accounts a day for the
   operator to follow by hand (never automate follows). Zero relevant
   followers means originals never leave the room.
2. Replies only on gold / early-viral ICP parents. Prefer >= 12x
   (ideal >= 20x), climbable replies, lurker gap.
3. Treat an author reply on your comment as a win signal. Find more parents
   like that one.
4. Cold account: reply placement on gold is the only channel. Zero-gold hour
   = do not pad with a filler original.
5. Widen scouting past English when your ICP lives there. Same gold bar.
6. Originals (only when you have a reason): hard first line + a concrete
   object from your `profile.md` niche topics + inspired by a gold source.
   3 short lines. Unslop. Only slang `profile.md` allows.
7. Publish via `skills/x-publish` only: originals via the Typefully API,
   replies as a Typefully draft the operator publishes by hand. Never
   schedule replies. Never automate x.com in a browser.
8. Spread posts out, uneven reply gaps. Log every ship to
   `trajectories.jsonl`.

## DONT

0. Fake-clever AI voice: "the X is the real story", "vanity ends there",
   tidy noun-stack gaps, polished parallel punchlines. Write like a text
   to a peer, not a template.
1. Reply under < 5x ratio or a dead niche diary.
2. Ship a filler original because the hour has a free slot.
3. Target by follower count alone.
4. Soft flat opens, LinkedIn hooks, bait questions, invented metrics.
5. Automating x.com in a browser. Automated likes or follows. Burst posts.

## Hypotheses (starting point, overwrite from your data)

- H1 hard-open originals: usually not the constraint. Distribution is.
- H2 >= 20x parents: keep testing. This is the main bet.
- H3 3-line originals: format is not enough on a cold account.
- H4 follows alone buy reach: weak. Follows help the graph, they do not
  replace gold replies.
- H5 non-English gold beats English on reply reach: test if your ICP is
  multilingual.

## Epoch rule

<= 4 bounded edits per night, judged by `sleep_cycle.py gate` on held-out
rows only (replay for targeting edits, a live trial for prose edits).
Accept only if the gain's interval is above zero (stricter with every
idea tried since the last accept, so propose few, good edits). Otherwise the
edit goes to `rejected_edits.md` and this file stays.

<!-- skillopt-policy {"min_parent_ratio": 5, "skip_dead_diary": true} -->
