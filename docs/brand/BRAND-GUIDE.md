# grokbot-x brand guide

One page for anyone who writes, designs or ships for grokbot-x. Read it before
you touch the README, the site, a social card or a post about the project.

## 1. What worked so far (data, 2026-11-08)

- 66 stars at the time of writing.
- About 96% of traffic comes from X via `t.co`. Search and GitHub discovery are close to zero.
- The star bursts lined up with an X post by the account Greshamtrade, "20 Grok Bot projects", that listed this repo.
  - The first burst came on 10-24.
  - A second wave ran 11-04 to 11-08. Its source is still unknown; check the referrer list before crediting anyone.
- Only about 6 of 443 visitors went past the README. The README is the product page: most people decide there and leave.

What this means:

1. One outside post can move this repo more than any feature. Make the repo easy to list: a one-line promise, one picture, one copyable command.
2. The README has to do the site's job, because people rarely click deeper. Lead with the promise and the 60-second start, then the detail.
3. X is the channel. Every visual we make should read on a phone in an X feed at 1x.

## 2. Positioning

**One line:** grokbot-x scouts the gold, drafts in your voice, waits for your yes, and every night SkillOpt keeps only what worked.

| | |
|---|---|
| For | Founders and solo operators who grow on X with Grok Bot and have no time for a content team |
| Problem | Prompt packs spam compose and never learn; growth tools break X's rules and get accounts limited |
| What it is | An open-source loop: scout posts with real reach, draft, publish through the official Typefully API, log, and let a nightly gate keep only the edits the numbers prove |
| Why believe it | Fixed reward in code, held-out data, bootstrap interval, rejected edits logged; MIT; Python stdlib only |
| Enemy | Blind automation: scripted browsers on x.com, bulk replies, engagement bait |

Three proof points to repeat everywhere, in this order:

1. **Your yes.** Nothing replies without a person reading and clicking Publish.
2. **Official API only.** Typefully OAuth, never a scripted browser on x.com.
3. **It learns honestly.** An edit ships only if its lower confidence bound beats zero.

## 3. Voice

Competent operator. Calm, direct, specific. Short sentences. Real nouns and numbers.

Do:
- Say what happens: "drafts a reply, waits for your click".
- Use the reader's words: posts, replies, reach, followers, voice.
- Name the guard rail next to the power: "scouts the gold, waits for your yes".

Do not:
- "like a human", "look human", "humanize", "undetectable", "bypass", "evade". X's rules treat disguised automation as a violation; we do not sell disguise. Say "in your voice" instead.
- "AI-powered", "seamless", "effortless growth", "fully autonomous", "set it and forget it", "10x your followers", "guaranteed".
- Growth numbers we have not measured. The repo claims none; neither do we.
- Em dashes, exclamation marks, hype emoji.

Swap list:

| Instead of | Write |
|---|---|
| draft like a human | draft in your voice |
| human cadence | posting cadence |
| humanizer | voice pass |
| auto-reply | reply draft you approve |
| grow your account | find the posts worth answering |

## 4. Tokens

Colour (site, social cards, README images):

| Token | Hex | Use |
|---|---|---|
| paper | `#F7F7F5` | every background |
| ink | `#000000` | all type |
| ink-2 | `#4A4A47` | meta text (8.1:1 on paper) |
| line | `#E2E2DD` | card borders |
| sticker yellow | `#FFD400` | "gold", star CTA; black text on it |
| sticker green | `#19D27C` | "your voice"; black text on it |
| sticker blue | `#2B3BFF` | "SkillOpt" only; white text on it |
| split red | `#FF2D55` | RGB split, motion only, never text |
| split cyan | `#00D8F0` | RGB split, motion only, never text |

Rules: colour lives only in stickers and the RGB split. Each sticker colour belongs to one idea (yellow = what you find, green = your voice, blue = the learning loop). Never put coloured text on paper.

Type:
- Display: Inter Tight 800, tracking -0.052em, word spacing +0.07em, line height 1.02. Sentence case, always a full sentence.
- UI and body: Inter Tight 500/600, 14 to 16 px.
- Code: the system monospace stack.

Shape: cards 18 px radius, 1 px `line` border, white fill, no shadow. Buttons 40 px tall, 12 px radius. Stickers: 0.09em radius, rotated -4deg to +3deg, never the same angle twice in a row.

## 5. Motion system

The signature is the **sentence build** from the founder's reference video, scaled up.

| Beat | Spec |
|---|---|
| Word land | 340 ms, ease out; starts 0.08em low at 106% scale with a 0.07em red/cyan split, settles to clean black |
| Word rhythm | 135 ms between plain words, 300 ms before a sticker, 120 ms after it |
| Sticker pop | 500 ms overshoot spring; enters at 3x its rotation and 135% scale; 9 confetti specks fly 0.45 to 1em and fade in 900 ms |
| SkillOpt glitch | every 1.1 to 1.8 s while holding: 260 ms, two clip-path slices with a split |
| Hold | 2.6 s on the full sentence |
| Dissolve | words leave in random order, 28 ms apart, 380 ms each: skew, slice, split, fade |
| Loop | three builds, then it rests on the full sentence |

Rules:
- A "Pause motion" control is always visible while anything moves.
- Reduced motion: the full sentence, static, no control.
- Motion never carries meaning that the static sentence lacks.

## 6. README proposal

Replace the top of the README with this order. Keep everything below "How it works" as is.

1. Title and the one line, as plain text so it renders in GitHub previews and on X link cards.
2. A 1280x640 hero image (the social preview, section 7) or the demo GIF (IMAGE-PROMPTS.md).
3. Three proof bullets: your yes, official API only, it learns honestly.
4. "Start in 60 seconds": the clone command and the dry run, nothing else.
5. A link to the site's agent prompt: "Using Claude Code, Codex or Cursor? Paste this prompt."
6. Then the current content.

Wording fixes to make in the README and the repo description:
- "draft like a human" becomes "draft in your voice" (two places: README intro and the GitHub description).
- "Human cadence is required" becomes "Keep a normal posting rhythm".

## 7. Social preview (1280x640)

Upload it in Settings -> General -> Social preview. That step is for the repo owner; this PR changes no settings.

- Canvas 1280x640, paper `#F7F7F5`. Keep 64 px of safe margin on every side; X crops the edges on phones.
- Left two thirds: "scouts the gold, drafts in your voice, waits for your yes." Inter Tight 800, about 64 px, black. Yellow sticker on "gold", green sticker on "your voice".
- Bottom left: "grokbot-x" 28 px 600, then "open source · MIT" in ink-2.
- Right third: leave an empty 240x240 square for a real logo once one exists. Until then leave it empty; never draw a placeholder mark.
- No screenshots of X UI, no bird or X logos, no xAI or Grok marks.
- Check: readable at 400 px wide on a phone, and stickers stay inside the safe area.

## 8. File organization proposal

Today the root mixes the product, the docs and the learning state. Proposed, in a separate PR (the GLM worker is editing README, docs and skills right now):

```
README.md            the product page
docs/
  start/             QUICKSTART, OPERATOR, PLAYBOOK
  publish/           PUBLISH, x-post-guide, posting cadence
  learn/             SKILLOPT
  brand/             this guide, IMAGE-PROMPTS
skills/              one folder per Grok Bot skill
skillopt/            gate code + local state (gitignored data)
scripts/             Typefully publishers
examples/            fake data for the dry run
site/                the one-page site
```

Moves only, no content changes, with redirects noted in the CHANGELOG.

## 9. Onboarding redesign

Today: clone, read a long README, copy three files by hand, find the Typefully key, run status. About 6 of 443 visitors get past the README.

Proposed path, three steps:

1. **One paste.** The site's agent prompt does the clone, reads the docs and runs the dry run. People without an agent copy the clone command.
2. **See it work before any key.** Today the dry run prints raw JSON (`n`, `train_mean`, `val_mean`). Add a plain-words summary line on top, for example "5 example posts scored, replies beat originals", with no stats jargon on the first screen.
3. **Connect last.** Ask for the Typefully key only when the user wants a first real draft, and say why it is safe: drafts only, nothing posts without your click.

Add a `make demo` or `python3 -m grokbot_x demo` entry point later that bundles step 2 into one command.

## 10. Skill renames (proposal)

The word "human" invites the "disguised automation" reading. Rename before the next listing post.

| Today | Proposed | Why |
|---|---|---|
| `x-human-cadence` | `x-posting-cadence` | says what it does: rhythm and volume discipline |
| `x-unslop-humanizer` | `x-voice-pass` | it removes filler and keeps the author's voice; no disguise claim |
| `x-unslop-humanizer-2` | `x-voice-pass-strict` | the stricter variant of the same pass |

Keep the old folder names as aliases for one release, note the rename in CHANGELOG.md, and update the README table.

## Credit

Built by the team behind [EcomBrain](https://ecombrain.io/?utm_source=github&utm_medium=grokbot-x&utm_campaign=oss). That footer line is the only place EcomBrain appears. Keep everything else brand-neutral.
