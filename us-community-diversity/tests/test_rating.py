"""Calls the shipped rating, association, and Costco functions."""

import unittest

from etl.rating import (
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
    pooled_within_band_association,
    year_end_series,
)


class DiversityRatingTests(unittest.TestCase):
    def test_one_group_scores_lower_than_the_same_count_spread_out(self):
        single_group = diversity_rating([120, 0, 0])
        several_groups = diversity_rating([40, 40, 40])
        self.assertLess(single_group, several_groups)
        self.assertEqual(single_group, 1.0)
        self.assertAlmostEqual(several_groups, 3.0)

    def test_empty_counts_sit_at_the_floor(self):
        floor = diversity_rating([])
        self.assertEqual(floor, 0.0)
        self.assertEqual(floor, diversity_rating([0, 0, 0]))
        self.assertLess(floor, diversity_rating([5]))

    def test_the_same_counts_return_the_same_rating(self):
        counts = [3, 9, 1, 0, 4]
        first = diversity_rating(counts)
        second = diversity_rating(list(counts))
        self.assertEqual(first, second)
        self.assertEqual(first, diversity_rating(tuple(reversed(counts))))


class AssociationTests(unittest.TestCase):
    def test_fixed_table_reports_the_known_positive_direction(self):
        summary = association_summary([(1, 10), (2, 20), (3, 30), (4, 40)])
        self.assertEqual(summary["direction"], "positive")
        self.assertEqual(summary["n"], 4)
        self.assertAlmostEqual(summary["coefficient"], 1.0)

    def test_higher_and_lower_flip_the_hypothesis_reading(self):
        self.assertEqual(hypothesis_reading(0.4, True), LINES_UP)
        self.assertEqual(hypothesis_reading(0.4, False), LINES_AGAINST)
        self.assertEqual(hypothesis_reading(-0.4, False), LINES_UP)
        self.assertEqual(hypothesis_reading(-0.4, True), LINES_AGAINST)

    def test_a_tiny_coefficient_has_no_clear_direction(self):
        self.assertEqual(hypothesis_reading(0.04, True), NO_CLEAR)
        self.assertEqual(hypothesis_reading(-0.049, False), NO_CLEAR)
        self.assertEqual(hypothesis_reading(None, True), NO_CLEAR)
        self.assertEqual(hypothesis_reading(0.05, True), LINES_UP)


class PopulationBandTests(unittest.TestCase):
    def test_pooled_bands_do_not_copy_a_size_only_national_correlation(self):
        # Inside each band the outcome falls as the score rises. Nationally
        # the correlation is positive only because the large-county band sits
        # higher on both measures.
        records = [
            ("50-150k", 1, 4),
            ("50-150k", 2, 3),
            ("50-150k", 3, 2),
            ("50-150k", 4, 1),
            ("500k+", 10, 14),
            ("500k+", 11, 13),
            ("500k+", 12, 12),
            ("500k+", 13, 11),
        ]
        national = association_summary((score, outcome) for _band, score, outcome in records)
        pooled = pooled_within_band_association(records)
        self.assertEqual(national["direction"], "positive")
        self.assertGreater(national["coefficient"], 0.0)
        self.assertEqual(pooled["direction"], "negative")
        self.assertLess(pooled["coefficient"], 0.0)
        self.assertNotAlmostEqual(pooled["coefficient"], national["coefficient"])
        self.assertEqual(pooled["n"], 8)
        line = hypothesis_line("unemployment rate", False, pooled, national)
        self.assertIn("expects a lower value", line)
        self.assertIn(LINES_UP, line)
        self.assertIn("does not show that diversity caused", line)


class CostcoQuartileTests(unittest.TestCase):
    def test_fixed_counties_produce_known_quartile_shares(self):
        rows = [
            ("Alpha", 1, False),
            ("Bravo", 2, False),
            ("Charlie", 3, False),
            ("Delta", 4, False),
            ("Echo", 5, True),
            ("Foxtrot", 6, True),
            ("Golf", 7, True),
            ("Hotel", 8, True),
        ]
        shares = costco_quartile_shares(rows)
        by_quarter = {item["quartile"]: item for item in shares["quartiles"]}
        self.assertEqual(shares["n"], 8)
        self.assertEqual(by_quarter[1]["share"], 0.0)
        self.assertEqual(by_quarter[2]["share"], 0.0)
        self.assertEqual(by_quarter[3]["share"], 1.0)
        self.assertEqual(by_quarter[4]["share"], 1.0)
        self.assertEqual(by_quarter[4]["with_warehouse"], 2)
        self.assertEqual(by_quarter[4]["n"], 2)


class ExplorerTests(unittest.TestCase):
    def test_a_fixed_band_produces_a_known_share_below(self):
        self.assertEqual(band_share_below([10, 20, 30, 40], 30), 50.0)
        self.assertEqual(band_share_below([5, 5, 5], 5), 0.0)
        self.assertIsNone(band_share_below([], 1))
        self.assertEqual(band_share_below([10, 20, 30, 40], 30), band_share_below([40, 10, 30, 20], 30))

    def test_year_end_uses_december_except_for_the_latest_partial_year(self):
        series = year_end_series(
            [
                ("2019-12-31", 90),
                ("2020-06-30", 95),
                ("2020-12-31", 100),
                ("2021-03-31", 110),
                ("2021-10-31", 130),
                ("2021-11-30", None),
            ]
        )
        self.assertEqual(series, [(2019, 90.0), (2020, 100.0), (2021, 130.0)])


class SourceRuleTests(unittest.TestCase):
    def test_highway_codes_keep_direct_spending_only(self):
        titles = [
            ("A44", "Regular Highway Charges"),
            ("A45", "Toll Highway Charges"),
            ("B46", "Federal IG Highways"),
            ("D46", "Local IG Highways"),
            ("E44", "Regular Highways-Current Oper"),
            ("E45", "Toll Highways-Current Oper"),
            ("F44", "Regular Highways-Construction"),
            ("F45", "Toll Highways-Construction"),
            ("M44", "Regular Highways-IG-Local Nec"),
            ("E62", "Police Protection-Current Oper"),
        ]
        self.assertEqual(direct_highway_codes(titles), ["E44", "E45", "F44", "F45"])

    def test_graduation_column_comes_from_the_dictionary_label(self):
        rows = [
            (
                "v168_rawvalue",
                "High School Completion raw value",
                "Percentage of adults ages 25 and over with a high school diploma or equivalent.",
            ),
            (
                "v021_rawvalue",
                "High School Graduation raw value",
                "Percentage of ninth-grade cohort that graduates in four years.",
            ),
        ]
        self.assertEqual(
            choose_chr_measure(rows, "graduation"),
            ("v021_rawvalue", "High School Graduation raw value"),
        )

    def test_missing_violent_crime_measure_is_not_invented(self):
        rows = [
            ("v043_numerator", "Violent crime numerator", "Not the rate."),
            ("v015_rawvalue", "Homicides raw value", "Number of deaths due to homicide per 100,000 population."),
        ]
        self.assertIsNone(choose_chr_measure(rows, "violent_crime"))


if __name__ == "__main__":
    unittest.main()
