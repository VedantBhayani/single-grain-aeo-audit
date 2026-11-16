Type: task
Status: resolved
Blocked by: 03, 05

## Question

Do the first live run on posts since 2026-10-14. Vedant hand-checks 3 findings against the live pages before the link goes to anyone. Record the counts, the cost and what was wrong. (HITL)

## Progress

- Run 1 (Actions 43721191939, 13:51 UTC): green; 97 posts checked; 11 issues opened; 9 Parallel calls ($0.009). Reading it line by line found 1 false positive (#9: an example sentence's 2019), a prose year on #8, and an AI step that showed sources when p < 0.5 and let the old HBR article back in via ?page=3 or web.archive.org.
- Fixed in ce951a9 with 3 regression tests (32/32 pass).
- Run 2 (Actions 43722522198, 14:06 UTC): 97 re-scored, not re-fetched (52 s: the shared 24 h fetch cache served Run 1's pages; fixed in ticket 07); 10 failing; #9 closed automatically, plus an explanatory comment. Pages shows 10.
- The private video on #7 was confirmed on YouTube's own page (\"Private video\").
- Hand check (Vedant, Nov 15, all 10 open findings, not just 3): [results/2026-11-15/hand-check.md](../../../results/2026-11-15/hand-check.md). 0 wrong. After Claude re-fetched the posts to build the rule, #1 turned out to label its stat as old too (Vedant re-checked it on the live page), so the corrected result is 5 true and 5 weak (the post itself calls the 2011 HBR stat historical or older). By real GitHub issue number (hand-check.md swapped four of them; see its correction section): true #6, #7, #8, #10, #11; weak #1, #2, #3, #4, #5.
- Run 43736721359 (16:57 UTC, `since 2026-10-14`, 97 posts fetched fresh): failing 5, fixed 5, 0 errors. Issues #1-#5 closed, each with a comment linking the hand check; #6, #7, #8, #10, #11 open. Dashboard shows 5. #7 is "Video unavailable" (not "private"). #11's stat is Reichheld/Bain from the 1990s behind a 2014 HBR link.
- Nov 16: Vedant saw on the live page that #6 (forward-deployed-marketer) labels its HBR stat as old too, in a chart image titled "Historical benchmark…" and the next paragraph ("historical lead-response rates"). The hand check missed it; the watcher can't read image text, and its rule reads only the stat's paragraph. Vedant's call: #6 is labelled as old, no code change before the interview, #6 stays open as a known limit. See the Nov 16 addendum in hand-check.md and [fdm_chart.txt](../../../results/2026-11-15/labelled-old-check/fdm_chart.txt).

## Answer

The findings are real; none is wrong. The watcher couldn't tell a stale stat presented as current from one the writer labels as old, so a rule now makes the labelled ones warnings (`labelled_old` in watch.py, tested on the real paragraphs). Honest headline: 4 real problems (#7, #8, #10, #11); the watcher still shows 5, because #6 labels its stat as old only in a chart image and the next paragraph.
