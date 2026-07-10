"""Static structure + file:// safety proof for docs/gpu-26-years site."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "docs" / "gpu-26-years"
SCRATCH = Path(
    os.environ.get(
        "SCRATCH",
        r"C:\Users\todor\AppData\Local\Temp\grok-goal-357c27c60412\implementer",
    )
)


def main() -> int:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    app = (SITE / "js" / "app.js").read_text(encoding="utf-8")
    ds = (SITE / "js" / "gpu-dataset.js").read_text(encoding="utf-8")
    logic = (SITE / "js" / "gpu-logic.js").read_text(encoding="utf-8")
    lines: list[str] = []

    assert 'type="module"' not in html and "type='module'" not in html
    assert "gpu-dataset.js" in html and "gpu-logic.js" in html and "app.js" in html
    assert "fetch(" not in app
    assert "window.GPU_DATASET" in ds
    m = re.search(r'"row_count"\s*:\s*(\d+)', ds)
    assert m and int(m.group(1)) > 50
    lines.append("PASS file://-safe: classic scripts, no ES modules, no fetch for dataset")
    lines.append(f"PASS dataset embedded: row_count={m.group(1)}")

    for t in ("hud-label", "panel-bracket", "status-dot"):
        assert t in html
    assert "affordab" in html.lower() or "AFFORD" in html
    assert "26" in html and ("GPU" in html or "gpu" in html)
    lines.append("PASS HUD primitives + GPU affordability subject in index.html")

    for t in (
        "addEventListener",
        "applyFilters",
        "filterGpus",
        "answerQuestion",
        "yearMin",
        "manufacturer",
        "btnAsk",
        "qaInput",
        "tableBody",
        "liveCount",
        "chartPrice",
    ):
        assert t in app or t in html, f"missing {t}"
    lines.append("PASS event handlers / filters / Q&A / charts / table wiring present")

    for t in ("inflateToTarget", "yearLevelStats", "mostExpensiveYear", "answerQuestion"):
        assert t in logic
    lines.append("PASS pure logic exports present in gpu-logic.js")

    # JSON export exists and non-empty
    jpath = SITE / "data" / "gpu-26-years.json"
    assert jpath.is_file()
    text = jpath.read_text(encoding="utf-8")
    assert '"gpus"' in text and len(text) > 1000
    lines.append("PASS web JSON export present and non-trivial")

    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = SCRATCH / "static-structure-proof.txt"
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
