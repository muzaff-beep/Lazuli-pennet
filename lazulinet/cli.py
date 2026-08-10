from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from lazulinet.application.report_service import ReportService
from lazulinet.application.legacy_migration import LegacyMigrationService
from lazulinet.domain.models import ScanRequest, TaskState
from lazulinet.platform.factory import create_runtime


def _terminal(state: TaskState) -> bool:
    return state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED)


def _print_json(payload) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lazulinet-safe",
        description="Shared LazuliNet administrative/passive-discovery CLI.",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="Override session storage root.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health", help="Show platform/dependency health.")
    sub.add_parser("interfaces", help="List detected interfaces.")
    sessions = sub.add_parser("sessions", help="List saved discovery sessions.")
    sessions.add_argument("--limit", type=int, default=20)

    scan = sub.add_parser("scan", help="Start passive discovery through the shared adapter.")
    scan.add_argument("interface")
    scan.add_argument("--duration", type=int, default=30)
    scan.add_argument("--channel", type=int, default=None)

    migrate = sub.add_parser("migrate-legacy", help="Import legacy networks.json files into structured sessions.")
    migrate.add_argument("legacy_root", type=Path)
    migrate.add_argument("--interface", default="legacy-import")
    migrate.add_argument("--dry-run", action="store_true")
    migrate.add_argument("--force", action="store_true", help="Import even if the source hash was already migrated.")

    verify = sub.add_parser("verify", help="Verify session metadata, counts, and recorded artifacts.")
    verify.add_argument("session_id", nargs="?", default=None)
    verify.add_argument("--limit", type=int, default=100)

    report = sub.add_parser("report", help="Generate a report for a saved session.")
    report.add_argument("session_id", nargs="?", default=None)
    report.add_argument("--format", choices=("txt", "json", "bundle"), default="txt")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = create_runtime(args.data_dir)

    if args.command == "health":
        _print_json(runtime.interface.health())
        return 0

    if args.command == "interfaces":
        _print_json([item.to_dict() for item in runtime.interface.list_interfaces()])
        return 0

    if args.command == "sessions":
        _print_json([session.to_dict() for session in runtime.sessions.list_sessions(max(1, args.limit))])
        return 0

    if args.command == "migrate-legacy":
        migration = LegacyMigrationService(runtime.sessions)
        results = migration.import_root(args.legacy_root, interface=args.interface, dry_run=args.dry_run, force=args.force)
        _print_json(results)
        if not results:
            return 2
        return 1 if any(result.get("error") for result in results) else 0

    if args.command == "verify":
        if args.session_id:
            result = runtime.sessions.verify(args.session_id)
            _print_json(result)
            return 0 if result["ok"] else 1
        results = runtime.sessions.verify_all(max(1, args.limit))
        _print_json(results)
        return 0 if all(result["ok"] for result in results) else 1

    if args.command == "report":
        session = runtime.sessions.load_session(args.session_id) if args.session_id else runtime.sessions.latest_with_networks()
        if not session:
            print("No normalized session is available.", file=sys.stderr)
            return 2
        reporter = ReportService(runtime.sessions)
        if args.format == "txt":
            path = reporter.generate_text(session.id)
        elif args.format == "json":
            path = reporter.export_json(session.id)
        else:
            path = reporter.export_bundle(session.id)
        print(path)
        return 0

    if args.command == "scan":
        handle = runtime.discovery.start_scan(
            ScanRequest(interface=args.interface, duration_seconds=args.duration, channel=args.channel)
        )
        try:
            while not _terminal(handle.snapshot().state):
                for event in runtime.tasks.poll_events():
                    if event.task_id == handle.id:
                        progress = f" {event.progress:.0%}" if event.progress is not None else ""
                        print(f"[{event.kind}]{progress} {event.message}")
                time.sleep(0.1)
        except KeyboardInterrupt:
            handle.cancel()
            print("Cancellation requested…", file=sys.stderr)
            while not _terminal(handle.snapshot().state):
                time.sleep(0.05)

        snapshot = handle.snapshot()
        if snapshot.state == TaskState.FAILED:
            print(snapshot.error, file=sys.stderr)
            return 1
        _print_json(snapshot.result or {"state": snapshot.state.value})
        return 130 if snapshot.state == TaskState.CANCELLED else 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
