# Contributing to PulseGuard RT

Thanks for helping make QNX scheduling diagnostics clearer and more reproducible. Contributions that improve trace parsing, correctness, accessibility, documentation, and tests are welcome.

## Local setup

PulseGuard RT uses Python 3.10+ and the standard library. You do **not** need QNX SDK access to run the synthetic fixture or host-side tests.

```bash
git clone https://github.com/samertall/pulseguard-rt.git
cd pulseguard-rt
python3 -m unittest discover -s tests -v
python3 -m pulseguard demo --output-dir demo-output
```

Open `demo-output/report.html` locally to inspect the offline dashboard. See [the codelab](docs/CODELAB.md) for the capture-to-analysis workflow.

## Propose a change

1. Search existing issues and pull requests before starting.
2. Open an issue for changes that may alter trace interpretation, output schemas, or command-line behavior.
3. Work on a focused branch and keep unrelated changes out of the pull request.
4. Add or update tests for behavior changes. Prefer small, synthetic QNX-format traces with known expected results.
5. Run `python3 -m unittest discover -s tests -v` and include the results in your pull request.
6. Explain what changed, why, how it was tested, and any limitations. Attach a screenshot for user-interface changes where useful.

## Correctness and safety

- Preserve the meaning of `THREADY`, `THRUNNING`, and `THMUTEX` events. Do not interpret every long dispatch as an application deadline miss, or every mutex wait as proven priority inversion.
- Keep the dashboard self-contained and offline. New third-party dependencies, remote telemetry, or external network requests should be explicitly justified before adoption.
- Respect the QNX license and attribution requirements. Never commit proprietary QNX SDK binaries or redistribution-restricted artifacts.
- Do not publish production traces containing credentials, customer information, internal paths, identifying process names, or other sensitive details. Reduce a failing case to a minimal **sanitized** trace.
- Clearly distinguish synthetic host tests from actual QNX 8.0 target validation; do not label a test as target-verified without evidence.

## Bug reports

Use the [Bug report issue form](.github/ISSUE_TEMPLATE/bug_report.yml). State the Python version, host OS, trace source, exact command, expected result, actual result, and whether the issue reproduces with the bundled synthetic fixture.

For feature ideas, describe the real diagnostic problem and a concrete example. Keep the original scope—offline performance analysis of QNX `traceprinter` text—in mind.

## License

By submitting a contribution, you agree that it may be distributed under this repository's [MIT License](LICENSE).
