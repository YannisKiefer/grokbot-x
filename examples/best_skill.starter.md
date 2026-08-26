# Starter copy

Copy this file to `skillopt/best_skill.md` when you start a new account.
Then let the nightly SkillOpt gate edit THAT file, not this one.

# x-what-works (SkillOpt trainable skill)

Frozen agent: your Grok Bot. Domain: X for @YOUR_HANDLE / YOUR_PRODUCT.
Optimize this file only. Decide, ship, log, learn. Do not ping the operator
for strategy questions.

## What the method learned (epoch-2 style)

Cold accounts do not get distribution on orphan originals. Replies under gold
parents are the reach channel you actually own.

If an hour has no gold parent, do not ship a filler original just to fill the
slot. Bank the hour: follow ICP, like/bookmark gold, scout harder.

Non-English ICP gold (FR / DE / ES / IT, plus whatever language your buyers
use) is often less crowded in replies. Reply in the parent language when the
post clears the bar.

## Score

- Use the latest metrics bucket (`t_night` > `t24h` > `t6h` > `t1h`).
- Views log1p + engagement.
- Reply bonus if parent `viral_ratio` >= 12 (stronger >= 20).
- `author_replied` x1.5.
- Dead-diary x0.4.
- Parent ratio < 5 x0.7.
- Until you have a real ICP graph, parent quality + author engagement beat
  raw view chasing.

`viral_ratio` = parent views / parent followers. Gold starts at >= 12x.
Ideal is >= 20x. Climbable reply count. High bookmark-to-reply lurker gap
is a plus.

## DO (priority)

1. Follow graph first, human gaps, about 15-20/day. Zero relevant followers
   means originals never leave the room.
2. Replies only on gold / early-viral ICP parents. Prefer >= 12x
   (ideal >= 20x), climbable replies, lurker gap.
3. Treat an author reply on your comment as a win signal. Find more parents
   like that one.
4. Cold account: reply placement on gold is the only channel. Zero-gold hour
   = do not pad with a filler original.
5. Widen scouting past English when your ICP lives there. Same gold bar.
6. Originals (only when you have a reason): hard first line + concrete ops
   object + inspired by a gold source. 3 short lines. Unslop. `imo` is fine.
7. Typefully: originals via API with `made_with_ai` false. Replies as a
   Typefully draft, then Publish NOW in the Typefully UI. Never schedule
   replies. Never compose on x.com from a bot browser.
8. Anti-bot jitter 0-35 min. Uneven reply gaps. Log every ship to
   `trajectories.jsonl`.

## DONT

0. Fake-clever AI voice: "the X is the real story", "vanity ends there",
   tidy noun-stack gaps, polished parallel punchlines. Write like a text
   to a peer, not a template.
1. Reply under < 5x ratio or a dead niche diary.
2. Ship a filler original because the hour has a free slot.
3. Target by follower count alone.
4. Soft flat opens, LinkedIn hooks, bait questions, invented metrics.
5. Bot-browser compose/reply on x.com. Burst posts. Burst follows.

## Hypotheses (starting point, overwrite from your data)

- H1 hard-open originals: usually not the constraint. Distribution is.
- H2 >= 20x parents: keep testing. This is the main bet.
- H3 3-line originals: format is not enough on a cold account.
- H4 follows alone buy reach: weak. Follows help the graph, they do not
  replace gold replies.
- H5 non-English gold beats English on reply reach: test if your ICP is
  multilingual.

## Epoch rule

<= 4 bounded edits per night. Accept only if held-out val mean score
strictly improves. Otherwise append to `rejected_edits.md` and keep this
file.
