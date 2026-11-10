"""Conservative state-transition analysis of QNX scheduling events."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import mean

from .parser import Trace


BLOCKED = {
    "THMUTEX", "THCONDVAR", "THRECEIVE", "THSEND", "THREPLY", "THSEM",
    "THNANOSLEEP", "THJOIN", "THINTR", "THWAITPAGE", "THSIGWAITINFO",
    "THSIGSUSPEND", "THNET_SEND", "THNET_REPLY", "THSTOPPED",
}


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(quantile * len(ordered)) - 1)], 3)


def analyze(trace: Trace, *, budget_us: float = 250.0, top: int = 30) -> dict:
    """Find THREADY → THRUNNING dispatch delays and THMUTEX → THREADY waits.

    No claim is made that a dispatch delay equals an application deadline miss.
    Measurements are observational, so truncated traces and lost events matter.
    """
    if budget_us <= 0 or not math.isfinite(budget_us):
        raise ValueError("--budget-us must be finite and positive")
    hz = trace.cycles_per_second
    first_cycle = min(e.cycle for e in trace.events)
    last_cycle = max(e.cycle for e in trace.events)
    ready: dict[tuple[int, int], tuple[int, int]] = {}
    mutex: dict[tuple[int, int], tuple[int, int]] = {}
    current_cpu: dict[int, tuple[tuple[int, int], int]] = {}
    samples: list[dict] = []
    mutex_waits: list[dict] = []
    segments: list[dict] = []
    state_count = Counter()
    per_thread: dict[tuple[int, int], list[float]] = defaultdict(list)
    per_cpu: dict[int, list[float]] = defaultdict(list)
    ignored_negative = 0

    def stop_running(key: tuple[int, int], event_cycle: int, cpu: int) -> None:
        old = current_cpu.get(cpu)
        if old and old[0] == key:
            _, started = old
            if event_cycle >= started:
                segments.append({
                    "cpu": cpu, "pid": key[0], "tid": key[1],
                    "start_us": us(started - first_cycle),
                    "end_us": us(event_cycle - first_cycle),
                })
            current_cpu.pop(cpu, None)

    def us(cycles: int) -> float:
        return round(cycles * 1_000_000 / hz, 3)

    for event in trace.events:
        if event.kind != "THREAD" or event.pid is None or event.tid is None:
            continue
        key = (event.pid, event.tid)
        state_count[event.name] += 1
        if event.name == "THREADY":
            stop_running(key, event.cycle, event.cpu)
            if key in mutex:
                started, line = mutex.pop(key)
                if event.cycle >= started:
                    mutex_waits.append({
                        "pid": key[0], "tid": key[1], "line": line,
                        "start_us": us(started - first_cycle),
                        "duration_us": us(event.cycle - started),
                    })
            ready.setdefault(key, (event.cycle, event.line))
        elif event.name == "THRUNNING":
            old = current_cpu.get(event.cpu)
            if old:
                old_key, start = old
                if event.cycle >= start and old_key != key:
                    segments.append({
                        "cpu": event.cpu, "pid": old_key[0], "tid": old_key[1],
                        "start_us": us(start - first_cycle), "end_us": us(event.cycle - first_cycle),
                    })
            current_cpu[event.cpu] = (key, event.cycle)
            if key in ready:
                queued, line = ready.pop(key)
                if event.cycle < queued:
                    ignored_negative += 1
                    continue
                latency = us(event.cycle - queued)
                samples.append({
                    "pid": key[0], "tid": key[1], "cpu": event.cpu,
                    "ready_line": line, "run_line": event.line,
                    "start_us": us(queued - first_cycle),
                    "run_us": us(event.cycle - first_cycle),
                    "latency_us": latency, "over_budget": latency > budget_us,
                })
                per_thread[key].append(latency)
                per_cpu[event.cpu].append(latency)
            mutex.pop(key, None)
        elif event.name in BLOCKED or event.name in {"THDESTROY", "THDEAD"}:
            stop_running(key, event.cycle, event.cpu)
            ready.pop(key, None)
            if event.name == "THMUTEX":
                mutex.setdefault(key, (event.cycle, event.line))
            else:
                mutex.pop(key, None)

    # Do not turn an unfinished segment into an invented switch event.
    latencies = [s["latency_us"] for s in samples]
    breaches = sum(s["over_budget"] for s in samples)
    threads = []
    for key, vals in per_thread.items():
        threads.append({
            "pid": key[0], "tid": key[1], "samples": len(vals),
            "p95_us": percentile(vals, .95), "max_us": round(max(vals), 3),
            "breaches": sum(v > budget_us for v in vals),
        })
    threads.sort(key=lambda t: (-t["max_us"], -t["samples"], t["pid"], t["tid"]))
    cpus = []
    for cpu in range(trace.cpu_count):
        vals = per_cpu.get(cpu, [])
        cpus.append({
            "cpu": cpu, "samples": len(vals), "p95_us": percentile(vals, .95),
            "max_us": round(max(vals), 3) if vals else None,
        })
    warnings = list(dict.fromkeys(trace.warnings))
    if ready:
        warnings.append(f"{len(ready)} ready-state(s) were still open at end of trace; excluded")
    if mutex:
        warnings.append(f"{len(mutex)} mutex wait(s) were still open at end of trace; excluded")
    if ignored_negative:
        warnings.append(f"Excluded {ignored_negative} non-monotonic latency observations")
    if not samples:
        warnings.append("No complete THREADY → THRUNNING pairs found; no latency is inferred")
    if len(samples) < 20:
        warnings.append("Small sample count: percentile estimates are exploratory")
    if len(samples) > 50000:
        warnings.append("Dashboard retains only the first 50,000 dispatches for interactive exploration; JSON aggregate metrics use all samples")
    if trace.system_release == "unknown":
        warnings.append("QNX release not recorded in trace header; verify capture on SDP 8.0")

    return {
        "schema_version": 1,
        "tool": "PulseGuard RT",
        "source_format": "QNX SDP 8.0 traceprinter text",
        "trace": {
            "system_release": trace.system_release,
            "cycles_per_second": hz,
            "cpu_count": trace.cpu_count,
            "event_count": len(trace.events),
            "duration_us": us(last_cycle - first_cycle),
        },
        "budget_us": budget_us,
        "metrics": {
            "samples": len(samples),
            "breaches": breaches,
            "breach_rate_pct": round(100 * breaches / len(samples), 2) if samples else None,
            "mean_us": round(mean(latencies), 3) if latencies else None,
            "p50_us": percentile(latencies, .50),
            "p95_us": percentile(latencies, .95),
            "p99_us": percentile(latencies, .99),
            "max_us": round(max(latencies), 3) if latencies else None,
            "mutex_wait_count": len(mutex_waits),
            "max_mutex_wait_us": max((s["duration_us"] for s in mutex_waits), default=None),
        },
        "threads": threads,
        "cpus": cpus,
        "worst_dispatches": sorted(samples, key=lambda x: -x["latency_us"])[:top],
        "mutex_waits": sorted(mutex_waits, key=lambda x: -x["duration_us"])[:top],
        "segments": segments[:10000],
        "dispatches": samples[:50000],
        "dispatches_truncated": len(samples) > 50000,
        "event_types": dict(state_count.most_common()),
        "warnings": warnings,
        "interpretation": {
            "dispatch": "THREADY-to-THRUNNING delay, not an application response time or deadline miss.",
            "mutex": "THMUTEX-to-THREADY duration, not proof of priority inversion.",
            "budget": "User-configured screening threshold; 'breach' does not assert a certified hard-real-time violation.",
        },
    }
