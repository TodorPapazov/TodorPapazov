"""
Unit tests for shipped client-side logic: docs/gpu-26-years/js/gpu-logic.js
against the real GPU dataset export. Uses dukpy to execute the real JS file.

Run:
  python GPUs-the-last-26-years/tests/test_gpu_logic.py

Captures should be written by the caller to {SCRATCH}/gpu-site-unit-tests.log
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGIC_PATH = ROOT / "docs" / "gpu-26-years" / "js" / "gpu-logic.js"
JSON_PATH = ROOT / "docs" / "gpu-26-years" / "data" / "gpu-26-years.json"
CSV_PATH = ROOT / "GPUs-the-last-26-years" / "data" / "GPU-26-Years.csv"
INDEX_PATH = ROOT / "docs" / "gpu-26-years" / "index.html"
APP_PATH = ROOT / "docs" / "gpu-26-years" / "js" / "app.js"


def recompute_from_csv(csv_path: Path, cpi: dict, target_cpi: float):
    by_year: dict[int, list[float]] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(float(row["Released_Year"]))
            msrp = float(row["MSRP_USD"])
            cpi_y = float(cpi[str(year)])
            real = msrp * (target_cpi / cpi_y)
            by_year.setdefault(year, []).append(real)

    def median(vals: list[float]) -> float:
        a = sorted(vals)
        n = len(a)
        mid = n // 2
        if n % 2:
            return a[mid]
        return (a[mid - 1] + a[mid]) / 2.0

    stats = [
        {"year": y, "median_real": median(v), "count": len(v)}
        for y, v in sorted(by_year.items())
    ]
    exp = max(stats, key=lambda s: s["median_real"])
    aff = min(stats, key=lambda s: s["median_real"])
    return exp, aff, stats


def load_gpu_logic():
    try:
        import dukpy
    except ImportError as e:
        raise SystemExit(
            "dukpy is required to execute shipped JS in tests. "
            "pip install dukpy\n" + str(e)
        ) from e

    logic_src = LOGIC_PATH.read_text(encoding="utf-8")
    dataset = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    # Evaluate IIFE and expose GpuLogic
    ctx_code = (
        logic_src
        + "\n"
        + "function __call(fn, argsJson) {\n"
        + "  var args = JSON.parse(argsJson);\n"
        + "  return GpuLogic[fn].apply(GpuLogic, args);\n"
        + "}\n"
    )
    # dukpy.evaljs doesn't keep state well between calls for complex objects —
    # use a single eval with embedded dataset for key assertions.

    class GpuLogicBridge:
        def __init__(self):
            self._base = ctx_code
            self.dataset = dataset

        def call(self, fn: str, *args):
            payload = json.dumps(list(args))
            # dukpy needs pure JS return values; wrap JSON
            code = (
                self._base
                + f"\nvar __result = GpuLogic[{json.dumps(fn)}].apply(GpuLogic, JSON.parse({json.dumps(payload)}));\n"
                + "JSON.stringify(__result);\n"
            )
            out = dukpy.evaljs(code)
            if out is None or out == "undefined":
                return None
            return json.loads(out)

        def build_insights_json(self):
            code = (
                self._base
                + f"\nvar ds = JSON.parse({json.dumps(json.dumps(self.dataset))});\n"
                + "var ins = GpuLogic.buildInsights(ds);\n"
                + "JSON.stringify({\n"
                + "  mostExpensive: ins.mostExpensive,\n"
                + "  mostAffordable: ins.mostAffordable,\n"
                + "  yearCount: ins.yearStats.length,\n"
                + "  rowCount: ins.rows.length,\n"
                + "  overallMedianReal: ins.overall.median_real,\n"
                + "  nvidiaMedianReal: ins.nvidiaMedianReal,\n"
                + "  amdMedianReal: ins.amdMedianReal\n"
                + "});\n"
            )
            return json.loads(dukpy.evaljs(code))

        def answer(self, question: str):
            code = (
                self._base
                + f"\nvar ds = JSON.parse({json.dumps(json.dumps(self.dataset))});\n"
                + "var ins = GpuLogic.buildInsights(ds);\n"
                + f"var ans = GpuLogic.answerQuestion({json.dumps(question)}, ins, ins.rows);\n"
                + "JSON.stringify(ans);\n"
            )
            return json.loads(dukpy.evaljs(code))

        def filter_count(self, year_min, year_max, mfr):
            code = (
                self._base
                + f"\nvar ds = JSON.parse({json.dumps(json.dumps(self.dataset))});\n"
                + "var ins = GpuLogic.buildInsights(ds);\n"
                + f"var f = GpuLogic.filterGpus(ins.rows, {{yearMin:{year_min}, yearMax:{year_max}, manufacturer:{json.dumps(mfr)}}});\n"
                + "JSON.stringify({count: f.length, all: ins.rows.length, sample: f.slice(0,3).map(function(r){return {y:r.year,m:r.manufacturer};})});\n"
            )
            return json.loads(dukpy.evaljs(code))

    return GpuLogicBridge()


def main() -> int:
    results: list[str] = []
    assert LOGIC_PATH.is_file(), f"missing {LOGIC_PATH}"
    assert JSON_PATH.is_file(), f"missing {JSON_PATH} — run export_web_data.py"
    assert CSV_PATH.is_file(), f"missing {CSV_PATH}"

    dataset = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert dataset["gpus"], "empty gpus"
    assert dataset["cpi"], "empty cpi"
    target_cpi = float(dataset["meta"]["target_cpi"])

    bridge = load_gpu_logic()

    # Inflation: recompute independently from first row
    g0 = dataset["gpus"][0]
    year = int(g0["year"])
    msrp = float(g0["msrp"])
    cpi_y = float(dataset["cpi"][str(year)])
    expected = msrp * (target_cpi / cpi_y)
    got = bridge.call("inflateToTarget", msrp, year, dataset["cpi"], target_cpi)
    assert abs(float(got) - expected) < 1e-9, f"inflate {got} != {expected}"
    results.append("PASS inflateToTarget against CPI formula")

    # Year KPIs vs CSV recompute (no hardcoded years)
    exp_i, aff_i, _ = recompute_from_csv(CSV_PATH, dataset["cpi"], target_cpi)
    insights = bridge.build_insights_json()
    assert insights["mostExpensive"]["year"] == exp_i["year"], (
        f"expensive year {insights['mostExpensive']['year']} != {exp_i['year']}"
    )
    assert abs(insights["mostExpensive"]["median_real"] - exp_i["median_real"]) < 0.05
    assert insights["mostAffordable"]["year"] == aff_i["year"], (
        f"affordable year {insights['mostAffordable']['year']} != {aff_i['year']}"
    )
    assert abs(insights["mostAffordable"]["median_real"] - aff_i["median_real"]) < 0.05
    results.append(
        f"PASS year KPIs match CSV recompute: expensive={exp_i['year']} affordable={aff_i['year']}"
    )
    results.append(
        f"PASS independent recompute medians: exp={exp_i['median_real']:.2f} aff={aff_i['median_real']:.2f}"
    )

    assert insights["rowCount"] == len(dataset["gpus"])
    assert insights["yearCount"] >= 10
    results.append(f"PASS buildInsights rows={insights['rowCount']} years={insights['yearCount']}")

    # Filter
    fc = bridge.filter_count(2018, 2025, "NVIDIA")
    assert fc["count"] > 0
    assert fc["count"] < fc["all"]
    for s in fc["sample"]:
        assert s["m"] == "NVIDIA"
        assert 2018 <= s["y"] <= 2025
    results.append(f"PASS filterGpus {fc['count']}/{fc['all']}")

    # Q&A
    a1 = bridge.answer("Which year was the most expensive?")
    assert a1.get("answer") and len(a1["answer"]) > 20
    assert str(exp_i["year"]) in a1["answer"]
    a2 = bridge.answer("Which year was most affordable?")
    assert str(aff_i["year"]) in a2["answer"]
    a3 = bridge.answer("How does inflation adjustment work?")
    assert "cpi" in a3["answer"].lower() or "inflation" in a3["answer"].lower()
    results.append("PASS answerQuestion grounded answers")

    # Structural site checks (if present)
    if INDEX_PATH.is_file():
        html = INDEX_PATH.read_text(encoding="utf-8")
        for token in ("hud-label", "panel-bracket", "GPU", "affordab", "SYS"):
            assert token.lower() in html.lower() or token in html, f"HUD token missing: {token}"
        assert "gpu-logic.js" in html and "gpu-dataset.js" in html
        results.append("PASS index.html HUD primitives + script includes")
    else:
        results.append("SKIP index.html not yet present")

    if APP_PATH.is_file():
        app = APP_PATH.read_text(encoding="utf-8")
        assert "filterGpus" in app or "GpuLogic.filter" in app or "applyFilters" in app
        assert "answerQuestion" in app
        results.append("PASS app.js wires filter + Q&A")
    else:
        results.append("SKIP app.js not yet present")

    print("=== test_gpu_logic.py (shipped gpu-logic.js via dukpy) ===")
    for line in results:
        print(line)
    print(f"ALL TESTS PASSED ({len(results)} checks)")
    print(
        f"Summary: rows={len(dataset['gpus'])} "
        f"expensiveYear={exp_i['year']} affordableYear={aff_i['year']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print("=== FAILED ===", file=sys.stderr)
        print(e, file=sys.stderr)
        raise SystemExit(1)
