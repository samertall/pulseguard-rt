# Devpost submission draft — QNX Global Hackathon

> Prepared November 9, 2026. **Not yet submitted to Devpost**. The repository and public YouTube demo URLs are listed below.

## Project name

PulseGuard RT — QNX Kernel Trace Intelligence

## Elevator pitch

Turn raw QNX 8.0 kernel traces into clear, offline diagnostics for thread scheduling delays, mutex contention signals, and latency regressions.

## Category

**Developer Tooling & Host Tools** (one category)

## Project description (paste into Devpost)

### Inspiration

Real-time systems power vehicles, industrial controls, and medical technology, but diagnosing scheduling problems still requires painstaking inspection of raw kernel events. A thread can be ready and yet wait for CPU time. We wanted to make that hidden scheduling interval visible and understandable to engineers without requiring special hardware, a cloud backend, or a proprietary analytics pipeline.

### What it does

PulseGuard RT is a zero-dependency, open-source host tool built specifically to analyze **QNX SDP 8.0** trace output. It ingests `traceprinter` text, reconstructs `THREADY` → `THRUNNING` thread dispatch observations, and computes latency distributions, p50/p95/p99, maximum dispatch delay, per-thread outliers, and observations that exceed a configurable screening threshold. It also highlights `THMUTEX` → `THREADY` waits as *contention candidates* without falsely claiming priority inversion.

Its self-contained HTML dashboard offers an interactive threshold explorer, observed CPU scheduling timeline, thread inspector, slowest-dispatch table with exact source-line references, and transparent capture warnings. JSON reports can be compared in CI to flag p95 regressions. No trace information is uploaded to a server.

### How we built it

We used Python 3.10+ standard library on a Linux host and built a QNX-specific parser that recognizes the output conventions documented for `traceprinter` in **QNX SDP 8.0**: `TRACE_CYCLES_PER_SEC`, CPU IDs, and QNX thread-state kernel events. The analysis module pairs verified state transitions and excludes incomplete or invalid observations. A standalone HTML, CSS, and JavaScript report is generated and runs offline. Nine automated tests verify parser behavior, time conversion, blocked-state handling, report generation, and CLI workflows.

The included reproducible sample contains **synthetic QNX-format events**. Its numbers demonstrate the host tool and are explicitly identified as generated—not measurements from a QNX device. The README and codelab explain how to use QNX 8.0's native `tracelogger` and `traceprinter` tools to analyze an actual QNX target or QEMU guest.

### Challenges

Interpreting kernel events responsibly was the biggest challenge. A dispatch delay is **not** an application deadline miss, a mutex wait is **not** proof of priority inversion, and incomplete traces can be misleading. We designed the state machine and diagnostics so that they report only complete observations and communicate these boundaries directly in the UI.

### Accomplishments

- Working Linux-hosted QNX 8.0 trace text analysis without runtime Python dependencies.
- Interactive, offline report with latency distributions, thread pressure map, and source-line evidence.
- CLI regression checks that can stop CI on a configurable p95 increase.
- Reproducible synthetic demonstration and automated tests.
- Guided codelab connecting native QNX `tracelogger` / `traceprinter` to the host analyzer.

### What we learned

The most useful observability tooling combines correctness with humility: it must explain not just what an event means, but also what cannot be inferred from it. A small, trustworthy scheduling signal is more valuable than a sophisticated but unsupported real-time claim.

### What's next

Validate with captures from QNX 8.0 QEMU/hardware, add optional target-side collection, expand correlations to QNX message passing and thread priorities, and support larger traces with streaming analytics. These are future ideas, not features claimed as completed.

## Detailed evidence of QNX-specific integration

1. [`pulseguard/parser.py`](pulseguard/parser.py): parses the QNX `TRACE_CYCLES_PER_SEC` header and canonical `t:0x... CPU:.. THREAD:THREADY/THRUNNING/THMUTEX pid:... tid:...` event stream produced by QNX's `traceprinter`.
2. [`pulseguard/analysis.py`](pulseguard/analysis.py): interprets QNX thread-state transitions into dispatch latency and mutex-wait candidates.
3. [`docs/CODELAB.md`](docs/CODELAB.md): shows real QNX OS 8.0 capture via `tracelogger`, vendor-native `.kev` decoding via `traceprinter`, then host analysis. The demo trace itself is synthetic.
4. [`tests/test_core.py`](tests/test_core.py): 9 automated tests covering the host tool's QNX-format parsing and diagnostics.

**Host runtime:** Linux/macOS/Windows, CPython 3.10+. **QNX target:** QNX OS 8.0 on supported hardware or QEMU; **target formatter:** QNX SDP 8.0 `traceprinter`; **capture:** QNX SDP 8.0 `tracelogger` with instrumented kernel. QNX SDP itself is not bundled.

## Verified URLs

- **Public source repo:** `https://github.com/samertall/pulseguard-rt`.
- **Public demo YouTube video:** `https://www.youtube.com/watch?v=HXBaztZVK-s` (84 seconds; synthetic-example results only).
- **Best Codelab/Tutorial bonus field:** `https://github.com/samertall/pulseguard-rt/blob/main/docs/CODELAB.md`.
- **Live demo website:** Not required. The project is an offline host application; HTML dashboard generated locally.

## Suggested tags

`qnx` · `realtime` · `embedded` · `python` · `observability` · `developer-tools` · `performance` · `kernel-tracing`

## Last-mile checklist

- [x] Original working host tool and QNX-specific data parser
- [x] Open-source MIT license
- [x] Build/test/run documentation, category, SDP version, target, host toolchain
- [x] Synthetic fixture and automated tests
- [x] Original 84-second demo MP4 created locally (no third-party music)
- [x] Public GitHub repository created and code committed
- [x] Public YouTube upload verified (under 3 minutes)
- [ ] Real QNX 8.0 trace validation, if available (strongly recommended for judges)
- [ ] Devpost registration/login and form completed
- [ ] Final submission confirmed in Devpost UI
