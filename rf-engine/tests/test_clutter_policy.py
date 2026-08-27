import unittest

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
)
from geovaris_rf.clutter_policy import (
    ClutterApplicabilityStatus,
    evaluate_p2108_applicability,
)


class ClutterPolicyTests(
    unittest.TestCase
):
    def test_suburban_classes_are_applicable(
        self,
    ):
        for clutter_class in (
            GeoVarisClutterClass.SUBURBAN,
            GeoVarisClutterClass.DENSE_SUBURBAN,
            GeoVarisClutterClass.URBAN,
        ):
            with self.subTest(
                clutter_class=clutter_class
            ):
                result = (
                    evaluate_p2108_applicability(
                        clutter_class
                    )
                )

                self.assertEqual(
                    result.status,
                    ClutterApplicabilityStatus.APPLICABLE,
                )

                self.assertIsNotNone(
                    result.model_name
                )

    def test_forest_requires_future_model(
        self,
    ):
        result = (
            evaluate_p2108_applicability(
                GeoVarisClutterClass.FOREST
            )
        )

        self.assertEqual(
            result.status,
            ClutterApplicabilityStatus.FUTURE_MODEL,
        )

        self.assertIsNone(
            result.model_name
        )

    def test_developed_open_is_not_applicable(
        self,
    ):
        result = (
            evaluate_p2108_applicability(
                GeoVarisClutterClass.DEVELOPED_OPEN
            )
        )

        self.assertEqual(
            result.status,
            ClutterApplicabilityStatus.NOT_APPLICABLE,
        )

    def test_non_p2108_classes_are_not_applicable(
        self,
    ):
        for clutter_class in (
            GeoVarisClutterClass.WATER,
            GeoVarisClutterClass.OPEN,
            GeoVarisClutterClass.AGRICULTURE,
            GeoVarisClutterClass.WETLAND,
        ):
            with self.subTest(
                clutter_class=clutter_class
            ):
                result = (
                    evaluate_p2108_applicability(
                        clutter_class
                    )
                )

                self.assertEqual(
                    result.status,
                    ClutterApplicabilityStatus.NOT_APPLICABLE,
                )

                self.assertIsNone(
                    result.model_name
                )

    def test_invalid_clutter_class_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            evaluate_p2108_applicability(
                "urban"  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()