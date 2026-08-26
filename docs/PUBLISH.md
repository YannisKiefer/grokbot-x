# Publish: Typefully originals vs replies

Read this once. Then never compose on x.com from a bot browser again.

## Why the AI label shows up

Grok Bot / Playwright / any datacenter browser posting through x.com
compose can get **Made with AI** stamped after publish. Disclosure OFF
does not save you. The session looks automated.

Official OAuth clients (Typefully connected to @YOUR_HANDLE on the
operator's own device) do not carry that fingerprint. That is the path.

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
Typefully UI and hit Publish NOW. Do not schedule replies.

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

Delete the post. Stop that lane. Check the payload. Do not test-spam
to debug.
