---
name: X publish no AI label
description: >-
  use this whenever publishing or scheduling any X post or reply for the
  operator so Made with AI never triggers and bot-browser compose is never used
---
# X publish without Made with AI

Use this whenever shipping any X original OR reply for @YOUR_HANDLE.

## Hard ban

NEVER publish through a bot browser on x.com (compose or reply). X's
automation rules ban scripting the X website and may permanently suspend
the account for it. Community reports also tie bot-browser compose to
auto-applied Made with AI labels (no official doc; treat as a report).

## Disclosure

`made_with_ai` is the operator's choice: set `X_MADE_WITH_AI=true` in
.env to disclose. Default is off. Never flip it secretly either way.

## Originals

Typefully API: social set `YOUR_TYPEFULLY_SOCIAL_SET_ID`,
`made_with_ai: false`, `publish_at: "now"`. Or the operator's own phone / laptop.

## Replies / comments

1. CREATE a draft via Typefully API with `platforms.x.settings.reply_to_url`
   and the operator's `made_with_ai` choice. Do NOT set `publish_at`. X
   policy blocks API reply publish.
2. PUBLISH that draft from the Typefully UI (open the draft private URL,
   read it once more, then Publish). That human click is the approval step;
   OAuth path; never schedule.
3. NEVER use x.com reply compose from a bot browser.

## Engagement on x.com from a bot browser

Likes and bookmarks only. No compose.

## Before publish checklist

- Correct path for originals vs replies
- `made_with_ai` false
- No AI-generated image
- Max 1 original/hour; spaced replies
- Not a throwaway test

## If the AI label appears

Stop that publish path immediately (suspension risk beats reach). Keep or
delete the labeled post is the operator's call. Fix the path before the
next ship.
