"""Calls the shipped rating and association functions."""

import unittest

from etl.build_communities import select_origin_columns
from etl.rating import (
    association_summary,
    describe_association,
    diversity_rating,
    rank_within_sets,
)


class DiversityRatingTests(unittest.TestCase):
    def test_one_origin_scores_lower_than_the_same_count_spread_out(self):
        single_origin = diversity_rating([120, 0, 0])
        several_origins = diversity_rating([40, 40, 40])
        self.assertLess(single_origin, several_origins)
        self.assertEqual(single_origin, 1.0)
        self.assertAlmostEqual(several_origins, 3.0)

    def test_zero_newcomers_score_at_the_floor(self):
        floor = diversity_rating([])
        self.assertEqual(floor, 0.0)
        self.assertEqual(floor, diversity_rating([0, 0, 0]))
        self.assertLess(floor, diversity_rating([5]))
        self.assertLess(floor, diversity_rating([2, 2, 2]))

    def test_the_same_counts_return_the_same_rating(self):
        counts = [3, 9, 1, 0, 4]
        first = diversity_rating(counts)
        second = diversity_rating(list(counts))
        self.assertEqual(first, second)
        self.assertEqual(first, diversity_rating(tuple(reversed(counts))))

    def test_even_split_matches_the_number_of_origins(self):
        self.assertAlmostEqual(diversity_rating([10, 10, 10, 10]), 4.0)


class AssociationTests(unittest.TestCase):
    def test_fixed_table_reports_the_known_positive_direction(self):
        table = [(1, 10), (2, 20), (3, 30), (4, 40)]
        summary = association_summary(table)
        self.assertEqual(summary["direction"], "positive")
        self.assertEqual(summary["n"], 4)
        self.assertAlmostEqual(summary["coefficient"], 1.0)
        sentence = describe_association(
            "US states", "median household income", summary
        )
        self.assertIn("direction is positive", sentence)
        self.assertIn("1.000000", sentence)
        self.assertIn("does not show that people born elsewhere caused", sentence)

    def test_opposite_table_reports_a_negative_direction(self):
        summary = association_summary([(1, 40), (2, 30), (3, 20), (4, 10)])
        self.assertEqual(summary["direction"], "negative")


class SeparateRankingTests(unittest.TestCase):
    def test_each_set_starts_its_own_ranking(self):
        rows = [
            {"community": "Alpha", "set": "US state", "rating": 5, "outcome": 1},
            {"community": "Beta", "set": "US state", "rating": 1, "outcome": 2},
            {"community": "Cairo", "set": "outside the US", "rating": 9, "outcome": 3},
            {"community": "Delta", "set": "outside the US", "rating": 2, "outcome": 4},
        ]
        ranked = rank_within_sets(rows)
        by_place = {
            (row["set"], row["community"]): row["rank_in_set"] for row in ranked
        }
        self.assertEqual(by_place[("US state", "Alpha")], 1)
        self.assertEqual(by_place[("US state", "Beta")], 2)
        self.assertEqual(by_place[("outside the US", "Cairo")], 1)
        self.assertEqual(by_place[("outside the US", "Delta")], 2)
        self.assertEqual([row["rank_in_set"] for row in ranked].count(1), 2)


class OriginColumnTests(unittest.TestCase):
    def test_groups_and_nested_details_are_not_added_twice(self):
        shell = "\n".join(
            [
                "B05006|1.0|0|B05006_001|Total:|t|u|int",
                "B05006|2.0|1|B05006_002|Europe:|t|u|int",
                "B05006|3.0|2|B05006_003|Denmark|t|u|int",
                "B05006|4.0|2|B05006_004|Portugal|t|u|int",
                "B05006|5.0|3|B05006_005|Azores Islands|t|u|int",
                "B05006|6.0|2|B05006_006|United Kingdom:|t|u|int",
                "B05006|7.0|3|B05006_007|England|t|u|int",
                "B05006|8.0|3|B05006_008|Scotland|t|u|int",
            ]
        )
        self.assertEqual(
            select_origin_columns(shell),
            ["B05006_E003", "B05006_E004", "B05006_E007", "B05006_E008"],
        )


if __name__ == "__main__":
    unittest.main()
