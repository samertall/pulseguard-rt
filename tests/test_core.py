import json
import tempfile
import unittest
from pathlib import Path

from pulseguard.analysis import analyze, percentile
from pulseguard.cli import main
from pulseguard.parser import parse_trace
from pulseguard.report import build_html


EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "synthetic_qnx8_trace.txt"


class TraceTests(unittest.TestCase):
    def test_fixture_is_parseable(self):
        trace = parse_trace(EXAMPLE)
        self.assertEqual(trace.cycles_per_second, 100_000_000)
        self.assertEqual(trace.cpu_count, 2)
        self.assertGreater(len(trace.events), 55)

    def test_analysis(self):
        report = analyze(parse_trace(EXAMPLE))
        self.assertGreater(report["metrics"]["samples"], 25)
        self.assertGreater(report["metrics"]["breaches"], 0)
        self.assertEqual(report["metrics"]["mutex_wait_count"], 1)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(len(report["cpus"]), 2)

    def test_dispatch_is_measured_in_microseconds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.txt"
            path.write_text(
                "TRACE_CYCLES_PER_SEC:: 1000000\nTRACE_SYS_RELEASE:: 8.0\n"
                "t:0x00001000 CPU:00 THREAD:THREADY pid:7 tid:3\n"
                "t:0x000010C8 CPU:00 THREAD:THRUNNING pid:7 tid:3\n",
                encoding="utf-8",
            )
            report = analyze(parse_trace(path), budget_us=150)
            self.assertEqual(report["metrics"]["p95_us"], 200)
            self.assertEqual(report["metrics"]["breaches"], 1)

    def test_blocked_state_cancels_stale_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.txt"
            path.write_text(
                "TRACE_CYCLES_PER_SEC:: 1000000\n"
                "t:0x0100 CPU:00 THREAD:THREADY pid:7 tid:3\n"
                "t:0x0110 CPU:00 THREAD:THMUTEX pid:7 tid:3\n"
                "t:0x0200 CPU:00 THREAD:THREADY pid:7 tid:3\n"
                "t:0x0250 CPU:00 THREAD:THRUNNING pid:7 tid:3\n",
                encoding="utf-8",
            )
            report = analyze(parse_trace(path))
            self.assertEqual(report["metrics"]["p95_us"], 80)
            self.assertEqual(report["metrics"]["max_mutex_wait_us"], 240)

    def test_frequency_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.txt"
            path.write_text("t:0x100 CPU:00 THREAD:THREADY pid:1 tid:1\n")
            with self.assertRaisesRegex(ValueError, "frequency"):
                parse_trace(path)
            self.assertEqual(parse_trace(path, frequency=1_000_000).cycles_per_second, 1_000_000)

    def test_broken_trace_not_fabricated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.txt"
            path.write_text("garbage\n")
            with self.assertRaisesRegex(ValueError, "No compatible"):
                parse_trace(path, frequency=1_000_000)

    def test_percentile(self):
        self.assertIsNone(percentile([], .95))
        self.assertEqual(percentile([20, 30, 10, 50, 40], .5), 30)
        self.assertEqual(percentile([20, 30, 10, 50, 40], .95), 50)

    def test_html_embedded_json_is_safe(self):
        report = analyze(parse_trace(EXAMPLE))
        report["warnings"].append("</script><script>alert(1)</script>")
        markup = build_html(report)
        self.assertNotIn("</script><script>alert", markup)
        self.assertIn("\\u003c/script>", markup)
        self.assertIn("id=\"thread-filter\"", markup)

    def test_cli_generates_reports_and_compare(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "a.json", root / "b.json"
            dashboard = root / "report.html"
            self.assertEqual(main(["analyze", str(EXAMPLE), "--json", str(a), "--html", str(dashboard)]), 0)
            self.assertEqual(main(["analyze", str(EXAMPLE), "--json", str(b)]), 0)
            self.assertTrue(dashboard.exists())
            self.assertEqual(json.loads(a.read_text())["tool"], "PulseGuard RT")
            self.assertEqual(main(["compare", str(a), str(b)]), 0)
            self.assertEqual(main(["analyze", str(EXAMPLE), "--strict"]), 2)


if __name__ == "__main__":
    unittest.main()
