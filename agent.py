#!/usr/bin/env python3
"""Instagram organizer agent.

For every post it:
  1. puts the post in a content series (Drama AI, Relationship AI, ...)
  2. rewrites the caption to sell, and says you teach how the content is made
  3. writes a page plan: bio, highlights, pinned posts, series order, posting rhythm

Inputs (pick one):
  --csv FILE        CSV with columns: id,date,permalink,caption
  --export FILE     posts_1.json from Instagram's "Download your information" (JSON)
  --fetch           read posts live with the Instagram API (needs IG_ACCESS_TOKEN)

Outputs go to ./output/ :
  captions.csv      old caption, new caption, series, hashtags, per post
  captions.md       the same, easy to read and copy from your phone
  page_plan.md      how to organize the page
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

MODEL = "claude-opus-5-5"
BATCH_SIZE = 10
OUT_DIR = Path("output")


# --------------------------------------------------------------------------- #
# Structured output schemas
# --------------------------------------------------------------------------- #
class RewrittenPost(BaseModel):
    id: str
    series: str = Field(description="Exactly one of the series names from the brand config")
    episode_label: str = Field(description="e.g. 'Part 2' for a multi-part story, else empty string")
    hook: str = Field(description="The first line, written to stop the scroll")
    new_caption: str = Field(description="Full ready-to-paste caption, under 2,200 characters, hashtags NOT included")
    hashtags: list[str] = Field(description="3 to 5 targeted hashtags, each starting with #")
    on_screen_text: str = Field(description="Short text for the cover image or first frame")
    why: str = Field(description="One sentence: why this caption will sell better")


class BatchResult(BaseModel):
    posts: list[RewrittenPost]


class Highlight(BaseModel):
    name: str
    cover_text: str
    what_goes_in_it: str


class SeriesPlan(BaseModel):
    series: str
    post_ids_in_order: list[str]
    recurring_title_format: str = Field(description="e.g. 'Drama AI · Ep. {n}: {title}'")
    content_ideas: list[str] = Field(description="3 new post ideas for this series")


class PagePlan(BaseModel):
    bio: str = Field(description="Instagram bio, 150 characters or fewer")
    name_field: str = Field(description="Searchable name field, e.g. 'Rabyn | AI Story Coach'")
    highlights: list[Highlight]
    pinned_post_ids: list[str] = Field(description="Up to 3 post ids to pin, best first")
    pinned_reasoning: str
    series: list[SeriesPlan]
    weekly_posting_rhythm: list[str] = Field(description="e.g. 'Mon - Drama AI episode'")
    grid_tips: list[str]


# --------------------------------------------------------------------------- #
# Loading posts
# --------------------------------------------------------------------------- #
def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [
        {
            "id": (r.get("id") or str(i + 1)).strip(),
            "date": (r.get("date") or "").strip(),
            "permalink": (r.get("permalink") or "").strip(),
            "caption": (r.get("caption") or "").strip(),
        }
        for i, r in enumerate(rows)
    ]


def _fix_export_text(s: str) -> str:
    # Instagram exports store UTF-8 bytes as latin-1 escapes (emoji come out garbled).
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def load_export(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):  # some export versions wrap the list
        data = next((v for v in data.values() if isinstance(v, list)), [])
    posts = []
    for i, item in enumerate(data):
        media = item.get("media") or [{}]
        caption = item.get("title") or media[0].get("title") or ""
        ts = item.get("creation_timestamp") or media[0].get("creation_timestamp")
        date = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() if ts else ""
        posts.append({
            "id": f"post{i + 1}",
            "date": date,
            "permalink": media[0].get("uri", ""),
            "caption": _fix_export_text(caption).strip(),
        })
    return posts


def fetch_from_api() -> list[dict]:
    """Read-only fetch using the Instagram API with Instagram Login."""
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        sys.exit("Set IG_ACCESS_TOKEN first (see README, 'Option C').")
    url = "https://graph.instagram.com/me/media?" + urllib.parse.urlencode({
        "fields": "id,caption,permalink,timestamp,media_type",
        "limit": 50,
        "access_token": token,
    })
    posts = []
    while url:
        with urllib.request.urlopen(url, timeout=30) as resp:
            page = json.load(resp)
        for m in page.get("data", []):
            posts.append({
                "id": m["id"],
                "date": (m.get("timestamp") or "")[:10],
                "permalink": m.get("permalink", ""),
                "caption": (m.get("caption") or "").strip(),
            })
        url = page.get("paging", {}).get("next")
    return posts


# --------------------------------------------------------------------------- #
# Claude calls
# --------------------------------------------------------------------------- #
def system_prompt(brand: dict) -> str:
    series_lines = "\n".join(f"- {s['name']}: {s['description']}" for s in brand["series"])
    return f"""You are a senior Instagram growth strategist and direct-response copywriter working for {brand['creator_name']} ({brand['account_handle']}).

ABOUT THE CREATOR
- Teaches: {brand['what_you_teach']}
- Offer: {brand['offer_name']} ({brand['offer_type']})
- Call to action: {brand['call_to_action']}
- Audience: {brand['audience']}
- Voice: {brand['voice']}

CONTENT SERIES (assign every post to exactly one, using the exact name):
{series_lines}

HOW TO WRITE EACH CAPTION
1. Hook line first. It has to stop the scroll: curiosity, a bold claim, or an open loop. Never start with "In this video".
2. For story posts (drama or relationship), tease the story without spoiling it, and point to the next or previous part when the post is part of a multi-part story.
3. Bridge to the teaching: say plainly that {brand['creator_name']} made this with AI and teaches people how to do it. Make it feel like an invitation, not an ad.
4. End with ONE clear call to action, based on: "{brand['call_to_action']}". You can vary the wording; keep the keyword the same.
5. Short lines with white space. A few emoji at most. Write in the creator's voice.
6. Keep the post's original meaning. Never invent results, numbers, testimonials, or claims that are not in the original caption.
7. Hashtags: 3 to 5 targeted ones (niche plus the series), in the hashtags field only, not in the caption.
"""


def make_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(max_retries=4)


def call_structured(client, brand: dict, prompt: str, schema):
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=system_prompt(brand),
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Model declined this batch: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Response was cut off; lower BATCH_SIZE and try again.")
    return response.parsed_output


def rewrite_batch(client, brand: dict, batch: list[dict]) -> list[RewrittenPost]:
    payload = json.dumps(
        [{"id": p["id"], "date": p["date"], "caption": p["caption"]} for p in batch],
        ensure_ascii=False, indent=2,
    )
    prompt = (
        "Here are posts from the account, oldest first. For each one, assign its series, "
        "spot multi-part stories, and write the new sales caption. Return one entry per post "
        f"with the same id.\n\n{payload}"
    )
    result: BatchResult = call_structured(client, brand, prompt, BatchResult)
    by_id = {p.id: p for p in result.posts}
    missing = [p["id"] for p in batch if p["id"] not in by_id]
    if missing:
        raise RuntimeError(f"Missing results for posts: {missing}")
    return [by_id[p["id"]] for p in batch]


def plan_page(client, brand: dict, posts: list[dict], rewritten: list[RewrittenPost]) -> PagePlan:
    summary = json.dumps(
        [
            {"id": r.id, "date": p["date"], "series": r.series, "episode": r.episode_label, "hook": r.hook}
            for p, r in zip(posts, rewritten)
        ],
        ensure_ascii=False, indent=2,
    )
    prompt = (
        "All posts have been sorted and rewritten. Now design the page so each series is "
        "clearly separated and visitors are moved toward the offer. Use Story Highlights, "
        "pinned posts, a recurring title format per series, a bio, and a weekly posting "
        "rhythm. Only use post ids from this list.\n\n" + summary
    )
    return call_structured(client, brand, prompt, PagePlan)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def write_outputs(brand, posts, rewritten, plan: PagePlan) -> None:
    OUT_DIR.mkdir(exist_ok=True)

    with open(OUT_DIR / "captions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "date", "permalink", "series", "episode", "old_caption",
                    "new_caption", "hashtags", "on_screen_text", "why"])
        for p, r in zip(posts, rewritten):
            w.writerow([p["id"], p["date"], p["permalink"], r.series, r.episode_label,
                        p["caption"], r.new_caption, " ".join(r.hashtags), r.on_screen_text, r.why])

    lines = [f"# New captions for {brand['account_handle']}\n"]
    for s in brand["series"]:
        group = [(p, r) for p, r in zip(posts, rewritten) if r.series == s["name"]]
        if not group:
            continue
        lines.append(f"\n## {s['name']} ({len(group)} posts)\n")
        for p, r in group:
            title = f"{r.episode_label} · " if r.episode_label else ""
            lines += [
                f"\n### {title}{p['date']} · `{p['id']}`",
                f"{p['permalink']}\n" if p["permalink"] else "",
                "**Old:**", f"> {p['caption'] or '(no caption)'}\n",
                "**New, ready to paste:**", "```", r.new_caption, "", " ".join(r.hashtags), "```",
                f"*Cover text:* {r.on_screen_text}  ",
                f"*Why:* {r.why}\n",
            ]
    (OUT_DIR / "captions.md").write_text("\n".join(lines), encoding="utf-8")

    pl = [f"# Page plan for {brand['account_handle']}\n",
          "## Profile", f"**Name field:** {plan.name_field}  ", f"**Bio:**\n```\n{plan.bio}\n```",
          f"**Link:** {brand['link_in_bio']}\n",
          "## Story Highlights (left to right)"]
    pl += [f"{i}. **{h.name}** · cover text: `{h.cover_text}` · {h.what_goes_in_it}"
           for i, h in enumerate(plan.highlights, 1)]
    pl += ["\n## Pinned posts", *[f"- `{pid}`" for pid in plan.pinned_post_ids], plan.pinned_reasoning]
    pl.append("\n## Series")
    for s in plan.series:
        pl += [f"\n### {s.series}", f"Title format: `{s.recurring_title_format}`  ",
               "Posts in order: " + ", ".join(f"`{x}`" for x in s.post_ids_in_order),
               "\nNew ideas:", *[f"- {idea}" for idea in s.content_ideas]]
    pl += ["\n## Weekly posting rhythm", *[f"- {d}" for d in plan.weekly_posting_rhythm]]
    pl += ["\n## Grid tips", *[f"- {t}" for t in plan.grid_tips]]
    (OUT_DIR / "page_plan.md").write_text("\n".join(pl), encoding="utf-8")


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv")
    src.add_argument("--export")
    src.add_argument("--fetch", action="store_true")
    ap.add_argument("--brand", default="brand.json")
    ap.add_argument("--limit", type=int, help="only process the first N posts (handy for a test run)")
    args = ap.parse_args()

    brand = json.loads(Path(args.brand).read_text(encoding="utf-8"))
    posts = load_csv(args.csv) if args.csv else load_export(args.export) if args.export else fetch_from_api()
    posts.sort(key=lambda p: p["date"])
    if args.limit:
        posts = posts[: args.limit]
    if not posts:
        sys.exit("No posts found.")

    client = make_client()
    rewritten: list[RewrittenPost] = []
    for i in range(0, len(posts), BATCH_SIZE):
        batch = posts[i: i + BATCH_SIZE]
        print(f"Rewriting posts {i + 1}-{i + len(batch)} of {len(posts)}...")
        rewritten += rewrite_batch(client, brand, batch)

    print("Designing the page layout...")
    plan = plan_page(client, brand, posts, rewritten)
    write_outputs(brand, posts, rewritten, plan)
    print(f"Done. Open {OUT_DIR}/captions.md and {OUT_DIR}/page_plan.md")


if __name__ == "__main__":
    main()
