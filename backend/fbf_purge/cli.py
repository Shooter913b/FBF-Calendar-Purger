import argparse
import asyncio
import json
import sys

from fbf_purge.canvas.client import CanvasClient
from fbf_purge.classifier.patterns import load_patterns
from fbf_purge.config import get_settings
from fbf_purge.services.courses import inspect_course
from fbf_purge.services.purge import execute_purge, preview_purge


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    if not settings.canvas_access_token:
        print("Error: CANVAS_ACCESS_TOKEN is not set", file=sys.stderr)
        return 1

    patterns = load_patterns(settings.resolved_patterns_path())
    client = CanvasClient(
        settings.canvas_base_url,
        settings.canvas_access_token,
        settings.rate_limit_requests_per_second,
    )
    try:
        if args.inspect:
            result = await inspect_course(client, args.course_id, patterns)
            print(json.dumps(result, indent=2))
            return 0

        if args.apply:
            report = await execute_purge(client, args.course_id, patterns)
        else:
            report = await preview_purge(client, args.course_id, patterns)

        print(f"\nCourse: {report.course_name} ({report.course_id})")
        print(f"Matched: {report.matched_count}  Deleted: {report.deleted_count}  Failed: {report.failed_count}")
        print(f"Dry run: {report.dry_run}\n")
        for ev in report.events:
            print(f"  [{ev.status}] {ev.event_id}  {ev.start_at or '—'}  {ev.title}")
        return 0
    finally:
        await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="FBF Calendar Purge CLI")
    parser.add_argument("--course-id", type=int, required=True)
    parser.add_argument("--apply", action="store_true", help="Execute deletion (default is dry-run)")
    parser.add_argument("--inspect", action="store_true", help="Dump classification diagnostics")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
