---
name: X publish no AI label
description: >-
  use this whenever publishing or scheduling any X post or reply for the
  operator so Made with AI never triggers and bot-browser compose is never used
---
# X publish without Made with AI

Use this whenever shipping any X original OR reply for @YOUR_HANDLE.

## Hard ban

NEVER publish through a bot browser on x.com (compose or reply). That path
can auto-label Made with AI even with disclosure OFF.

## Originals

Typefully API: social set `YOUR_TYPEFULLY_SOCIAL_SET_ID`,
`made_with_ai: false`, `publish_at: "now"`. Or the operator's own phone / laptop.

## Replies / comments

1. CREATE a draft via Typefully API with `platforms.x.settings.reply_to_url`
   and `made_with_ai: false`. Do NOT set `publish_at`. X policy blocks API
   reply publish.
2. PUBLISH that draft from the Typefully UI (open the draft private URL,
   then Publish). OAuth path, no AI badge.
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

Delete that post/reply immediately. Stop that lane. Fix the path before
the next ship.
