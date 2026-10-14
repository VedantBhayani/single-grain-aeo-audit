# Tracking guard

Eric Siu, on an AI CRO loop: it "started to make changes to the site and it removed tags and it removed uh analytics codes" ([youtu.be/tcgfrAAgRK4](https://youtu.be/tcgfrAAgRK4)).

This snapshots the tracking tags, forms and index signals on his public sites, compares each run with the last, and alerts when something was lost.

```bash
python tracking_guard/guard.py run              # -> results/snapshots/<time>.json + results/<date>/tracking/report.md
python tracking_guard/guard.py diff OLD.json NEW.json
```

The `tracking-guard` GitHub Actions workflow runs it every Monday. It commits the dated report and fails the job on an alert, so GitHub notifies the repo owner.

## What it watches

Pages come from the sitemaps of singlegrain.com (page and service sitemaps), singlebrain.com, gateway.singlebrain.com and clickflow.com, plus a few pages Eric sends people to (`/apply/`, `/careers/`, `/skills/`, `/gateway`).

**ALERT** when, compared with the last run:
- a GTM container, GA4 or UA ID, or tracker disappears (HubSpot, Meta pixel, LinkedIn Insight, Vercel Analytics, PostHog, Segment, Clarity, Plausible)
- a page has fewer forms, or a form posts somewhere else
- the canonical changes, or noindex turns on
- the status code changes, or a page starts redirecting

New tags and title changes are logged as INFO only.

## Limits

- **It reads the HTML the server sends.** GA4 loaded through GTM won't show as a GA4 ID; the GTM container is what's checked on those pages.
- **A page with no tags in its HTML may still track** through JavaScript or server-side. It's reported as a question, not as broken.
- **It only catches a change if it runs again.** That's what the weekly workflow is for.
