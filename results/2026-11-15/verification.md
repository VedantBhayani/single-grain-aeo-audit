# Re-check of the Oct 14 findings, Nov 15, 2026

Were the October findings real, and are they still live a month later? This re-check was run on 2026-11-15 (about 13:40 UTC) against the live site. It uses separate code ([`verify_live.py`](verify_live.py)): plain downloads and text search, with none of the audit's parsing, and 2 s between requests.

Re-run the same day at about 15:20 UTC after a review found that the first version didn't check robots.txt and sent a generic browser User-Agent. The script now honours robots.txt (singlegrain.com allows every path checked here) and identifies itself. The results were identical, and this time all 10 of the Oct 14 404s were re-checked, not 8.

```bash
python results/2026-11-15/verify_live.py results/2026-10-14/aeo/findings.csv
```

## Result: every finding re-checked is still live

### The 2011 Harvard Business Review study: 9 of 9 posts still link it

Each post still links `hbr.org/2011/03/the-short-life-of-online-sales-leads` once.

| Post | Status | Last modified |
|---|---|---|
| /blog-posts/five-step-reliable-marketing-bots/ | 200 | 2026-09-25 |
| /blog-posts/forward-deployed-marketer/ | 200 | 2026-10-16 |
| /blog-posts/how-to-hire-or-build-ai-marketing-agents-that-own-pipeline-jobs-without-a-chatbot-demo/ | 200 | 2026-10-14 |
| /blog-posts/marketing-agent-pipeline-raci/ | 200 | 2026-09-25 |
| /blog-posts/slas-kill-switches-managed-marketing-agents/ | 200 | 2026-10-14 |
| /blog-posts/specialized-marketing-llms-pipeline-jobs/ | 200 | 2026-09-25 |
| /blog-posts/startups-test-thousands-of-ads/ | 200 | 2026-10-14 |
| /blog-posts/which-ai-marketing-services-to-buy-when-you-need-pipeline-not-another-content-calendar/ | 200 | 2026-10-14 |
| /blog-posts/which-marketing-jobs-a-founder-can-hand-gpt-6-astra-for-a-full-day-before-hiring/ | 200 | 2026-10-14 |

This is the study Eric read out in the AEO webinar ([youtu.be/45AWhSkkaQ4](https://youtu.be/45AWhSkkaQ4), transcript lines 636-641): "a 2011 maybe that's a little too old… we only want stuff after 2020… an audit of 2241 US companies". The 2,241-company audit is the HBR study.

### Pipeline instructions published as article text: 4 of 4 still live

On Oct 14 each of these posts contained: "Together with the embedded scene above, that is three on-angle Eric tape inputs for this job, not a link dump." The script searches each live page for the first pipeline phrase in that sentence ("on-angle"), and it is still there on all 4. The raw output of the 15:20 re-run is in [`verify_live_output.txt`](verify_live_output.txt).

- /blog-posts/ai-overview-query-capture-playbook/
- /blog-posts/brand-equity-citation-hygiene-llms/
- /blog-posts/technical-seo-for-llm-scrapers/
- /blog-posts/content-attention-to-pipeline-conversion/

### Internal links that returned 404 on Oct 14: 10 of 10 still return 404

10 distinct URLs returned 404 on Oct 14 (the first run re-checked 8; the 15:20 re-run checked all 10):

- /agency/managed-marketing-agents/
- /artificial-intelligence/company-brain-stop-agents-guessing-icp/
- /artificial-intelligence/crm-field-contracts-marketing-agent-outputs/
- /artificial-intelligence/how-many-agent-jobs-before-hire-human/
- /artificial-intelligence/how-to-price-managed-marketing-agents-without-guessing-margin/
- /artificial-intelligence/incident-response-agent-ships-bad-copy/
- /artificial-intelligence/landing-page-creative-claim-consistency/
- /artificial-intelligence/lead-qualify-handoff-contracts-before-human/
- /artificial-intelligence/marketing-agent-eval-harness-before-crm/
- /artificial-intelligence/prompt-version-pinning-specialized-marketing-llms/

## What this does and doesn't show

- It shows the October findings were real, and that none of the re-checked ones have been fixed in a month.
- It doesn't show who or what wrote these posts. "The AEO pipeline's posts" means posts in the flat `/blog-posts/<slug>/` format Eric showed on camera.
- Posts published since Nov 10 passed the hard checks in a test run of the new watcher on Nov 15. Newer posts look cleaner; the older ones above are unchanged.
