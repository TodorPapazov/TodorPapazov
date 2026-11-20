(function () {
  var data = window.EXPLORER;
  if (!data) return;

  var svg = document.getElementById("map");
  var measureSelect = document.getElementById("measure");
  var finder = document.getElementById("finder");
  var legend = document.getElementById("legend");
  var panelEmpty = document.getElementById("panel-empty");
  var panelBody = document.getElementById("panel-body");
  var names = document.getElementById("county-names");
  var selected = null;
  var byFips = {};
  var shapeBox = {};

  data.counties.forEach(function (county) {
    byFips[county.fips] = county;
    var option = document.createElement("option");
    option.value = county.name;
    names.appendChild(option);
  });
  data.shapes.forEach(function (shape) {
    shapeBox[shape.fips] = shape.box;
  });

  data.measures.forEach(function (measure) {
    if (data.mapKeys.indexOf(measure.key) === -1) return;
    var option = document.createElement("option");
    option.value = measure.key;
    option.textContent = measure.label;
    measureSelect.appendChild(option);
  });

  svg.setAttribute("viewBox", "0 0 " + data.width + " " + data.height);
  var paths = document.createElementNS("http://www.w3.org/2000/svg", "g");
  data.shapes.forEach(function (shape) {
    var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", shape.rings.map(ringPath).join(" "));
    path.setAttribute("data-fips", shape.fips);
    path.setAttribute("data-study", shape.study ? "1" : "0");
    path.setAttribute("class", shape.study ? "county" : "other");
    paths.appendChild(path);
  });
  svg.appendChild(paths);

  svg.addEventListener("click", function (event) {
    var node = event.target;
    if (!node.getAttribute) return;
    if (node.getAttribute("data-study") !== "1") return;
    selectCounty(node.getAttribute("data-fips"));
  });
  measureSelect.addEventListener("change", paint);
  finder.addEventListener("input", jump);
  finder.addEventListener("change", jump);
  document.getElementById("zoom-us").addEventListener("click", function () {
    setView([0, 0, data.width, data.height]);
  });
  document.getElementById("zoom-closer").addEventListener("click", function () {
    if (selected && shapeBox[selected]) setView(padded(shapeBox[selected], 0.45));
  });
  document.getElementById("zoom-in").addEventListener("click", function () { scaleView(0.7); });
  document.getElementById("zoom-out").addEventListener("click", function () { scaleView(1.3); });
  paint();

  function jump() {
    var query = finder.value.trim().toLowerCase();
    if (!query) return;
    var hits = data.counties.filter(function (county) {
      return county.name.toLowerCase().indexOf(query) !== -1;
    });
    if (hits.length === 1) selectCounty(hits[0].fips);
  }

  function selectCounty(fips) {
    selected = fips;
    paint();
    var county = byFips[fips];
    if (!county) return;
    showPanel(county);
    if (data.states[county.state]) setView(padded(data.states[county.state], 0.18));
  }

  function paint() {
    var key = measureSelect.value;
    var measure = measureByKey(key);
    var numbers = [];
    data.counties.forEach(function (county) {
      var value = county.values[key];
      if (value !== null && value !== undefined) numbers.push(value);
    });
    var min = numbers.length ? Math.min.apply(null, numbers) : 0;
    var max = numbers.length ? Math.max.apply(null, numbers) : 1;
    var nodes = svg.querySelectorAll("path");
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      var fips = node.getAttribute("data-fips");
      var county = byFips[fips];
      var value = county ? county.values[key] : null;
      if (node.getAttribute("data-study") !== "1" || value === null || value === undefined) {
        node.setAttribute("fill", "#e4ddd2");
      } else {
        node.setAttribute("fill", shade((value - min) / (max - min || 1)));
      }
      node.setAttribute("stroke", fips === selected ? "#1c2430" : "#fffdf8");
      node.setAttribute("stroke-width", fips === selected ? "2.2" : "0.35");
    }
    if (measure && numbers.length) {
      legend.textContent = measure.label + ", low " + format(min, measure.digits) + " to high " + format(max, measure.digits) + ". Gray counties are outside the 50,000-resident study or have no published value.";
    }
  }

  function showPanel(county) {
    panelEmpty.hidden = true;
    panelBody.hidden = false;
    var key = measureSelect.value;
    var measure = measureByKey(key);
    var lines = [];
    lines.push("<h2>" + esc(county.name) + "</h2>");
    lines.push("<p>" + format(county.population, 0) + " residents. Size band " + esc(county.band) + ".</p>");
    lines.push("<p><strong>Who lives there</strong> " + format(county.values.racial_ethnic, 4) + ". <strong>Foreign-born</strong> " + format(county.values.foreign_born_pct, 2) + "%.</p>");
    lines.push("<p>" + bandSentence(county, measure) + "</p>");
    lines.push("<h3>Latest published figures</h3><ul>");
    data.measures.forEach(function (item) {
      if (item.key === "racial_ethnic" || item.key === "foreign_born_pct") return;
      var value = county.values[item.key];
      lines.push("<li>" + esc(item.label) + ": " + (value === null || value === undefined ? "blank" : format(value, item.digits)) + "</li>");
    });
    lines.push("</ul>");
    lines.push(chart("Typical home value", county.series.home_value, "Year-end Zillow index."));
    lines.push(chart("Who lives there", county.series.racial_ethnic, "Each point is a five-year Census period. Neighboring points share four years."));
    lines.push(chart("Foreign-born percent", county.series.foreign_born_pct, "Each point is a five-year Census period. Neighboring points share four years."));
    lines.push(chart("Unemployment rate", county.series.unemployment_rate, "Each point is a five-year Census period. Neighboring points share four years."));
    panelBody.innerHTML = lines.join("");
  }

  function bandSentence(county, measure) {
    if (!measure) return "";
    var value = county.values[measure.key];
    if (value === null || value === undefined) {
      return esc(measure.label) + " is blank for this county.";
    }
    var share = county.bandBelow[measure.key];
    var text = "In the " + county.band + " band, " + format(share, 1) + "% of counties have a lower " + measure.label.toLowerCase() + ".";
    if (measure.higher === true) {
      text += " The hypothesis expected a higher value where diversity is higher.";
    } else if (measure.higher === false) {
      text += " The hypothesis expected a lower value where diversity is higher.";
    }
    if (measure.higher === true || measure.higher === false) {
      text += " This does not show that diversity caused the number.";
    }
    return esc(text);
  }

  function chart(title, series, note) {
    if (!series || !series.length) {
      return "<figure><figcaption>" + esc(title) + "</figcaption><p>No published points.</p></figure>";
    }
    var values = series.map(function (pair) { return pair[1]; });
    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    if (min === max) { min -= 1; max += 1; }
    var width = 280;
    var height = 88;
    var pad = 8;
    var points = series.map(function (pair, index) {
      var x = pad + (series.length === 1 ? (width - 2 * pad) / 2 : index * (width - 2 * pad) / (series.length - 1));
      var y = pad + (1 - (pair[1] - min) / (max - min)) * (height - 2 * pad);
      return x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    var labels = series.map(function (pair) { return pair[0]; }).join("  ");
    return "<figure><figcaption>" + esc(title) + "</figcaption><svg class=\"chart\" viewBox=\"0 0 " + width + " " + height + "\"><polyline points=\"" + points + "\"></polyline></svg><p class=\"axis\">" + esc(labels) + "</p><p class=\"note\">" + esc(note) + "</p></figure>";
  }

  function measureByKey(key) {
    for (var i = 0; i < data.measures.length; i++) {
      if (data.measures[i].key === key) return data.measures[i];
    }
    return null;
  }

  function ringPath(ring) {
    var parts = [];
    for (var i = 0; i < ring.length; i++) {
      parts.push((i === 0 ? "M" : "L") + ring[i][0] + " " + ring[i][1]);
    }
    return parts.join("") + "Z";
  }

  function shade(t) {
    t = Math.max(0, Math.min(1, t));
    var start = [232, 220, 196];
    var end = [15, 92, 92];
    var channels = start.map(function (channel, index) {
      return Math.round(channel + (end[index] - channel) * t);
    });
    return "rgb(" + channels.join(",") + ")";
  }

  function format(value, digits) {
    if (value === null || value === undefined || value === "") return "";
    var number = Number(value);
    if (isNaN(number)) return "";
    return number.toLocaleString("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    });
  }

  function padded(box, portion) {
    var width = Math.max(box[2] - box[0], 8);
    var height = Math.max(box[3] - box[1], 8);
    var padX = width * portion;
    var padY = height * portion;
    return [box[0] - padX, box[1] - padY, box[2] + padX, box[3] + padY];
  }

  function setView(box) {
    var width = Math.max(box[2] - box[0], 8);
    var height = Math.max(box[3] - box[1], 8);
    svg.setAttribute("viewBox", box[0] + " " + box[1] + " " + width + " " + height);
  }

  function scaleView(factor) {
    var parts = svg.getAttribute("viewBox").split(/\s+/).map(Number);
    var cx = parts[0] + parts[2] / 2;
    var cy = parts[1] + parts[3] / 2;
    var width = parts[2] * factor;
    var height = parts[3] * factor;
    setView([cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2]);
  }

  function esc(value) {
    return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
})();
