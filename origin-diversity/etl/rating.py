"""Origin-diversity rating and within-set association.

The rating uses only counts of people who were not born in the community,
grouped by the origin community in the published table. It does not use
people born in the community, and it does not claim that origin diversity
caused any outcome placed beside it.
"""

from __future__ import annotations

import math


def diversity_rating(origin_counts) -> float:
    """Effective number of origin communities among people born elsewhere.

    ``origin_counts`` is a sequence of counts, one per origin community.
    Non-positive and non-numeric entries are ignored. No newcomers returns
    0, the bottom of the scale. Every newcomer from one origin returns 1.
    An even split across ``k`` origins returns ``k``. The same counts always
    return the same number. Order does not matter.

    The value is the Hill number of order 1: the exponential of the Shannon
    entropy of the origin shares. Equal shares across four origins score 4.
    A lopsided mix scores closer to 1 than an even mix of the same people.
    """

    counts = _positive_counts(origin_counts)
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


def association_summary(pairs) -> dict:
    """Spearman association between a rating and an outcome.

    ``pairs`` is a sequence of ``(rating, outcome)`` numbers. The direction
    is ``"positive"`` when higher ratings sit with higher outcomes,
    ``"negative"`` when they sit with lower outcomes, and ``"none"`` when
    the rank correlation is undefined or zero. Ties use average ranks.
    """

    clean = []
    for rating, outcome in pairs:
        clean.append((float(rating), float(outcome)))
    result = {"n": len(clean), "coefficient": None, "direction": "none"}
    if len(clean) < 2:
        return result
    coefficient = _spearman(
        [rating for rating, _outcome in clean],
        [outcome for _rating, outcome in clean],
    )
    result["coefficient"] = coefficient
    if coefficient is None or coefficient == 0.0:
        result["direction"] = "none"
    elif coefficient > 0.0:
        result["direction"] = "positive"
    else:
        result["direction"] = "negative"
    return result


def describe_association(community_label, outcome_label, summary) -> str:
    """Plain-language association line for one set. Descriptive only."""

    direction = summary["direction"]
    coefficient = summary["coefficient"]
    if coefficient is None:
        coefficient_text = "not defined"
    else:
        coefficient_text = f"{coefficient:.6f}"
    if direction == "positive":
        lining = f"higher origin diversity sits with higher {outcome_label}"
    elif direction == "negative":
        lining = f"higher origin diversity sits with lower {outcome_label}"
    else:
        lining = (
            f"origin diversity and {outcome_label} do not line up in either direction"
        )
    return (
        f"Among {community_label}, the direction is {direction}: {lining}. "
        f"Spearman rank correlation is {coefficient_text} across {summary['n']} communities. "
        "This describes the published numbers. It does not show that people born elsewhere caused the outcome."
    )


def rank_within_sets(rows):
    """Rank each set on its own. Rank 1 is the highest rating in that set.

    Rows need ``community``, ``set``, and ``rating``. The returned rows are
    new dicts with ``rank_in_set``. A high rating in one set does not change
    the rank of any row in another set. Ties break by community name, so the
    same input always produces the same ranks.
    """

    grouped = {}
    for row in rows:
        grouped.setdefault(row["set"], []).append(dict(row))
    ranked = []
    for set_name in sorted(grouped):
        members = grouped[set_name]
        members.sort(key=lambda row: (-float(row["rating"]), row["community"]))
        for index, row in enumerate(members, start=1):
            row["rank_in_set"] = index
            ranked.append(row)
    return ranked


def _positive_counts(origin_counts):
    counts = []
    for item in origin_counts:
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
        while (
            end + 1 < len(values)
            and values[order[end + 1]] == values[order[start]]
        ):
            end += 1
        average = (start + 1 + end + 1) / 2.0
        for position in range(start, end + 1):
            ranks[order[position]] = average
        start = end + 1
    return ranks


def _pearson(left, right):
    count = len(left)
    left_mean = math.fsum(left) / count
    right_mean = math.fsum(right) / count
    numerator = math.fsum(
        (x_value - left_mean) * (y_value - right_mean)
        for x_value, y_value in zip(left, right)
    )
    left_scale = math.sqrt(math.fsum((value - left_mean) ** 2 for value in left))
    right_scale = math.sqrt(math.fsum((value - right_mean) ** 2 for value in right))
    if left_scale == 0.0 or right_scale == 0.0:
        return None
    return numerator / (left_scale * right_scale)
