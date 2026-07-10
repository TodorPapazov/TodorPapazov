/**
 * Unit tests for shipped docs/gpu-26-years/js/gpu-logic.js
 * against the real exported dataset (or regenerates path).
 *
 * Run: node GPUs-the-last-26-years/tests/test_gpu_logic.js
 * Exit 0 = pass. Writes summary to stdout (capture to scratch).
 */
"use strict";

var fs = require("fs");
var path = require("path");

var ROOT = path.resolve(__dirname, "..", "..");
var LOGIC_PATH = path.join(ROOT, "docs", "gpu-26-years", "js", "gpu-logic.js");
var JSON_PATH = path.join(ROOT, "docs", "gpu-26-years", "data", "gpu-26-years.json");
var CSV_PATH = path.join(ROOT, "GPUs-the-last-26-years", "data", "GPU-26-Years.csv");

function assert(cond, msg) {
  if (!cond) {
    throw new Error("ASSERT FAIL: " + msg);
  }
}

function parseCsv(text) {
  var lines = text.trim().split(/\r?\n/);
  var headers = lines[0].split(",");
  var rows = [];
  for (var i = 1; i < lines.length; i++) {
    // Simple CSV split (dataset has no quoted commas in key fields we need)
    var parts = lines[i].split(",");
    if (parts.length < headers.length) continue;
    var obj = {};
    for (var h = 0; h < headers.length; h++) {
      obj[headers[h]] = parts[h];
    }
    rows.push(obj);
  }
  return rows;
}

function recomputeFromCsv(csvRows, cpi, targetCpi) {
  var byYear = {};
  csvRows.forEach(function (r) {
    var year = Number(r.Released_Year);
    var msrp = Number(r.MSRP_USD);
    if (!isFinite(year) || !isFinite(msrp)) return;
    var cpiY = cpi[String(year)] !== undefined ? cpi[String(year)] : cpi[year];
    if (!cpiY) return;
    var real = msrp * (targetCpi / cpiY);
    if (!byYear[year]) byYear[year] = [];
    byYear[year].push(real);
  });
  function med(arr) {
    var a = arr.slice().sort(function (x, y) {
      return x - y;
    });
    var m = Math.floor(a.length / 2);
    return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
  }
  var stats = Object.keys(byYear).map(function (y) {
    return { year: Number(y), median_real: med(byYear[y]), count: byYear[y].length };
  });
  var exp = stats.reduce(function (a, b) {
    return !a || b.median_real > a.median_real ? b : a;
  }, null);
  var aff = stats.reduce(function (a, b) {
    return !a || b.median_real < a.median_real ? b : a;
  }, null);
  return { exp: exp, aff: aff, stats: stats };
}

function main() {
  var failures = 0;
  var results = [];

  try {
    assert(fs.existsSync(LOGIC_PATH), "logic file missing: " + LOGIC_PATH);
    assert(fs.existsSync(JSON_PATH), "json export missing — run export_web_data.py: " + JSON_PATH);
    assert(fs.existsSync(CSV_PATH), "csv missing: " + CSV_PATH);

    var GpuLogic = require(LOGIC_PATH);
    var dataset = JSON.parse(fs.readFileSync(JSON_PATH, "utf8"));

    assert(dataset.gpus && dataset.gpus.length > 0, "gpus array empty");
    assert(dataset.cpi, "cpi map missing");
    assert(dataset.meta && dataset.meta.target_cpi, "meta.target_cpi missing");

    // --- Inflation unit ---
    var sampleYear = dataset.gpus[0].year;
    var sampleMsrp = dataset.gpus[0].msrp;
    var cpiY = dataset.cpi[String(sampleYear)];
    var expectedInflate = sampleMsrp * (dataset.meta.target_cpi / cpiY);
    var gotInflate = GpuLogic.inflateToTarget(sampleMsrp, sampleYear, dataset.cpi, dataset.meta.target_cpi);
    assert(Math.abs(gotInflate - expectedInflate) < 1e-9, "inflate mismatch " + gotInflate + " vs " + expectedInflate);
    results.push("PASS inflateToTarget against CPI formula");

    // --- Year KPIs vs independent CSV recompute ---
    var csvRows = parseCsv(fs.readFileSync(CSV_PATH, "utf8"));
    assert(csvRows.length === dataset.gpus.length, "csv/json row count mismatch " + csvRows.length + " vs " + dataset.gpus.length);

    var independent = recomputeFromCsv(csvRows, dataset.cpi, dataset.meta.target_cpi);
    var insights = GpuLogic.buildInsights(dataset);

    assert(insights.mostExpensive, "mostExpensive missing");
    assert(insights.mostAffordable, "mostAffordable missing");

    assert(
      insights.mostExpensive.year === independent.exp.year,
      "most expensive year " + insights.mostExpensive.year + " != independent " + independent.exp.year
    );
    assert(
      Math.abs(insights.mostExpensive.median_real - independent.exp.median_real) < 0.02,
      "most expensive median_real mismatch"
    );
    assert(
      insights.mostAffordable.year === independent.aff.year,
      "most affordable year " + insights.mostAffordable.year + " != independent " + independent.aff.year
    );
    assert(
      Math.abs(insights.mostAffordable.median_real - independent.aff.median_real) < 0.02,
      "most affordable median_real mismatch"
    );
    results.push(
      "PASS year KPIs match CSV recompute: expensive=" +
        insights.mostExpensive.year +
        " affordable=" +
        insights.mostAffordable.year
    );

    // Ensure tests did NOT hardcode years — independent recompute drove the expected values
    results.push(
      "PASS independent recompute (not hardcoded): exp.median=" +
        independent.exp.median_real.toFixed(2) +
        " aff.median=" +
        independent.aff.median_real.toFixed(2)
    );

    // --- Filter changes set ---
    var filtered = GpuLogic.filterGpus(insights.rows, { yearMin: 2018, yearMax: 2025, manufacturer: "NVIDIA" });
    assert(filtered.length > 0, "filter empty unexpectedly");
    assert(
      filtered.every(function (r) {
        return r.manufacturer === "NVIDIA" && r.year >= 2018 && r.year <= 2025;
      }),
      "filter predicate failed"
    );
    var allCount = insights.rows.length;
    assert(filtered.length < allCount, "filter should shrink dataset");
    results.push("PASS filterGpus shrinks and predicates hold (" + filtered.length + "/" + allCount + ")");

    // --- Q&A grounded answers ---
    var q1 = GpuLogic.answerQuestion("Which year was the most expensive?", insights, insights.rows);
    assert(q1.answer && q1.answer.length > 20, "Q&A expensive answer empty");
    assert(String(q1.answer).indexOf(String(insights.mostExpensive.year)) >= 0, "Q&A must cite expensive year from data");

    var q2 = GpuLogic.answerQuestion("Which year was most affordable?", insights, insights.rows);
    assert(q2.answer && q2.answer.length > 20, "Q&A affordable answer empty");
    assert(String(q2.answer).indexOf(String(insights.mostAffordable.year)) >= 0, "Q&A must cite affordable year");

    var q3 = GpuLogic.answerQuestion("How does inflation adjustment work?", insights, insights.rows);
    assert(q3.answer && /cpi|real|inflation/i.test(q3.answer), "inflation Q&A not grounded");

    results.push("PASS answerQuestion returns grounded non-empty answers");

    // --- yearLevelStats length ---
    assert(insights.yearStats.length >= 10, "expected multi-year stats");
    results.push("PASS yearLevelStats has " + insights.yearStats.length + " years");

    console.log("=== test_gpu_logic.js ===");
    results.forEach(function (line) {
      console.log(line);
    });
    console.log("ALL TESTS PASSED (" + results.length + " checks)");
    console.log(
      "Summary: rows=" +
        dataset.gpus.length +
        " expensiveYear=" +
        insights.mostExpensive.year +
        " affordableYear=" +
        insights.mostAffordable.year
    );
    process.exit(0);
  } catch (e) {
    failures += 1;
    console.error("=== test_gpu_logic.js FAILED ===");
    console.error(e && e.stack ? e.stack : e);
    process.exit(1);
  }
}

main();
