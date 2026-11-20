"""County diversity scores, associations, and the Costco quartile share.

These functions describe published counts. They do not say that a more
diverse county caused any outcome placed beside the score.
"""

from __future__ import annotations

import math


CLEAR_ABS = 0.05
LINES_UP = "lines up with the hypothesis"
LINES_AGAINST = "lines up against the hypothesis"
NO_CLEAR = "no clear direction"


def diversity_rating(group_counts) -> float:
    """Effective number of groups.

    ``group_counts`` is one count per group. Non-positive and non-numeric
    entries are ignored. No people returns 0, the bottom of the scale. Every
    person in one group returns 1. An even split across ``k`` groups returns
    ``k``. The same counts always return the same number. Order does not matter.

    The value is the Hill number of order 1: the exponential of the Shannon
    entropy of the group shares.
    """

    counts = _positive_counts(group_counts)
    total = math.fsum(counts)
    if total <= 0.0 or not counts:
        return 0.0
    if len(counts) == 1:
        return 1.0
    entropy = 0.0
    for count in counts:
        share = count / total
        entropy -= share * math.log(share)
    return math.exp(entropy)


def population_band(population) -> str | None:
    """Band for a county that already cleared the 50,000-resident floor.

    Returns ``None`` below 50,000. The three bands are ``50-150k``,
    ``150-500k``, and ``500k+``.
    """

    if population is None:
        return None
    people = float(population)
    if people < 50000:
        return None
    if people < 150000:
        return "50-150k"
    if people < 500000:
        return "150-500k"
    return "500k+"


def association_summary(pairs) -> dict:
    """Spearman association between a diversity score and an outcome.

    ``pairs`` is a sequence of ``(score, outcome)`` numbers. Direction is
    ``positive`` when higher scores sit with higher outcomes, ``negative``
    when they sit with lower outcomes, and ``none`` when the correlation is
    undefined or exactly zero. Ties use average ranks.
    """

    clean = [(float(score), float(outcome)) for score, outcome in pairs]
    result = {"n": len(clean), "coefficient": None, "direction": "none"}
    if len(clean) < 2:
        return result
    coefficient = _spearman(
        [score for score, _outcome in clean],
        [outcome for _score, outcome in clean],
    )
    result["coefficient"] = coefficient
    if coefficient is None or coefficient == 0.0:
        result["direction"] = "none"
    elif coefficient > 0.0:
        result["direction"] = "positive"
    else:
        result["direction"] = "negative"
    return result


def pooled_within_band_association(records) -> dict:
    """One Spearman after ranking inside each population band.

    ``records`` is a sequence of ``(band, score, outcome)``. Each band is
    ranked on its own, then those ranks are pooled. A national correlation
    that appears only because large counties differ from small ones does not
    survive this step. Bands with fewer than two counties are left out of the
    coefficient. The returned ``bands`` map still records each band's own
    association.
    """

    grouped = {}
    for band, score, outcome in records:
        grouped.setdefault(band, []).append((float(score), float(outcome)))
    band_summaries = {
        band: association_summary(pairs) for band, pairs in sorted(grouped.items())
    }
    pooled_scores = []
    pooled_outcomes = []
    for pairs in grouped.values():
        if len(pairs) < 2:
            continue
        score_ranks = _average_ranks([score for score, _outcome in pairs])
        outcome_ranks = _average_ranks([outcome for _score, outcome in pairs])
        pooled_scores.extend(score_ranks)
        pooled_outcomes.extend(outcome_ranks)
    summary = association_summary(zip(pooled_scores, pooled_outcomes))
    summary["bands"] = band_summaries
    return summary


def hypothesis_reading(coefficient, higher_is_better: bool) -> str:
    """How a coefficient sits against the stated direction.

    Absolute values below 0.05, and an undefined coefficient, are
    ``no clear direction``. A higher-is-better outcome lines up when the
    coefficient is positive. A lower-is-better outcome lines up when the
    coefficient is negative.
    """

    if coefficient is None or abs(float(coefficient)) < CLEAR_ABS:
        return NO_CLEAR
    positive = float(coefficient) > 0.0
    lines_up = positive if higher_is_better else not positive
    if lines_up:
        return LINES_UP
    return LINES_AGAINST


def band_share_below(values, target):
    """Percent of band values strictly below ``target``.

    The target county is included in ``values``. Ties are not counted as
    lower. An empty band returns ``None``. The same values and target always
    return the same percent.
    """

    usable = []
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            usable.append(number)
    if not usable or target is None:
        return None
    try:
        mark = float(target)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(mark):
        return None
    below = sum(1 for value in usable if value < mark)
    return 100.0 * below / len(usable)


def year_end_series(month_values):
    """Year-end values from a monthly series.

    ``month_values`` is a sequence of ``(YYYY-MM-DD, value)``. December is
    used when that month has a number. Otherwise the latest month in the year
    that has a number is used. A latest year with no December still returns
    that latest month. Years with no number are omitted.
    """

    by_year = {}
    for raw_date, raw_value in month_values:
        text = str(raw_date)
        if len(text) < 7 or text[4] != "-":
            continue
        year = int(text[:4])
        month = int(text[5:7])
        if raw_value is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        current = by_year.get(year)
        if current is None or month > current[0]:
            by_year[year] = (month, value)
        if month == 12:
            by_year[year] = (12, value)
    series = []
    for year in sorted(by_year):
        series.append((year, by_year[year][1]))
    return series


def hypothesis_line(outcome_label, higher_is_better, within_band, overall) -> str:
    """One plain-language line for one outcome and one diversity score."""

    expect = "higher" if higher_is_better else "lower"
    reading = hypothesis_reading(within_band.get("coefficient"), higher_is_better)
    return (
        f"{outcome_label}: the hypothesis expects a {expect} value where diversity is higher. "
        f"Within population bands the Spearman correlation is {_coef(within_band)} "
        f"across {within_band.get('n', 0)} counties ({reading}). "
        f"The overall correlation, before banding, is {_coef(overall)} "
        f"across {overall.get('n', 0)} counties. "
        "This describes the published numbers. It does not show that diversity caused the outcome."
    )


def direct_highway_codes(code_titles) -> list[str]:
    """Item codes for county highway direct expenditure.

    ``code_titles`` is the code-and-title list printed in the government
    finance manual. A code is kept when its title names a highway and
    describes current operations or construction. Charges and
    intergovernmental items are not direct expenditure.
    """

    kept = []
    seen = set()
    for code, title in code_titles:
        text = " ".join(str(title).lower().split())
        if "highway" not in text:
            continue
        if "charge" in text or "intergov" in text or _intergovernmental(text):
            continue
        if "current oper" not in text and "construction" not in text:
            continue
        item = str(code)
        if item in seen:
            continue
        seen.add(item)
        kept.append(item)
    return kept


def _intergovernmental(text: str) -> bool:
    return " ig" in f" {text}" or "-ig" in text or text.startswith("ig")


def choose_chr_measure(rows, kind: str):
    """Pick one analytic raw-value column from dictionary rows.

    ``rows`` is ``(variable, measure, description)``. Returns
    ``(variable, measure)`` when exactly one raw-value row matches, and
    ``None`` when the published dictionary does not contain that measure.
    """

    matches = []
    for variable, measure, description in rows:
        variable_text = str(variable).strip()
        measure_text = " ".join(str(measure).split())
        description_text = " ".join(str(description).split())
        if not variable_text.endswith("_rawvalue"):
            continue
        haystack = f"{measure_text} {description_text}".lower()
        if kind == "graduation":
            if "high school graduation" in haystack and "completion" not in measure_text.lower():
                matches.append((variable_text, measure_text))
        elif kind == "violent_crime":
            if "violent crime" in haystack:
                matches.append((variable_text, measure_text))
        else:
            raise ValueError(f"Unknown measure kind: {kind}")
    found = {(variable, measure) for variable, measure in matches}
    if len(found) != 1:
        return None
    return matches[0]


def costco_quartile_shares(rows) -> dict:
    """Share of counties with a warehouse inside each diversity quarter.

    ``rows`` is a sequence of ``(name, score, has_warehouse)``. Quartile 1 is
    the lowest diversity quarter. Counties are ordered by score, then by name,
    and split with ``index * 4 // n``. Ties at a boundary follow that name
    order. ``share`` is the fraction of counties in the quarter with at least
    one warehouse.
    """

    ordered = sorted(
        ((str(name), float(score), bool(has_warehouse)) for name, score, has_warehouse in rows),
        key=lambda row: (row[1], row[0]),
    )
    count = len(ordered)
    buckets = {
        quartile: {"quartile": quartile, "n": 0, "with_warehouse": 0, "share": None}
        for quartile in (1, 2, 3, 4)
    }
    if count == 0:
        return {"n": 0, "quartiles": [buckets[quartile] for quartile in (1, 2, 3, 4)]}
    for index, (_name, _score, has_warehouse) in enumerate(ordered):
        quartile = (index * 4) // count + 1
        bucket = buckets[quartile]
        bucket["n"] += 1
        if has_warehouse:
            bucket["with_warehouse"] += 1
    for bucket in buckets.values():
        if bucket["n"]:
            bucket["share"] = bucket["with_warehouse"] / bucket["n"]
    return {"n": count, "quartiles": [buckets[quartile] for quartile in (1, 2, 3, 4)]}


def _coef(summary) -> str:
    coefficient = summary.get("coefficient") if summary else None
    if coefficient is None:
        return "not defined"
    return f"{float(coefficient):.6f}"


def _positive_counts(group_counts):
    counts = []
    for item in group_counts:
        if isinstance(item, bool) or item is None:
            continue
        try:
            number = float(item)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number > 0.0:
            counts.append(number)
    return counts


def _spearman(left, right):
    return _pearson(_average_ranks(left), _average_ranks(right))


def _average_ranks(values):
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(values):
        end = start
        while end + 1 < len(values) and values[order[end + 1]] == values[order[start]]:
            end += 1
        average = (start + 1 + end + 1) / 2.0
        for position in range(start, end + 1):
            ranks[order[position]] = average
        start = end + 1
    return ranks


def _pearson(left, right):
    count = len(left)
    if count == 0:
        return None
    left_mean = math.fsum(left) / count
    right_mean = math.fsum(right) / count
    numerator = math.fsum(
        (x_value - left_mean) * (y_value - right_mean) for x_value, y_value in zip(left, right)
    )
    left_scale = math.sqrt(math.fsum((value - left_mean) ** 2 for value in left))
    right_scale = math.sqrt(math.fsum((value - right_mean) ** 2 for value in right))
    if left_scale == 0.0 or right_scale == 0.0:
        return None
    return numerator / (left_scale * right_scale)
