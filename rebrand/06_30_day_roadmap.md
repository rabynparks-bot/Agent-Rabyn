# 30-Day Implementation Roadmap

**Approach: build first, then migrate.** Build the new Vault structure and materials alongside the current community, so current members aren't disrupted. Then switch over in one planned move.

## Week 1: Audit and foundation
- [ ] RJ sends Skool screenshots of the current classrooms, modules and lessons, plus pricing and levels
- [ ] RJ sends the Instagram export (`posts_1.json`)
- [ ] RJ sends tested prompts and codes, and logo or brand assets
- [ ] Claude maps each current classroom to keep, merge, rename or retire, **for RJ's approval** (`01_audit.md`)
- [ ] Run the Instagram agent on 10 posts and review the tone
- [ ] Make the new logo and covers in black, white and chrome (`02_brand_blueprint.md`)

## Week 2: Build the new Vault (hidden)
- [ ] In Skool, create the new courses as **unpublished/drafts**, or set them to a level only RJ has
- [ ] Paste the classroom names and descriptions from `skool/classroom_master_list.md`
- [ ] Generate full lessons for 01 START HERE and 02 THE PROMPTING LAB:
      `python rebrand/skool/build_skool.py lessons --classroom 01` (then `--classroom 02`)
- [ ] RJ fills in every `[RJ TO ADD]` item and records the intro videos
- [ ] Upload classroom covers

## Week 3: Rebrand Instagram
- [ ] Run the agent on all posts and paste the new captions, working one pillar at a time
- [ ] Update the bio, name field and link
- [ ] Rebuild Highlights: START · VAULT · DRAMA · LOVE · HOW TO · P2P · CEO · WINS
- [ ] Pin the 3 chosen posts
- [ ] Generate lessons for 03, 04, 05 and 06, and RJ reviews them

## Week 4: Launch and migrate
- [ ] Day 22: tell current members the new Vault is coming (and what stays the same for them)
- [ ] Day 24: publish the new courses, and archive or hide old ones (**only those RJ approved**)
- [ ] Day 25–29: run the 5-day Story campaign and post the reveal Reel and carousel (`04_marketing_strategy.md`)
- [ ] Turn on the onboarding flow: membership questions and welcome DM (`05_onboarding.md`)
- [ ] Day 30: review the numbers (new members, Day-7 first wins, Reel reach) and plan next month

## After day 30: ongoing maintenance (Phase 7)
- **Weekly:** run the agent on new posts and follow the content calendar
- **Monthly:** update the App Vault update log, add or refresh 2–4 lessons, feature Showcase wins
- **Quarterly:** check every classroom against its learning outcome and retire anything outdated
- **Remaining lessons (07–14):** generate and review 2 classrooms a week
