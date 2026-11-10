"""Create repository artwork from the bundled, explicitly synthetic demo data.

Requires Pillow only for generating these marketing assets. The PulseGuard CLI
and offline report retain their zero-third-party-dependency guarantee.
Run ``python3 -m pulseguard demo --output-dir demo-output`` first.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
DATA = ROOT / "demo-output" / "report.json"
BG = "#090f16"
SIDE = "#0b131d"
PANEL = "#101b28"
PANEL2 = "#152230"
LINE = "#263746"
TEXT = "#e8f3f3"
MUTED = "#8296a8"
GREEN = "#67e9b3"
TEAL = "#1fcfbd"
AMBER = "#e6ac68"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONT_DIR / name), size)


def label(d: ImageDraw.ImageDraw, xy: tuple[int, int], value: str,
          size: int = 18, color: str = TEXT, bold: bool = False) -> None:
    d.text(xy, value, font=font(size, bold), fill=color)


def rounded(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
            fill: str, outline: str | None = LINE, radius: int = 12) -> None:
    d.rounded_rectangle(box, radius, fill=fill, outline=outline, width=2 if outline else 1)


def heartbeat(d: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1,
              color: str = GREEN, width: int = 4) -> None:
    raw = [(0, 29), (28, 29), (45, 29), (59, 10), (78, 49),
           (95, 0), (111, 29), (151, 29), (172, 20), (192, 29), (220, 29)]
    pts = [(int(x + a * scale), int(y + b * scale)) for a, b in raw]
    d.line(pts, fill=color, width=width, joint="curve")


def histogram(d: ImageDraw.ImageDraw, values: list[float], rect: tuple[int, int, int, int],
              bins: int = 15, maximum: float = 320) -> None:
    x1, y1, x2, y2 = rect
    for n in range(5):
        y = y1 + (y2-y1) * n // 4
        d.line((x1, y, x2, y), fill="#243744", width=1)
    counts = [0] * bins
    for v in values:
        counts[min(int(v / maximum * bins), bins-1)] += 1
    max_count = max(counts) or 1
    bar_step = (x2 - x1) / bins
    for i, count in enumerate(counts):
        height = int((y2-y1-12) * count / max_count)
        left = int(x1 + i * bar_step + 5)
        right = int(x1 + (i+1) * bar_step - 5)
        d.rounded_rectangle((left, y2-height, right, y2), 3, fill=GREEN if i < 12 else AMBER)


def report_preview(data: dict) -> None:
    metrics = data["metrics"]
    im = Image.new("RGB", (1440, 900), BG)
    d = ImageDraw.Draw(im)

    # The composition follows the actual report's colors, sections and hierarchy.
    d.rectangle((0, 0, 234, 900), fill=SIDE)
    d.line((234, 0, 234, 900), fill="#1c2d3a", width=2)
    heartbeat(d, 25, 29, .17, width=4)
    label(d, (76, 26), "pulseguard", 26, TEXT, True)
    label(d, (202, 24), "RT", 11, GREEN, True)
    label(d, (27, 66), "PERFORMANCE INTELLIGENCE", 10, MUTED, True)
    label(d, (28, 143), "WORKSPACE", 12, "#597183", True)
    for i, text in enumerate(("Overview", "Dispatch analysis", "CPU timeline", "Thread explorer")):
        y = 185 + i * 61
        if i == 0:
            rounded(d, (16, y-8, 218, y+43), "#19302f", None, 8)
        label(d, (36, y+2), ("●  " if i == 0 else "◦  ") + text, 15,
              GREEN if i == 0 else MUTED, i == 0)
    d.line((27, 784, 204, 784), fill=LINE, width=1)
    label(d, (29, 803), "●  LOCAL / OFFLINE", 12, GREEN, True)
    label(d, (29, 844), "SYNTHETIC EXAMPLE", 11, AMBER, True)

    d.line((234, 73, 1440, 73), fill=LINE, width=1)
    label(d, (276, 26), "PERFORMANCE  /  OVERVIEW", 13, MUTED, True)
    label(d, (1210, 26), "PRIVATE  •  NO CLOUD", 12, GREEN, True)
    rounded(d, (275, 107, 1402, 326), "#102525", "#234540", 14)
    label(d, (312, 135), "◆  QNX SDP 8.0   •   SCHEDULER ANALYSIS", 13, GREEN, True)
    label(d, (312, 184), "Real-time, revealed.", 48, TEXT, True)
    label(d, (315, 256), "From kernel trace text to actionable thread dispatch insights.", 17, "#a0babd")
    heartbeat(d, 1030, 167, 1.25, color=GREEN, width=8)
    rounded(d, (275, 339, 1402, 376), "#302719", "#70512e", 5)
    label(d, (294, 349), "SYNTHETIC DEMO DATA  •  NOT A QNX DEVICE CAPTURE", 14, AMBER, True)

    label(d, (279, 403), "01  /  PERFORMANCE SNAPSHOT", 12, GREEN, True)
    cards = [
        ("P50 DISPATCH", f'{metrics["p50_us"]:.2f}', "µs", "Median observed dispatch", GREEN),
        ("P95 DISPATCH", f'{metrics["p95_us"]:.2f}', "µs", "95th percentile", GREEN),
        ("WORST DISPATCH", f'{metrics["max_us"]:.2f}', "µs", "Maximum observed", TEXT),
        ("OVER 250 µs", f'{metrics["breaches"]} / {metrics["samples"]}', "", "Screening exceedances", AMBER),
    ]
    for i, (name, value, unit, caption, tint) in enumerate(cards):
        x = 275 + i * 284
        rounded(d, (x, 434, x+270, 596), PANEL, LINE, 10)
        d.line((x+1, 435, x+268, 435), fill=tint, width=3)
        label(d, (x+19, 454), name, 12, MUTED, True)
        label(d, (x+19, 488), value, 31, tint, True)
        if unit:
            right = d.textbbox((0, 0), value, font=font(31, True))[2]
            label(d, (x+25+right, 501), unit, 14, MUTED)
        label(d, (x+19, 563), caption, 12, MUTED)

    rounded(d, (275, 611, 916, 873), PANEL, LINE, 10)
    label(d, (302, 632), "02  /  DISPATCH LATENCY DISTRIBUTION", 13, GREEN, True)
    label(d, (302, 660), "Observed THREADY → THRUNNING intervals", 14, TEXT)
    histogram(d, [s["latency_us"] for s in data["dispatches"]], (312, 709, 880, 834))
    for x, tick in ((312, "0"), (583, "160 µs"), (845, "320 µs")):
        label(d, (x, 844), tick, 10, MUTED)

    rounded(d, (932, 611, 1402, 873), PANEL, LINE, 10)
    label(d, (959, 632), "03  /  SCREENING BUDGET", 13, GREEN, True)
    label(d, (959, 679), "Configured threshold", 15, MUTED)
    label(d, (959, 712), "250 µs", 36, GREEN, True)
    rounded(d, (959, 778, 1374, 789), "#30444d", None, 5)
    rounded(d, (959, 778, 985, 789), GREEN, None, 5)
    label(d, (959, 810), "6.25% exceed the screening budget", 14, AMBER)
    im.quantize(colors=128, method=Image.Quantize.FASTOCTREE,
                dither=Image.Dither.NONE).save(OUT / "dashboard-preview.png", optimize=True)


def social_preview(data: dict) -> None:
    m = data["metrics"]
    im = Image.new("RGB", (1280, 640), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, 1280, 32):
        d.line((x, 0, x, 640), fill="#10202a", width=1)
    for y in range(0, 640, 32):
        d.line((0, y, 1280, y), fill="#10202a", width=1)
    d.rectangle((0, 0, 1280, 12), fill=GREEN)
    heartbeat(d, 62, 69, .28, width=5)
    label(d, (143, 64), "PULSEGUARD", 30, TEXT, True)
    label(d, (393, 71), "RT", 20, GREEN, True)
    label(d, (65, 159), "See what the scheduler", 40, TEXT, True)
    label(d, (65, 218), "is telling you.", 40, GREEN, True)
    label(d, (66, 302), "Offline QNX SDP 8.0 trace intelligence", 21, TEXT)
    label(d, (66, 343), "Dispatch latency • Mutex-wait signals • CI gates", 16, MUTED)
    rounded(d, (64, 431, 352, 480), "#1c5144", None, 9)
    label(d, (84, 444), "ZERO DEPENDENCIES", 16, GREEN, True)
    label(d, (66, 550), "github.com/samertall/pulseguard-rt", 16, MUTED, True)

    # Right-hand panel uses measured calculations from the bundled fixture.
    rounded(d, (751, 91, 1207, 533), "#101b28", "#2a4d4a", 16)
    label(d, (779, 120), "SYNTHETIC REPORT / OVERVIEW", 14, GREEN, True)
    d.line((778, 164, 1179, 164), fill="#2b414d", width=1)
    label(d, (779, 192), "P95 DISPATCH", 12, MUTED, True)
    label(d, (780, 220), f'{m["p95_us"]:.2f} µs', 34, GREEN, True)
    label(d, (1019, 192), "WORST", 12, MUTED, True)
    label(d, (1020, 231), f'{m["max_us"]:.2f}', 23, AMBER, True)
    label(d, (781, 302), "DISPATCH DISTRIBUTION", 12, MUTED, True)
    histogram(d, [s["latency_us"] for s in data["dispatches"]], (782, 341, 1172, 465), bins=12)
    label(d, (781, 489), f'{m["samples"]} dispatches  •  {m["breaches"]} over budget', 13, MUTED)
    label(d, (763, 551), "SYNTHETIC EXAMPLE  /  NOT A DEVICE CAPTURE", 12, AMBER, True)
    im.quantize(colors=128, method=Image.Quantize.FASTOCTREE,
                dither=Image.Dither.NONE).save(OUT / "social-preview.png", optimize=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if not DATA.is_file():
        raise SystemExit("Generate demo-output/report.json with the PulseGuard demo command first")
    report = json.loads(DATA.read_text(encoding="utf-8"))
    report_preview(report)
    social_preview(report)
    print("Created docs/images/dashboard-preview.png (1440×900)")
    print("Created docs/images/social-preview.png (1280×640)")
