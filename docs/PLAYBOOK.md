# Operator playbook

You are tired. You have an X handle and a product. This is the whole job.

## 0. Fill the blanks

1. Copy `.env.example` to `.env`. Set `YOUR_HANDLE`,
   `YOUR_TYPEFULLY_API_KEY`, `YOUR_TYPEFULLY_SOCIAL_SET_ID`.
2. Fill `docs/BRAND-BIBLE.template.md` so the bot knows what you sell.
3. Copy `examples/best_skill.starter.md` over `skillopt/best_skill.md`
   if you want a clean start.
4. Install the five files under `skills/` into your Grok Bot / agent
   skill folder.

No key, no publish. Draft only.

## 1. Scout gold, not "nice posts"

Open X. For each candidate parent, do this in your head:

```
viral_ratio = parent_views / parent_followers
```

Keep it if:

- ratio >= 12 (better >= 20)
- replies are still climbable (you can still be seen)
- the author is in your ICP, or the readers are
- it is moving for its age, not a dead diary

Throw it away if:

- on-topic but 80 views on a 400-follower account
- huge follower count, mediocre views
- 400 replies already (you will be invisible)

Views beat followers. Always.

## 2. Draft like a human

Load `skills/x-unslop-humanizer`. Write the reply or original.
Run the spoken test. Kill em dashes. Kill "the X is the real story".
Name a real object (checkout, refund, pixel, sku).

Replies: add the missing next step. Do not plug YOUR_PRODUCT unless
you earned it.

Originals: only if you have a gold source and a hard first line.
On a cold account, originals are optional. Replies are not.

## 3. Publish the right way

- Original -> Typefully API, `made_with_ai: false`, `publish_at: "now"`.
- Reply -> Typefully draft with `reply_to_url`, then Publish NOW in the
  Typefully UI.
- Never x.com compose from a bot browser.

See `PUBLISH.md`. One original per hour. Jitter 0-35 min. Weekends on.

## 4. Log the ship

One JSON line per post, same shape as `examples/trajectories.example.jsonl`.

```bash
python3 skillopt/sleep_cycle.py append --json '{"id":"ex_new", ...}'
```

Mark ~20% as `"split": "val"` and put those ids in `held_out.json`.
Leave metrics empty at first. Fill views later.

## 5. Nightly SkillOpt

Refresh numbers. Run `sleep_cycle.py status`. If you have enough rows,
propose at most 4 edits to `best_skill.md`. Keep them only if val score
goes up. Details in `SKILLOPT.md`.

The bot should get harder to fool over time. That is the product.

## Daily shape (adapt to YOUR_TIMEZONE)

- Morning: scout overnight climbers. Reply if gold. Maybe one original.
- Midday: second scout. No gold? Do not pad. Follow ICP. Leave.
- Evening: one more wave in the timezone where your buyers scroll.
- Night: metrics + SkillOpt. No posting dump.

## What "good" looks like

Author replies to you. ICP profile visits. A DM that names the pain.
Not a spam-follow. Not a 6-view original you are proud of because the
wording was clever.

## What gets you banned or ignored

Burst posting. Burst follows. Auto-like rings. Rage pile-ons.
Guaranteed-revenue claims. Browser compose. Filler hours. Soft-sell
replies under strangers.

Human cadence is not decoration. It is the license to keep the account.
