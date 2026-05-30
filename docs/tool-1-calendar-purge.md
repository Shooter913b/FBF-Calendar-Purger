# Tool 1: FBF Calendar Purge

Remove all Feedback Fruits–associated calendar events from a Canvas course. Best for **semester-to-semester migrations**, **course copies**, and when instructors want a clean calendar slate before rebuilding deadlines in Feedback Fruits.

---

## Table of contents

1. [The underlying problem](#the-underlying-problem)
2. [Shared building blocks](#shared-building-blocks)
3. [Purpose and use cases](#purpose-and-use-cases)
4. [Form factor](#form-factor)
5. [Algorithm](#algorithm)
6. [CLI usage](#cli-usage)
7. [UX and safety](#ux-and-safety)
8. [Limitations](#limitations)
9. [Token and permissions](#token-and-permissions)
10. [Comparison with Tool 2](#comparison-with-tool-2)
11. [Recommended rollout](#recommended-rollout)

---

## The underlying problem

Feedback Fruits uses the **Canvas Calendar Events API** (via institution-level API integration) to push assignment deadlines into the course calendar.

Per [Feedback Fruits: Synchronising Deadlines to Your LMS Calendar](https://help.feedbackfruits.com/hc/en-us/articles/23527088273298-Integrations-Synchronising-Deadlines-to-Your-LMS-Calendar):

| Behavior | Impact |
|----------|--------|
| Deadline changed in Feedback Fruits | A **new** calendar entry is synced; the **old one is not removed** |
| Assignment deleted in Feedback Fruits | The calendar entry **is not removed** |
| Multiple steps per activity | **Multiple** calendar events (e.g. `Give Feedback - Essay 1`, `Read Feedback - Essay 1`) |

Canvas native assignment due dates are **not** the source of truth—instructors are advised to set due dates only inside Feedback Fruits. This tool targets **`type=event` calendar events**, not assignment-type calendar entries.

---

## Shared building blocks

These apply to both Tool 1 and Tool 2.

### Authentication

| Variable | Description |
|----------|-------------|
| `CANVAS_BASE_URL` | Your institution’s Canvas URL (e.g. `https://yourschool.instructure.com`) |
| `CANVAS_ACCESS_TOKEN` | Personal or developer access token (env or `.env`; **never commit**) |

### Canvas API essentials

| Operation | Endpoint |
|-----------|----------|
| List events | `GET /api/v1/calendar_events?type=event&context_codes[]=course_{id}&all_events=1` |
| Delete event | `DELETE /api/v1/calendar_events/:id` |
| Update event | `PUT /api/v1/calendar_events/:id` (Tool 2 only) |

Use pagination via the `Link` response header. Respect rate limits (~10 req/s with exponential backoff).

### Identifying Feedback Fruits events

Run **`--inspect`** on one real course first and save 2–3 sample event JSON blobs. Event HTML varies by institution; tune a configurable classifier (e.g. `fbf_patterns.yaml`).

**Heuristic signals:**

- `description` or `html_url` contains `feedbackfruits` or your institution’s FBF launch domain
- Title matches step prefixes: `Give Feedback`, `Read Feedback`, `Hand in`, `Submissions`, etc., often as `{Step} - {Assignment name}`
- Optional: description link resolves to the same Canvas assignment as an external-tool FBF assignment

### Safety defaults

| Flag | Behavior |
|------|----------|
| `--dry-run` | Default: list actions without mutating Canvas |
| `--apply` | Perform deletes/updates |
| Structured logging | Every action recorded for audit |

---

## Purpose and use cases

| Scenario | Why purge helps |
|----------|-----------------|
| **Course copy** (semester → semester) | Stale FBF calendar events from the source course remain after copy |
| **New term setup** | Start with an empty FBF calendar footprint before activities are reconfigured |
| **Major course reset** | Remove confusing duplicate/orphan dates before students see the calendar |
| **Before Tool 2 sync** | Optional: purge first, then let FBF recreate events—or sync in place |

**What this tool does *not* do:** It does not delete Canvas assignments, modules, or Feedback Fruits activities—**calendar events only**.

---

## Form factor

**CLI script** (recommended: Python 3.11+ with `requests` and `click`, or Node with `fetch`).

Simple to run locally or in a batch script for many courses at the start of a term.

**Suggested package layout:**

```
fbf-calendar-purger/
├── fbf_purge/          # core library
├── docs/
│   ├── tool-1-calendar-purge.md
│   └── tool-2-calendar-sync.md
└── pyproject.toml      # entry point: fbf-purge
```

---

## Algorithm

```mermaid
flowchart TD
  A[Load course ID(s)] --> B[GET all calendar events type=event]
  B --> C[Filter: is_feedback_fruits_event]
  C --> D{Dry run?}
  D -->|yes| E[Print table: id, title, start_at]
  D -->|no| F[DELETE /calendar_events/:id]
  F --> G[Summary: deleted / failed / skipped]
```

### Steps

1. **Load course IDs** — single `--course-id` or `--course-list` file (one ID per line).
2. **Paginate** all course calendar **events** with `all_events=1` (not limited to “today forward”).
3. **Classify** each event with `is_feedback_fruits_event(event)`.
4. **Optional exclude** — `--exclude-title-regex` to skip instructor-created events that matched heuristics by mistake.
5. **Delete** — `DELETE /api/v1/calendar_events/:id` for each match when `--apply` is set.

---

## CLI usage

```bash
# Preview what would be deleted (default)
fbf-purge --course-id 12345 --dry-run

# Execute deletions
fbf-purge --course-id 12345 --apply

# Bulk semester migration
fbf-purge --course-list courses.txt --apply

# Dump sample events to tune detection rules
fbf-purge --course-id 12345 --inspect
```

### Example output (dry-run)

```
Course 12345 — Feedback Fruits calendar events (12 found)

  ID      start_at                  title
  ------  ------------------------  ---------------------------------
  88421   2025-09-10T23:59:00-04:00 Give Feedback - Peer Review 1
  88422   2025-09-17T23:59:00-04:00 Read Feedback - Peer Review 1
  ...

Dry run: no changes made. Re-run with --apply to delete.
```

---

## UX and safety

| Feature | Description |
|---------|-------------|
| **Dry-run default** | Prevents accidental mass deletion |
| **Confirmation prompt** | Unless `--yes` is passed |
| **Audit report** | CSV e.g. `purge-report-2026-05-29.csv` with `event_id`, `title`, `start_at`, `action`, `status` |
| **Inspect mode** | Prints raw JSON for unmatched/matched samples to refine `fbf_patterns.yaml` |

---

## Limitations

| Limitation | Notes |
|------------|-------|
| **Assignment-type calendar entries** | If someone set a due date on the Canvas assignment shell, those appear as `type=assignment`—different API surface. Optional follow-up: warn on external-tool assignments with `due_at` set. |
| **Classifier false positives** | Rare if heuristics are tuned with `--inspect`; use `--exclude-title-regex` as a safeguard. |
| **Does not prevent FBF from re-syncing** | After purge, opening/saving FBF assignments may create new calendar events (expected). |
| **Permissions** | Token must have teacher (or admin) access to each target course. |

---

## Token and permissions

Ask your Canvas admin to ensure your token (or developer key) includes:

- `url:GET|/api/v1/calendar_events`
- `url:DELETE|/api/v1/calendar_events/:id`

Helpful but not required for purge-only:

- `url:GET|/api/v1/courses/:course_id` (course metadata / timezone)

---

## Comparison with Tool 2

| | **Tool 1: Purge** | **Tool 2: Sync** |
|--|-------------------|------------------|
| **Best for** | Course copy, new semester, wipe slate | Ongoing teaching, after editing FBF deadlines |
| **Canvas API only?** | Yes | Phase 2 yes; Phase 1 needs FBF deadline data |
| **Risk** | Low with good classifier + dry-run | Medium: wrong match could move a date |
| **Complexity** | ~200–300 LOC | ~800–1500 LOC (with Playwright collector) |
| **Run frequency** | Once per migrated course | Weekly or after deadline changes |

See [tool-2-calendar-sync.md](./tool-2-calendar-sync.md) for the reconciliation tool.

---

## Recommended rollout

1. Run **`fbf-purge --inspect`** on one production-like course; save sample events.
2. Tune **`fbf_patterns.yaml`** (or equivalent) with your instructional technology team.
3. **`--dry-run`** on a pilot course; review the table with an instructor.
4. **`--apply`** on pilot, then batch **`--course-list`** for semester migration.
5. Optionally introduce **Tool 2** for ongoing deadline hygiene instead of purge-only workflows.

---

## References

- [Feedback Fruits: Synchronising Deadlines to Your LMS Calendar](https://help.feedbackfruits.com/hc/en-us/articles/23527088273298-Integrations-Synchronising-Deadlines-to-Your-LMS-Calendar)
- [Feedback Fruits: Configuring the API for Canvas](https://help.feedbackfruits.com/hc/en-us/articles/23527057192338-Configuring-the-API-for-Canvas)
- [Canvas Calendar Events API](https://canvas.instructure.com/doc/api/calendar_events.html)
- [Cornell: Feedback Fruits FAQs](https://learn.canvas.cornell.edu/feedbackfruits-faqs/) — calendar duplication and editing guidance
