"""Zero-dependency command line entry point for PulseGuard RT."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .analysis import analyze
from .parser import parse_trace
from .report import build_html


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pulseguard",
        description="Diagnose QNX 8.0 traceprinter thread dispatch latency on Linux/macOS/Windows",
    )
    p.add_argument("--version", action="version", version=f"PulseGuard RT {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("analyze", help="Analyze a QNX traceprinter text capture")
    scan.add_argument("input", type=Path)
    scan.add_argument("--budget-us", type=float, default=250.0, help="Dispatch latency screening threshold (default: 250)")
    scan.add_argument("--frequency", type=int, help="Explicit CPU cycles/second if header is missing")
    scan.add_argument("--json", type=Path, dest="json_path", help="Write machine-readable report")
    scan.add_argument("--html", type=Path, help="Write self-contained interactive dashboard")
    scan.add_argument("--strict", action="store_true", help="Exit 2 if any dispatch exceeds the screening threshold")

    compare = sub.add_parser("compare", help="Compare two saved JSON reports for latency regressions")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--max-p95-regression-pct", type=float, default=10.0)

    demo = sub.add_parser("demo", help="Generate a dashboard from a clearly synthetic QNX-format trace")
    demo.add_argument("--output-dir", type=Path, default=Path("demo-output"))
    return p


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _scan(input_path: Path, budget_us: float, frequency: int | None = None) -> dict:
    trace = parse_trace(input_path, frequency=frequency)
    return analyze(trace, budget_us=budget_us)


def _print_summary(report: dict) -> None:
    m = report["metrics"]
    t = report["trace"]
    print("\n  PULSEGUARD RT  /  QNX THREAD DIAGNOSTICS")
    print("  " + "─" * 46)
    print(f"  Trace          QNX {t['system_release']} | {t['cpu_count']} CPUs | {t['event_count']} events")
    print(f"  Dispatch pairs {m['samples']}")
    print(f"  p50 / p95 / p99  {m['p50_us']} / {m['p95_us']} / {m['p99_us']} µs")
    print(f"  Worst dispatch  {m['max_us']} µs")
    print(f"  Threshold       {report['budget_us']} µs")
    print(f"  Over threshold  {m['breaches']} ({m['breach_rate_pct']}%)")
    print(f"  Mutex waits     {m['mutex_wait_count']} observed")
    if report["warnings"]:
        print("  Warnings:")
        for warning in report["warnings"]:
            print(f"    ! {warning}")
    print("  Note: threshold breaches are NOT proven application deadline misses.\n")


def _compare(baseline_path: Path, candidate_path: Path, limit: float) -> int:
    if limit < 0:
        raise ValueError("--max-p95-regression-pct must be nonnegative")
    a = json.loads(baseline_path.read_text(encoding="utf-8"))
    b = json.loads(candidate_path.read_text(encoding="utf-8"))
    for report in (a, b):
        if report.get("schema_version") != 1 or "metrics" not in report:
            raise ValueError("Expected a PulseGuard RT schema version 1 JSON report")
    old, new = a["metrics"]["p95_us"], b["metrics"]["p95_us"]
    if old is None or new is None:
        raise ValueError("Both traces need completed dispatch samples")
    regression = (new - old) / old * 100 if old else (0.0 if new == 0 else float("inf"))
    print(f"Baseline p95: {old} µs")
    print(f"Candidate p95: {new} µs")
    print(f"p95 regression: {regression:+.2f}% (maximum allowed: {limit:.2f}%)")
    if regression > limit:
        print("REGRESSION: candidate exceeded configured threshold")
        return 2
    print("PASS: no p95 regression beyond configured threshold")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "demo":
            fixture = Path(__file__).resolve().parent.parent / "examples" / "synthetic_qnx8_trace.txt"
            if not fixture.is_file():
                raise ValueError("Bundled demo fixture missing; run from the repository root")
            args.output_dir.mkdir(parents=True, exist_ok=True)
            copied = args.output_dir / "synthetic_qnx8_trace.txt"
            shutil.copyfile(fixture, copied)
            report = _scan(copied, 250.0)
            _write(args.output_dir / "report.json", json.dumps(report, indent=2) + "\n")
            _write(args.output_dir / "report.html", build_html(report, title="Synthetic demo · PulseGuard RT"))
            _print_summary(report)
            print(f"Demo dashboard: {args.output_dir / 'report.html'}")
            print("Synthetic trace: not evidence of actual QNX runtime measurements.")
            return 0
        if args.command == "compare":
            return _compare(args.baseline, args.candidate, args.max_p95_regression_pct)
        report = _scan(args.input, args.budget_us, args.frequency)
        _print_summary(report)
        if args.json_path:
            _write(args.json_path, json.dumps(report, indent=2) + "\n")
            print(f"JSON: {args.json_path}")
        if args.html:
            _write(args.html, build_html(report))
            print(f"Dashboard: {args.html}")
        return 2 if args.strict and report["metrics"]["breaches"] > 0 else 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"pulseguard: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
