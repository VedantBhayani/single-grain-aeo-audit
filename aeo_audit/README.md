# AEO post audit and pre-publish gate

Checks posts on singlegrain.com against what Eric Siu said on camera about his AEO bot, plus a few objective defects. Every check is labelled as one of:
- something he said on camera, with his exact words
- his team's review criteria
- a defect that is not a rule he stated

## Two ways to run it

```bash
# Everything in /blog-posts/ updated since a date -> results/<today>/aeo/{report.md, findings.csv, posts.csv}
python aeo_audit/audit.py run --since 2026-08-01

# Gate one page before it publishes: a preview URL or a saved .html file. Exit code 1 = don't publish.
python aeo_audit/audit.py check path/to/draft.html
```

## Checks

| Check | Kind | In `check` |
|---|---|---|
| Pre-2020 source (year in the text, or in a linked URL's path) | Eric, as an idea: "maybe I need to refine a little bit and say, hey, we only want stuff after 2020" | **hard fail** |
| A cited YouTube video doesn't resolve | related to Eric's "real statistics… or are you just making stuff up?" gate (checks the video exists, not the stat) | **hard fail** |
| His video linked but not embedded | Eric: "embed that part of the YouTube video inside of the blog post" | warning |
| No images | Eric: "are we putting in images in there as well" | warning |
| Claimed stat ("a study found…") with no link in its paragraph | His team: "stats must already be named… hyperl[inked]" | warning |
| Pipeline instructions published as article text | defect | warning |
| Internal link that 404s or redirects | defect | warning |
| Video link without a timestamp | defect (reading of "that part") | warning |
| No link to a service page | defect (he called them "always helpful") | warning |
| No table of contents | defect | warning |
| Same 15+ word passage in 3+ posts | defect (site-wide `run` only) | n/a |

**Not checked:** title promise, fake anonymized reviews, robotic voice. These are judgment calls from his team's review. They'd need a classifier, and a classifier would need hand-labelled posts first to measure how often it's right. Until then, no score is reported.

**Sources:**
- Quotes are from his AEO webinar (published Oct 1, 2026) ([youtu.be/45AWhSkkaQ4](https://youtu.be/45AWhSkkaQ4)) and his team-review webinar ([youtu.be/O2D8DvQ6zWA](https://youtu.be/O2D8DvQ6zWA)).
- The line numbers in `audit.py` refer to auto-generated transcripts, which have no timestamps.

## How it decides

**Pre-2020 sources**
- Any year from 1950 to 2019 in the article text counts, and so does a year in a linked URL's path (e.g. `hbr.org/2011/03/...`).
- Years inside a link's query or slug don't count (e.g. `...-2000-icp`).
- A pre-2020 year can be legitimate history. Every hit is listed for a person to judge.

**Videos**
- Videos come from `youtube.com/watch`, `/embed`, `/shorts` and `youtu.be` links.
- "Resolves" means YouTube's public oEmbed endpoint returns the video. That doesn't prove the video says what the post claims.

**Internal links**
- A link fails if it doesn't return 200 at the same URL, so redirects count.

**Service pages**
- `/agency/…`, `/services/…`, or anything in `service-sitemap.xml`. The live `/agency/` pages aren't in any sitemap, so the path rule is needed.

**Pipeline leak phrases**
- The list is seeded from text found live on 2026-10-13: "tape inputs", "link dump", "on-angle", "this job, not", "as instructed", "per the brief".
- Extend it as new leaks turn up.

**The post body**
- The first `<article class="container post-…">` up to the author box. For a draft without that wrapper, the whole page.

## Using it in a pipeline

The skill file in [`skill/SKILL.md`](skill/SKILL.md) tells an agent (Grok Bot, Codex, Claude Code) when to run the gate and what to do with the result. It never edits a post. It only reports what's wrong and where.
