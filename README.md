# Agent Rabyn: Instagram organizer and caption rewriter

An AI agent built on Claude that goes through your Instagram posts and:

1. **Sorts every post into a series**: Drama AI, Relationship AI, AI Tutorials, Results & Students, or Other.
2. **Rewrites every caption to sell.** Each one gets a scroll-stopping hook, a line saying you made it with AI and **teach people how**, and one clear call to action (for example "Comment LEARN").
3. **Plans the whole page**: bio, name field, Story Highlights for each series, which posts to pin, a title format for each series, new post ideas, and a weekly posting schedule.

## What it can and can't do

Instagram doesn't let any outside app **edit captions on existing posts** or **create Highlights**. The agent writes everything for you, and you paste it in. Posts are grouped by series in `output/captions.md`, so you can work through one series at a time from your phone: open the post, tap ⋯, then Edit, and paste.

## Setup (one time)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...     # from console.anthropic.com
```

Then open **`brand.json`** and fill in your handle, what you teach, your offer, your link, and your call to action. You can also rename, add, or remove series there.

## Get your posts in (pick one)

**Option A: Instagram data download (easiest, no developer account)**
Instagram app: Settings → Accounts Center → Your information and permissions → Download your information. Choose **JSON** format and include **Content**. Unzip the file and find `posts_1.json` (under `your_instagram_activity/content/`).
```bash
python agent.py --export path/to/posts_1.json
```

**Option B: a spreadsheet.** Make a CSV with the columns `id,date,permalink,caption` (see `sample/posts.csv`).
```bash
python agent.py --csv sample/posts.csv
```

**Option C: live from Instagram (read-only).** This needs a Professional (Creator or Business) account and an access token from a Meta developer app that uses the Instagram API with Instagram Login.
```bash
export IG_ACCESS_TOKEN=...
python agent.py --fetch
```

Tip: do a test run on 10 posts first with `--limit 10`.

## What you get (in `output/`)

| File | What's in it |
|---|---|
| `captions.md` | Posts grouped by series, with the old caption, the new caption ready to paste, hashtags, cover text, and why the new version works |
| `captions.csv` | The same content as a spreadsheet |
| `page_plan.md` | Bio, Highlights (with cover text), pinned posts, the order of posts in each series, new ideas, and a weekly schedule |

## How it works

- Model: Claude Opus 5.5 (`claude-opus-5-5`), with structured outputs so every result has the same fields. Server-side fallback is turned on, so if a request is declined it reruns on a fallback model automatically.
- It handles posts in batches of 10 (`BATCH_SIZE` in `agent.py`), then makes one more call to plan the page.
- Its rules: keep the original meaning of each post, never make up results or testimonials, use 3 to 5 hashtags, and stay under Instagram's 2,200-character limit.
