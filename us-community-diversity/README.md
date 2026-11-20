# US community diversity

A map publication that asks whether more diverse US counties also show the local conditions in a stated hypothesis: lower unemployment, higher payroll, higher and rising home values, higher high school completion, lower violent crime, higher county road spending, more places to gather, and more Costco warehouses.

Open `docs/index.html` from disk. Click a county to zoom the map and read that community. A find box jumps to a county by name. The page does not say diversity caused an outcome, and it does not combine the measures into a ranking of good counties.

## What a community is

A community is a county or county equivalent in the 50 states and the District of Columbia with at least 50,000 residents in the 2019-2023 American Community Survey. Smaller counties are left out so one theater, one crime count, or one warehouse does not swing the result. Puerto Rico is left out.

## Two diversity scores

The scores are not averaged.

**Who lives there.** Effective number of racial and ethnic groups from ACS table B03002. The groups are the mutually exclusive Census lines: Hispanic or Latino, and the non-Hispanic race groups, with two or more races kept as one group. One group scores 1. An even mix scores higher. The same counts always score the same.

**Born outside the United States.** Percent of residents who are foreign-born, from ACS table B05002.

## What "better" means here

Each measure has a hypothesis direction. The page says whether higher diversity lines up with that direction, lines up against it, or has no clear direction. A Spearman correlation smaller than 0.05 in absolute value is no clear direction.

The sentence uses the correlation **inside population bands** (50-150k, 150-500k, and 500k or more). The overall correlation is shown after that. Large counties can be more diverse and also have more of everything; the band result is the one the hypothesis uses.

| Question | Measure | Hypothesis direction |
| --- | --- | --- |
| Better jobs | Unemployment rate of residents | Lower |
| Better jobs | Average annual payroll per employee | Higher |
| Property value | Latest Zillow Home Value Index for the county | Higher |
| Rising property value | Percent change in that index over the prior five years | Higher |
| Good schools | High school graduation rate, the share of a ninth-grade cohort that graduates in four years | Higher. This is completion, not test scores or a judgment of a whole school system. |
| Crime | Violent crime rate, when the 2025 County Health Rankings analytic file publishes one | Lower. Counties the source leaves missing stay blank. |
| Roads | County-government highway direct expenditure per resident | Higher. This is the county government's own current operations and construction for regular and toll highways. It is not city spending, state spending, or a measure of pavement. Counties that were not in the survey sample stay blank. |
| Places to gather | Establishments per 10,000 residents for full-service restaurants, limited-service restaurants, movie theaters, bowling centers, museums, theater companies, fitness centers, and drinking places | Higher for each rate |
| Places to gather | How many of those eight categories have at least one establishment | Higher |
| Costco | Warehouses per 100,000 residents, and the share of counties with at least one warehouse in each diversity quarter | Higher. Published only when OpenStreetMap contributes at least 400 US points. |

## Sources

- American Community Survey 5-year summary files for 2021, 2022, and 2023, tables B01003, B03002, B05002, and B23025. The map's current scores use 2019-2023. The county charts also show 2017-2021 and 2018-2022. Those periods overlap: neighboring points share four years. Earlier table-based files are not published, and the older sequence-file bundle is about 7 GB, so it is not used: <https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/>
- County Business Patterns 2023 county file. Annual payroll is published in thousands of dollars: <https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip>
- Zillow county Home Value Index. The chart uses a year-end value: December when that month is published for the county, otherwise the latest month in the year. The newest year uses the latest month in the file: <https://files.zillowstatic.com/research/public_csvs/zhvi/County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv>
- County Health Rankings 2025 analytic CSV and the 2025 data dictionary. The build chooses the graduation and violent-crime columns from that dictionary instead of hard-coding measure numbers. A measure the dictionary does not publish stays blank: <https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation>
- Census 2024 Annual Survey of State and Local Government Finances, individual unit file. Highway item codes and the "thousands of dollars" unit are read from the technical documentation inside the zip: <https://www2.census.gov/programs-surveys/gov-finances/tables/2024/2024_Individual_Unit_Files.zip>
- Census 2023 county cartographic boundaries, 1:20,000,000. The build projects them once with an Albers equal-area layout: the lower 48 on parallels 29.5 and 45.5, Alaska on 55 and 65, and Hawaii on 8 and 18, then places Alaska and Hawaii below the lower 48. A warehouse on a boundary can miss the simplified line: <https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_20m.zip>
- OpenStreetMap Costco points through the Overpass API. This is not a download from Costco's website.

If Zillow, County Health Rankings, the finance file, or Overpass fails, the build saves the error under `data/raw/` and leaves that outcome blank. It does not fill in a figure.

## Rebuild

From this folder:

```powershell
python etl/build_counties.py
```

`--refresh` downloads the public files again instead of using `data/raw`. The command writes `data/processed/counties.csv`, `data/processed/summary.json`, `docs/data.js`, and `docs/index.html`. `docs/app.js` and `docs/styles.css` are the map and the county panel.

Open `docs/index.html` from disk. The numbers and the county shapes are already in the page. No server is required.

The same page is published at <https://todorpapazov.github.io/us-community-diversity/>.

`data/raw/` is the download cache and is not part of the result.
