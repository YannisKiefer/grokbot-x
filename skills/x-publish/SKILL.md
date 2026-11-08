---
name: X publish
description: >-
  use this whenever publishing or scheduling any X post or reply for the
  operator: official API clients only, a human approves every reply, and
  AI disclosure is the operator's own setting
---
# X publish

Use this whenever shipping any X original OR reply for @YOUR_HANDLE.
Details and curl examples: `docs/PUBLISH.md`.

## Hard ban

NEVER automate x.com in a browser: no compose, no replies, no likes, no
bookmarks, no follows. X's automation rules ban scripting the X website
and ban automated likes and follows; the account can be permanently
suspended. Likes, bookmarks and follows are the operator's own clicks.

## Disclosure

Whether posts carry X's "Made with AI" disclosure is the operator's
choice: `X_MADE_WITH_AI=true` in `.env` turns it on (default off). Use
whatever the operator set; never change it on your own. If X applies a
label itself, that is X's call: leave it, never try to work around it.

## Originals

`python3 scripts/publish_original.py --text "..."` (Typefully API,
`publish_at: "now"`, disclosure from `.env`). Or the operator's own
phone / laptop.

## Replies

1. CREATE a draft: `python3 scripts/create_reply_draft.py --text "..."
   --reply-to URL`. It never sets `publish_at`; X does not allow API
   reply publish.
2. The operator opens the draft's private URL in Typefully, reads it,
   and clicks Publish. That human click is the approval step. Never
   schedule replies.

## Before publish checklist

- Right path for originals vs replies
- Disclosure as the operator set it
- Max 1 original/hour; spaced replies
- Not a throwaway test, not a duplicate of an earlier post
