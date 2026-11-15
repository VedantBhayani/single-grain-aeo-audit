Type: task
Status: resolved
Blocked by: 01

## Question

Vedant puts the keys in place: PARALLEL_API_KEY in `.env` on the box, and INSTABOX_API_KEY in GitHub secrets. Claude gives the checklist and confirms only that each key is present, never its value. (HITL)

## Answer

Done 2026-11-15. Checked without reading: the GitHub secret INSTABOX_API_KEY was set 13:50 UTC. On the box, ~/aeo.env is mode 600, 58 bytes, with one PARALLEL_API_KEY line. nano isn't on the box, so the key was written with read -s.
