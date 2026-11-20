"""Download public origin counts and write the community portfolio.

Run from this project's folder:

    python etl/build_communities.py
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.rating import (  # noqa: E402
    association_summary,
    describe_association,
    diversity_rating,
    rank_within_sets,
)

USER_AGENT = "origin-diversity-portfolio/1.0 (educational; public-data rebuild)"
US_SET = "US state"
WORLD_SET = "outside the US"
US_MEASURE = "Median household income (2023 dollars)"
US_YEAR = "2019-2023"
WORLD_MEASURE = "GDP per capita (current US$)"
US_OUTCOME_LABEL = "median household income"
WORLD_OUTCOME_LABEL = "GDP per capita"

CENSUS = "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF"
SHELL_URL = f"{CENSUS}/documentation/ACS20235YR_Table_Shells.txt"
GEOS_URL = f"{CENSUS}/documentation/Geos20231YR.txt"
BIRTH_URL = f"{CENSUS}/data/5YRData/acsdt5y2023-b05006.dat"
INCOME_URL = f"{CENSUS}/data/5YRData/acsdt5y2023-b19013.dat"
UN_URL = (
    "https://www.un.org/development/desa/pd/sites/"
    "www.un.org.development.desa.pd/files/"
    "undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx"
)
ISO_URL = (
    "https://raw.githubusercontent.com/lukes/"
    "ISO-3166-Countries-with-Regional-Codes/master/all/all.csv"
)
WB_COUNTRIES_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"
WB_GDP_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD"
    "?date=2022:2023&format=json&per_page=1000"
)

# UN M49 codes for the United States and inhabited US territories.
# They are not communities outside the United States.
US_TERRITORY_CODES = {16, 316, 580, 581, 630, 840, 850}
UN_OTHERS = 2003
UN_WORLD_ORIGIN = 900

NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"

FIELDNAMES = [
    "community",
    "set",
    "rating",
    "outcome",
    "outcome_measure",
    "outcome_year",
    "newcomers",
    "origin_count",
    "rank_in_set",
]


def select_origin_columns(shell_text: str) -> list[str]:
    """Mutually exclusive B05006 estimate columns.

    A line that ends with a colon is a group total, so its children are used
    instead. A line that does not end with a colon keeps its own count, and
    any deeper detail under it (the Azores under Portugal) is not added again.
    """

    rows = []
    for line in shell_text.splitlines():
        if not line.startswith("B05006|"):
            continue
        parts = line.split("|")
        number = int(parts[3].split("_")[1])
        rows.append(
            {
                "indent": int(float(parts[2])),
                "label": parts[4],
                "column": f"B05006_E{number:03d}",
            }
        )
    selected = []
    index = 0
    while index < len(rows):
        row = rows[index]
        if index == 0:
            index += 1
            continue
        has_child = index + 1 < len(rows) and rows[index + 1]["indent"] > row["indent"]
        if row["label"].endswith(":"):
            index += 1
            continue
        if has_child:
            selected.append(row["column"])
            index += 1
            while index < len(rows) and rows[index]["indent"] > row["indent"]:
                index += 1
            continue
        selected.append(row["column"])
        index += 1
    if not selected:
        raise SystemExit("The Census table shell did not yield origin columns.")
    return selected


def main(argv=None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    raw_dir = ROOT / "data" / "raw"
    processed_dir = ROOT / "data" / "processed"
    docs_dir = ROOT / "docs"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    print("BUILD origin-diversity")
    shell_text = fetch_bytes(SHELL_URL, raw_dir / "ACS20235YR_Table_Shells.txt", args.refresh).decode("utf-8-sig")
    geo_text = fetch_bytes(GEOS_URL, raw_dir / "Geos20231YR.txt", args.refresh).decode("utf-8-sig")
    names = state_names(geo_text)
    if len(names) < 51:
        raise SystemExit(f"Expected 51 US state geographies, found {len(names)}.")
    origin_columns = select_origin_columns(shell_text)
    birth_text = fetch_state_rows(
        BIRTH_URL, raw_dir / "acsdt5y2023-b05006-states.dat", set(names), args.refresh
    )
    income_text = fetch_state_rows(
        INCOME_URL, raw_dir / "acsdt5y2023-b19013-states.dat", set(names), args.refresh
    )
    us_rows, us_gap = build_us_rows(names, origin_columns, birth_text, income_text)
    print(f"us_origin_gap\t{us_gap:.6f}")

    migrant_path = raw_dir / "undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx"
    fetch_bytes(UN_URL, migrant_path, args.refresh)
    iso_text = fetch_bytes(ISO_URL, raw_dir / "iso3166-m49.csv", args.refresh).decode("utf-8-sig")
    country_rows = fetch_world_bank(WB_COUNTRIES_URL, "wb-countries", raw_dir, args.refresh)
    gdp_rows = fetch_world_bank(WB_GDP_URL, "wb-gdp", raw_dir, args.refresh)
    world_rows, world_gap = build_world_rows(migrant_path, iso_text, country_rows, gdp_rows)
    print(f"world_origin_gap\t{world_gap:.6f}")

    if len(us_rows) < 50:
        raise SystemExit(f"Only {len(us_rows)} US states had both a rating and an income.")
    if len(world_rows) < 40:
        raise SystemExit(
            f"Only {len(world_rows)} communities outside the US had both a rating and GDP per capita."
        )

    us_summary = association_summary((row["rating"], row["outcome"]) for row in us_rows)
    world_summary = association_summary((row["rating"], row["outcome"]) for row in world_rows)
    ranked = rank_within_sets(us_rows + world_rows)
    rendered = [present_row(row) for row in ranked]
    summaries = {US_SET: us_summary, WORLD_SET: world_summary}
    write_outputs(processed_dir, docs_dir, rendered, summaries)
    print(render_dump(rendered, summaries), end="")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Build the origin-diversity portfolio.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Download the public files again instead of using data/raw.",
    )
    return parser.parse_args(argv)


def fetch_bytes(url: str, dest: Path, refresh: bool) -> bytes:
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        return dest.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = response.read()
    except urllib.error.URLError as exc:
        raise SystemExit(f"download failed: {url}: {exc}") from exc
    dest.write_bytes(payload)
    return payload


def fetch_state_rows(url: str, dest: Path, wanted: set[str], refresh: bool) -> str:
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        return dest.read_text(encoding="utf-8")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    found = {}
    header = None
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
                if geo_id not in wanted:
                    continue
                if line.count("|") != header.count("|"):
                    continue
                found[geo_id] = line
                if len(found) == len(wanted):
                    break
    except urllib.error.URLError as exc:
        raise SystemExit(f"download failed: {url}: {exc}") from exc
    missing = sorted(wanted - set(found))
    if missing:
        raise SystemExit(f"Missing state rows from {url}: {', '.join(missing[:8])}")
    text = header + "\n" + "\n".join(found[geo_id] for geo_id in sorted(found)) + "\n"
    dest.write_text(text, encoding="utf-8", newline="\n")
    return text


def fetch_world_bank(base_url: str, cache_stem: str, raw_dir: Path, refresh: bool):
    page = 1
    rows = []
    while True:
        joiner = "&" if "?" in base_url else "?"
        url = f"{base_url}{joiner}page={page}"
        payload = json.loads(
            fetch_bytes(url, raw_dir / f"{cache_stem}-{page}.json", refresh).decode("utf-8")
        )
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            raise SystemExit(f"Unexpected World Bank payload from {url}")
        rows.extend(payload[1])
        if page >= int(payload[0]["pages"]):
            break
        page += 1
    return rows


def state_names(geo_text: str) -> dict[str, str]:
    lines = geo_text.splitlines()
    header = lines[0].lstrip("\ufeff").split("|")
    index = {name: position for position, name in enumerate(header)}
    names = {}
    for line in lines[1:]:
        parts = line.split("|")
        if len(parts) <= index["NAME"]:
            continue
        if parts[index["SUMLEVEL"]] != "040" or parts[index["COMPONENT"]] != "00":
            continue
        geo_id = parts[index["GEO_ID"]]
        if geo_id.endswith("US72"):
            continue
        names[geo_id] = parts[index["NAME"]]
    return names


def build_us_rows(names, origin_columns, birth_text, income_text):
    birth_header, birth_rows = parse_pipe_table(birth_text)
    income_header, income_rows = parse_pipe_table(income_text)
    birth_index = {name: position for position, name in enumerate(birth_header)}
    income_index = {name: position for position, name in enumerate(income_header)}
    missing = [column for column in origin_columns + ["B05006_E001"] if column not in birth_index]
    if missing or "B19013_E001" not in income_index:
        raise SystemExit(f"Census columns missing from the summary file: {missing[:6]}")
    rows = []
    worst_gap = 0.0
    for geo_id, community in sorted(names.items()):
        birth = birth_rows.get(geo_id)
        income_parts = income_rows.get(geo_id)
        if birth is None or income_parts is None:
            continue
        income = as_number(income_parts[income_index["B19013_E001"]])
        total = as_number(birth[birth_index["B05006_E001"]])
        if income is None or income <= 0 or total is None:
            continue
        counts = []
        for column in origin_columns:
            value = as_number(birth[birth_index[column]])
            if value is not None:
                counts.append(value)
        leaf_sum = math.fsum(count for count in counts if count > 0)
        if total > 0:
            worst_gap = max(worst_gap, abs(leaf_sum - total) / total)
        rating = round(diversity_rating(counts), 4)
        rows.append(
            {
                "community": community,
                "set": US_SET,
                "rating": rating,
                "outcome": int(round(income)),
                "outcome_measure": US_MEASURE,
                "outcome_year": US_YEAR,
                "newcomers": int(round(leaf_sum)),
                "origin_count": sum(1 for count in counts if count > 0),
            }
        )
    if worst_gap > 0.05:
        raise SystemExit(
            f"Census origin lines do not add up to the foreign-born total (gap {worst_gap:.3f})."
        )
    return rows, worst_gap


def build_world_rows(migrant_path: Path, iso_text: str, country_rows, gdp_rows):
    crosswalk = m49_to_iso3(iso_text)
    real_codes = real_country_codes(country_rows)
    gdp = gdp_by_iso3(gdp_rows, real_codes)
    counts, names, totals = read_migrant_stock(migrant_path)
    worst_gap = 0.0
    checked = 0
    for dest, total in totals.items():
        if total <= 0:
            continue
        got = math.fsum(counts.get(dest, {}).values())
        worst_gap = max(worst_gap, abs(got - total) / total)
        checked += 1
    if checked == 0 or worst_gap > 0.05:
        raise SystemExit(
            f"UN origin lines do not add up to the migrant stock (gap {worst_gap:.3f}, places {checked})."
        )
    rows = []
    for dest, name in sorted(names.items(), key=lambda item: item[1]):
        if dest in US_TERRITORY_CODES or not name:
            continue
        iso3 = crosswalk.get(dest)
        if iso3 is None or iso3 not in gdp:
            continue
        year, outcome = gdp[iso3]
        origin_counts = list(counts.get(dest, {}).values())
        rating = round(diversity_rating(origin_counts), 4)
        rows.append(
            {
                "community": name,
                "set": WORLD_SET,
                "rating": rating,
                "outcome": round(outcome, 2),
                "outcome_measure": WORLD_MEASURE,
                "outcome_year": str(year),
                "newcomers": int(round(math.fsum(origin_counts))),
                "origin_count": sum(1 for count in origin_counts if count > 0),
            }
        )
    return rows, worst_gap


def read_migrant_stock(path: Path):
    counts = {}
    names = {}
    totals = {}
    for cells in iter_table1_rows(path):
        dest_raw = cells.get(5)
        origin_raw = cells.get(7)
        if dest_raw is None or origin_raw is None:
            continue
        try:
            dest = int(float(dest_raw))
            origin = int(float(origin_raw))
        except ValueError:
            continue
        if dest >= 900:
            continue
        name_raw = cells.get(2)
        if name_raw:
            names[dest] = clean_name(name_raw)
        value = as_number(str(cells.get(15, "")))
        if value is None:
            continue
        if origin == UN_WORLD_ORIGIN:
            totals[dest] = value
            continue
        if origin == dest or value <= 0:
            continue
        if origin >= 900 and origin != UN_OTHERS:
            continue
        bucket = counts.setdefault(dest, {})
        bucket[origin] = bucket.get(origin, 0.0) + value
    if not names:
        raise SystemExit("The UN workbook did not contain country destination rows.")
    return counts, names, totals


def iter_table1_rows(path: Path):
    with zipfile.ZipFile(path) as workbook:
        strings = shared_strings(workbook)
        sheet_path = table1_sheet_path(workbook)
        with workbook.open(sheet_path) as handle:
            for _event, element in ET.iterparse(handle, events=("end",)):
                if element.tag != f"{NS_MAIN}row":
                    continue
                row_number = int(element.attrib.get("r", "0"))
                if row_number >= 12:
                    cells = {}
                    for cell in element.findall(f"{NS_MAIN}c"):
                        ref = cell.attrib.get("r")
                        if not ref:
                            continue
                        column, _row = split_cell_ref(ref)
                        if column > 15:
                            continue
                        value = cell_text(cell, strings)
                        if value is not None and value != "":
                            cells[column] = value
                    if cells:
                        yield cells
                element.clear()


def table1_sheet_path(workbook: zipfile.ZipFile) -> str:
    workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
    relationships = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}
    for sheet in workbook_xml.findall(f"{NS_MAIN}sheets/{NS_MAIN}sheet"):
        if sheet.attrib.get("name") != "Table 1":
            continue
        target = targets[sheet.attrib[f"{NS_REL}id"]]
        if target.startswith("/"):
            return target.lstrip("/")
        return "xl/" + target
    raise SystemExit("UN workbook is missing Table 1.")


def shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall(f"{NS_MAIN}si"):
        strings.append("".join(node.text or "" for node in item.iter(f"{NS_MAIN}t")))
    return strings


def cell_text(cell, strings):
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{NS_MAIN}t"))
    value = cell.find(f"{NS_MAIN}v")
    if value is None or value.text is None:
        return None
    if kind == "s":
        return strings[int(value.text)]
    return value.text


def split_cell_ref(ref: str):
    column = 0
    index = 0
    while index < len(ref) and ref[index].isalpha():
        column = column * 26 + (ord(ref[index].upper()) - 64)
        index += 1
    return column, int(ref[index:])


def m49_to_iso3(text: str) -> dict[int, str]:
    mapping = {}
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    for row in reader:
        raw = (row.get("country-code") or "").strip()
        iso3 = (row.get("alpha-3") or "").strip()
        if not raw or not iso3:
            continue
        mapping[int(raw)] = iso3
    if len(mapping) < 100:
        raise SystemExit("The ISO / M49 crosswalk did not contain country codes.")
    return mapping


def real_country_codes(rows) -> set[str]:
    codes = set()
    for row in rows:
        region = ((row.get("region") or {}).get("value") or "").strip()
        if region == "Aggregates":
            continue
        code = row.get("id") or ""
        if len(code) == 3 and code.isalpha():
            codes.add(code)
    if len(codes) < 100:
        raise SystemExit("The World Bank country list did not contain countries.")
    return codes


def gdp_by_iso3(rows, real_codes: set[str]) -> dict[str, tuple[int, float]]:
    chosen = {}
    for row in rows:
        iso3 = row.get("countryiso3code") or ""
        if iso3 not in real_codes or row.get("value") is None:
            continue
        year = int(row["date"])
        value = float(row["value"])
        if not math.isfinite(value) or value <= 0:
            continue
        current = chosen.get(iso3)
        if current is None or year > current[0]:
            chosen[iso3] = (year, value)
    return chosen


def parse_pipe_table(text: str):
    lines = [line for line in text.splitlines() if line]
    header = lines[0].lstrip("\ufeff").split("|")
    rows = {}
    for line in lines[1:]:
        parts = line.split("|")
        if len(parts) == len(header):
            rows[parts[0]] = parts
    return header, rows


def as_number(raw):
    if raw is None:
        return None
    text = str(raw).strip()
    if text in {"", ".", "-", "null", "N", "(X)"}:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def clean_name(value) -> str:
    text = str(value).strip()
    while text.endswith("*"):
        text = text[:-1].strip()
    return text


def present_row(row):
    presented = dict(row)
    presented["rating"] = f"{float(row['rating']):.4f}"
    if row["set"] == US_SET:
        presented["outcome"] = str(int(row["outcome"]))
    else:
        presented["outcome"] = f"{float(row['outcome']):.2f}"
    presented["newcomers"] = str(int(row["newcomers"]))
    presented["origin_count"] = str(int(row["origin_count"]))
    presented["rank_in_set"] = str(int(row["rank_in_set"]))
    return presented


def write_outputs(processed_dir: Path, docs_dir: Path, rows, summaries) -> None:
    with (processed_dir / "communities.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "rating": (
            "Effective number of origin communities among people not born in the community. "
            "Zero newcomers score 0. One origin scores 1. An even split across k origins scores k."
        ),
        "sets_ranked_together": False,
        "sets": {},
    }
    for set_name, summary in summaries.items():
        coefficient = summary["coefficient"]
        payload["sets"][set_name] = {
            "n": summary["n"],
            "direction": summary["direction"],
            "coefficient": None if coefficient is None else f"{coefficient:.6f}",
        }
    (processed_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (docs_dir / "index.html").write_text(render_html(rows, summaries), encoding="utf-8")


def render_dump(rows, summaries) -> str:
    lines = [
        "rankings\tseparate",
        "combined_rank_column\tno",
    ]
    for set_name in (US_SET, WORLD_SET):
        members = [row for row in rows if row["set"] == set_name]
        start = members[0]["rank_in_set"] if members else "none"
        summary = summaries[set_name]
        coefficient = summary["coefficient"]
        coefficient_text = "none" if coefficient is None else f"{coefficient:.6f}"
        lines.append(f"set\t{set_name}\tcount\t{len(members)}\trank_start\t{start}")
        lines.append(
            f"association\t{set_name}\t{summary['direction']}\t{coefficient_text}\t{summary['n']}"
        )
    lines.append("community\tset\trating\toutcome\trank_in_set")
    for row in rows:
        lines.append(
            f"{row['community']}\t{row['set']}\t{row['rating']}\t{row['outcome']}\t{row['rank_in_set']}"
        )
    return "\n".join(lines) + "\n"



def spread_note(rows) -> str:
    """Say whether the top rating is also the largest newcomer count."""

    top_rating = max(rows, key=lambda row: float(row["rating"]))
    top_people = max(rows, key=lambda row: int(row["newcomers"]))
    if top_rating["community"] == top_people["community"]:
        return (
            f"{top_rating['community']} has both the highest rating "
            f"({top_rating['rating']}) and the most people born elsewhere "
            f"({top_people['newcomers']}) in this set."
        )
    return (
        f"{top_rating['community']} has the highest rating in this set "
        f"({top_rating['rating']}), with {top_rating['newcomers']} people born elsewhere. "
        f"{top_people['community']} has more people born elsewhere "
        f"({top_people['newcomers']}) and a lower rating ({top_people['rating']}). "
        "The rating follows how those people are spread, not how many of them there are."
    )


def render_html(rows, summaries) -> str:
    examples = [
        ("No people born elsewhere", []),
        ("100 people from one origin", [100]),
        ("100 people split 70 / 10 / 10 / 10", [70, 10, 10, 10]),
        ("100 people split evenly across four origins", [25, 25, 25, 25]),
    ]
    example_rows = []
    for label, counts in examples:
        example_rows.append(
            "<tr><td>"
            + escape(label)
            + '</td><td class="num">'
            + f"{diversity_rating(counts):.4f}"
            + "</td></tr>"
        )
    us_panel = [row for row in rows if row["set"] == US_SET]
    world_panel = [row for row in rows if row["set"] == WORLD_SET]
    us_sentence = describe_association("US states", US_OUTCOME_LABEL, summaries[US_SET])
    world_sentence = describe_association(
        "communities outside the US", WORLD_OUTCOME_LABEL, summaries[WORLD_SET]
    )
    us_spread = spread_note(us_panel)
    world_spread = spread_note(world_panel)
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Origin diversity and community outcomes</title>",
        '<link rel="stylesheet" href="styles.css">',
        "</head>",
        "<body>",
        '<main class="wrap">',
        "<p class=\"kicker\">Portfolio data project</p>",
        "<h1>Origin diversity and community outcomes</h1>",
        "<p>This page rates how widely the people who were not born in a community come from different origin communities. It does that once for US states, and once for communities outside the United States. The same rule scores every place. The two sets are ranked only within themselves.</p>",
        '<section id="rating-rule">',
        "<h2>The rating rule</h2>",
        "<p>The rating uses only people who were not born in that community, and how those people are spread across origin communities in the published table. The same newcomer count from one origin scores lower than that count spread across many origins. A community with no such newcomers scores 0, the bottom of the scale. One origin scores 1. An even split across four origins scores 4. A lopsided mix of the same people scores lower than an even mix. Scoring the same counts again returns the same rating.</p>",
        "<p>The score is the effective number of origin communities: the exponential of the Shannon entropy of the origin shares. Order does not matter. People born in the community are not in the count.</p>",
        "<table class=\"examples\"><caption>The same rule on fixed counts</caption><thead><tr><th>People not born in the community</th><th>Rating</th></tr></thead><tbody>",
        *example_rows,
        "</tbody></table>",
        "<p>For a US state, the people in the rating are the foreign-born population in the 2019-2023 American Community Survey: people born outside the United States. An origin is a Census place-of-birth line. A named country counts as one origin. A residual line such as Other Eastern Africa also counts as one origin, because that is how the Census groups people it does not assign to a named country. A detail already included in a country line, such as the Azores inside Portugal, is not added again. People born in another US state are not in this rating.</p>",
        "<p>For a community outside the United States, the people in the rating are the 2024 UN international migrant stock by country or area of origin. That stock is the foreign-born population where the country publishes birthplace, and the foreign-citizen count where it does not. People from the community itself are not included. The residual origin Others counts as one origin. Regional totals are not added on top of the country lines. The United States and US territories are left out of this set.</p>",
        "<p>US states, including the District of Columbia, are ranked only among themselves. Communities outside the United States are ranked only among themselves. Rank 1 is the highest rating inside that set. There is no combined league table.</p>",
        "</section>",
        '<section id="us-states">',
        "<h2>US states</h2>",
        f"<p class=\"association\">{escape(us_sentence)}</p>",
        f"<p>{escape(us_spread)}</p>",
        "<p>The outcome is median household income from the same 2019-2023 American Community Survey, in 2023 dollars.</p>",
        render_table(
            us_panel,
            "Median household income",
        ),
        "</section>",
        '<section id="outside-the-us">',
        "<h2>Communities outside the United States</h2>",
        f"<p class=\"association\">{escape(world_sentence)}</p>",
        f"<p>{escape(world_spread)}</p>",
        "<p>The outcome is World Bank GDP per capita in current US dollars. The year is 2023 when that figure is published, and 2022 when it is not. The year is in the table.</p>",
        render_table(
            world_panel,
            "GDP per capita",
        ),
        "</section>",
        "<footer>",
        "<h2>Sources</h2>",
        "<ul>",
        '<li><a href="https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-b05006.dat">U.S. Census Bureau, American Community Survey 2019-2023 5-year B05006</a>, place of birth for the foreign-born population. State rows only.</li>',
        '<li><a href="https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-b19013.dat">U.S. Census Bureau, American Community Survey 2019-2023 5-year B19013</a>, median household income in 2023 dollars.</li>',
        '<li><a href="https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/documentation/ACS20235YR_Table_Shells.txt">ACS 2023 5-year table shells</a> and <a href="https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/documentation/Geos20231YR.txt">2023 geography names</a>.</li>',
        '<li><a href="https://www.un.org/development/desa/pd/content/international-migrant-stock">United Nations Department of Economic and Social Affairs, Population Division, International Migrant Stock 2024</a>, Table 1, both sexes, mid-2024, destination by origin. CC BY 3.0 IGO.</li>',
        '<li><a href="https://data.worldbank.org/indicator/NY.GDP.PCAP.CD">World Bank, GDP per capita (current US$)</a>, indicator NY.GDP.PCAP.CD, 2023 or 2022.</li>',
        '<li><a href="https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/master/all/all.csv">ISO 3166 country codes with UN M49 numeric codes</a>, used only to match UN location codes to World Bank country codes.</li>',
        "</ul>",
        "<p>Rebuild from the project folder with <code>python etl/build_communities.py</code>. The page is filled in by that command. Opening this file from disk does not need a server.</p>",
        "</footer>",
        "</main>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(parts)


def render_table(rows, outcome_heading: str) -> str:
    top = max((float(row["rating"]) for row in rows), default=0.0)
    body = []
    for row in rows:
        width = 0 if top <= 0 else max(0, min(100, round(100 * float(row["rating"]) / top)))
        body.append(
            "<tr>"
            f"<td class=\"num\">{escape(row['rank_in_set'])}</td>"
            f"<td>{escape(row['community'])}</td>"
            f"<td class=\"rating\"><span class=\"num\">{escape(row['rating'])}</span>"
            f"<span class=\"bar\" style=\"width:{width}%\"></span></td>"
            f"<td class=\"num\">{escape(row['outcome'])}</td>"
            f"<td class=\"num\">{escape(row['outcome_year'])}</td>"
            f"<td class=\"num\">{escape(row['newcomers'])}</td>"
            f"<td class=\"num\">{escape(row['origin_count'])}</td>"
            "</tr>"
        )
    return (
        "<div class=\"table-wrap\"><table>"
        "<caption>Ranked only within this set. Rank 1 has the highest origin diversity here.</caption>"
        "<thead><tr>"
        "<th>Rank</th><th>Community</th><th>Origin diversity</th>"
        f"<th>{escape(outcome_heading)}</th><th>Outcome year</th>"
        "<th>People born elsewhere</th><th>Origin groups</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def escape(value) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    main()
