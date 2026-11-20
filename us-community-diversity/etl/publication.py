"""Assemble the map publication from scored counties and projected shapes."""

from __future__ import annotations

import json

from etl.geo_us import HEIGHT, WIDTH
from etl.rating import LINES_AGAINST, LINES_UP, band_share_below

MAP_KEYS = (
    "racial_ethnic",
    "foreign_born_pct",
    "unemployment_rate",
    "home_value",
    "home_value_change_5yr",
    "graduation_rate",
    "highway_per_resident",
    "entertainment_kinds",
)


def write_explorer(docs_dir, counties, shapes, hypotheses, history, home_series, gap, measures):
    payload = build_payload(counties, shapes, history, home_series, measures)
    (docs_dir / "data.js").write_text(
        "window.EXPLORER = " + json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + ";\n",
        encoding="utf-8",
        newline="\n",
    )
    (docs_dir / "index.html").write_text(
        render_shell(hypotheses, gap),
        encoding="utf-8",
        newline="\n",
    )


def build_payload(counties, shapes, history, home_series, measures):
    by_band = {}
    for row in counties:
        by_band.setdefault(row["band"], []).append(row)
    study = {row["fips"] for row in counties}
    state_boxes = {}
    shape_rows = []
    for shape in shapes:
        box = shape["box"]
        state = shape["state"]
        current = state_boxes.get(state)
        if current is None:
            state_boxes[state] = list(box)
        else:
            state_boxes[state] = [
                min(current[0], box[0]),
                min(current[1], box[1]),
                max(current[2], box[2]),
                max(current[3], box[3]),
            ]
        shape_rows.append(
            {
                "fips": shape["fips"],
                "state": state,
                "study": shape["fips"] in study,
                "rings": shape["rings"],
                "box": box,
            }
        )
    county_rows = []
    for row in sorted(counties, key=lambda item: item["fips"]):
        fips = row["fips"]
        band_rows = by_band[row["band"]]
        below = {}
        values = {}
        for key, _label, _higher, digits in measures:
            number = row.get(key)
            values[key] = number
            share = band_share_below([other.get(key) for other in band_rows], number)
            below[key] = None if share is None else round(share, 1)
        record_history = history.get(fips, {})
        county_rows.append(
            {
                "fips": fips,
                "name": row["county"],
                "state": fips[:2],
                "population": row["population"],
                "band": row["band"],
                "values": values,
                "bandBelow": below,
                "series": {
                    "home_value": home_series.get(fips, []),
                    "racial_ethnic": record_history.get("racial_ethnic", []),
                    "foreign_born_pct": record_history.get("foreign_born_pct", []),
                    "unemployment_rate": record_history.get("unemployment_rate", []),
                },
            }
        )
    return {
        "width": WIDTH,
        "height": HEIGHT,
        "mapKeys": list(MAP_KEYS),
        "measures": [
            {"key": key, "label": label, "higher": higher, "digits": digits}
            for key, label, higher, digits in measures
        ],
        "states": state_boxes,
        "shapes": shape_rows,
        "counties": county_rows,
    }


def render_shell(hypotheses, gap) -> str:
    items = []
    for key, label, _higher, _digits in _outcome_order(hypotheses):
        racial = hypotheses["racial_ethnic"]["outcomes"][key]
        foreign = hypotheses["foreign_born_pct"]["outcomes"][key]
        items.append(
            "<li>"
            f"<strong>{_esc(label)}.</strong> "
            f"Who lives there {_phrase(racial['reading'])} ({_coef(racial)}). "
            f"Foreign-born percent {_phrase(foreign['reading'])} ({_coef(foreign)})."
            "</li>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>US community diversity</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
<main>
  <h1>Do more diverse US counties also show the local conditions in this hypothesis?</h1>
  <p class="lede">Click a county to zoom in and read that community. The map colors one measure at a time. The panel places the county among counties of a similar size and shows how home values, the mix of who lives there, the foreign-born share, and unemployment have moved. These are published numbers side by side. They do not show that diversity caused an outcome, and they do not rank counties as better or worse places to live.</p>
  <p class="method">A community is a county in the 50 states or the District of Columbia with at least 50,000 residents in the 2019-2023 American Community Survey. Smaller counties stay on the map in gray. Who lives there is the effective number of racial and ethnic groups. Born outside the United States is the foreign-born percent. The two scores are never averaged. Comparisons use three size bands: 50-150k, 150-500k, and 500k or more. The widest gap between race and ethnicity group counts and the county total is {gap:.4f}. High school graduation is a ninth-grade cohort's four-year completion, not a test score. County highway spending is that government's own direct highway spending. A blank means the source did not publish a figure.</p>
  <div class="layout">
    <section class="stage">
      <div class="toolbar">
        <label>Color the map
          <select id="measure"></select>
        </label>
        <label>Find a county
          <input id="finder" type="search" placeholder="County name" list="county-names">
        </label>
        <datalist id="county-names"></datalist>
        <div class="zoom-buttons">
          <button type="button" id="zoom-us">United States</button>
          <button type="button" id="zoom-closer">Closer</button>
          <button type="button" id="zoom-in">Zoom in</button>
          <button type="button" id="zoom-out">Zoom out</button>
        </div>
      </div>
      <svg id="map" role="img" aria-label="Map of US counties"></svg>
      <p id="legend" class="legend"></p>
    </section>
    <aside id="panel">
      <h2>County</h2>
      <p id="panel-empty">Click a county on the map.</p>
      <div id="panel-body" hidden></div>
    </aside>
  </div>
  <h2>How the hypothesis reads inside population bands</h2>
  <ul class="findings">{''.join(items)}</ul>
  <p class="method">Home-value charts use the year-end Zillow index. December is the year-end month when that county has a December value. The latest year uses the newest month in the file. The Census charts are the 2017-2021, 2018-2022, and 2019-2023 five-year releases. Neighboring points share four years, so the line is a slow average, not a one-year shock. A missing point stays blank, including Connecticut counties whose codes changed. No crosswalk is filled in.</p>
</main>
<script src="data.js"></script>
<script src="app.js"></script>
</body>
</html>
"""


def _outcome_order(hypotheses):
    outcomes = hypotheses["racial_ethnic"]["outcomes"]
    return [(key, outcomes[key]["label"], outcomes[key]["higher_is_better"], 0) for key in outcomes]


def _phrase(reading: str) -> str:
    if reading == LINES_UP:
        return "lines up with the hypothesis"
    if reading == LINES_AGAINST:
        return "lines up against the hypothesis"
    return "shows no clear direction"


def _coef(item) -> str:
    coefficient = item["within_band"].get("coefficient")
    return "not defined" if coefficient in (None, "") else str(coefficient)


def _esc(value) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
