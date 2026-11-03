#!/usr/bin/env python3
"""Build the DGL BY RJ Vault (Skool) classroom materials from curriculum.json.

  python rebrand/skool/build_skool.py render
      Writes classroom_master_list.md, ready to paste. No API key needed.

  python rebrand/skool/build_skool.py lessons --classroom 02 [--module 1] [--limit 3]
      Writes a full lesson for every lesson title, using Claude, into lessons/<classroom>/.
      Lessons that already exist are skipped, so nothing gets overwritten.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CURRICULUM = HERE / "curriculum.json"
MODEL = "claude-opus-5-5"


def load() -> dict:
    return json.loads(CURRICULUM.read_text(encoding="utf-8"))


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #
def render(cur: dict) -> Path:
    by_id = {c["id"]: c for c in cur["classrooms"]}
    out = [f"# {cur['community']}: Classroom Master List",
           f"*{cur['tagline']}*\n",
           "> **Status: proposed structure.** None of this has been created in Skool yet. "
           "Build it in a hidden/draft course first (see `../06_30_day_roadmap.md`).\n",
           "In Skool's editor, each classroom below is a **course**, each module is a **set** (folder), "
           "and each lesson is a **module** (page).\n",
           "## Learning paths\n"]
    for path, ids in cur["learning_paths"].items():
        out.append(f"- **{path}:** " + " → ".join(f"{i} {by_id[i]['name'].split(':')[0]}" for i in ids))
    total_lessons = sum(len(m["lessons"]) for c in cur["classrooms"] for m in c["modules"])
    out.append(f"\n**{len(cur['classrooms'])} classrooms · "
               f"{sum(len(c['modules']) for c in cur['classrooms'])} modules · {total_lessons} lessons**\n")

    for c in cur["classrooms"]:
        out += [f"\n---\n\n## {c['id']} · {c['name']}",
                f"**Cover text:** `{c['cover_text']}` · **Level:** {c['level']}\n",
                "**Classroom description (paste into Skool):**", f"> {c['description']}\n",
                f"**Learning outcome:** {c['learning_outcome']}\n"]
        for mi, m in enumerate(c["modules"], 1):
            out.append(f"**Module {mi}: {m['name']}**")
            out += [f"{mi}.{li}. {l}" for li, l in enumerate(m["lessons"], 1)]
            if m.get("assignment"):
                out.append(f"\n*Assignment:* {m['assignment']}")
            out.append("")
        out.append("**Resources:** " + "; ".join(c["resources"]))

    path = HERE / "classroom_master_list.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# lessons (Claude)
# --------------------------------------------------------------------------- #
def write_lessons(cur: dict, classroom_id: str, module_no: int | None, limit: int | None) -> None:
    import anthropic
    from pydantic import BaseModel, Field

    class Step(BaseModel):
        title: str
        instructions: str = Field(description="Clear, detailed, beginner-friendly instructions")

    class Lesson(BaseModel):
        title: str
        objective: str = Field(description="What the member can do after this lesson, one sentence")
        intro_script: str = Field(description="What RJ says on camera to open the lesson, 60-120 words, in RJ's voice")
        key_concepts: list[str]
        steps: list[Step]
        example_prompts: list[str] = Field(description="General teaching examples labeled as examples; never claim they are RJ's tested prompts")
        common_mistakes: list[str]
        assignment: str
        resources: list[str]
        rj_to_add: list[str] = Field(description="Things only RJ can supply: tested prompts, screen recordings, personal examples, current app names")

    brand = json.loads((ROOT / "brand.json").read_text(encoding="utf-8"))
    c = next((x for x in cur["classrooms"] if x["id"] == classroom_id), None)
    if not c:
        sys.exit(f"No classroom {classroom_id}. Options: {[x['id'] for x in cur['classrooms']]}")

    system = f"""You are the Curriculum Architect for {brand['brand_name']} ({brand['positioning']}), founded by {brand['creator_name']}.
Method: {brand['method']}. Community: {brand['community']} on {brand['community_platform']}.
Audience: {brand['audience']}. Voice: {brand['voice']}

Write complete, detailed, actionable Skool lessons that beginners can follow step by step.
Rules:
- Teach the technique so it works in any app. Name current apps only as examples, because apps and models change.
- Never present a prompt as RJ's own tested prompt or code. Write general examples, and list in rj_to_add every spot where RJ's tested version should go.
- Never invent student results, earnings, testimonials or personal stories. No income promises.
- Keep Drama AI and Relationship AI material separate.
- Visual references follow the brand: black, white and chrome silver. Never purple or hot pink."""

    client = anthropic.Anthropic(max_retries=4)
    out_dir = HERE / "lessons" / f"{c['id']}-{slug(c['name'])}"
    done = 0
    for mi, m in enumerate(c["modules"], 1):
        if module_no and mi != module_no:
            continue
        for li, title in enumerate(m["lessons"], 1):
            if limit and done >= limit:
                return
            path = out_dir / f"{mi:02d}-{li:02d}-{slug(title)}.md"
            if path.exists():
                print(f"skip (exists) {path.relative_to(ROOT)}")
                continue
            print(f"writing {c['id']} · {mi}.{li} {title}")
            resp = client.beta.messages.parse(
                model=MODEL,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": (
                    f"Classroom: {c['name']}: {c['description']}\n"
                    f"Classroom outcome: {c['learning_outcome']}\n"
                    f"Module {mi}: {m['name']} (lessons: {', '.join(m['lessons'])})\n"
                    f"Module assignment: {m.get('assignment', '')}\n\n"
                    f"Write lesson {mi}.{li}: \"{title}\"."
                )}],
                output_format=Lesson,
                output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            if resp.stop_reason in ("refusal", "max_tokens"):
                print(f"  stopped ({resp.stop_reason}); skipping")
                continue
            lesson: Lesson = resp.parsed_output
            md = [f"# {mi}.{li} {lesson.title}", f"*{c['name']} → Module {mi}: {m['name']}*\n",
                  f"**Objective:** {lesson.objective}\n", "## Intro (RJ on camera)", lesson.intro_script,
                  "\n## Key concepts", *[f"- {k}" for k in lesson.key_concepts], "\n## Step by step"]
            for si, s in enumerate(lesson.steps, 1):
                md += [f"\n### Step {si}: {s.title}", s.instructions]
            md += ["\n## Example prompts", *[f"```\n{p}\n```" for p in lesson.example_prompts],
                   "\n## Common mistakes", *[f"- {x}" for x in lesson.common_mistakes],
                   "\n## Assignment", lesson.assignment,
                   "\n## Resources", *[f"- {r}" for r in lesson.resources],
                   "\n## RJ to add before publishing", *[f"- [ ] {r}" for r in lesson.rj_to_add]]
            out_dir.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(md) + "\n", encoding="utf-8")
            done += 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("render")
    lp = sub.add_parser("lessons")
    lp.add_argument("--classroom", required=True, help="e.g. 02")
    lp.add_argument("--module", type=int)
    lp.add_argument("--limit", type=int)
    args = ap.parse_args()
    cur = load()
    if args.cmd == "render":
        print(f"wrote {render(cur).relative_to(ROOT)}")
    else:
        write_lessons(cur, args.classroom, args.module, args.limit)


if __name__ == "__main__":
    main()
