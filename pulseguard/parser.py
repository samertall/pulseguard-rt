"""Stream-aware parser for QNX 8.0 traceprinter's documented text output.

The input is the *formatted* output of QNX's traceprinter, not a binary .kev.
No attempt is made to parse QNX's proprietary binary event format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


EVENT = re.compile(
    r"^\s*t:0x(?P<cycles>[0-9a-fA-F]+)\s+CPU:(?P<cpu>\d+)\s+"
    r"(?P<kind>[A-Z_]+)\s*:\s*(?P<name>[^\s]+)?(?P<details>.*)$"
)
HEADER = re.compile(r"^\s*(TRACE_[A-Z_]+)::\s*(.*?)\s*$")
ARG = re.compile(r"\b(?P<key>pid|tid|ppid|msb|lsb\(offset\))\s*:\s*(?P<value>0x[0-9a-fA-F]+|[-+]?\d+)")


@dataclass(frozen=True)
class Event:
    cycle: int
    cpu: int
    kind: str
    name: str
    pid: int | None
    tid: int | None
    line: int


@dataclass(frozen=True)
class Trace:
    events: list[Event]
    cycles_per_second: int
    system_release: str
    cpu_count: int
    unparsed_events: int
    warnings: list[str]


def parse_trace(path: str | Path, *, frequency: int | None = None) -> Trace:
    """Parse QNX traceprinter text; reject traces without reliable timing metadata.

    The `-p` flag can change traceprinter's output layout. We intentionally
    support the documented default t:0x... CPU:... layout, avoiding guesses.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Trace file does not exist: {path}")
    events: list[Event] = []
    headers: dict[str, str] = {}
    pending: Event | None = None
    unparsed = 0
    warnings: list[str] = []
    high = 0
    prev_low: int | None = None
    last_cycle = -1
    with path.open("r", encoding="utf-8", errors="replace") as file:
        for number, raw in enumerate(file, 1):
            line = raw.rstrip("\n")
            h = HEADER.match(line)
            if h:
                headers[h.group(1)] = h.group(2)
            match = EVENT.match(line)
            if match:
                if pending:
                    events.append(pending)
                low = int(match.group("cycles"), 16)
                # Old-style traceprinter prints only a 32-bit LSB except at
                # rollovers. An explicit >32-bit timestamp is already complete.
                if len(match.group("cycles")) > 8:
                    cycle = low
                    high = cycle >> 32
                else:
                    if prev_low is not None and low < prev_low:
                        if prev_low - low > 0x80000000:
                            high += 1
                        else:
                            warnings.append(
                                f"Out-of-order timestamp near line {number}; "
                                "some latency samples may be excluded"
                            )
                    cycle = (high << 32) | low
                if cycle < last_cycle:
                    warnings.append(f"Non-monotonic timestamp at line {number}")
                prev_low = low & 0xFFFFFFFF
                last_cycle = cycle
                args = {m.group("key"): int(m.group("value"), 0) for m in ARG.finditer(match.group("details"))}
                pending = Event(
                    cycle=cycle,
                    cpu=int(match.group("cpu")),
                    kind=match.group("kind"),
                    name=match.group("name") or "",
                    pid=args.get("pid"),
                    tid=args.get("tid"),
                    line=number,
                )
            elif pending and line.strip():
                # traceprinter wraps some event args onto subsequent lines.
                args = {m.group("key"): int(m.group("value"), 0) for m in ARG.finditer(line)}
                if args:
                    pending = Event(
                        cycle=pending.cycle, cpu=pending.cpu, kind=pending.kind,
                        name=pending.name, pid=pending.pid if pending.pid is not None else args.get("pid"),
                        tid=pending.tid if pending.tid is not None else args.get("tid"), line=pending.line,
                    )
            elif "t:0x" in line and "CPU:" in line:
                unparsed += 1
    if pending:
        events.append(pending)
    if not events:
        raise ValueError("No compatible traceprinter events found (expected 't:0x... CPU:00 THREAD:...')")

    header_frequency = headers.get("TRACE_CYCLES_PER_SEC")
    try:
        cycles_per_second = frequency or int(header_frequency or "0")
    except ValueError as error:
        raise ValueError("TRACE_CYCLES_PER_SEC is invalid; use --frequency") from error
    if cycles_per_second <= 0:
        raise ValueError("Missing TRACE_CYCLES_PER_SEC; specify --frequency in cycles/second")
    if unparsed:
        warnings.append(f"Ignored {unparsed} event lines using unsupported output formatting")
    if not any(e.kind == "THREAD" for e in events):
        warnings.append("No THREAD events; enable the thread class in tracelogger")
    release = headers.get("TRACE_SYS_RELEASE", "unknown")
    if release != "unknown" and not release.startswith("8"):
        warnings.append(f"Trace declares QNX release {release}; this tool targets QNX 8.0")
    try:
        cpu_count = int(headers.get("TRACE_CPU_NUM", "0"))
    except ValueError:
        cpu_count = 0
    cpu_count = max(cpu_count, max(e.cpu for e in events) + 1)
    return Trace(events, cycles_per_second, release, cpu_count, unparsed, warnings)
