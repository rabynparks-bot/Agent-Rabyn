# DGL BY RJ: Rebrand & Business Operations Agent

*Skills For CEOs Who Prompt To Profit.*

This repo is RJ's AI agent for rebranding and running DGL BY RJ. It covers four areas:

1. **Brand rebrand:** DGL BY RJ, DGL x P2P, messaging, identity, offers → `rebrand/02_brand_blueprint.md`
2. **Instagram organization:** six content pillars, series, caption rewrites → `agent.py` + `rebrand/03_instagram_organization.md`
3. **Skool community rebuild:** 14 classrooms, full lessons → `rebrand/skool/`
4. **Content and sales:** campaigns, DM scripts, calendar, onboarding → `rebrand/04_…`, `05_…`, `06_…`

**Start with `rebrand/00_STATUS.md`** to see what's done, what's waiting, and what needs your approval.

The agent's standing instructions are in `CLAUDE.md`. Any Claude Code session opened on this repo follows them automatically.

## What it can and can't do on the platforms

| | Build | Analyze | Execute directly |
|---|---|---|---|
| **Instagram** | ✅ captions, plans, campaigns | ✅ reads your posts (export or API) | ❌ Instagram doesn't let outside apps edit captions or Highlights, so you paste them in |
| **Skool** | ✅ classrooms, lessons, descriptions | ✅ from screenshots or copy-paste | ⚠️ no public API; only through a browser session you authorize and watch |

## Setup (one time)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...     # from console.anthropic.com
```

Your brand settings are already in `brand.json`. Add your Instagram handle in `account_handle`.

## 1. Instagram: rewrite every caption

Download your posts: Instagram → Settings → Accounts Center → Your information and permissions → Download your information → **JSON**, including **Content**. Then find `posts_1.json`.

```bash
python agent.py --export path/to/posts_1.json --limit 10   # test on 10 posts first
python agent.py --export path/to/posts_1.json              # all posts
```

Other ways in: `--csv file.csv` (columns `id,date,permalink,caption`) or `--fetch` with `IG_ACCESS_TOKEN` (Professional account plus a Meta developer app).

**You get, in `output/`:**
- `captions.md`: posts grouped by pillar, each with the old caption, the new caption ready to paste, hashtags, cover text, and series ideas
- `captions.csv`: the same content as a spreadsheet
- `page_plan.md`: bio, Highlights, pinned posts, order for each pillar, and a weekly schedule

## 2. Skool: build the classrooms and lessons

```bash
python rebrand/skool/build_skool.py render                    # classroom master list (no API key needed)
python rebrand/skool/build_skool.py lessons --classroom 01    # writes full lessons for classroom 01
python rebrand/skool/build_skool.py lessons --classroom 02 --module 1 --limit 2
```

- The classroom structure lives in `rebrand/skool/curriculum.json`. Edit it there, then run `render` again.
- Lessons are saved in `rebrand/skool/lessons/`. Existing lessons are never overwritten.
- Each lesson ends with an **"RJ to add before publishing"** checklist: your tested prompts, screen recordings, current app names. The agent never makes those up.

## Models

Both tools use Claude Opus 5.5 (`claude-opus-5-5`) with structured outputs, so every result has the same fields. Server-side fallback is on, so a declined request reruns on a fallback model automatically.
