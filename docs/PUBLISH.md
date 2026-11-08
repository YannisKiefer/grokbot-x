# Publish: Typefully originals vs replies

Read this once. Then never compose on x.com from a bot browser again.

## Why API-only

Two reasons, one proven, one reported:

1. Official rule (this is why the path exists): X's automation rules ban
   non-API automation, "such as scripting the X website", and say it may
   result in permanent suspension. See
   https://help.x.com/en/rules-and-policies/x-automation.
2. Community-reported: users have seen **Made with AI** stamped on posts
   composed from bot browsers (headless, Playwright, datacenter IPs) even
   with disclosure off. There is no official X documentation of that
   fingerprinting; treat it as a report, not a rule. Officially, the
   label targets AI-generated media via composer disclosure and automatic
   detection of AI images/video.

Publish only through official OAuth clients (Typefully connected to
@YOUR_HANDLE on the operator's own device), or the operator's own
phone/laptop. Whether a post carries the "Made with AI" disclosure is the
operator's choice: set `X_MADE_WITH_AI=true` in `.env` to disclose
(default is off).

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
        "settings": {"made_with_ai": false}
      }
    },
    "publish_at": "now"
  }'
```

`publish_at: "now"` is async. Poll `GET /v2/social-sets/{id}/drafts/{draft_id}`
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
          "made_with_ai": false,
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
| Typefully API `publish_at=now`, `made_with_ai=false` | yes | no |
| Typefully draft + UI Publish NOW | yes | yes |
| Operator phone / normal browser | yes | yes |
| Bot browser on x.com compose | never | never |
| Schedule a reply | | never |

Likes and bookmarks from a bot browser are fine. Compose is not.

## Typefully free tier

Free plans cap monthly publishes. When you hit the cap, draft only.
Do not invent a second publish path to "keep shipping".

## If the AI label appears

The label means the session looked automated. Stop that publish path
(permanent-suspension risk beats any reach), figure out which client
produced it, and stay on official clients. Keeping or deleting the post
is the operator's call. Do not test-spam to debug.
