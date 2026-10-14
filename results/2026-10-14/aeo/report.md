# What shipped vs the rules: singlegrain.com /blog-posts/

Run 2026-10-14T08:48+00:00 UTC on 48 live posts (sitemap lastmod >= 2026-08-01). Public pages only.

**flat** = `/blog-posts/<slug>/`, the format of the posts Eric showed on camera. **nested** = `/blog-posts/<category>/<slug>/`.

| Check | Kind | Flat posts failing | Nested posts failing |
|---|---|---|---|
| Pre-2020 source | Eric, stated (as an intended fix) | 9 of 40 | 0 of 8 |
| His video linked, not embedded | Eric, a gate he described (he also says 'sometimes it'll embed the video') | 28 of 40 | 0 of 8 |
| Cited video does not resolve | Eric, a gate he described | 0 of 40 | 0 of 8 |
| No images in the body | Eric, a gate he described | 0 of 40 | 0 of 8 |
| Claimed stat with no link in its paragraph | his team's criteria | 0 of 40 | 1 of 8 |
| Pipeline instructions published as article text | defect, not a stated rule | 4 of 40 | 0 of 8 |
| Internal link that 404s or redirects | defect, not a stated rule | 19 of 40 | 2 of 8 |
| Same 15+ word passage in 3+ posts | defect (his gate is about repeating a topic; reused passages are an extension) | 20 of 40 | 0 of 8 |
| Video link has no timestamp | defect (a reading of 'that part', not his words) | 37 of 40 | 0 of 8 |
| No link to a service page | defect (he called them helpful, not a rule) | 27 of 40 | 8 of 8 |
| No table of contents | defect (an observation, not a rule) | 0 of 40 | 0 of 8 |
| Title promise drift | his team's criteria | not checked (needs human labels first) | |
| Fake anonymized reviews | his team's criteria | not checked (needs human labels first) | |
| Robotic voice | his team's criteria | not checked (needs human labels first) | |

## Where each check comes from

- **Pre-2020 source** (Eric, stated (as an intended fix)): "a 2011 maybe that's a little too old right maybe I need to refine a little bit and say hey we we only want stuff after 2020" (youtu.be/45AWhSkkaQ4 L635-639)
- **His video linked, not embedded** (Eric, a gate he described (he also says 'sometimes it'll embed the video')): "if Eric actually talked about this, and this is in a YouTube video, why don't we just embed that part of the YouTube video inside of the blog post?" (youtu.be/45AWhSkkaQ4 L285-289)
- **Cited video does not resolve** (Eric, a gate he described): "do you actually have real statistics to back this up or are you just making stuff up?" (youtu.be/45AWhSkkaQ4 L282-284)
- **No images in the body** (Eric, a gate he described): "are we putting in images in there as well" (youtu.be/45AWhSkkaQ4 L289-291)
- **Claimed stat with no link in its paragraph** (his team's criteria): "stats must already be named. They must be hyperl[inked]" (youtu.be/O2D8DvQ6zWA L318-321)
- **Pipeline instructions published as article text** (defect, not a stated rule)
- **Internal link that 404s or redirects** (defect, not a stated rule)
- **Same 15+ word passage in 3+ posts** (defect (his gate is about repeating a topic; reused passages are an extension)): "have we actually published this piece of content before? ... you don't want to publish more duplicate content" (youtu.be/45AWhSkkaQ4 L277-282)
- **Video link has no timestamp** (defect (a reading of 'that part', not his words)): "embed that part of the YouTube video" (youtu.be/45AWhSkkaQ4 L285-289)
- **No link to a service page** (defect (he called them helpful, not a rule)): "internal links to our services pages, right? ... Those are always helpful." (youtu.be/45AWhSkkaQ4 L624-627)
- **No table of contents** (defect (an observation, not a rule)): "here's a table of contents down here, which should probably honestly go higher" (youtu.be/45AWhSkkaQ4 L596-598)
- **Title promise drift** (his team's criteria): "the title must pay a promise" (youtu.be/O2D8DvQ6zWA L318-319)
- **Fake anonymized reviews** (his team's criteria): "fake anonymized reviews" (youtu.be/O2D8DvQ6zWA L342-344)
- **Robotic voice** (his team's criteria): "robotic voice" (youtu.be/O2D8DvQ6zWA L345)

## Examples (first 3 per check; all in findings.csv)

### No link to a service page (35)
- https://www.singlegrain.com/blog-posts/analytics/server-side-tracking-when-its-worth-the-cost/: 6 internal links, none to /agency/, /services/ or the service sitemap
- https://www.singlegrain.com/blog-posts/analytics/funnel-analysis-find-leaks-and-fix-bad-data-first/: 5 internal links, none to /agency/, /services/ or the service sitemap
- https://www.singlegrain.com/blog-posts/analytics/marketing-mix-modeling-for-mid-market-brands-a-skeptics-guide/: 4 internal links, none to /agency/, /services/ or the service sitemap

### Internal link that 404s or redirects (49)
- https://www.singlegrain.com/blog-posts/analytics/funnel-analysis-find-leaks-and-fix-bad-data-first/: https://www.singlegrain.com/marketing-funnels/tools-to-optimize-your-funnels-raghav/ -> 200 (redirects to https://www.singlegrain.com/blog/how-to-create-marketing-funnel/)
- https://www.singlegrain.com/blog-posts/agency-2x2-productize-vs-stop/: https://www.singlegrain.com/artificial-intelligence/how-many-agent-jobs-before-hire-human/ -> 404
- https://www.singlegrain.com/blog-posts/agency-2x2-productize-vs-stop/: https://www.singlegrain.com/artificial-intelligence/how-to-hire-or-build-ai-marketing-agents-that-own-pipeline-jobs-without-a-chatbot-demo/ -> 200 (redirects to https://www.singlegrain.com/blog-posts/how-to-hire-or-build-ai-marketing-agents-that-own-pipeline-jobs-without-a-chatbot-demo/)

### Claimed stat with no link in its paragraph (2)
- https://www.singlegrain.com/blog-posts/analytics/net-revenue-retention-calculation-rules-investors-test/: Growth-stage ($5M–$50M ARR): Reported ranges tend to cluster roughly between 100% and 120%, with product-led expansion models sitting toward the higher end.
- https://www.singlegrain.com/blog-posts/analytics/net-revenue-retention-calculation-rules-investors-test/: Scale-stage ($50M+ ARR): Top-quartile companies in this range frequently report 110% to 130%+.

### His video linked, not embedded (28)
- https://www.singlegrain.com/blog-posts/agency-2x2-productize-vs-stop/: 4 video(s) linked, 0 players embedded
- https://www.singlegrain.com/blog-posts/forward-deployed-marketer/: 7 video(s) linked, 0 players embedded
- https://www.singlegrain.com/blog-posts/specialized-marketing-llms-pipeline-jobs/: 6 video(s) linked, 0 players embedded

### Video link has no timestamp (154)
- https://www.singlegrain.com/blog-posts/agency-2x2-productize-vs-stop/: https://www.youtube.com/watch?v=x7uxtQMNjiE
- https://www.singlegrain.com/blog-posts/agency-2x2-productize-vs-stop/: https://www.youtube.com/watch?v=SrTAYem7OEs
- https://www.singlegrain.com/blog-posts/agency-2x2-productize-vs-stop/: https://www.youtube.com/watch?v=GkwhXu4ftM4

### Pre-2020 source (18)
- https://www.singlegrain.com/blog-posts/forward-deployed-marketer/: 2011: For supporting evidence, a 2011 Harvard Business Review article reported an audit of 2,241 U.S.
- https://www.singlegrain.com/blog-posts/forward-deployed-marketer/: link https://hbr.org/2011/03/the-short-life-of-online-sales-leads
- https://www.singlegrain.com/blog-posts/specialized-marketing-llms-pipeline-jobs/: 2011: Harvard Business Review’s 2011 audit of 2,241 U.S.

### Pipeline instructions published as article text (4)
- https://www.singlegrain.com/blog-posts/ai-overview-query-capture-playbook/: Together with the embedded scene above, that is three on-angle Eric tape inputs for this job, not a link dump.
- https://www.singlegrain.com/blog-posts/brand-equity-citation-hygiene-llms/: Together with the embedded scene above, that is three on-angle Eric tape inputs for this job, not a link dump.
- https://www.singlegrain.com/blog-posts/technical-seo-for-llm-scrapers/: Together with the embedded scene above, that is three on-angle Eric tape inputs for this job, not a link dump.

### Same 15+ word passage in 3+ posts (13)
- 5 posts: https://www.singlegrain.com/blog-posts/agent-job-cards-definition-of-done/ https://www.singlegrain.com/blog-posts/brand-equity-citation-hygiene-llms/ h: single brain installs the system single grain runs it when you need the team single brain is the ai implementation os for job specific agents evaluations and kill switches
- 5 posts: https://www.singlegrain.com/blog-posts/churn-signals-hubspot-slack-stripe-agent/ https://www.singlegrain.com/blog-posts/how-to-find-the-best-instagram-: if the note lives in a random slack thread next week starts from folklore again
- 5 posts: https://www.singlegrain.com/blog-posts/ai-content-agent-rewrite-riskier-than-thin-claim/ https://www.singlegrain.com/blog-posts/churn-signals-hubspot-s: teams that cannot refuse end up automating noise and then blaming the model for being unreliable when the real failure was missing judgment

