/**
 * GPU 26 Years — HUD presentation controller
 * Classic script (file:// safe). Depends on: GPU_DATASET, GpuLogic, Chart (optional).
 */
(function () {
  "use strict";

  var state = {
    insights: null,
    filtered: [],
    chartPrice: null,
    chartMfr: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function money(n) {
    if (n === null || n === undefined || !isFinite(n)) return "—";
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

  function renderMarkdownLite(text) {
    // **bold** only
    var esc = String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return esc.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function getFilterOpts() {
    var ymin = parseInt($("yearMin").value, 10);
    var ymax = parseInt($("yearMax").value, 10);
    if (ymin > ymax) {
      var t = ymin;
      ymin = ymax;
      ymax = t;
    }
    return {
      yearMin: ymin,
      yearMax: ymax,
      manufacturer: $("manufacturer").value || "ALL",
    };
  }

  function applyFilters() {
    if (!state.insights) return;
    var opts = getFilterOpts();
    state.filtered = GpuLogic.filterGpus(state.insights.rows, opts);

    $("yearMinLabel").textContent = String(opts.yearMin);
    $("yearMaxLabel").textContent = String(opts.yearMax);
    $("yearMin").setAttribute("aria-valuenow", String(opts.yearMin));
    $("yearMax").setAttribute("aria-valuenow", String(opts.yearMax));
    $("liveCount").textContent = String(state.filtered.length);
    $("liveCount").setAttribute("data-count", String(state.filtered.length));

    var sum = GpuLogic.summarize(state.filtered);
    $("kpiFilteredMedian").textContent = money(sum.median_real);
    $("kpiFilteredCount").textContent = String(sum.count);
    $("kpiFilteredPerGb").textContent = money(sum.median_real_per_gb) + "/GB";

    updateCharts();
    updateTable();
  }

  function updateHeroKpis() {
    var ins = state.insights;
    var exp = ins.mostExpensive;
    var aff = ins.mostAffordable;
    $("kpiExpYear").textContent = exp ? String(exp.year) : "—";
    $("kpiExpPrice").textContent = exp ? money(exp.median_real) + " real" : "";
    $("kpiAffYear").textContent = aff ? String(aff.year) : "—";
    $("kpiAffPrice").textContent = aff ? money(aff.median_real) + " real" : "";
    $("kpiOverall").textContent = money(ins.overall.median_real);
    $("kpiRows").textContent = String(ins.rows.length);
    $("calloutExp").textContent =
      exp
        ? "Most expensive year (median real " + ins.targetYear + " $): " + exp.year + " · " + money(exp.median_real)
        : "";
    $("calloutAff").textContent =
      aff
        ? "Most affordable year (median real " + ins.targetYear + " $): " + aff.year + " · " + money(aff.median_real)
        : "";
  }

  function chartDefaults() {
    if (typeof Chart === "undefined") return;
    Chart.defaults.color = "#94a3b8";
    Chart.defaults.borderColor = "rgba(34,211,238,0.12)";
    Chart.defaults.font.family = "'JetBrains Mono', ui-monospace, monospace";
    Chart.defaults.font.size = 11;
  }

  function yearStatsForFiltered() {
    return GpuLogic.yearLevelStats(state.filtered);
  }

  function updateCharts() {
    var ys = yearStatsForFiltered();
    var labels = ys.map(function (s) {
      return String(s.year);
    });
    var real = ys.map(function (s) {
      return s.median_real;
    });
    var nominal = ys.map(function (s) {
      return s.median_nominal;
    });

    var expY = state.insights.mostExpensive && state.insights.mostExpensive.year;
    var affY = state.insights.mostAffordable && state.insights.mostAffordable.year;
    var colors = labels.map(function (y) {
      var n = Number(y);
      if (n === expY) return "rgba(244, 63, 94, 0.85)";
      if (n === affY) return "rgba(52, 211, 153, 0.85)";
      return "rgba(34, 211, 238, 0.65)";
    });

    if (typeof Chart === "undefined") {
      $("chartFallback").style.display = "block";
      return;
    }
    $("chartFallback").style.display = "none";

    if (state.chartPrice) {
      state.chartPrice.data.labels = labels;
      state.chartPrice.data.datasets[0].data = real;
      state.chartPrice.data.datasets[0].backgroundColor = colors;
      state.chartPrice.data.datasets[1].data = nominal;
      state.chartPrice.update();
    } else {
      var ctx = $("chartPrice").getContext("2d");
      state.chartPrice = new Chart(ctx, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Median real (2025 $)",
              data: real,
              backgroundColor: colors,
              borderWidth: 0,
              borderRadius: 3,
            },
            {
              type: "line",
              label: "Median nominal $",
              data: nominal,
              borderColor: "rgba(251, 191, 36, 0.9)",
              backgroundColor: "transparent",
              tension: 0.25,
              pointRadius: 2,
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "bottom" },
            tooltip: {
              callbacks: {
                label: function (c) {
                  var v = c.parsed.y;
                  return c.dataset.label + ": " + money(v);
                },
              },
            },
          },
          scales: {
            x: { grid: { display: false } },
            y: {
              title: { display: true, text: "USD" },
              beginAtZero: true,
            },
          },
        },
      });
    }

    // Manufacturer breakdown for filtered set
    var mfrMap = {};
    state.filtered.forEach(function (r) {
      var m = r.manufacturer || "Other";
      if (!mfrMap[m]) mfrMap[m] = [];
      if (r.real_msrp != null) mfrMap[m].push(r.real_msrp);
    });
    var mLabels = Object.keys(mfrMap).sort();
    var mData = mLabels.map(function (m) {
      return GpuLogic.median(mfrMap[m]);
    });
    var mColors = mLabels.map(function (m) {
      if (m === "NVIDIA") return "rgba(34, 211, 238, 0.8)";
      if (m === "AMD") return "rgba(244, 63, 94, 0.75)";
      return "rgba(167, 139, 250, 0.75)";
    });

    if (state.chartMfr) {
      state.chartMfr.data.labels = mLabels;
      state.chartMfr.data.datasets[0].data = mData;
      state.chartMfr.data.datasets[0].backgroundColor = mColors;
      state.chartMfr.update();
    } else {
      var ctx2 = $("chartMfr").getContext("2d");
      state.chartMfr = new Chart(ctx2, {
        type: "doughnut",
        data: {
          labels: mLabels,
          datasets: [
            {
              label: "Median real MSRP",
              data: mData,
              backgroundColor: mColors,
              borderWidth: 1,
              borderColor: "#0b1220",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "bottom" },
            tooltip: {
              callbacks: {
                label: function (c) {
                  return c.label + ": " + money(c.parsed);
                },
              },
            },
          },
        },
      });
    }
  }

  function updateTable() {
    var tbody = $("tableBody");
    var rows = state.filtered.slice().sort(function (a, b) {
      if (b.year !== a.year) return b.year - a.year;
      return (b.msrp || 0) - (a.msrp || 0);
    });
    var max = 80;
    var html = "";
    for (var i = 0; i < Math.min(rows.length, max); i++) {
      var r = rows[i];
      html +=
        "<tr>" +
        "<td>" +
        r.year +
        "</td>" +
        "<td>" +
        escapeHtml(r.manufacturer) +
        "</td>" +
        "<td>" +
        escapeHtml(r.name) +
        "</td>" +
        '<td class="num">' +
        money(r.msrp) +
        "</td>" +
        '<td class="num">' +
        money(r.real_msrp) +
        "</td>" +
        '<td class="num">' +
        (r.memory_gb != null ? r.memory_gb : "—") +
        "</td>" +
        '<td class="num">' +
        money(r.real_price_per_gb) +
        "</td>" +
        "</tr>";
    }
    if (!rows.length) {
      html = '<tr><td colspan="7" class="muted">No GPUs match the current filters.</td></tr>';
    } else if (rows.length > max) {
      html +=
        '<tr><td colspan="7" class="muted">Showing ' +
        max +
        " of " +
        rows.length +
        " — narrow filters to see more focus.</td></tr>";
    }
    tbody.innerHTML = html;
    tbody.setAttribute("data-row-count", String(rows.length));
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function runQa(question) {
    var q = question || ($("qaInput") && $("qaInput").value) || "";
    var box = $("qaAnswer");
    if (!state.insights) {
      box.innerHTML = '<span class="tag">STATUS · WAIT</span>Dataset still loading.';
      return;
    }
    var res = GpuLogic.answerQuestion(q, state.insights, state.filtered);
    var tag = res.matched ? "ANSWER · GROUNDED" : "HINT · TRY ANOTHER ANGLE";
    box.innerHTML = '<span class="tag">' + tag + "</span>" + renderMarkdownLite(res.answer);
    box.setAttribute("data-has-answer", res.answer && res.answer.length > 0 ? "1" : "0");
  }

  function setNavOpen(open) {
    var nav = $("primaryNav");
    var btn = $("navToggle");
    if (!nav || !btn) return;
    if (open) {
      nav.classList.add("is-open");
      btn.setAttribute("aria-expanded", "true");
      btn.setAttribute("aria-label", "Close menu");
    } else {
      nav.classList.remove("is-open");
      btn.setAttribute("aria-expanded", "false");
      btn.setAttribute("aria-label", "Open menu");
    }
  }

  function wireMobileNav() {
    var btn = $("navToggle");
    var nav = $("primaryNav");
    if (!btn || !nav) return;
    btn.addEventListener("click", function () {
      setNavOpen(!nav.classList.contains("is-open"));
    });
    var links = nav.querySelectorAll("a");
    for (var i = 0; i < links.length; i++) {
      links[i].addEventListener("click", function () {
        setNavOpen(false);
      });
    }
    window.addEventListener("resize", function () {
      if (window.innerWidth >= 768) setNavOpen(false);
    });
  }

  function wireEvents() {
    wireMobileNav();
    ["yearMin", "yearMax", "manufacturer"].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      el.addEventListener("input", applyFilters);
      el.addEventListener("change", applyFilters);
    });
    $("btnReset").addEventListener("click", function () {
      $("yearMin").value = $("yearMin").min;
      $("yearMax").value = $("yearMax").max;
      $("manufacturer").value = "ALL";
      applyFilters();
    });
    $("btnAsk").addEventListener("click", function () {
      runQa();
    });
    $("qaInput").addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        runQa();
      }
    });
    var chips = document.querySelectorAll("[data-qa]");
    for (var i = 0; i < chips.length; i++) {
      chips[i].addEventListener("click", function (ev) {
        var q = ev.currentTarget.getAttribute("data-qa");
        $("qaInput").value = q;
        runQa(q);
      });
    }
  }

  function initYearControls() {
    var years = state.insights.rows
      .map(function (r) {
        return r.year;
      })
      .filter(function (y) {
        return y != null;
      });
    var ymin = Math.min.apply(null, years);
    var ymax = Math.max.apply(null, years);
    $("yearMin").min = ymin;
    $("yearMin").max = ymax;
    $("yearMin").value = ymin;
    $("yearMax").min = ymin;
    $("yearMax").max = ymax;
    $("yearMax").value = ymax;
    $("yearMinLabel").textContent = String(ymin);
    $("yearMaxLabel").textContent = String(ymax);
  }

  function init() {
    var status = $("sysStatus");
    if (typeof GPU_DATASET === "undefined" || !GPU_DATASET) {
      if (status) status.textContent = "DATA · MISSING";
      $("qaAnswer").innerHTML =
        '<span class="tag">ERROR</span>GPU_DATASET not loaded. Ensure js/gpu-dataset.js is present.';
      return;
    }
    if (typeof GpuLogic === "undefined") {
      if (status) status.textContent = "LOGIC · MISSING";
      return;
    }

    chartDefaults();
    state.insights = GpuLogic.buildInsights(GPU_DATASET);
    if (status) {
      status.innerHTML = '<span class="status-dot"></span> SYS · ONLINE · ' + state.insights.rows.length + " GPUs";
    }

    initYearControls();
    updateHeroKpis();
    wireEvents();
    applyFilters();
    // Seed Q&A with a default grounded answer
    runQa("Which year was the most expensive?");
  }

  // Expose for tests / console
  window.GpuApp = {
    applyFilters: applyFilters,
    runQa: runQa,
    getState: function () {
      return state;
    },
    getFilterOpts: getFilterOpts,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
