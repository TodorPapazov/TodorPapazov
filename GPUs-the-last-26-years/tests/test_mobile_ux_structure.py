"""
Structural proof: mobile UX + GPU-themed background + interactivity wiring
for docs/gpu-26-years. Captures to goal scratch when SCRATCH env set,
else default implementer scratch for this goal.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "docs" / "gpu-26-years"
DEFAULT_SCRATCH = Path(
    r"C:\Users\todor\AppData\Local\Temp\grok-goal-357c27c60412\implementer"
)


def main() -> int:
    scratch = Path(os.environ.get("SCRATCH", DEFAULT_SCRATCH))
    scratch.mkdir(parents=True, exist_ok=True)

    html = (SITE / "index.html").read_text(encoding="utf-8")
    css = (SITE / "css" / "hud.css").read_text(encoding="utf-8")
    app = (SITE / "js" / "app.js").read_text(encoding="utf-8")
    logic = (SITE / "js" / "gpu-logic.js").read_text(encoding="utf-8")
    lines: list[str] = []

    # Entry exists
    assert (SITE / "index.html").is_file()
    lines.append("PASS entry index.html exists")

    # Viewport + mobile layout markers
    assert 'name="viewport"' in html
    assert "width=device-width" in html
    assert "@media" in css
    assert "max-width" in css or "min-width" in css
    # Narrow-width / stack patterns
    assert "grid-template-columns: 1fr" in css or "grid-template-columns:1fr" in css
    assert "nav-toggle" in html and "nav-toggle" in css
    assert "mobile-dock" in html and "mobile-dock" in css
    assert "overflow-x: hidden" in css or "overflow-x:hidden" in css
    assert "min-height: var(--tap)" in css or "--tap" in css
    lines.append("PASS mobile viewport, breakpoints, nav-toggle, mobile-dock, overflow-x, tap targets")

    # GPU-themed background (not plain solid alone)
    assert 'id="gpuBackground"' in html or "gpu-bg" in html
    assert "gpu-silicon-bg.svg" in html or "gpu-bg__art" in html
    bg_svg = SITE / "assets" / "gpu-silicon-bg.svg"
    assert bg_svg.is_file(), "missing GPU background SVG asset"
    svg = bg_svg.read_text(encoding="utf-8")
    motif = any(k in svg.lower() for k in ("gpu", "die", "silicon", "circuit", "chip"))
    assert motif, "SVG must include GPU/circuit/die/silicon motif keywords"
    assert "gpu-bg" in css and "gpu-bg__veil" in css
    # Contrast overlay
    assert "veil" in css.lower() or "rgba(6, 10, 20" in css
    assert "panel" in css and "--surface" in css
    lines.append("PASS GPU-themed background layer (SVG silicon/die/circuit) + contrast veil/panels")

    # Filters / Q&A still wired
    for t in ("applyFilters", "filterGpus", "answerQuestion", "yearMin", "btnAsk", "liveCount"):
        assert t in app or t in html, f"missing wiring {t}"
    for t in ("inflateToTarget", "mostExpensiveYear", "answerQuestion"):
        assert t in logic
    lines.append("PASS filter + Q&A + inflation logic wiring retained")

    # file:// safe
    assert 'type="module"' not in html
    assert "gpu-dataset.js" in html
    lines.append("PASS file://-safe classic scripts retained")

    # Chip-row / touch-friendly classes present
    assert "chip-row" in html or "chip-row" in css
    assert "btn-block" in css or "min-height: var(--tap)" in css
    lines.append("PASS user-friendly control layout markers")

    out = scratch / "mobile-ux-structure.log"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("Wrote", out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print("FAIL:", e, file=sys.stderr)
        raise SystemExit(1)
