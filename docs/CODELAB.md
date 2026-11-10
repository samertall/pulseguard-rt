# Codelab: Diagnose QNX 8.0 scheduling delay using PulseGuard RT

**Skill level:** beginner–intermediate embedded developer  
**Duration:** 20–35 minutes with a configured QNX target (5 minutes with the synthetic example)  
**Target:** QNX OS 8.0 in QEMU or supported hardware  
**Host:** Linux, macOS, or Windows with Python 3.10+  
**Outcome:** a shareable, offline diagnostic report with evidence-backed thread dispatch latency observations.

> This codelab teaches a *diagnostic workflow*. Its metrics are not evidence of safety certification or application deadline compliance.

## 1. Understand the signal

The QNX kernel exposes thread state transitions. `THREADY` means a thread has become runnable; `THRUNNING` means it has been scheduled to execute. The time between these events gives an **observed dispatch delay**, useful for investigating scheduler headroom. This is **not** the same as end-to-end task latency.

`THMUTEX` marks a wait for a mutex. Measuring time from that event to the next `THREADY` provides a mutex-blocking observation, but without ownership/priority data, it is **not proof of priority inversion**.

## 2. Install and check your environment

Download the appropriate host tools from [QNX Everywhere](https://qnx.software/en/developers/get-started/qnx-everywhere). Follow the [official QNX SDP 8.0 Quick Start Guide](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.qnxsdp.quickstart/topic/about.html) to boot an OS 8.0 target. Verify your target is actually QNX 8.0 using its version information. No SDK download or credentials are distributed with PulseGuard.

For an initial test without QNX, skip ahead to step 5 and use the synthetic fixture.

## 3. Capture ten seconds of QNX kernel events

On the QNX target, with root permissions and an instrumented kernel running:

```sh
tracelogger -s 10 -w -f /dev/shmem/pulseguard.kev
```

Start your workload while capture is active. `-s 10` records ten seconds; `-w` selects wide trace events; `-f` names the output file. The capture is from QNX, **not** from the Linux host running PulseGuard. QNX warns against running a competing `tracelogger`/IDE tracing session simultaneously.

## 4. Decode the trace with the vendor tool

On QNX or an SDP-equipped supported host, use the QNX binary-to-text conversion utility:

```sh
traceprinter -f /path/to/pulseguard.kev -o pulseguard.txt
```

Confirm the resulting file contains header fields like `TRACE_CYCLES_PER_SEC` and events such as:

```text
t:0x00001000 CPU:00 THREAD:THREADY pid:7 tid:3
t:0x000010C8 CPU:00 THREAD:THRUNNING pid:7 tid:3
```

These two lines are **illustrative, invented events**, not an extracted real QNX trace. Do not use a custom `-p` text layout; the parser expects the documented default layout.

## 5. Run PulseGuard locally

Clone the project, then run an initial synthetic walkthrough:

```bash
git clone https://github.com/samertall/pulseguard-rt.git
cd pulseguard-rt
python3 -m pulseguard demo --output-dir demo-output
```

Open `demo-output/report.html` in your browser. You should see the **SYNTHETIC DATA** warning, two CPU lanes, 32 complete dispatch observations, and a default 250 µs screening threshold.

To analyze your **real** `pulseguard.txt` instead:

```bash
python3 -m pulseguard analyze pulseguard.txt \
  --budget-us 250 \
  --html output/qnx-report.html \
  --json output/qnx-report.json
```

If the trace header lacks a clock frequency, use `--frequency 1000000000` **only if you have measured/verified your actual cycles-per-second value**. Never guess this value to make errors disappear.

## 6. Investigate latency and contention

In the report:

1. Find the **p95 dispatch** tile. Consider what it says about 95% of observed transitions, especially if sample count is low.
2. Adjust the **Threshold explorer**. Observe the proportion of dispatches over your user-selected screening budget.
3. Open **Thread pressure map**, search for a PID/TID, and compare its worst dispatch with the system-wide maximum.
4. Open **Slowest dispatches**, find source-line references, and inspect those exact lines in the traceprinter text to verify context.
5. Open **Capture diagnostics**. If the file has too few samples or non-monotonic timing, treat the numbers as provisional.

### Discussion prompts

- If the worst dispatch is 286.72 µs and the threshold is 250 µs, can we say a medical device missed its deadline? **No.** We lack the device's task deadlines and end-to-end timing evidence.
- If `THMUTEX` is observed, does that establish priority inversion? **No.** Additional mutex ownership and thread-priority information would be necessary.
- If two captures have different p95, can it be caused by workload differences? **Yes.** Control the workload and capture conditions before interpreting regressions.

## 7. Add a simple regression gate

Capture and analyze a baseline with the same workload, then capture a candidate run. Compare their JSON reports:

```bash
python3 -m pulseguard compare output/baseline.json output/candidate.json \
  --max-p95-regression-pct 10
```

An exit status of `2` means that the measured p95 regression exceeds 10% and the pipeline can raise a review flag. It does *not* certify whether the software is safe or deadline-compliant.

## 8. Verify and extend

Run the built-in tests:

```bash
python3 -m unittest discover -s tests -v
```

Optional extension: add a richer QNX `traceprinter` fixture from your own target, writing tests for each observed event variation. Avoid checking proprietary or sensitive operational trace data into a public repository.

## Official QNX references

- [tracelogger — QNX SDP 8.0](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/t/tracelogger.html)
- [traceprinter — QNX SDP 8.0](https://qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/t/traceprinter.html)
- [Interpreting traceprinter output — QNX SAT](https://qnx.com/developers/docs/8.0/com.qnx.doc.sat/topic/datainterpretation_Using_traceprinter.html)

*Original tutorial authored November 2026 for PulseGuard RT.*
