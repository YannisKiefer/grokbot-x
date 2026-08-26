# X publish without Made with AI

## Root cause

If you compose on x.com from a bot browser (headless, Playwright, CDP,
datacenter IP), X can stamp **Made with AI** after publish even when the
content-disclosure toggle is OFF.

Public docs talk about a manual toggle and C2PA for AI images. The bot-browser
path is a fingerprint problem, not a toggle you forgot.

## Fix

Publish ONLY through official OAuth clients that send `made_with_ai=false`
(or omit the flag / never set it true).

### Primary: Typefully

1. The operator connects @YOUR_HANDLE to Typefully via OAuth once, on their
   own device.
2. Create a Typefully API key in Settings -> API.
3. Create / schedule / publish via the Typefully API.
4. Always set Made with AI / `made_with_ai` OFF.
5. Never use a bot browser on x.com compose.

### Fallback

- Post from the operator's phone or normal desktop browser.
- Or Typefully / Buffer UI on that same device with AI-Generated OFF.

### Forbidden

- Bot-browser posting to x.com
- Post -> delete verification loops
- AI image generation / Content disclosure Made with AI ON

## Verification without spam

- Confirm the payload has `made_with_ai` false before the first real publish.
- The first real publish is a post the operator actually wants live.
  Not a throwaway.
