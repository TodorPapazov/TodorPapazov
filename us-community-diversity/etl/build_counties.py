"""Build the US community diversity page from public county files.

Run from this project's folder:

    python etl/build_counties.py

Pass --refresh to ignore data/raw. Downloads and file writing stay in this
module. Rating, association, and the Costco quarter share live in etl.rating.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.geo_us import project_counties  # noqa: E402
from etl.publication import write_explorer  # noqa: E402
from etl.rating import (  # noqa: E402
    LINES_AGAINST,
    LINES_UP,
    NO_CLEAR,
    association_summary,
    band_share_below,
    choose_chr_measure,
    costco_quartile_shares,
    direct_highway_codes,
    diversity_rating,
    hypothesis_line,
    hypothesis_reading,
    population_band,
    pooled_within_band_association,
    year_end_series,
)

USER_AGENT = "us-community-diversity/1.0 (educational; public-data rebuild)"
CENSUS = "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF"
SHELL_URL = f"{CENSUS}/documentation/ACS20235YR_Table_Shells.txt"
GEOS_URL = f"{CENSUS}/documentation/Geos20235YR.txt"
CBP_URL = "https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip"
ZILLOW_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)
CHR_URL = (
    "https://www.countyhealthrankings.org/sites/default/files/media/document/"
    "analytic_data2025_v3.csv"
)
CHR_DICT_URL = (
    "https://www.countyhealthrankings.org/sites/default/files/media/document/"
    "DataDictionary_2025.xlsx"
)
CHR_CODEBOOK_URL = (
    "https://www.countyhealthrankings.org/sites/default/files/media/document/"
    "2025%20CHR%20CSV%20SAS%20Analytic%20Documentation.pdf"
)
FINANCE_URL = (
    "https://www2.census.gov/programs-surveys/gov-finances/tables/2024/"
    "2024_Individual_Unit_Files.zip"
)
COUNTY_SHP_URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_20m.zip"
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
COSTCO_MIN_POINTS = 400
HISTORY_VINTAGES = ((2021, "2017-2021"), (2022, "2018-2022"), (2023, "2019-2023"))
MAP_MEASURES = (
    "racial_ethnic",
    "foreign_born_pct",
    "unemployment_rate",
    "home_value",
    "home_value_change_5yr",
    "graduation_rate",
    "highway_per_resident",
    "entertainment_kinds",
)
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

STATE_FIPS = {
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16",
    "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
    "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42",
    "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56",
}

ENTERTAINMENT = (
    ("full_service_restaurants_per_10k", "722511", "Full-service restaurants per 10,000 residents"),
    ("limited_service_restaurants_per_10k", "722513", "Limited-service restaurants per 10,000 residents"),
    ("movie_theaters_per_10k", "512131", "Movie theaters per 10,000 residents"),
    ("bowling_per_10k", "713950", "Bowling centers per 10,000 residents"),
    ("museums_per_10k", "712110", "Museums per 10,000 residents"),
    ("theater_companies_per_10k", "711110", "Theater companies per 10,000 residents"),
    ("fitness_per_10k", "713940", "Fitness centers per 10,000 residents"),
    ("drinking_places_per_10k", "722410", "Drinking places per 10,000 residents"),
)

OUTCOMES = (
    ("unemployment_rate", "Unemployment rate", False, 2),
    ("payroll_per_employee", "Average annual payroll per employee", True, 0),
    ("home_value", "Typical home value", True, 0),
    ("home_value_change_5yr", "Five-year change in typical home value", True, 2),
    ("graduation_rate", "High school graduation rate", True, 2),
    ("violent_crime_rate", "Violent crime rate", False, 2),
    ("highway_per_resident", "County highway spending per resident", True, 2),
    ("entertainment_kinds", "Entertainment categories with at least one establishment", True, 0),
    ("costco_per_100k", "Costco warehouses per 100,000 residents", True, 3),
) + tuple((key, label, True, 2) for key, _naics, label in ENTERTAINMENT)

SCORE_FIELDS = (
    ("racial_ethnic", "Who lives there"),
    ("foreign_born_pct", "Born outside the United States"),
)

FIELD_ORDER = (
    ["fips", "county", "population", "band", "racial_ethnic", "foreign_born_pct"]
    + [key for key, _label, _higher, _digits in OUTCOMES]
    + ["costco_warehouses"]
)


def main(argv=None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    raw_dir = ROOT / "data" / "raw"
    processed_dir = ROOT / "data" / "processed"
    docs_dir = ROOT / "docs"
    for folder in (raw_dir, processed_dir, docs_dir):
        folder.mkdir(parents=True, exist_ok=True)

    shell = fetch_bytes(SHELL_URL, raw_dir / "ACS20235YR_Table_Shells.txt", args.refresh).decode("utf-8-sig")
    race_columns = select_race_columns(shell)
    if len(race_columns) != 8:
        raise SystemExit(f"Expected 8 mutually exclusive race and ethnicity groups, found {race_columns}.")
    foreign_column = column_by_label(shell, "B05002", "Foreign-born")
    labor_column = column_by_label(shell, "B23025", "Civilian labor force")
    unemployed_column = column_by_label(shell, "B23025", "Unemployed")
    names = load_county_names(raw_dir, args.refresh)
    population_rows = load_pipe_counties(f"{CENSUS}/data/5YRData/acsdt5y2023-b01003.dat", raw_dir / "b01003-counties.dat", args.refresh)
    race_rows = load_pipe_counties(f"{CENSUS}/data/5YRData/acsdt5y2023-b03002.dat", raw_dir / "b03002-counties.dat", args.refresh)
    birth_rows = load_pipe_counties(f"{CENSUS}/data/5YRData/acsdt5y2023-b05002.dat", raw_dir / "b05002-counties.dat", args.refresh)
    labor_rows = load_pipe_counties(f"{CENSUS}/data/5YRData/acsdt5y2023-b23025.dat", raw_dir / "b23025-counties.dat", args.refresh)
    counties, gap = build_base_counties(
        names, population_rows, race_rows, race_columns, birth_rows, foreign_column,
        labor_rows, labor_column, unemployed_column,
    )
    if len(counties) < 200:
        raise SystemExit(f"Only {len(counties)} counties had both diversity scores and 50,000 residents.")
    if gap > 0.05:
        raise SystemExit(f"Race and ethnicity groups do not add up to the county total (gap {gap:.3f}).")

    sources = {}
    cbp, cbp_error = attempt(raw_dir, "cbp", lambda: load_cbp(raw_dir, args.refresh))
    sources["payroll_and_entertainment"] = source_status(cbp, cbp_error, "County Business Patterns 2023 county file")
    zillow, zillow_error = attempt(raw_dir, "zillow", lambda: load_zillow(raw_dir, args.refresh))
    sources["home_value"] = source_status(zillow, zillow_error, "Zillow county home value index")
    chr_result, chr_error = attempt(raw_dir, "chr", lambda: load_chr(raw_dir, args.refresh))
    sources["schools_and_crime"] = source_status(chr_result, chr_error, "County Health Rankings 2025 analytic file")
    highways, highway_error = attempt(raw_dir, "highway", lambda: load_highways(raw_dir, args.refresh))
    sources["highway"] = source_status(highways, highway_error, "Census 2024 government finances")
    costco, costco_error = attempt(raw_dir, "costco", lambda: load_costco(raw_dir, args.refresh))
    sources["costco"] = source_status(costco, costco_error, "OpenStreetMap Costco points")
    if costco_error:
        sources["costco"]["detail"] = (
            "OpenStreetMap did not return a usable warehouse list. "
            f"The comparison needs at least {COSTCO_MIN_POINTS} US points. No Costco counts were filled in."
        )

    attach(counties, cbp, zillow, chr_result, highways, costco)
    notes = apply_sanity(counties, sources)
    hypotheses = {
        key: summarize_score(counties, key, label) for key, label in SCORE_FIELDS
    }
    costco_block = costco_report(counties, costco, sources["costco"])
    history, history_labels = load_score_history(
        raw_dir, args.refresh, counties, foreign_column, labor_column, unemployed_column
    )
    home_series = load_home_series(raw_dir, args.refresh)
    shapes = project_counties(county_polygons(raw_dir, args.refresh))
    write_csv(processed_dir / "counties.csv", counties)
    write_json(processed_dir / "summary.json", counties, sources, hypotheses, costco_block, gap, notes)
    write_explorer(
        docs_dir,
        counties,
        shapes,
        hypotheses,
        history,
        home_series,
        gap,
        (
            ("racial_ethnic", "Who lives there", None, 4),
            ("foreign_born_pct", "Foreign-born percent", None, 2),
        )
        + OUTCOMES,
    )
    print(render_dump(counties, sources, hypotheses, costco_block, gap, len(shapes), history_labels), end="")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Build the US community diversity page.")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached files in data/raw.")
    return parser.parse_args(argv)


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def fetch_bytes(url: str, dest: Path, refresh: bool) -> bytes:
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        return dest.read_bytes()
    log(f"download {dest.name}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"download failed: {url}: {exc}") from exc
    dest.write_bytes(payload)
    return payload


def fetch_text(url: str, dest: Path, refresh: bool) -> str:
    return fetch_bytes(url, dest, refresh).decode("utf-8-sig")


def attempt(raw_dir: Path, key: str, func):
    try:
        return func(), None
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        (raw_dir / f"{key}-error.txt").write_text(message, encoding="utf-8", newline="\n")
        log(f"{key} unavailable: {message}")
        return None, message


def source_status(payload, error, label):
    if error:
        return {"label": label, "status": "missing", "detail": error}
    detail = ""
    if isinstance(payload, tuple) and payload and isinstance(payload[-1], str):
        detail = payload[-1]
    return {"label": label, "status": "ok", "detail": detail}


def table_url(table: str) -> str:
    return f"{CENSUS}/data/5YRData/acsdt5y2023-{table.lower()}.dat"


def shell_rows(shell_text: str, table: str):
    rows = []
    for line in shell_text.splitlines():
        if not line.startswith(table + "|"):
            continue
        parts = line.split("|")
        number = int(parts[3].split("_")[1])
        rows.append(
            {
                "indent": int(float(parts[2])),
                "label": parts[4],
                "column": f"{table}_E{number:03d}",
            }
        )
    if not rows:
        raise RuntimeError(f"The Census shell has no {table} rows.")
    return rows


def select_race_columns(shell_text: str) -> list[str]:
    """Non-Hispanic race groups, with two-or-more as one group, plus Hispanic origin."""

    rows = shell_rows(shell_text, "B03002")
    columns = []
    index = 0
    while index < len(rows):
        row = rows[index]
        if row["label"].startswith("Not Hispanic"):
            parent = row["indent"]
            index += 1
            while index < len(rows) and rows[index]["indent"] > parent:
                child = rows[index]
                if child["indent"] != parent + 1:
                    index += 1
                    continue
                columns.append(child["column"])
                index += 1
                while index < len(rows) and rows[index]["indent"] > child["indent"]:
                    index += 1
            continue
        if row["label"].startswith("Hispanic or Latino"):
            columns.append(row["column"])
            parent = row["indent"]
            index += 1
            while index < len(rows) and rows[index]["indent"] > parent:
                index += 1
            continue
        index += 1
    return columns


def column_by_label(shell_text: str, table: str, prefix: str) -> str:
    wanted = _shell_label(prefix)
    matches = [
        row["column"]
        for row in shell_rows(shell_text, table)
        if _shell_label(row["label"]).startswith(wanted)
    ]
    if len(matches) != 1:
        raise RuntimeError(f"{table} label {prefix!r} matched {matches}.")
    return matches[0]


def _shell_label(text: str) -> str:
    return " ".join(text.lower().replace("-", " ").split())


def load_pipe_counties(url: str, dest: Path, refresh: bool) -> dict[str, list[str]]:
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        text = dest.read_text(encoding="utf-8")
    else:
        text = stream_county_lines(url)
        dest.write_text(text, encoding="utf-8", newline="\n")
    return parse_pipe(text)


def stream_county_lines(url: str) -> str:
    log(f"stream {url.rsplit('/', 1)[-1]}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    kept = []
    header = None
    seen = 0
    passed_higher_first = False
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            for raw_line in response:
                line = raw_line.decode("latin-1").rstrip("\r\n")
                if not line:
                    continue
                if header is None:
                    header = line
                    continue
                geo_id = line.split("|", 1)[0]
                prefix = geo_id[:3]
                if prefix == "050":
                    seen += 1
                    kept.append(line)
                    continue
                if seen == 0 and prefix.isdigit() and int(prefix) > 50:
                    passed_higher_first = True
                if seen >= 3000 and not passed_higher_first and prefix.isdigit() and int(prefix) > 50:
                    break
    except urllib.error.URLError as exc:
        raise RuntimeError(f"download failed: {url}: {exc}") from exc
    if seen < 3000:
        raise RuntimeError(f"{url} yielded {seen} county rows.")
    return header + "\n" + "\n".join(kept) + "\n"


def parse_pipe(text: str):
    lines = [line for line in text.splitlines() if line]
    header = lines[0].lstrip("\ufeff").split("|")
    rows = {}
    width = len(header)
    geo_at = header.index("GEO_ID") if "GEO_ID" in header else 0
    for line in lines[1:]:
        parts = line.split("|")
        if len(parts) != width:
            continue
        rows[parts[geo_at]] = parts
    return {"header": header, "rows": rows}


def index_map(table):
    return {name: position for position, name in enumerate(table["header"])}


def load_county_names(raw_dir: Path, refresh: bool) -> dict[str, str]:
    dest = raw_dir / "county-names.dat"
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        text = dest.read_text(encoding="utf-8")
    else:
        text = stream_geo_names(GEOS_URL)
        dest.write_text(text, encoding="utf-8", newline="\n")
    header, *lines = text.splitlines()
    columns = header.lstrip("\ufeff").split("|")
    index = {name: position for position, name in enumerate(columns)}
    names = {}
    for line in lines:
        parts = line.split("|")
        if len(parts) <= index["NAME"]:
            continue
        geo_id = parts[index["GEO_ID"]]
        fips = geo_id[-5:]
        if fips[:2] not in STATE_FIPS:
            continue
        names[fips] = parts[index["NAME"]]
    if len(names) < 3000:
        raise RuntimeError(f"County name file has {len(names)} counties.")
    return names


def stream_geo_names(url: str) -> str:
    log("stream county names")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    kept = []
    header = None
    seen = 0
    passed_higher_first = False
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            for raw_line in response:
                line = raw_line.decode("latin-1").rstrip("\r\n")
                if not line:
                    continue
                if header is None:
                    header = line
                    columns = header.lstrip("\ufeff").split("|")
                    sum_at = columns.index("SUMLEVEL")
                    component_at = columns.index("COMPONENT")
                    continue
                parts = line.split("|")
                if len(parts) <= max(sum_at, component_at):
                    continue
                level = parts[sum_at]
                if level == "050" and parts[component_at] == "00":
                    seen += 1
                    kept.append(line)
                    continue
                if seen == 0 and level.isdigit() and int(level) > 50:
                    passed_higher_first = True
                if seen >= 3000 and not passed_higher_first and level.isdigit() and int(level) > 50:
                    break
    except urllib.error.URLError as exc:
        raise RuntimeError(f"download failed: {url}: {exc}") from exc
    if seen < 3000:
        raise RuntimeError(f"Geography file yielded {seen} counties.")
    return header + "\n" + "\n".join(kept) + "\n"


def as_number(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("$", "").replace("%", "")
    if text in {"", ".", "NA", "N", "null", "-", "null"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def cell(table, geo_id, column):
    row = table["rows"].get(geo_id)
    if row is None or column not in index_map(table):
        return None
    return as_number(row[index_map(table)[column]])


def build_base_counties(names, population_rows, race_rows, race_columns, birth_rows, foreign_column, labor_rows, labor_column, unemployed_column):
    worst_gap = 0.0
    counties = []
    gap_skips = 0
    pop_index = index_map(population_rows)
    for fips, county_name in sorted(names.items()):
        geo_id = f"0500000US{fips}"
        population = cell(population_rows, geo_id, "B01003_E001")
        if population is None or population < 50000:
            continue
        if "B01003_E001" not in pop_index:
            raise RuntimeError("B01003 total column is missing.")
        total = cell(race_rows, geo_id, "B03002_E001")
        counts = [cell(race_rows, geo_id, column) for column in race_columns]
        if total is None or any(count is None for count in counts):
            continue
        leaf = math.fsum(count for count in counts if count > 0)
        gap = abs(leaf - total) / total if total else 1.0
        if gap > 0.05:
            gap_skips += 1
            continue
        worst_gap = max(worst_gap, gap)
        birth_total = cell(birth_rows, geo_id, "B05002_E001")
        foreign_born = cell(birth_rows, geo_id, foreign_column)
        if birth_total is None or birth_total <= 0 or foreign_born is None or foreign_born > birth_total:
            continue
        labor = cell(labor_rows, geo_id, labor_column)
        unemployed = cell(labor_rows, geo_id, unemployed_column)
        unemployment = None
        if labor and labor > 0 and unemployed is not None and 0 <= unemployed <= labor:
            unemployment = round(100.0 * unemployed / labor, 2)
        row = empty_row(fips, county_name, int(round(population)))
        row["racial_ethnic"] = round(diversity_rating(counts), 4)
        row["foreign_born_pct"] = round(100.0 * foreign_born / birth_total, 2)
        row["unemployment_rate"] = unemployment
        counties.append(row)
    counties.sort(key=lambda row: (row["county"], row["fips"]))
    if gap_skips > max(20, len(counties) // 20):
        raise RuntimeError(f"{gap_skips} counties had race groups that did not add up to the total.")
    return counties, worst_gap


def empty_row(fips, county_name, population):
    row = {
        "fips": fips,
        "county": county_name,
        "population": population,
        "band": population_band(population),
    }
    for key in FIELD_ORDER:
        row.setdefault(key, None)
    return row


def load_cbp(raw_dir: Path, refresh: bool):
    payload = fetch_bytes(CBP_URL, raw_dir / "cbp23co.zip", refresh)
    wanted = {naics for _key, naics, _label in ENTERTAINMENT}
    found = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as book:
        name = [item for item in book.namelist() if item.endswith(".txt")][0]
        with book.open(name) as handle:
            text = io.TextIOWrapper(handle, encoding="latin-1", newline="")
            for record in csv.DictReader(text):
                naics = (record.get("naics") or "").strip()
                if naics != "------" and naics not in wanted:
                    continue
                fips = (record.get("fipstate") or "").zfill(2) + (record.get("fipscty") or "").zfill(3)
                if fips[:2] not in STATE_FIPS:
                    continue
                bucket = found.setdefault(fips, {"payroll": None, "establishments": {}})
                if naics == "------":
                    employment = as_number(record.get("emp"))
                    payroll = as_number(record.get("ap"))
                    if employment and employment > 0 and payroll is not None and payroll >= 0:
                        bucket["payroll"] = payroll * 1000.0 / employment
                else:
                    establishments = as_number(record.get("est"))
                    if establishments is not None and establishments >= 0:
                        bucket["establishments"][naics] = establishments
    if len(found) < 1000:
        raise RuntimeError(f"County Business Patterns returned {len(found)} counties.")
    return found, "Establishments, and annual payroll in thousands of dollars divided by March employment."


def load_zillow(raw_dir: Path, refresh: bool):
    text = fetch_text(ZILLOW_URL, raw_dir / "zillow-county-zhvi.csv", refresh)
    reader = csv.DictReader(io.StringIO(text))
    months = [name for name in reader.fieldnames or [] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", name or "")]
    if len(months) < 61:
        raise RuntimeError("Zillow file does not have five years of months.")
    latest = months[-1]
    year, month, _day = latest.split("-")
    prior_prefix = f"{int(year) - 5}-{month}-"
    prior = next((name for name in months if name.startswith(prior_prefix)), None)
    if prior is None:
        raise RuntimeError(f"Zillow file has no month five years before {latest}.")
    values = {}
    for record in reader:
        if (record.get("RegionType") or "county").lower() not in {"", "county"}:
            continue
        state = (record.get("StateCodeFIPS") or "").zfill(2)
        local = (record.get("MunicipalCodeFIPS") or "").zfill(3)
        fips = state[-2:] + local[-3:]
        if fips[:2] not in STATE_FIPS:
            continue
        current = as_number(record.get(latest))
        earlier = as_number(record.get(prior))
        change = None
        if current is not None and earlier is not None and earlier > 0:
            change = (current - earlier) / earlier * 100.0
        values[fips] = {"home_value": current, "home_value_change_5yr": change}
    if len(values) < 1000:
        raise RuntimeError(f"Zillow returned {len(values)} counties.")
    return values, f"Latest month {latest}. Five-year change is from {prior}."


def load_chr(raw_dir: Path, refresh: bool):
    dictionary = read_dictionary(fetch_bytes(CHR_DICT_URL, raw_dir / "DataDictionary_2025.xlsx", refresh))
    graduation = choose_chr_measure(dictionary, "graduation")
    violent = choose_chr_measure(dictionary, "violent_crime")
    if graduation is None:
        raise RuntimeError("The 2025 data dictionary has no single high school graduation raw value.")
    codebook_note = codebook_violent_note(raw_dir, refresh, violent)
    text = fetch_text(CHR_URL, raw_dir / "analytic_data2025_v3.csv", refresh)
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    graduation_column = match_header(headers, graduation[1])
    violent_column = match_header(headers, violent[1]) if violent else None
    if graduation_column is None:
        raise RuntimeError(f"Analytic CSV has no column {graduation[1]!r}.")
    values = {}
    for record in reader:
        fips = re.sub(r"\D", "", record.get("5-digit FIPS Code") or record.get("fipscode") or "")
        if len(fips) != 5 or fips[:2] not in STATE_FIPS or fips.endswith("000"):
            continue
        values[fips] = {
            "graduation_rate": as_number(record.get(graduation_column)),
            "violent_crime_rate": as_number(record.get(violent_column)) if violent_column else None,
        }
    scale_graduation(values)
    if violent is None or violent_column is None:
        detail = (
            "High school graduation is the ninth-grade cohort rate. "
            "The 2025 data dictionary has no violent crime raw value, so that rate is blank. "
            + codebook_note
        )
    else:
        detail = f"Graduation column {graduation[0]}. Violent crime column {violent[0]}."
    return values, detail


def match_header(headers, label):
    wanted = " ".join(label.split())
    for header in headers:
        if " ".join((header or "").split()) == wanted:
            return header
    return None


def scale_graduation(values):
    raw = [row["graduation_rate"] for row in values.values() if row["graduation_rate"] is not None]
    if not raw:
        raise RuntimeError("High school graduation has no county values.")
    median = sorted(raw)[len(raw) // 2]
    factor = 100.0 if median <= 1.5 else 1.0
    for row in values.values():
        if row["graduation_rate"] is not None:
            row["graduation_rate"] = row["graduation_rate"] * factor


def read_dictionary(payload: bytes):
    with zipfile.ZipFile(io.BytesIO(payload)) as book:
        shared = []
        root = ET.fromstring(book.read("xl/sharedStrings.xml"))
        for item in root.findall(f"{NS}si"):
            shared.append("".join(node.text or "" for node in item.iter(f"{NS}t")))
        sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.findall(f"{NS}sheetData/{NS}row"):
        values = {}
        for cell in row.findall(f"{NS}c"):
            ref = cell.get("r") or "A"
            letters = "".join(ch for ch in ref if ch.isalpha())
            index = 0
            for ch in letters:
                index = index * 26 + ord(ch) - 64
            kind = cell.get("t")
            node = cell.find(f"{NS}v")
            text = "" if node is None or node.text is None else node.text
            if kind == "s" and text.isdigit():
                text = shared[int(text)]
            values[index - 1] = text
        if not values:
            continue
        width = max(values) + 1
        rows.append(tuple(values.get(position, "") for position in range(width)))
    parsed = []
    for row in rows[1:]:
        if len(row) >= 3:
            parsed.append((row[0], row[1], row[2]))
    return parsed


def codebook_violent_note(raw_dir: Path, refresh: bool, violent) -> str:
    if violent is not None:
        return ""
    try:
        payload = fetch_bytes(CHR_CODEBOOK_URL, raw_dir / "2025-chr-analytic-codebook.pdf", refresh)
    except Exception as exc:
        return f"The analytic codebook could not be read ({exc})."
    text = pdf_paren_text(payload).lower()
    if "violent crime" in text:
        return "The analytic codebook mentions violent crime, but the data dictionary has no single raw-value column."
    return "The 2025 analytic codebook text that could be read does not name a violent crime measure."


def load_highways(raw_dir: Path, refresh: bool):
    payload = fetch_bytes(FINANCE_URL, raw_dir / "2024_Individual_Unit_Files.zip", refresh)
    with zipfile.ZipFile(io.BytesIO(payload)) as book:
        pdf_name = [name for name in book.namelist() if name.lower().endswith(".pdf") and "technical" in name.lower()][0]
        data_name = [name for name in book.namelist() if name.endswith("2024FinEstDAT_07152026modp.txt")][0]
        pid_name = [name for name in book.namelist() if name.endswith("Fin_PID_2024.txt")][0]
        manual = pdf_paren_text(book.read(pdf_name))
        data = book.read(data_name)
        pid = book.read(pid_name)
    if "thousands of dollars" not in manual.lower():
        raise RuntimeError("The finance manual does not say the amount is in thousands of dollars.")
    titles = item_code_titles(manual)
    codes = direct_highway_codes(titles)
    if not codes:
        raise RuntimeError("The finance manual did not yield direct highway item codes.")
    sample = set()
    for line in pid.decode("latin-1").splitlines():
        if len(line) < 12 or line[2] != "1":
            continue
        state, county = line[0:2], line[3:6]
        if state in STATE_FIPS and county.isdigit():
            sample.add(state + county)
    totals = {fips: 0.0 for fips in sample}
    used = set()
    for raw_line in data.decode("latin-1").splitlines():
        if len(raw_line) < 31 or raw_line[2] != "1":
            continue
        state, county = raw_line[0:2], raw_line[3:6]
        fips = state + county
        if fips not in totals:
            continue
        item = raw_line[12:15]
        if item not in codes:
            continue
        year = raw_line[27:31]
        if year != "2024":
            continue
        amount = as_number(raw_line[15:27])
        if amount is None:
            continue
        totals[fips] += amount * 1000.0
        used.add(item)
    if not sample:
        raise RuntimeError("No county governments were found in the finance ID file.")
    if not used:
        raise RuntimeError(f"None of the direct highway codes {codes} appeared for county governments.")
    detail = (
        f"Direct highway codes from the 2024 manual: {', '.join(codes)}. "
        f"Amounts are thousands of dollars. Sampled county governments: {len(sample)}. "
        "A blank county was not in that sample. A zero means the sampled county government had none of these highway amounts."
    )
    return totals, detail


def item_code_titles(manual: str):
    parts = re.split(r"en-US", manual)
    titles = []
    for index, part in enumerate(parts[:-1]):
        code = part.strip()
        if re.fullmatch(r"[A-Z][A-Z0-9]{2}", code):
            titles.append((code, parts[index + 1].strip()))
    return titles


def pdf_paren_text(payload: bytes) -> str:
    pieces = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", payload, re.S):
        data = match.group(1)
        try:
            data = zlib.decompress(data)
        except zlib.error:
            continue
        chunks = re.findall(r"\((?:\\.|[^\\)])*\)", data.decode("latin-1", "replace"))
        if not chunks:
            continue
        words = []
        for chunk in chunks:
            word = chunk[1:-1].replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
            words.append(word)
        pieces.append("".join(words))
    return "\n".join(pieces)


def load_costco(raw_dir: Path, refresh: bool):
    error_path = raw_dir / "costco-error.txt"
    cached = raw_dir / "costco-overpass.json"
    if error_path.exists() and not cached.exists() and not refresh:
        raise RuntimeError("A previous OpenStreetMap download failed. Pass --refresh to try again.")
    points = costco_points(raw_dir, refresh)
    counties = county_polygons(raw_dir, refresh)
    counts = {county["fips"]: 0 for county in counties}
    unassigned = 0
    us_points = 0
    for lat, lon in points:
        if not (17.0 <= lat <= 72.0 and -179.0 <= lon <= -65.0):
            continue
        us_points += 1
        hits = []
        for county in counties:
            minx, miny, maxx, maxy = county["bbox"]
            if lon < minx or lon > maxx or lat < miny or lat > maxy:
                continue
            if point_in_rings(lon, lat, county["rings"]):
                hits.append(county["fips"])
        if len(hits) == 1:
            counts[hits[0]] += 1
        else:
            unassigned += 1
    detail = f"{us_points} US Costco points after removing duplicates. {unassigned} were not inside one county polygon."
    return {"counts": counts, "us_points": us_points, "unassigned": unassigned}, detail


def costco_points(raw_dir: Path, refresh: bool):
    dest = raw_dir / "costco-overpass.json"
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        payload = json.loads(dest.read_text(encoding="utf-8"))
    else:
        payload = download_overpass()
        dest.write_text(json.dumps(payload), encoding="utf-8")
    raw_points = []
    for element in payload.get("elements") or []:
        tags = element.get("tags") or {}
        if not keep_warehouse(tags):
            continue
        if "lat" in element and "lon" in element:
            lat, lon = element["lat"], element["lon"]
        elif "center" in element:
            lat, lon = element["center"]["lat"], element["center"]["lon"]
        else:
            continue
        raw_points.append((float(lat), float(lon)))
    return dedupe_points(raw_points)


def download_overpass():
    query = """
[out:json][timeout:180];
area["ISO3166-1"="US"]["admin_level"="2"]->.usa;
(
  nwr["brand"="Costco"](area.usa);
  nwr["name"~"^Costco",i](area.usa);
);
out center tags;
""".strip()
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    errors = []
    for url in OVERPASS_URLS:
        request = urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            continue
        if payload.get("elements"):
            return payload
        errors.append(f"{url}: {payload.get('remark') or 'no elements'}")
    raise RuntimeError("Overpass failed. " + " | ".join(errors))


def keep_warehouse(tags) -> bool:
    brand = (tags.get("brand") or "").lower()
    name = (tags.get("name") or "").lower()
    operator = (tags.get("operator") or "").lower()
    if "costco" not in brand and "costco" not in name and "costco" not in operator:
        return False
    if "gas" in name or "fuel" in name:
        return False
    amenity = (tags.get("amenity") or "").lower()
    shop = (tags.get("shop") or "").lower()
    if amenity == "fuel" and shop not in {"supermarket", "wholesale", "department_store"}:
        return False
    return True


def dedupe_points(points):
    kept = []
    for lat, lon in sorted(points):
        if all(haversine_km(lat, lon, other_lat, other_lon) > 0.4 for other_lat, other_lon in kept):
            kept.append((lat, lon))
    return kept


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    arc = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(arc))


def county_polygons(raw_dir: Path, refresh: bool):
    payload = fetch_bytes(COUNTY_SHP_URL, raw_dir / "cb_2023_us_county_20m.zip", refresh)
    with zipfile.ZipFile(io.BytesIO(payload)) as book:
        shp = book.read([name for name in book.namelist() if name.endswith(".shp")][0])
        dbf = book.read([name for name in book.namelist() if name.endswith(".dbf")][0])
    records = read_dbf(dbf)
    shapes = read_shp_polygons(shp)
    if len(records) != len(shapes):
        raise RuntimeError("County boundary attributes and shapes are different lengths.")
    counties = []
    for record, rings in zip(records, shapes):
        if not record or not rings:
            continue
        fips = (record.get("GEOID") or "").zfill(5)
        if fips[:2] not in STATE_FIPS:
            continue
        xs = [point[0] for ring in rings for point in ring]
        ys = [point[1] for ring in rings for point in ring]
        if not xs:
            continue
        counties.append({"fips": fips, "rings": rings, "bbox": (min(xs), min(ys), max(xs), max(ys))})
    if len(counties) < 3000:
        raise RuntimeError(f"County boundary file produced {len(counties)} polygons.")
    return counties


def read_dbf(data: bytes):
    count, header_length, record_length = struct.unpack("<IHH", data[4:12])
    fields = []
    pos = 32
    while data[pos] != 0x0D:
        name = data[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", "replace")
        length = data[pos + 16]
        fields.append((name, length))
        pos += 32
    rows = []
    start = header_length
    for _index in range(count):
        record = data[start : start + record_length]
        start += record_length
        if not record or record[:1] == b"*":
            rows.append(None)
            continue
        offset = 1
        row = {}
        for name, length in fields:
            row[name] = record[offset : offset + length].decode("latin-1").strip()
            offset += length
        rows.append(row)
    return rows


def read_shp_polygons(data: bytes):
    shapes = []
    pos = 100
    while pos + 8 <= len(data):
        _number, word_length = struct.unpack(">ii", data[pos : pos + 8])
        pos += 8
        content = data[pos : pos + word_length * 2]
        pos += word_length * 2
        if len(content) < 44:
            shapes.append([])
            continue
        shape_type = struct.unpack("<i", content[:4])[0]
        if shape_type not in {5, 15, 25}:
            shapes.append([])
            continue
        num_parts, num_points = struct.unpack("<ii", content[36:44])
        parts = struct.unpack("<" + "i" * num_parts, content[44 : 44 + 4 * num_parts])
        point_at = 44 + 4 * num_parts
        points = [
            struct.unpack("<dd", content[point_at + 16 * index : point_at + 16 * index + 16])
            for index in range(num_points)
        ]
        rings = []
        for index, part in enumerate(parts):
            end = parts[index + 1] if index + 1 < len(parts) else num_points
            rings.append(points[part:end])
        shapes.append(rings)
    return shapes


def point_in_rings(x, y, rings) -> bool:
    inside = False
    for ring in rings:
        if len(ring) < 3:
            continue
        previous = len(ring) - 1
        for current in range(len(ring)):
            xi, yi = ring[current]
            xj, yj = ring[previous]
            if (yi > y) != (yj > y):
                cross = (xj - xi) * (y - yi) / (yj - yi) + xi
                if x < cross:
                    inside = not inside
            previous = current
    return inside


def attach(counties, cbp, zillow, chr_result, highways, costco):
    cbp_map = cbp[0] if cbp else {}
    zillow_map = zillow[0] if zillow else {}
    chr_map = chr_result[0] if chr_result else {}
    highway_map = highways[0] if highways else None
    publish_costco = bool(costco) and costco[0]["us_points"] >= COSTCO_MIN_POINTS
    costco_counts = costco[0]["counts"] if publish_costco else {}
    for row in counties:
        fips = row["fips"]
        population = row["population"]
        business = cbp_map.get(fips)
        if business is not None:
            if business["payroll"] is not None:
                row["payroll_per_employee"] = round(business["payroll"])
            kinds = 0
            for key, naics, _label in ENTERTAINMENT:
                count = business["establishments"].get(naics, 0)
                row[key] = round(count / population * 10000.0, 2)
                if count >= 1:
                    kinds += 1
            row["entertainment_kinds"] = kinds
        home = zillow_map.get(fips)
        if home:
            if home["home_value"] is not None:
                row["home_value"] = round(home["home_value"])
            if home["home_value_change_5yr"] is not None:
                row["home_value_change_5yr"] = round(home["home_value_change_5yr"], 2)
        health = chr_map.get(fips)
        if health:
            if health["graduation_rate"] is not None:
                row["graduation_rate"] = round(health["graduation_rate"], 2)
            if health["violent_crime_rate"] is not None:
                row["violent_crime_rate"] = round(health["violent_crime_rate"], 2)
        if highway_map is not None and fips in highway_map:
            row["highway_per_resident"] = round(highway_map[fips] / population, 2)
        if publish_costco and fips in costco_counts:
            count = costco_counts[fips]
            row["costco_warehouses"] = count
            row["costco_per_100k"] = round(count / population * 100000.0, 3)


def apply_sanity(counties, sources):
    notes = []
    checks = (
        ("unemployment_rate", 1, 20, "Unemployment"),
        ("payroll_per_employee", 10000, 400000, "Payroll per employee"),
        ("home_value", 40000, 3000000, "Typical home value"),
        ("home_value_change_5yr", -40, 250, "Five-year home value change"),
        ("graduation_rate", 40, 100, "High school graduation"),
        ("highway_per_resident", 5, 5000, "Highway spending per resident"),
        ("full_service_restaurants_per_10k", 0.2, 80, "Full-service restaurants"),
    )
    foreign_values = sorted(row["foreign_born_pct"] for row in counties)
    foreign_median = foreign_values[len(foreign_values) // 2]
    if not 0.3 <= foreign_median <= 70:
        raise SystemExit(f"Foreign-born percent median {foreign_median} is outside the expected range.")
    for key, low, high, label in checks:
        values = sorted(row[key] for row in counties if row.get(key) is not None)
        if not values:
            continue
        median = values[len(values) // 2]
        if low <= median <= high:
            continue
        for row in counties:
            row[key] = None
        message = f"{label} median {median} is outside {low} to {high}, so those values were left blank."
        notes.append(message)
        for source in sources.values():
            if key.split("_")[0] in source["label"].lower() or label.split()[0].lower() in source["label"].lower():
                source["status"] = "missing"
                source["detail"] = message
    ratings = [row["racial_ethnic"] for row in counties]
    if ratings and (min(ratings) < 0 or max(ratings) > 8):
        raise SystemExit("The racial and ethnic score fell outside the 0 to 8 range of its eight groups.")
    return notes


def summarize_score(counties, score_key, score_label):
    lines = {}
    for key, label, higher, _digits in OUTCOMES:
        pairs = [
            (row[score_key], row[key])
            for row in counties
            if row.get(score_key) is not None and row.get(key) is not None
        ]
        records = [
            (row["band"], row[score_key], row[key])
            for row in counties
            if row.get("band") and row.get(score_key) is not None and row.get(key) is not None
        ]
        overall = association_summary(pairs)
        within = pooled_within_band_association(records) if records else {"n": 0, "coefficient": None, "direction": "none", "bands": {}}
        lines[key] = {
            "label": label,
            "higher_is_better": higher,
            "line": hypothesis_line(label, higher, within, overall),
            "reading": hypothesis_reading(within.get("coefficient"), higher),
            "within_band": pack_association(within),
            "overall": pack_association(overall),
        }
    return {"label": score_label, "outcomes": lines}


def pack_association(summary):
    coefficient = summary.get("coefficient")
    packed = {
        "n": summary.get("n", 0),
        "coefficient": None if coefficient is None else f"{coefficient:.6f}",
        "direction": summary.get("direction", "none"),
    }
    if "bands" in summary:
        packed["bands"] = {
            band: pack_association(band_summary) for band, band_summary in summary["bands"].items()
        }
    return packed


def costco_report(counties, costco, source):
    if costco is None:
        return {
            "published": False,
            "text": (
                "Costco warehouses are blank. OpenStreetMap did not return a usable warehouse list, "
                f"so the comparison is not published. It is published only when at least {COSTCO_MIN_POINTS} US points come back."
            ),
            "quartiles": {},
        }
    us_points = costco[0]["us_points"]
    if us_points < COSTCO_MIN_POINTS:
        return {
            "published": False,
            "us_points": us_points,
            "text": (
                f"OpenStreetMap returned {us_points} US Costco points. "
                f"The comparison is published only when that count is at least {COSTCO_MIN_POINTS}. "
                "County Costco counts are left blank."
            ),
            "quartiles": {},
        }
    quartiles = {}
    sentences = [source["detail"], f"Counties with at least one warehouse: {sum(1 for row in counties if (row.get('costco_warehouses') or 0) > 0)}."]
    for key, label in SCORE_FIELDS:
        rows = [
            (row["county"], row[key], (row.get("costco_warehouses") or 0) > 0)
            for row in counties
            if row.get(key) is not None and row.get("costco_warehouses") is not None
        ]
        shares = costco_quartile_shares(rows)
        quartiles[key] = shares
        low, high = shares["quartiles"][0], shares["quartiles"][3]
        sentences.append(
            f"{label}: lowest diversity quarter {fmt_share(low)}; highest diversity quarter {fmt_share(high)}."
        )
    return {"published": True, "us_points": us_points, "text": " ".join(sentences), "quartiles": quartiles}


def fmt_share(bucket) -> str:
    share = bucket["share"]
    percent = "n/a" if share is None else f"{share * 100:.1f}%"
    return f"{bucket['with_warehouse']} of {bucket['n']} ({percent})"


def write_csv(path: Path, counties):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELD_ORDER, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in counties:
            writer.writerow({key: "" if row.get(key) is None else row.get(key) for key in FIELD_ORDER})


def write_json(path, counties, sources, hypotheses, costco_block, gap, notes):
    payload = {
        "scores_merged": False,
        "min_population": 50000,
        "bands": ["50-150k", "150-500k", "500k+"],
        "county_count": len(counties),
        "race_group_gap": f"{gap:.6f}",
        "sources": sources,
        "sanity_notes": notes,
        "hypotheses": hypotheses,
        "costco": {
            "published": costco_block["published"],
            "us_points": costco_block.get("us_points"),
            "text": costco_block["text"],
            "quartiles": costco_block["quartiles"],
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def render_dump(counties, sources, hypotheses, costco_block, gap, shape_count=0, history_labels=()) -> str:
    lines = [
        "BUILD us-community-diversity",
        f"counties\t{len(counties)}",
        "scores_merged\tno",
        "min_population\t50000",
        "bands\t50-150k,150-500k,500k+",
        f"race_group_gap\t{gap:.6f}",
        f"map_shapes\t{shape_count}",
        "history\t" + ",".join(history_labels),
    ]
    for key, source in sources.items():
        lines.append(f"source\t{key}\t{source['status']}\t{source['detail']}")
    lines.append(f"costco_published\t{'yes' if costco_block['published'] else 'no'}")
    lines.append(f"costco\t{costco_block['text']}")
    for score_key, _label in SCORE_FIELDS:
        for outcome_key, _label, _higher, _digits in OUTCOMES:
            item = hypotheses[score_key]["outcomes"][outcome_key]
            lines.append(f"hypothesis\t{score_key}\t{outcome_key}\t{item['line']}")
    lines.append("county\t" + "\t".join(FIELD_ORDER))
    for row in counties:
        values = ["" if row.get(key) is None else str(row.get(key)) for key in FIELD_ORDER]
        lines.append("county\t" + "\t".join(values))
    lines.append("")
    return "\n".join(lines)


def render_html(counties, sources, hypotheses, costco_block, gap, notes) -> str:
    outcome_items = []
    for _key, label, higher, _digits in OUTCOMES:
        direction = "higher" if higher else "lower"
        outcome_items.append(f"<li>{esc(label)}: the hypothesis expects a {direction} number.</li>")
    source_items = []
    for source in sources.values():
        source_items.append(
            f"<li><strong>{esc(source['label'])}.</strong> {esc(source['status'])}. {esc(source['detail'])}</li>"
        )
    sections = []
    for score_key, score_label in SCORE_FIELDS:
        blocks = [f"<h2>{esc(score_label)}</h2>"]
        for outcome_key, _label, _higher, _digits in OUTCOMES:
            item = hypotheses[score_key]["outcomes"][outcome_key]
            blocks.append(
                f"<p class=\"line {reading_class(item['reading'])}\">{esc(item['line'])} "
                f"<span class=\"reading\">{esc(item['reading'])}.</span></p>"
            )
        sections.append("\n".join(blocks))
    headers = "".join(f"<th>{esc(header_label(key))}</th>" for key in FIELD_ORDER)
    body = []
    for row in counties:
        cells = []
        for key in FIELD_ORDER:
            text = "" if row.get(key) is None else str(row.get(key))
            kind = " data-sort=\"\"" if text == "" else f" data-sort=\"{esc(text)}\""
            cells.append(f"<td{kind}>{esc(text)}</td>")
        body.append(f"<tr data-name=\"{esc(row['county'].lower())}\">{''.join(cells)}</tr>")
    note_html = "".join(f"<p>{esc(note)}</p>" for note in notes)
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
  <p class="lede">This page compares two descriptions of diversity with jobs, home values, school completion, violent crime, county road spending, places to gather, and Costco warehouses. It reports whether the numbers line up. It does not say diversity caused any of them, and it does not rank counties as better or worse places to live.</p>
  <div class="method">
    <p>A community here is a county or county equivalent in the 50 states and the District of Columbia with at least 50,000 residents in the 2019-2023 American Community Survey. Smaller counties are left out. Puerto Rico is left out.</p>
    <p><strong>Who lives there</strong> is the effective number of racial and ethnic groups in Census table B03002. One group scores 1. An even mix of the eight mutually exclusive groups scores 8. The same counts always score the same.</p>
    <p><strong>Born outside the United States</strong> is the percent of residents who are foreign-born in Census table B05002. The two scores are never averaged.</p>
    <p>The hypothesis line uses the rank correlation inside population bands (50-150k, 150-500k, and 500k or more), so a result that appears only because large counties differ from small ones is not the one in the sentence. A coefficient smaller than 0.05 in absolute value is no clear direction. The widest gap between the race and ethnicity group counts and the county total, among published counties, is {gap:.4f}.</p>
    <p>High school graduation is the share of a ninth-grade cohort that finishes in four years. It is not a test score and it is not a judgment of a whole school system. County highway spending is the county government's own direct spending on regular and toll highways. A blank means that county was not in the finance sample. A zero means the sampled government had none of those highway amounts.</p>
  </div>
  <h2>What the hypothesis calls the favorable direction</h2>
  <ul class="method">{''.join(outcome_items)}</ul>
  <h2>Sources in this build</h2>
  <ul class="source-list">{''.join(source_items)}</ul>
  {note_html}
  {''.join(sections)}
  <h2>Costco</h2>
  <p class="quartz">{esc(costco_block['text'])}</p>
  <h2>Counties</h2>
  <p>The table is a reading aid. Sorting and the name filter do not make a league table of good communities. A blank cell means that source did not publish a figure for that county.</p>
  <label>Find a county <input id="county-filter" type="search" placeholder="Type a county name"></label>
  <div class="scroll">
    <table id="counties">
      <thead><tr>{headers}</tr></thead>
      <tbody>
        {''.join(body)}
      </tbody>
    </table>
  </div>
</main>
<script>
(function () {{
  var input = document.getElementById("county-filter");
  var table = document.getElementById("counties");
  var body = table.tBodies[0];
  input.addEventListener("input", function () {{
    var query = input.value.toLowerCase();
    var rows = body.rows;
    for (var i = 0; i < rows.length; i++) {{
      var name = rows[i].getAttribute("data-name") || "";
      rows[i].style.display = name.indexOf(query) === -1 ? "none" : "";
    }}
  }});
  var headers = table.tHead.rows[0].cells;
  var sortState = {{index: -1, asc: true}};
  for (var h = 0; h < headers.length; h++) {{
    headers[h].addEventListener("click", function () {{
      var index = this.cellIndex;
      sortState.asc = sortState.index === index ? !sortState.asc : true;
      sortState.index = index;
      var rows = Array.prototype.slice.call(body.rows);
      rows.sort(function (a, b) {{
        var av = a.cells[index].getAttribute("data-sort") || "";
        var bv = b.cells[index].getAttribute("data-sort") || "";
        if (av === "" && bv !== "") return 1;
        if (bv === "" && av !== "") return -1;
        var an = Number(av);
        var bn = Number(bv);
        var cmp = (av !== "" && bv !== "" && !isNaN(an) && !isNaN(bn)) ? an - bn : (av < bv ? -1 : av > bv ? 1 : 0);
        return sortState.asc ? cmp : -cmp;
      }});
      for (var i = 0; i < rows.length; i++) body.appendChild(rows[i]);
    }});
  }}
}})();
</script>
</body>
</html>
"""


def load_score_history(raw_dir, refresh, counties, foreign_column, labor_column, unemployed_column):
    study = [row["fips"] for row in counties]
    history = {
        fips: {"racial_ethnic": [], "foreign_born_pct": [], "unemployment_rate": []}
        for fips in study
    }
    labels = []
    for year, label in HISTORY_VINTAGES:
        if year == 2023:
            for row in counties:
                append_history(history[row["fips"]], label, row)
            labels.append(label)
            continue
        try:
            vintage = load_vintage(year, raw_dir, refresh)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            (raw_dir / f"acs-{year}-error.txt").write_text(message, encoding="utf-8", newline="\n")
            log(f"acs {year} unavailable: {message}")
            continue
        for fips in study:
            scored = vintage.get(fips)
            if scored:
                append_history(history[fips], label, scored)
        labels.append(label)
    return history, tuple(labels)


def append_history(bucket, label, scored):
    for key in ("racial_ethnic", "foreign_born_pct", "unemployment_rate"):
        value = scored.get(key) if isinstance(scored, dict) else None
        if value is not None:
            bucket[key].append([label, value])


def load_vintage(year, raw_dir, refresh):
    base = f"https://www2.census.gov/programs-surveys/acs/summary_file/{year}/table-based-SF"
    shell = fetch_bytes(
        f"{base}/documentation/ACS{year}5YR_Table_Shells.txt",
        raw_dir / f"ACS{year}5YR_Table_Shells.txt",
        refresh,
    ).decode("utf-8-sig")
    race_columns = select_race_columns(shell)
    if len(race_columns) != 8:
        raise RuntimeError(f"{year} race columns: {race_columns}")
    foreign = column_by_label(shell, "B05002", "Foreign-born")
    labor = column_by_label(shell, "B23025", "Civilian labor force")
    unemployed = column_by_label(shell, "B23025", "Unemployed")
    race_rows = load_pipe_counties(
        f"{base}/data/5YRData/acsdt5y{year}-b03002.dat", raw_dir / f"b03002-{year}.dat", refresh
    )
    birth_rows = load_pipe_counties(
        f"{base}/data/5YRData/acsdt5y{year}-b05002.dat", raw_dir / f"b05002-{year}.dat", refresh
    )
    labor_rows = load_pipe_counties(
        f"{base}/data/5YRData/acsdt5y{year}-b23025.dat", raw_dir / f"b23025-{year}.dat", refresh
    )
    scored = {}
    for geo_id in race_rows["rows"]:
        if not geo_id.startswith("0500000US"):
            continue
        fips = geo_id[-5:]
        if fips[:2] not in STATE_FIPS:
            continue
        point = score_vintage_geo(
            geo_id, race_rows, race_columns, birth_rows, foreign, labor_rows, labor, unemployed
        )
        if point:
            scored[fips] = point
    if len(scored) < 500:
        raise RuntimeError(f"{year} produced {len(scored)} scored counties.")
    return scored


def score_vintage_geo(geo_id, race_rows, race_columns, birth_rows, foreign_column, labor_rows, labor_column, unemployed_column):
    total = cell(race_rows, geo_id, "B03002_E001")
    counts = [cell(race_rows, geo_id, column) for column in race_columns]
    if total is None or total <= 0 or any(count is None for count in counts):
        return None
    leaf = math.fsum(count for count in counts if count > 0)
    if abs(leaf - total) / total > 0.05:
        return None
    scored = {"racial_ethnic": round(diversity_rating(counts), 4)}
    birth_total = cell(birth_rows, geo_id, "B05002_E001")
    foreign_born = cell(birth_rows, geo_id, foreign_column)
    if birth_total and birth_total > 0 and foreign_born is not None and 0 <= foreign_born <= birth_total:
        scored["foreign_born_pct"] = round(100.0 * foreign_born / birth_total, 2)
    labor = cell(labor_rows, geo_id, labor_column)
    unemployed = cell(labor_rows, geo_id, unemployed_column)
    if labor and labor > 0 and unemployed is not None and 0 <= unemployed <= labor:
        scored["unemployment_rate"] = round(100.0 * unemployed / labor, 2)
    return scored


def load_home_series(raw_dir, refresh):
    text = fetch_text(ZILLOW_URL, raw_dir / "zillow-county-zhvi.csv", refresh)
    reader = csv.DictReader(io.StringIO(text))
    months = [name for name in (reader.fieldnames or []) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", name or "")]
    series = {}
    for record in reader:
        state = (record.get("StateCodeFIPS") or "").zfill(2)
        local = (record.get("MunicipalCodeFIPS") or "").zfill(3)
        fips = state[-2:] + local[-3:]
        if fips[:2] not in STATE_FIPS:
            continue
        pairs = [(month, as_number(record.get(month))) for month in months]
        values = year_end_series(pairs)
        if values:
            series[fips] = [[year, round(value)] for year, value in values]
    if len(series) < 500:
        raise RuntimeError(f"Zillow year-end series covered {len(series)} counties.")
    return series


def header_label(key: str) -> str:
    labels = {
        "fips": "FIPS",
        "county": "County",
        "population": "Population",
        "band": "Population band",
        "racial_ethnic": "Who lives there",
        "foreign_born_pct": "Foreign-born percent",
        "costco_warehouses": "Costco warehouses",
    }
    if key in labels:
        return labels[key]
    for outcome_key, label, _higher, _digits in OUTCOMES:
        if outcome_key == key:
            return label
    return key


def reading_class(reading: str) -> str:
    if reading == LINES_UP:
        return "up"
    if reading == LINES_AGAINST:
        return "against"
    return "unclear"


def esc(value) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    main()
