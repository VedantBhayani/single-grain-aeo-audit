# Hand check of every watcher finding, 2026-11-15

Done by Vedant Bhayani on the live pages, in Chrome, one post at a time. Claude guided each step and recorded the results here; Vedant did the looking.

**Method**, per post:
- On the normal page, Ctrl+F the year to read the sentence in context.
- In the page source (Ctrl+U), Ctrl+F the link URL and count the matches.
- Mark each finding: ✅ true (an old source presented as current), ⚠️ weak (it's there, but the post says itself that the data is old), or ❌ wrong (not there, or misread).

Ctrl+F on the normal page only finds visible text, not link targets. That's why each link was counted in the page source.

## Result

- **10 open findings:** 6 ✅ true, 4 ⚠️ weak, 0 ❌ wrong.
- **The closed false positive (#9)** was correctly closed.

| Issue | Post | Verdict |
|---|---|---|
| #8 | /blog-posts/pay-per-click/alternative-ad-networks/ | ✅ |
| #7 | /blog-posts/i-fired-my-youtube-team-here-is-what-ai-youtube-automation-did-to-my-views/ | ✅ |
| #1 | /blog-posts/how-to-hire-or-build-ai-marketing-agents-that-own-pipeline-jobs-without-a-chatbot-demo/ | ✅ |
| #5 | /blog-posts/forward-deployed-marketer/ | ✅ (borderline) |
| #10 | /blog-posts/saas-landing-page-examples/ | ✅ |
| #11 | /blog-posts/client-retention-strategies/ | ✅ |
| #2 | /blog-posts/startups-test-thousands-of-ads/ | ⚠️ |
| #3 | /blog-posts/slas-kill-switches-managed-marketing-agents/ | ⚠️ |
| #4 | /blog-posts/which-ai-marketing-services-to-buy-when-you-need-pipeline-not-another-content-calendar/ | ⚠️ |
| #6 | /blog-posts/which-marketing-jobs-a-founder-can-hand-gpt-6-astra-for-a-full-day-before-hiring/ | ⚠️ |
| #9 (closed) | humanizer rubric post | ✅ closing it was right |

**What it changes:** the watcher can't tell a stale stat from one the writer openly labels as historical. 4 of the 6 HBR 2011 posts label it. The honest headline is 6 real problems, not 10. Proposed rule change: a pre-2020 stat whose sentence, or the next sentence, labels it as old ("historic", "historical", "older", "not a current") becomes a warning, not a hard failure. The 4 sentences below become the test.

## Per post (quotes as Vedant read them on the live page)

### #8: WordStream 2015–2017 links: ✅
- **Page source:** `wordstream.com/blog/ws` had 3 matches, with /2015/, /2016/ and /2017/ in the paths.
- **Normal page:** "benchmark" isn't visible text; the links use other words.
- **Parallel's suggested replacements** both load:
  - https://www.wordstream.com/blog/2026-google-ads-benchmarks
  - https://www.wordstream.com/blog/facebook-ads-benchmarks-2026

### #7: cited YouTube video: ✅
- **Page source:** `D5MeFtrnuOE` had 4 matches.
- **YouTube's own page:** "Video unavailable" (earlier wording said "private"; the correct claim is unavailable, private or deleted).

### #1: HBR 2011: ✅
- **Sentence:** "Harvard Business Review's 2011 report described an audit of 2,241 U.S. companies, and 37% responded to a web lead within an hour."
- **Labelled as old:** no.
- **`hbr.org/2011` matches:** 1.

### #2: HBR 2011: ⚠️
- **Sentence:** "…the historic Harvard Business Review audit of 2,241 U.S. companies found that 37% responded to a web lead within an hour, while 23% never responded."
- **Labelled as old:** yes, "historic".
- **`hbr.org/2011` matches:** 1.

### #3: HBR 2011: ⚠️
- **Sentence:** "…HBR['s audit] of 2,241 US companies reported that 37% responded to a web-generated test lead within an hour, while 23% never responded. These are historical 2011 inbound response findings and not outbound agent [benchmarks]. Use them to justify staff use and escalation coverage."
- **Labelled as old:** yes.
- **`hbr.org/2011` matches:** 1.

### #4: HBR 2011: ⚠️
- **Sentence:** "Harvard Business Review's 2011 audit of 2,241 U.S. companies found that 37% responded to a web lead within an hour, while 23% never responded. This is an older operational warning, not a current AI benchmark."
- **Labelled as old:** yes.
- **`hbr.org/2011` matches:** 1.

### #5: HBR 2011: ✅ (borderline)
- **Sentence:** "For supporting evidence, a 2011 Harvard Business Review article reported an audit of 2,241 U.S. companies: 37% responded to a web-generated test lead within an hour, while 23% never responded. Those were inbound inquiries, not stalled opportunities. The findings justify auditing follow-up gaps; they do not predict this agent's conversion lift."
- **Labelled as old:** no. It limits what the study proves but never says the data is old.
- **`hbr.org/2011` matches:** 1.

### #6: HBR 2011: ⚠️
- **Sentence:** "Harvard Business Review's 2011 research on online sales leads associated faster contact with greater qualification likelihood. That older evidence supports inspecting response handling, not promising a conversion lift from this audit."
- **Labelled as old:** yes.
- **`hbr.org/2011` matches:** 1.

### #10: Nielsen Norman Group 2018: ✅
- **Sentence:** "In a 2018 eyetracking study on scrolling and attention from Nielsen Norman Group, people spent about 57% of their page-viewing time above the fold and 74% in the first two screens. Attention dropped sharply after the fold."
- **Labelled as old:** no. It's presented as current fact.
- **`nngroup.com` matches:** 1. The link (nngroup.com/articles/scrolling-and-attention/) has no year; the year came from the sentence.
- **Known weakness:** Parallel's "newer" suggestion is the same NN/g article.

### #11: HBR 2014 / Bain: ✅
- **Sentence:** "Research from Bain & Company's Frederick Reichheld found that a 5% increase in customer retention can lift profits by 25% to 95%." The link goes to hbr.org/2014/10/the-value-of-keeping-the-right-customers, and the post also links Reichheld's original Bain brief.
- **Labelled as old:** no. The TL;DR repeats it as current.
- **`hbr.org/2014` matches:** 1.
- **Note:** the stat comes from Reichheld's Bain research from the 1990s, so it's older than the 2014 in the URL.
- **Known weakness:** one Parallel suggestion was a Studocu page.

### #9 (closed false positive): ✅ closing was correct
- **Sentence:** "After: 'The company launched its first programmatic ad campaign in 2019.'"
- This is a made-up example in a writing rubric ("Before and After Examples From the Rubric"), not a cited source.

## Addendum, same day: #1 is labelled old too (added by Claude; the text above is unchanged)

Before building the rule, Claude fetched the 6 HBR posts again (read-only) to test it on the real text, and found that #1 does label its stat as old, two sentences after the number:

> "Harvard Business Review's 2011 report described an audit of 2,241 U.S. companies: 37% responded to a web lead within an hour, while 23% never responded. This is historical evidence, not a current industry baseline."

- **Re-checked by Vedant** on the live page (Ctrl+F `2,241`, then the next sentence): the sentence is there. **#1 is ⚠️ weak, not ✅.**
- **Not a site change:** every one of the 6 posts still shows its Oct 14–16 modified time, so the text was there during the hand check; the label was missed because it sits after the number, not beside it.
- **Exact live wording** for two of the quotes above (same meaning): #2 reads "A historical Harvard Business Review audit… These are 2011 findings, not current Meta benchmarks."; #3 ends "…Use them to justify staffed queues and escalation coverage."

**Corrected result: 5 ✅ true (#5, #7, #8, #10, #11), 5 ⚠️ weak (#1, #2, #3, #4, #6), 0 ❌ wrong.** The honest headline is 5 real problems.

**The rule change** (`aeo_watch/watch.py`, `labelled_old`): a pre-2020 stat, or the dated link in its sentence, whose sentence or next sentence says "historic(al)", "not (a) current", or "older" + an evidence word ("older evidence", "older operational warning") becomes the warning "Pre-2020 stat, labelled as old by the post". Run against all 10 live posts: #1 #2 #3 #4 #6 become warnings; #5 #7 #8 #10 #11 stay hard. The test uses the real paragraphs. The pre-publish gate is unchanged: it still blocks any pre-2020 source in a draft.

Evidence, with the scripts that produced it, in [`labelled-old-check/`](labelled-old-check/): `hbr_context.txt` (the live paragraph around each HBR link), `modtimes.txt` (modified dates then and now: unchanged), `rule_live.txt` (the rule run on all 10 live posts).

## Not checked

The 3 posts last modified Sep 25 that also cite HBR 2011 (listed in `verification.md`). The watcher skips them because of the 2026-10-14 baseline.
