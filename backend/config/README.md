# FBF detection patterns

Edit `fbf_patterns.yaml` to match how Feedback Fruits calendar events appear at your institution.

## Tuning process

1. Enable inspect: set `ENABLE_INSPECT=true` in `.env`.
2. Call `GET /api/courses/{course_id}/inspect` with a teacher token.
3. Review `classified` results for false positives/negatives.
4. Adjust `domains`, `title_step_prefixes`, or `description_substrings`.
5. Re-run preview on a pilot course until the list matches instructor expectations.

Do not commit Canvas access tokens or raw student data in fixtures.
