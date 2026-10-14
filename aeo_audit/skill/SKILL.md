---
name: aeo-pre-publish-gate
description: Before an AEO/SEO blog draft goes live on singlegrain.com, run the gate on its preview URL or saved HTML. Do not publish on a hard failure. Send warnings to the human reviewer with the draft.
---

# AEO pre-publish gate

## When

After a draft is complete and before it's published through WordPress (WP Vibe or any other route).

## How

```bash
python aeo_audit/audit.py check <preview-url-or-draft.html>
```

## What to do with the result

- **Exit code 1 (hard failure):** don't publish. The output names the rule and quotes the sentence or link. Fix the draft and run again. Hard failures:
  - a source from before 2020
  - a cited YouTube video that doesn't resolve
- **Exit code 0 with `warn` lines:** publishing is allowed. Pass every warn line to the human reviewer together with the draft. Don't fix warnings silently and don't drop them.
- **Never edit or publish anything from inside this skill.** It only reports.

## Weekly readback

```bash
python aeo_audit/audit.py run --since <date of last run>
```

Compare `results/<date>/aeo/report.md` with the previous week. The target is 0 hard failures on everything published. A check that stays above 0 for two runs goes to the pipeline owner, with `findings.csv` attached.
