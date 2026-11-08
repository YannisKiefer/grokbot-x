# Publish: Typefully originals vs replies

Read this once. Publish only through official API clients; never automate x.com.

## Why API-only

X's automation rules ban non-API automation, "such as scripting the X
website", ban automated likes and follows, and say breaking them may mean
permanent suspension. See
https://help.x.com/en/rules-and-policies/x-automation.

Publish only through official OAuth clients (Typefully connected to
@YOUR_HANDLE on the operator's own device), or the operator's own
phone/laptop. Whether a post carries X's "Made with AI" disclosure is the
operator's choice: set `X_MADE_WITH_AI=true` in `.env` to disclose
(default is off). The helper scripts send whatever `.env` says.

## One-time setup

1. On your phone or laptop, connect @YOUR_HANDLE to Typefully via OAuth.
2. Typefully -> Settings -> API -> create a key.
3. Turn on Development mode so you can see your social set id.
4. Put these in `.env` (never commit it):

```
YOUR_TYPEFULLY_API_KEY
YOUR_TYPEFULLY_SOCIAL_SET_ID
YOUR_HANDLE
```

`YOUR_SOCIAL_SET_ID` is the same value. Docs use both names.
Optional: `X_MADE_WITH_AI=true` if you want posts to carry the AI
disclosure. Default is off; it is your call.

## Originals: API can publish now

`POST https://api.typefully.com/v2/social-sets/{YOUR_TYPEFULLY_SOCIAL_SET_ID}/drafts`

```bash
curl -sS -X POST \
  "https://api.typefully.com/v2/social-sets/${YOUR_TYPEFULLY_SOCIAL_SET_ID}/drafts" \
  -H "Authorization: Bearer ${YOUR_TYPEFULLY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": {
      "x": {
        "enabled": true,
        "posts": [{"text": "your copy here"}],
        "settings": {"made_with_ai": MADE_WITH_AI}
      }
    },
    "publish_at": "now"
  }'
```

`MADE_WITH_AI` is `true` or `false`, the operator's choice. `publish_at: "now"` is async. Poll `GET /v2/social-sets/{id}/drafts/{draft_id}`
until `publish_state` is `finished`, then read `x_published_url`.

Helper: `python3 scripts/publish_original.py --text "your copy here"`

## Replies: API drafts only, UI publishes

X does not let the Typefully API publish a reply. Create the draft with
`reply_to_url` and **omit** `publish_at`. Then open the draft in the
Typefully UI, read it once more, and hit Publish NOW. That click is the
human approval X's automation rules expect; do not schedule replies.

```bash
curl -sS -X POST \
  "https://api.typefully.com/v2/social-sets/${YOUR_TYPEFULLY_SOCIAL_SET_ID}/drafts" \
  -H "Authorization: Bearer ${YOUR_TYPEFULLY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": {
      "x": {
        "enabled": true,
        "posts": [{"text": "your reply here"}],
        "settings": {
          "made_with_ai": MADE_WITH_AI,
          "reply_to_url": "https://x.com/someone/status/PARENT_ID"
        }
      }
    }
  }'
```

Helper: `python3 scripts/create_reply_draft.py --text "..." --reply-to URL`

Then open the returned private URL and publish by hand.

## Allowed vs forbidden

| Path | Originals | Replies |
|---|---|---|
| Typefully API `publish_at=now` | yes | no |
| Typefully draft + UI Publish NOW | yes | yes |
| Operator phone / normal browser | yes | yes |
| Any scripted browser on x.com | never | never |
| Schedule a reply | | never |

Likes, bookmarks and follows are the operator's own clicks. Never automate
them: X bans automated likes and follows.

## Typefully free tier

Free plans cap monthly publishes. When you hit the cap, draft only.
Do not invent a second publish path to "keep shipping".

## If X labels a post

X decides its own labels. Leave the label and the post as they are (the
operator may delete a post if they want). Do not try to work around a
label, and do not test-spam to debug.
