# entry-news-image-20261120

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![make.fun rank · news-image-20261120](https://make.fun/badge/news-image-20261120/rank/ikiroki15-web/entry-news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![make.fun reward · news-image-20261120](https://make.fun/badge/news-image-20261120/reward/ikiroki15-web/entry-news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

**THE WORLD TODAY — Friday, 20 November 2026.** One 1024x1024 newspaper
front page that sums up the day's world news, drawn entirely at runtime
by a single Python 3 program using only the standard library.

## What it draws

- Masthead with the date set large and clear: **FRIDAY, 20 NOVEMBER 2026**
- One lead story (the first-ever Trump–Xi–Putin trilateral summit in Shenzhen)
- Six story cards across regions and beats — the ICJ Myanmar genocide
  ruling, the postponed Iran decision, the Kerch Bridge strikes, Cyclone
  Akvan, the record Anthropic IPO, and the Wellington Test match
- A hand-drawn pictogram per story, an "ALSO TODAY" ticker, and a sources line

## How it works

No PIL, no image files, no fonts, no network, no clock, no randomness.
The program renders into an in-memory pixel buffer with its own drawing
primitives (rectangles, discs, lines, triangles, arcs), typesets with a
hand-built 5x7 bitmap font, and encodes the PNG itself with `zlib` and
`struct`. Output is byte-identical on every run.

## Run

```bash
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024x1024, well under 1 MiB).
