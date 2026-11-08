# How to make good posts on X (2026 algo update)

The play: clear hook > useful body > real proof > cut the filler.

This is the writing half of the kit. The scorer in `skillopt/` only reads X
counters; this guide is how you earn them. Pair it with
`x-human-cadence.md` (when to post) and `PUBLISH.md` (how to publish).

## What changed in the weights

Community-extracted from X's open-sourced algorithm code (old > new):

| Signal | Before | Now |
|---|---|---|
| like | 0.66 | 0.708 |
| time spent | 0.006 | 0.0075 |
| share | 2 | 2.118 |
| opening a post | 0.3 | 0.274 |
| reading time after opening | 0.4 | 0.385 |
| opening a video | 0.02 | 0 |
| "not interested" | -52.272 | -53.07 |

X does not officially document these weights or this update. Treat the
numbers as directional community data from the-algorithm repo, not gospel.

## What those numbers actually mean

- X predicts what each viewer might do, then applies these weights.
- They are not points you collect for every like or reply.
- A higher reading-time weight does not mean your next post gets 25% more
  reach.

## How to use this

- Line 1: say exactly what the reader gets.
- Line 2: show the result, screenshot, or fact that backs it up.
- After "show more": deliver the steps you promised.
- Remove the intro that repeats the hook in four different ways.
- Show the catch before someone wastes their time or money.

## For video

- Show what the video is about immediately.
- Cut the logo intro and "wait till the end".
- Video open weight hitting 0 does not mean videos get 0 reach. It is one
  signal, not the whole ranking system.

## For replies

- Add a missing step, a number, or a useful counterpoint.
- "huge", "this changes everything", and a rewritten version of the post
  add nothing.
- Write something the author can actually respond to.

An author reply to your comment is the strongest win signal this kit
tracks (the scorer multiplies it x1.5). To earn it, leave them something
worth answering.

## The catch

- These numbers are community-extracted from GitHub.
- Experiment with different formats and let your own trajectories decide.
- None of this guarantees views.
- A bad topic does not become useful because you formatted it correctly.

That is what the nightly gate is for: propose an edit, run it as a live
trial (`append --skill`), keep it only if the held-out numbers move. Format advice is a
hypothesis; `trajectories.jsonl` is the verdict.

## What not to do

- Do not stretch 3 useful lines into 30 to farm reading time.
- Do not ask people to like your post because the like weight increased
  (engagement groups are against X's rules and get accounts limited).
- Do not turn every trending topic into your niche. Off-niche virality is
  penalized by the scorer, not just by taste.
- Do not read one weight and invent a growth hack around it.

A hook gets someone to open the post. The rest needs to justify it.
