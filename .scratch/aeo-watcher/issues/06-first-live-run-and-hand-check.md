Type: task
Status: claimed
Blocked by: 03, 05

## Question

Do the first live run on posts since 2026-10-14. Vedant hand-checks 3 findings against the live pages before the link goes to anyone. Record the counts, the cost and what was wrong. (HITL)

## Progress

- Run 1 (Actions 43721191939, 13:51 UTC): green; 97 posts checked; 11 issues opened; 9 Parallel calls ($0.009). Reading it line by line found 1 false positive (#9: an example sentence's 2019), a prose year on #8, and an AI step that showed sources when p < 0.5 and let the old HBR article back in via ?page=3 or web.archive.org.
- Fixed in ce951a9 with 3 regression tests (32/32 pass).
- Run 2 (Actions 43722522198, 14:06 UTC): 97 re-scored, not re-fetched (52 s: the shared 24 h fetch cache served Run 1's pages; fixed in ticket 07); 10 failing; #9 closed automatically, plus an explanatory comment. Pages shows 10.
- The private video on #7 was confirmed on YouTube's own page (\"Private video\").
- **Waiting on Vedant's hand check of 3 findings: #1, #7, #8.**
