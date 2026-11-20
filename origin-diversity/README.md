# Origin diversity

How widely are the people who were not born in a community spread across different origin communities, and how does that rating sit next to one published outcome?

US states are rated on their own. Communities outside the United States are rated on their own. The same rule scores both. The page does not put them in one league table, and it does not say that newcomers caused the outcome.

## The rating

The score uses only people who were not born in the community.

- No such people scores 0, the bottom of the scale.
- The same count from one origin scores 1.
- That count spread evenly across four origins scores 4.
- A lopsided mix scores lower than an even mix of the same people.
- The same counts always return the same score.

The number is the effective number of origin communities: the exponential of the Shannon entropy of the origin shares.

For a US state, those people are the foreign-born population (born outside the United States) in the American Community Survey. People born in another US state are not in the rating. For a country, they are the UN international migrant stock by origin. Where a country counts migrants by citizenship instead of birthplace, the UN figure uses that count.

## The outcome

- US states, including the District of Columbia: median household income from the 2019-2023 American Community Survey, in 2023 dollars.
- Communities outside the United States: World Bank GDP per capita in current US dollars, for 2023, or 2022 when 2023 is not published.

Each panel reports the Spearman rank correlation between the rating and that outcome. The sign is the direction. It is a description of these published numbers.

## Look at the page

Open `docs/index.html` from disk. The tables are already filled in.

## Rebuild

From this folder, with Python 3.11 and no extra packages:

```powershell
python etl/build_communities.py
```

Add `--refresh` to download the public files again. Cached downloads stay in `data/raw` and are not part of the project history. The rebuilt table is `data/processed/communities.csv`.

The 2023 one-year place-of-birth summary file does not include every state, so the build uses the 2019-2023 five-year file and the matching five-year income table.

## Sources

- U.S. Census Bureau, American Community Survey 2019-2023 5-year summary files, tables B05006 (place of birth for the foreign-born population) and B19013 (median household income), plus the 2023 5-year table shells and the 2023 geography file for state names. https://www.census.gov/programs-surveys/acs/data/data-via-ftp.html
- United Nations Department of Economic and Social Affairs, Population Division. International Migrant Stock 2024, destination and origin, Table 1, both sexes, mid-2024. https://www.un.org/development/desa/pd/content/international-migrant-stock
- World Bank, GDP per capita (current US$), indicator NY.GDP.PCAP.CD. https://data.worldbank.org/indicator/NY.GDP.PCAP.CD
- ISO 3166 codes with UN M49 numeric codes, used only to match UN location codes to World Bank countries. https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes
