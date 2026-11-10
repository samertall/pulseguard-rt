"""Produce an original, silent 84-second demo from actual PulseGuard CLI output.

Optional dependencies: Pillow and ffmpeg. The tool itself uses only stdlib.
The video openly labels synthetic example data, and does not claim QNX capture.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo-output" / "pulseguard_demo.mp4"
WIDTH, HEIGHT, FPS, DURATION = 1280, 720, 12, 84
BG = "#09121b"
PANEL = "#122430"
GREEN = "#68e7b4"
WHITE = "#e5f0ef"
MUTED = "#8da4ad"
ORANGE = "#e5a76c"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONT_DIR / filename), size)


def text(draw, xy, value, size=22, color=WHITE, bold=False):
    draw.text(xy, value, font=font(size, bold), fill=color)


def base(title: str, chapter: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((50, 37, 1230, 680), 18, fill="#101e2a", outline="#28433f", width=2)
    d.rectangle((50, 37, 1230, 42), fill=GREEN)
    text(d, (85, 73), "///  PULSEGUARD RT", 21, GREEN, True)
    text(d, (970, 78), "OFFLINE  /  OPEN SOURCE", 13, MUTED, True)
    text(d, (85, 132), chapter, 16, GREEN, True)
    text(d, (85, 170), title, 38, WHITE, True)
    d.line((85, 632, 1195, 632), fill="#2b4248", width=2)
    text(d, (85, 644), "QNX 8.0-FORMAT SYNTHETIC DATA  -  NOT A MEASURED DEVICE CAPTURE", 12, ORANGE)
    return image


def main() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pulseguard", "analyze", str(ROOT / "examples/synthetic_qnx8_trace.txt")],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    report = json.loads((ROOT / "demo-output/report.json").read_text(encoding="utf-8"))
    m = report["metrics"]
    summary = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    scenes = []

    im = base("Real-time, revealed.", "01  /  INTRODUCTION")
    d = ImageDraw.Draw(im)
    text(d, (88, 254), "Scheduling trace intelligence for QNX SDP 8.0", 26, WHITE)
    text(d, (88, 305), "From kernel events to measurable dispatch delay.", 20, MUTED)
    d.rounded_rectangle((88, 388, 375, 452), 9, fill="#1d5145")
    text(d, (115, 403), "DEVELOPER TOOLING", 18, GREEN, True)
    text(d, (88, 511), "Linux  /  macOS  /  Windows  -  Python 3.10+", 17, MUTED)
    scenes.append(im)

    im = base("1. Analyze the trace", "02  /  LIVE CLI OUTPUT")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((85, 253, 1190, 600), 11, fill="#06111a", outline="#36525a", width=2)
    text(d, (112, 272), "samer@linux:~/pulseguard-rt$", 16, GREEN)
    text(d, (112, 310), "python3 -m pulseguard analyze examples/synthetic_qnx8_trace.txt", 17, WHITE)
    for i, line in enumerate(summary[:9]):
        text(d, (112, 354 + i * 24), line[:97], 15, MUTED if i > 0 else GREEN)
    scenes.append(im)

    im = base("2. Read the signal", "03  /  PERFORMANCE")
    d = ImageDraw.Draw(im)
    metrics = [
        ("P95 DISPATCH", f"{m['p95_us']}", "microseconds"),
        ("WORST DISPATCH", f"{m['max_us']}", "microseconds"),
        ("DISPATCH PAIRS", str(m["samples"]), "complete observations"),
        ("OVER 250 US", str(m["breaches"]), "screening exceedances"),
    ]
    for i, (label, val, caption) in enumerate(metrics):
        x = 85 + i * 279
        d.rounded_rectangle((x, 278, x + 260, 478), 10, fill=PANEL, outline="#2a4a4f", width=2)
        text(d, (x + 16, 302), label, 15, MUTED, True)
        text(d, (x + 16, 351), val, 40, GREEN if i != 3 else ORANGE, True)
        text(d, (x + 16, 425), caption, 13, MUTED)
    text(d, (85, 545), "The threshold is configurable; exceedance does not prove a deadline miss.", 17, MUTED)
    scenes.append(im)

    im = base("3. Inspect outliers", "04  /  THREAD DIAGNOSTICS")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((85, 265, 1190, 581), 9, fill=PANEL)
    text(d, (111, 288), "THREAD", 15, MUTED, True)
    text(d, (380, 288), "SAMPLES", 15, MUTED, True)
    text(d, (630, 288), "P95", 15, MUTED, True)
    text(d, (875, 288), "WORST", 15, MUTED, True)
    for i, t in enumerate(report["threads"][:4]):
        y = 352 + i * 52
        d.line((111, y - 13, 1160, y - 13), fill="#33505a", width=1)
        text(d, (111, y), f"PID {t['pid']} / TID {t['tid']}", 17, WHITE)
        text(d, (380, y), str(t['samples']), 17, WHITE)
        text(d, (630, y), f"{t['p95_us']} us", 17, GREEN)
        text(d, (875, y), f"{t['max_us']} us", 17, ORANGE)
    scenes.append(im)

    im = base("4. QNX-specific workflow", "05  /  VERIFIABLE INTEGRATION")
    d = ImageDraw.Draw(im)
    blocks = [
        ("QNX 8.0 TARGET", "tracelogger -s 10 -w", 85),
        ("QNX SDP TOOL", "traceprinter -f ...", 465),
        ("HOST DIAGNOSTICS", "pulseguard analyze", 845),
    ]
    for label, command, x in blocks:
        d.rounded_rectangle((x, 299, x + 345, 475), 12, fill=PANEL, outline="#306b5d", width=2)
        text(d, (x + 20, 330), label, 18, GREEN, True)
        text(d, (x + 20, 398), command, 15, WHITE)
    text(d, (86, 533), "QNX kernel event names, CPU cycle frequency, PID/TID scheduling transitions.", 17, MUTED)
    scenes.append(im)

    im = base("Open source. Reproducible.", "06  /  NEXT STEPS")
    d = ImageDraw.Draw(im)
    text(d, (88, 280), "9 automated tests  /  Interactive offline HTML  /  JSON export", 23, GREEN)
    text(d, (88, 343), "Includes an end-to-end QNX 8.0 tracing codelab.", 21, WHITE)
    text(d, (88, 410), "Repository: github.com/samertall/pulseguard-rt", 20, MUTED)
    text(d, (88, 486), "Built by Samer Tallauze  -  samertall.com", 18, WHITE)
    scenes.append(im)

    # Chapters are intentionally modestly paced, music-free, and <3 minutes.
    timeline = [(0, 12), (12, 27), (27, 44), (44, 59), (59, 73), (73, 84)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-crf", "24", "-movflags", "+faststart", str(OUT),
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        assert encoder.stdin is not None
        for f in range(DURATION * FPS):
            t = f / FPS
            idx = next(i for i, (start, end) in enumerate(timeline) if start <= t < end)
            frame = scenes[idx].copy()
            draw = ImageDraw.Draw(frame)
            start, end = timeline[idx]
            draw.rounded_rectangle((85, 613, 1195, 620), 3, fill="#29443d")
            draw.rounded_rectangle((85, 613, 85 + int(1110 * (t-start)/(end-start)), 620), 3, fill=GREEN)
            encoder.stdin.write(frame.tobytes())
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError("ffmpeg failed to encode the video")
    print(f"Demo video: {OUT} ({DURATION}s, {WIDTH}x{HEIGHT}, silent)")
    print("Note: video uses genuine CLI results on explicitly synthetic data.")


if __name__ == "__main__":
    main()
