"""Generate an offline HTML report; no CDN, cookies, APIs, or hosted assets."""

from __future__ import annotations

import html
import json
from importlib.resources import files


def build_html(report: dict, *, title: str = "PulseGuard RT · Trace report") -> str:
    css = files("pulseguard").joinpath("assets/report.css").read_text(encoding="utf-8")
    js = files("pulseguard").joinpath("assets/report.js").read_text(encoding="utf-8")
    # JSON inside an HTML script node must not contain literal '<' or '</script>'.
    payload = json.dumps(report, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta name="color-scheme" content="dark"/><title>{html.escape(title)}</title>
<style>{css}</style></head><body>
<div class="app">
  <aside class="sidebar">
    <div class="brand"><div class="brand-symbol" aria-hidden="true"><span></span><span></span><span></span></div>
    <div><div class="brand-name">pulseguard<span>RT</span></div><div class="brand-caption">REAL-TIME INTELLIGENCE</div></div></div>
    <div class="side-label">WORKSPACE</div>
    <nav aria-label="Report sections">
      <a href="#overview" class="nav-item active"><span class="nav-icon">◈</span> Overview <span class="nav-dot"></span></a>
      <a href="#timeline" class="nav-item"><span class="nav-icon">▥</span> CPU timeline</a>
      <a href="#threads" class="nav-item"><span class="nav-icon">⌘</span> Thread inspector</a>
      <a href="#events" class="nav-item"><span class="nav-icon">≋</span> Worst dispatches</a>
      <a href="#diagnostics" class="nav-item"><span class="nav-icon">◇</span> Diagnostics</a>
    </nav>
    <div class="side-bottom"><span class="status-pulse"></span> LOCAL ANALYSIS ENGINE
      <p>All processing is offline. No trace data leaves this device.</p>
      <div class="side-version">QNX 8.0 target format · v0.1</div>
    </div>
  </aside>
  <main class="main">
    <header class="topbar"><div class="breadcrumbs">WORKSPACE <span>/</span> TRACE ANALYSIS <span>/</span> <strong>OVERVIEW</strong></div>
      <div class="top-actions"><span class="private"><i></i> OFFLINE MODE</span><button id="download-json" class="outline-btn">↓ Export JSON</button></div></header>
    <div class="content" id="overview">
      <section class="hero"><div class="hero-eyebrow"><span class="tiny-square"></span> PERFORMANCE OBSERVABILITY <span class="divider-dot">·</span> QNX SDP 8.0</div>
        <div class="hero-row"><div><h1>Real-time, <em>revealed.</em></h1><p>Turn kernel scheduling traces into actionable latency insights. Detect dispatch delays, compare thread behavior, and expose contention signals.</p></div>
        <div class="hero-mark" aria-hidden="true"><svg viewBox="0 0 160 90" fill="none"><path d="M0 49h32l13-25 17 48 18-43 13 20h24l13-28 16 28h14" stroke="#67e9b3" stroke-width="3" stroke-linejoin="round"/><path d="M0 49h32l13-25 17 48 18-43 13 20h24l13-28 16 28h14" stroke="#67e9b3" stroke-width="15" opacity=".07"/></svg></div></div>
      </section>
      <div class="notice" id="synthetic-alert" hidden><span>◉</span> SYNTHETIC DATA <span class="notice-text">This example is generated for demonstration. It is not a measured QNX hardware run.</span></div>
      <div class="section-heading"><div><div class="eyebrow">01 / PERFORMANCE</div><h2>Dispatch health</h2></div><div class="snapshot" id="snapshot"></div></div>
      <div class="metrics" id="metrics"></div>
      <div class="analysis-grid">
        <section class="panel distribution"><div class="panel-heading"><div><div class="eyebrow">LATENCY DISTRIBUTION</div><h3>Ready → Running</h3></div><span class="pill">µs · MICROSECONDS</span></div><div class="chart-area" id="distribution" role="img" aria-label="Histogram of dispatch latencies"></div><div class="chart-footer"><span>Each bar represents observed dispatches in a latency bucket.</span><span id="sample-count"></span></div></section>
        <section class="panel budget-panel"><div class="panel-heading"><div><div class="eyebrow">SENSITIVITY</div><h3>Threshold explorer</h3></div><span class="circle-icon">◎</span></div><p class="muted">Adjust your screening threshold to explore how many observed dispatches exceed it.</p>
          <div class="input-line"><label for="budget">Threshold</label><div><input id="budget" type="number" min="0.001" step="10"/><span>µs</span></div></div>
          <div class="gauge-wrap"><div class="gauge-label"><span>WITHIN THRESHOLD</span><strong id="gauge-pct">—</strong></div><div class="gauge-track"><div id="gauge-bar"></div></div></div><div class="budget-foot"><span id="within-count"></span><span id="breach-count"></span></div>
          <div class="insight"><span class="insight-icon">✧</span><p><strong>Interpretation</strong><br/>This is scheduling dispatch latency—not a verified application deadline miss.</p></div>
        </section>
      </div>
      <section id="timeline" class="panel spaced"><div class="panel-heading"><div><div class="eyebrow">02 / CPU EXECUTION</div><h3>Scheduling timeline</h3></div><span class="pill">OBSERVED THREAD SWITCHES</span></div><div class="timeline-scroller" id="timeline-body"></div><div class="timeline-note">Observed THRUNNING-to-THRUNNING spans only. Blank areas and partial spans are not interpreted as idle CPU time.</div></section>
      <section id="threads" class="panel spaced"><div class="panel-heading"><div><div class="eyebrow">03 / THREAD INSPECTOR</div><h3>Thread pressure map</h3></div><input id="thread-filter" type="search" placeholder="Filter PID or TID" aria-label="Filter threads"/></div><div class="table-scroll"><table><thead><tr><th>THREAD</th><th>SAMPLES</th><th>P95 DISPATCH</th><th>WORST</th><th>OVER THRESHOLD</th><th>RELATIVE PRESSURE</th></tr></thead><tbody id="thread-rows"></tbody></table></div></section>
      <section id="events" class="panel spaced"><div class="panel-heading"><div><div class="eyebrow">04 / OUTLIERS</div><h3>Slowest dispatches</h3></div><span class="pill">TOP OBSERVATIONS</span></div><div class="table-scroll"><table><thead><tr><th>THREAD</th><th>CPU</th><th>READY AT</th><th>RAN AT</th><th>DELAY</th><th>SOURCE LINES</th></tr></thead><tbody id="event-rows"></tbody></table></div></section>
      <section id="diagnostics" class="panel spaced"><div class="panel-heading"><div><div class="eyebrow">05 / EVIDENCE</div><h3>Capture diagnostics</h3></div><span class="pill">READ BEFORE ACTING</span></div><div id="warnings"></div><div class="provenance" id="provenance"></div></section>
      <footer>BUILT FOR DETERMINISTIC SYSTEMS <span>·</span> PULSEGUARD RT <span>·</span> OPEN SOURCE <span class="foot-right">Developed by Samer Tallauze</span></footer>
    </div>
  </main>
</div>
<script id="report-data" type="application/json">{payload}</script><script>{js}</script></body></html>"""
