/**
 * Pure GPU affordability helpers — shared by the HUD site and Node unit tests.
 * Classic script / CommonJS dual export (file:// safe, no ES modules).
 */
(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.GpuLogic = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function toNumber(v) {
    if (v === null || v === undefined || v === "") return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }

  function inflateToTarget(price, year, cpiMap, targetCpi) {
    var p = toNumber(price);
    var y = toNumber(year);
    if (p === null || y === null) return null;
    var yearKey = String(Math.trunc(y));
    var cpi = toNumber(cpiMap[yearKey] !== undefined ? cpiMap[yearKey] : cpiMap[Math.trunc(y)]);
    var target = toNumber(targetCpi);
    if (cpi === null || cpi === 0 || target === null) return null;
    return p * (target / cpi);
  }

  function annotateRows(gpus, cpiMap, targetCpi) {
    return (gpus || []).map(function (g) {
      var msrp = toNumber(g.msrp);
      var year = toNumber(g.year);
      var real = inflateToTarget(msrp, year, cpiMap, targetCpi);
      var mem = toNumber(g.memory_gb);
      var realPerGb = real !== null && mem !== null && mem > 0 ? real / mem : null;
      var tflops = toNumber(g.tflops);
      var tflopsPerK = real !== null && tflops !== null && real > 0 ? tflops / (real / 1000) : null;
      return Object.assign({}, g, {
        msrp: msrp,
        year: year !== null ? Math.trunc(year) : null,
        real_msrp: real,
        real_price_per_gb: realPerGb,
        tflops_per_1000_real: tflopsPerK,
      });
    });
  }

  function median(nums) {
    var arr = nums.filter(function (n) {
      return n !== null && n !== undefined && isFinite(n);
    }).slice().sort(function (a, b) {
      return a - b;
    });
    if (!arr.length) return null;
    var mid = Math.floor(arr.length / 2);
    if (arr.length % 2 === 0) return (arr[mid - 1] + arr[mid]) / 2;
    return arr[mid];
  }

  function mean(nums) {
    var arr = nums.filter(function (n) {
      return n !== null && n !== undefined && isFinite(n);
    });
    if (!arr.length) return null;
    var s = 0;
    for (var i = 0; i < arr.length; i++) s += arr[i];
    return s / arr.length;
  }

  function yearLevelStats(rows) {
    var byYear = {};
    (rows || []).forEach(function (r) {
      if (r.year === null || r.year === undefined) return;
      var y = r.year;
      if (!byYear[y]) byYear[y] = { year: y, nominals: [], reals: [], count: 0 };
      byYear[y].count += 1;
      if (r.msrp !== null && isFinite(r.msrp)) byYear[y].nominals.push(r.msrp);
      if (r.real_msrp !== null && isFinite(r.real_msrp)) byYear[y].reals.push(r.real_msrp);
    });

    return Object.keys(byYear)
      .map(function (k) {
        return byYear[k];
      })
      .sort(function (a, b) {
        return a.year - b.year;
      })
      .map(function (b) {
        return {
          year: b.year,
          count: b.count,
          median_nominal: median(b.nominals),
          mean_nominal: mean(b.nominals),
          median_real: median(b.reals),
          mean_real: mean(b.reals),
          min_real: b.reals.length ? Math.min.apply(null, b.reals) : null,
          max_real: b.reals.length ? Math.max.apply(null, b.reals) : null,
        };
      });
  }

  function mostExpensiveYear(yearStats) {
    var best = null;
    (yearStats || []).forEach(function (s) {
      if (s.median_real === null || s.median_real === undefined) return;
      if (!best || s.median_real > best.median_real) best = s;
    });
    return best;
  }

  function mostAffordableYear(yearStats) {
    var best = null;
    (yearStats || []).forEach(function (s) {
      if (s.median_real === null || s.median_real === undefined) return;
      if (!best || s.median_real < best.median_real) best = s;
    });
    return best;
  }

  function filterGpus(rows, opts) {
    opts = opts || {};
    var yearMin = opts.yearMin !== undefined && opts.yearMin !== null ? Number(opts.yearMin) : null;
    var yearMax = opts.yearMax !== undefined && opts.yearMax !== null ? Number(opts.yearMax) : null;
    var mfr = opts.manufacturer || "ALL";
    return (rows || []).filter(function (r) {
      if (yearMin !== null && isFinite(yearMin) && r.year < yearMin) return false;
      if (yearMax !== null && isFinite(yearMax) && r.year > yearMax) return false;
      if (mfr && mfr !== "ALL" && r.manufacturer !== mfr) return false;
      return true;
    });
  }

  function summarize(rows) {
    var reals = (rows || []).map(function (r) {
      return r.real_msrp;
    });
    var nominals = (rows || []).map(function (r) {
      return r.msrp;
    });
    var perGb = (rows || []).map(function (r) {
      return r.real_price_per_gb;
    });
    var mfrs = {};
    (rows || []).forEach(function (r) {
      var m = r.manufacturer || "Unknown";
      mfrs[m] = (mfrs[m] || 0) + 1;
    });
    return {
      count: (rows || []).length,
      median_real: median(reals),
      mean_real: mean(reals),
      median_nominal: median(nominals),
      median_real_per_gb: median(perGb),
      manufacturers: mfrs,
    };
  }

  function buildInsights(dataset) {
    var cpi = dataset.cpi || {};
    var targetCpi = dataset.meta && dataset.meta.target_cpi != null ? dataset.meta.target_cpi : cpi["2025"];
    var rows = annotateRows(dataset.gpus || [], cpi, targetCpi);
    var ys = yearLevelStats(rows);
    var exp = mostExpensiveYear(ys);
    var aff = mostAffordableYear(ys);
    var all = summarize(rows);

    var vramByYear = {};
    rows.forEach(function (r) {
      if (r.year === null || r.real_price_per_gb === null) return;
      if (!vramByYear[r.year]) vramByYear[r.year] = [];
      vramByYear[r.year].push(r.real_price_per_gb);
    });
    var bestVramYear = null;
    Object.keys(vramByYear).forEach(function (y) {
      var med = median(vramByYear[y]);
      if (med === null) return;
      if (!bestVramYear || med < bestVramYear.median) {
        bestVramYear = { year: Number(y), median: med };
      }
    });

    var nv = rows.filter(function (r) {
      return r.manufacturer === "NVIDIA";
    });
    var amd = rows.filter(function (r) {
      return r.manufacturer === "AMD";
    });

    return {
      rows: rows,
      yearStats: ys,
      mostExpensive: exp,
      mostAffordable: aff,
      overall: all,
      bestVramYear: bestVramYear,
      nvidiaMedianReal: median(
        nv.map(function (r) {
          return r.real_msrp;
        })
      ),
      amdMedianReal: median(
        amd.map(function (r) {
          return r.real_msrp;
        })
      ),
      targetCpi: targetCpi,
      targetYear: (dataset.meta && dataset.meta.target_year) || 2025,
    };
  }

  /**
   * Data-grounded Q&A over precomputed insights + optional filtered rows.
   * No live LLM — keyword/intent match with answers from the dataset.
   */
  function answerQuestion(question, insights, filteredRows) {
    var q = String(question || "").toLowerCase().trim();
    if (!q) {
      return {
        matched: false,
        answer:
          "Ask a question about affordability, inflation-adjusted prices, manufacturers, or VRAM value. Try: “Which year was most expensive?”",
      };
    }

    var exp = insights.mostExpensive;
    var aff = insights.mostAffordable;
    var overall = insights.overall;
    var rows = filteredRows || insights.rows || [];
    var fsum = summarize(rows);

    function money(n) {
      if (n === null || n === undefined || !isFinite(n)) return "n/a";
      // Avoid toLocaleString (not available in some JS engines used for tests)
      var rounded = Math.round(n);
      var s = String(Math.abs(rounded));
      var out = "";
      while (s.length > 3) {
        out = "," + s.slice(-3) + out;
        s = s.slice(0, -3);
      }
      out = s + out;
      return (rounded < 0 ? "-$" : "$") + out;
    }

    // Most expensive
    if (
      /(most\s+expensive|highest\s+(real\s+)?price|priciest|costliest)/.test(q) ||
      (q.indexOf("expensive") >= 0 && (q.indexOf("year") >= 0 || q.indexOf("which") >= 0))
    ) {
      if (!exp) return { matched: true, answer: "Not enough data to rank expensive years." };
      return {
        matched: true,
        answer:
          "Most expensive year by median inflation-adjusted (real " +
          insights.targetYear +
          " $) launch MSRP: **" +
          exp.year +
          "** at " +
          money(exp.median_real) +
          " (nominal median at the time: " +
          money(exp.median_nominal) +
          "). Based on " +
          exp.count +
          " major consumer desktop launches that year.",
      };
    }

    // Most affordable / cheapest
    if (
      /(most\s+affordable|cheapest|lowest\s+(real\s+)?price|best\s+value\s+year)/.test(q) ||
      (q.indexOf("affordable") >= 0 && (q.indexOf("year") >= 0 || q.indexOf("which") >= 0))
    ) {
      if (!aff) return { matched: true, answer: "Not enough data to rank affordable years." };
      return {
        matched: true,
        answer:
          "Most affordable year by median real launch MSRP (" +
          insights.targetYear +
          " $): **" +
          aff.year +
          "** at " +
          money(aff.median_real) +
          " (nominal median: " +
          money(aff.median_nominal) +
          "). " +
          aff.count +
          " major launches in the curated set.",
      };
    }

    // Inflation / real vs nominal
    if (/(inflation|real\s+price|nominal|cpi|adjust)/.test(q)) {
      return {
        matched: true,
        answer:
          "Prices are adjusted with US CPI-U annual averages to " +
          insights.targetYear +
          " dollars (target CPI " +
          insights.targetCpi +
          "). Formula: real = MSRP × (CPI_" +
          insights.targetYear +
          " / CPI_year). Across the full set, overall median real MSRP is " +
          money(overall.median_real) +
          " vs median nominal " +
          money(overall.median_nominal) +
          ". Real prices reveal which eras were truly expensive after inflation.",
      };
    }

    // Manufacturer
    if (/(nvidia|amd|intel|manufacturer|premium)/.test(q)) {
      var parts = [];
      if (insights.nvidiaMedianReal != null) parts.push("NVIDIA median real MSRP " + money(insights.nvidiaMedianReal));
      if (insights.amdMedianReal != null) parts.push("AMD median real MSRP " + money(insights.amdMedianReal));
      var premium = "";
      if (insights.nvidiaMedianReal != null && insights.amdMedianReal != null && insights.amdMedianReal > 0) {
        var pct = ((insights.nvidiaMedianReal - insights.amdMedianReal) / insights.amdMedianReal) * 100;
        premium =
          " NVIDIA sits about " +
          (pct >= 0 ? "+" : "") +
          pct.toFixed(1) +
          "% vs AMD on overall median real launch price (curated set, not identical SKUs).";
      }
      var filtMfr = fsum.manufacturers || {};
      var fkeys = Object.keys(filtMfr);
      var filterNote =
        fkeys.length ?
          " Current filter covers " +
          fsum.count +
          " cards (" +
          fkeys
            .map(function (k) {
              return k + ": " + filtMfr[k];
            })
            .join(", ") +
          ")."
        : "";
      return {
        matched: true,
        answer:
          (parts.length ? parts.join("; ") + "." : "Manufacturer medians unavailable.") +
          premium +
          filterNote,
      };
    }

    // VRAM / price per GB
    if (/(vram|per\s*gb|memory\s*price|\$\/gb|price\s+per\s+gb)/.test(q)) {
      var bv = insights.bestVramYear;
      return {
        matched: true,
        answer:
          "VRAM value uses real $ per GB (MSRP inflated to " +
          insights.targetYear +
          " $ ÷ Memory_GB). Overall median real $/GB: " +
          money(overall.median_real_per_gb) +
          "/GB." +
          (bv
            ? " Best (lowest) median real $/GB year in the set: **" + bv.year + "** at " + money(bv.median) + "/GB."
            : "") +
          " Filtered selection median real $/GB: " +
          money(fsum.median_real_per_gb) +
          "/GB.",
      };
    }

    // Count / how many
    if (/(how many|count|rows|dataset|sample)/.test(q)) {
      return {
        matched: true,
        answer:
          "The curated web dataset has " +
          (insights.rows ? insights.rows.length : 0) +
          " major consumer desktop discrete GPUs. Your current filters show " +
          fsum.count +
          " cards with median real MSRP " +
          money(fsum.median_real) +
          ".",
      };
    }

    // Flagship / max
    if (/(flagship|most expensive gpu|highest msrp|rtx 4090|ultra)/.test(q)) {
      var top = null;
      rows.forEach(function (r) {
        if (r.real_msrp == null) return;
        if (!top || r.real_msrp > top.real_msrp) top = r;
      });
      if (!top) return { matched: true, answer: "No GPU prices available in the current filter." };
      return {
        matched: true,
        answer:
          "Highest real launch price in the current view: **" +
          top.name +
          "** (" +
          top.year +
          ", " +
          top.manufacturer +
          ") at " +
          money(top.real_msrp) +
          " real (" +
          money(top.msrp) +
          " nominal).",
      };
    }

    // Default grounded summary
    return {
      matched: false,
      answer:
        "I can answer from this dataset about: most expensive/affordable years, inflation (real vs nominal), NVIDIA vs AMD, VRAM $/GB, flagship prices, and row counts. " +
        "Quick snapshot under your filters: " +
        fsum.count +
        " GPUs, median real MSRP " +
        money(fsum.median_real) +
        ". Try: “Which year was most affordable?”",
    };
  }

  return {
    inflateToTarget: inflateToTarget,
    annotateRows: annotateRows,
    median: median,
    mean: mean,
    yearLevelStats: yearLevelStats,
    mostExpensiveYear: mostExpensiveYear,
    mostAffordableYear: mostAffordableYear,
    filterGpus: filterGpus,
    summarize: summarize,
    buildInsights: buildInsights,
    answerQuestion: answerQuestion,
  };
});
