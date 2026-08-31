import unittest

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
)
from geovaris_rf.clutter_height import (
    CLUTTER_HEIGHT_UNITS,
    GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_NAME,
    GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_SOURCE,
    GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_VERSION,
    GEOVARIS_DEFAULT_CLUTTER_HEIGHTS_M,
    GOVERNED_CLUTTER_CATEGORIES,
    GOVERNED_NLCD_CLASSES,
    apply_clutter_height_overrides,
    build_clutter_height_class,
    build_clutter_height_profile,
    build_geovaris_default_clutter_height_profile,
    build_governed_clutter_height_profile,
)


def build_complete_category_heights() -> dict[
    GeoVarisClutterClass,
    float,
]:
    """Return explicit test-only clutter assumptions.

    These values exist only for unit testing and are not GeoVaris
    production defaults.
    """

    return {
        GeoVarisClutterClass.WATER: 0.0,
        GeoVarisClutterClass.OPEN: 1.0,
        GeoVarisClutterClass.AGRICULTURE: 2.0,
        GeoVarisClutterClass.DEVELOPED_OPEN: 3.0,
        GeoVarisClutterClass.SUBURBAN: 4.0,
        GeoVarisClutterClass.DENSE_SUBURBAN: 5.0,
        GeoVarisClutterClass.URBAN: 6.0,
        GeoVarisClutterClass.FOREST: 7.0,
        GeoVarisClutterClass.WETLAND: 8.0,
    }


class ClutterHeightTests(unittest.TestCase):
    def test_build_clutter_height_class(
        self,
    ) -> None:
        clutter_class = build_clutter_height_class(
            nlcd_class_value=41,
            nlcd_class_name=(
                "Deciduous Forest"
            ),
            clutter_category=(
                GeoVarisClutterClass.FOREST
            ),
            height_m=15.0,
        )

        self.assertEqual(
            clutter_class.nlcd_class_value,
            41,
        )

        self.assertEqual(
            clutter_class.nlcd_class_name,
            "Deciduous Forest",
        )

        self.assertEqual(
            clutter_class.clutter_category,
            GeoVarisClutterClass.FOREST,
        )

        self.assertEqual(
            clutter_class.height_m,
            15.0,
        )

    def test_negative_height_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            build_clutter_height_class(
                nlcd_class_value=41,
                nlcd_class_name=(
                    "Deciduous Forest"
                ),
                clutter_category=(
                    GeoVarisClutterClass.FOREST
                ),
                height_m=-1.0,
            )

    def test_empty_class_name_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            build_clutter_height_class(
                nlcd_class_value=41,
                nlcd_class_name="",
                clutter_category=(
                    GeoVarisClutterClass.FOREST
                ),
                height_m=15.0,
            )

    def test_profile_preserves_metadata(
        self,
    ) -> None:
        clutter_class = build_clutter_height_class(
            nlcd_class_value=21,
            nlcd_class_name=(
                "Developed Open Space"
            ),
            clutter_category=(
                GeoVarisClutterClass.DEVELOPED_OPEN
            ),
            height_m=2.0,
        )

        profile = build_clutter_height_profile(
            name="Test Profile",
            version="test-1",
            source=(
                "Unit-test assumptions"
            ),
            classes=[
                clutter_class
            ],
        )

        self.assertEqual(
            profile.name,
            "Test Profile",
        )

        self.assertEqual(
            profile.version,
            "test-1",
        )

        self.assertEqual(
            profile.source,
            "Unit-test assumptions",
        )

        self.assertEqual(
            profile.units,
            CLUTTER_HEIGHT_UNITS,
        )

    def test_profile_rejects_duplicate_class_values(
        self,
    ) -> None:
        first = build_clutter_height_class(
            nlcd_class_value=21,
            nlcd_class_name=(
                "Developed Open Space"
            ),
            clutter_category=(
                GeoVarisClutterClass.DEVELOPED_OPEN
            ),
            height_m=2.0,
        )

        second = build_clutter_height_class(
            nlcd_class_value=21,
            nlcd_class_name="Duplicate",
            clutter_category=(
                GeoVarisClutterClass.DEVELOPED_OPEN
            ),
            height_m=3.0,
        )

        with self.assertRaisesRegex(
            ValueError,
            "Duplicate NLCD class value",
        ):
            build_clutter_height_profile(
                name="Test",
                version="test-1",
                source="Unit test",
                classes=[
                    first,
                    second,
                ],
            )

    def test_get_height_for_known_class(
        self,
    ) -> None:
        profile = build_clutter_height_profile(
            name="Test",
            version="test-1",
            source="Unit test",
            classes=[
                build_clutter_height_class(
                    nlcd_class_value=41,
                    nlcd_class_name=(
                        "Deciduous Forest"
                    ),
                    clutter_category=(
                        GeoVarisClutterClass.FOREST
                    ),
                    height_m=15.0,
                )
            ],
        )

        self.assertEqual(
            profile.get_height_m(
                41
            ),
            15.0,
        )

    def test_unknown_class_is_rejected(
        self,
    ) -> None:
        profile = build_clutter_height_profile(
            name="Test",
            version="test-1",
            source="Unit test",
            classes=[
                build_clutter_height_class(
                    nlcd_class_value=41,
                    nlcd_class_name=(
                        "Deciduous Forest"
                    ),
                    clutter_category=(
                        GeoVarisClutterClass.FOREST
                    ),
                    height_m=15.0,
                )
            ],
        )

        with self.assertRaises(
            KeyError
        ):
            profile.get_height_m(
                42
            )

    def test_governed_category_set_has_nine_categories(
        self,
    ) -> None:
        self.assertEqual(
            len(
                GOVERNED_CLUTTER_CATEGORIES
            ),
            9,
        )

    def test_governed_nlcd_set_has_fifteen_classes(
        self,
    ) -> None:
        self.assertEqual(
            len(
                GOVERNED_NLCD_CLASSES
            ),
            15,
        )

    def test_governed_profile_expands_all_nlcd_classes(
        self,
    ) -> None:
        profile = build_governed_clutter_height_profile(
            name="Test Governed Profile",
            version="test-1",
            source="Unit-test assumptions",
            category_heights_m=(
                build_complete_category_heights()
            ),
        )

        self.assertEqual(
            len(
                profile.classes
            ),
            15,
        )

        for nlcd_class in GOVERNED_NLCD_CLASSES:
            self.assertIn(
                int(nlcd_class),
                profile.classes,
            )

    def test_forest_category_expands_to_three_nlcd_classes(
        self,
    ) -> None:
        profile = build_governed_clutter_height_profile(
            name="Test Governed Profile",
            version="test-1",
            source="Unit-test assumptions",
            category_heights_m=(
                build_complete_category_heights()
            ),
        )

        self.assertEqual(
            profile.get_height_m(
                41
            ),
            7.0,
        )

        self.assertEqual(
            profile.get_height_m(
                42
            ),
            7.0,
        )

        self.assertEqual(
            profile.get_height_m(
                43
            ),
            7.0,
        )

    def test_open_category_expands_to_multiple_nlcd_classes(
        self,
    ) -> None:
        profile = build_governed_clutter_height_profile(
            name="Test Governed Profile",
            version="test-1",
            source="Unit-test assumptions",
            category_heights_m=(
                build_complete_category_heights()
            ),
        )

        self.assertEqual(
            profile.get_height_m(
                31
            ),
            1.0,
        )

        self.assertEqual(
            profile.get_height_m(
                52
            ),
            1.0,
        )

        self.assertEqual(
            profile.get_height_m(
                71
            ),
            1.0,
        )

    def test_missing_category_is_rejected(
        self,
    ) -> None:
        heights = build_complete_category_heights()

        del heights[
            GeoVarisClutterClass.URBAN
        ]

        with self.assertRaisesRegex(
            ValueError,
            "missing required GeoVaris categories",
        ):
            build_governed_clutter_height_profile(
                name="Test",
                version="test-1",
                source="Unit test",
                category_heights_m=heights,
            )

    def test_invalid_category_is_rejected(
        self,
    ) -> None:
        heights = dict(
            build_complete_category_heights()
        )

        heights[
            "unsupported-category"
        ] = 10.0

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported GeoVaris clutter category",
        ):
            build_governed_clutter_height_profile(
                name="Test",
                version="test-1",
                source="Unit test",
                category_heights_m=heights,
            )

    def test_override_changes_selected_class(
        self,
    ) -> None:
        base_profile = build_governed_clutter_height_profile(
            name="Base",
            version="test-1",
            source="Unit test",
            category_heights_m=(
                build_complete_category_heights()
            ),
        )

        override_profile = apply_clutter_height_overrides(
            base_profile=base_profile,
            profile_name=(
                "Customer Override"
            ),
            profile_version="test-2",
            source=(
                "Customer override"
            ),
            overrides_m={
                41: 20.0,
            },
        )

        self.assertEqual(
            override_profile.get_height_m(
                41
            ),
            20.0,
        )

        self.assertEqual(
            override_profile.get_height_m(
                42
            ),
            7.0,
        )

        self.assertEqual(
            base_profile.get_height_m(
                41
            ),
            7.0,
        )

    def test_override_unknown_class_rejected(
        self,
    ) -> None:
        base_profile = build_governed_clutter_height_profile(
            name="Base",
            version="test-1",
            source="Unit test",
            category_heights_m=(
                build_complete_category_heights()
            ),
        )

        with self.assertRaisesRegex(
            ValueError,
            "unknown NLCD class values",
        ):
            apply_clutter_height_overrides(
                base_profile=base_profile,
                profile_name=(
                    "Customer Override"
                ),
                profile_version="test-2",
                source=(
                    "Customer override"
                ),
                overrides_m={
                    99: 10.0,
                },
            )

    def test_default_profile_metadata(
        self,
    ) -> None:
        profile = (
            build_geovaris_default_clutter_height_profile()
        )

        self.assertEqual(
            profile.name,
            GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_NAME,
        )

        self.assertEqual(
            profile.version,
            GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_VERSION,
        )

        self.assertEqual(
            profile.source,
            GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_SOURCE,
        )

        self.assertEqual(
            profile.units,
            "m",
        )

    def test_default_profile_has_nine_category_values(
        self,
    ) -> None:
        self.assertEqual(
            len(
                GEOVARIS_DEFAULT_CLUTTER_HEIGHTS_M
            ),
            9,
        )

    def test_default_profile_category_heights(
        self,
    ) -> None:
        expected = {
            GeoVarisClutterClass.WATER: 0.0,
            GeoVarisClutterClass.OPEN: 0.0,
            GeoVarisClutterClass.AGRICULTURE: 4.0,
            GeoVarisClutterClass.DEVELOPED_OPEN: 4.0,
            GeoVarisClutterClass.SUBURBAN: 10.0,
            GeoVarisClutterClass.DENSE_SUBURBAN: 12.0,
            GeoVarisClutterClass.URBAN: 15.0,
            GeoVarisClutterClass.FOREST: 15.0,
            GeoVarisClutterClass.WETLAND: 4.0,
        }

        self.assertEqual(
            dict(
                GEOVARIS_DEFAULT_CLUTTER_HEIGHTS_M
            ),
            expected,
        )

    def test_default_profile_expands_to_all_fifteen_nlcd_classes(
        self,
    ) -> None:
        profile = (
            build_geovaris_default_clutter_height_profile()
        )

        self.assertEqual(
            len(
                profile.classes
            ),
            15,
        )

        for nlcd_class in GOVERNED_NLCD_CLASSES:
            self.assertIn(
                int(nlcd_class),
                profile.classes,
            )

    def test_default_profile_expansion_uses_category_values(
        self,
    ) -> None:
        profile = (
            build_geovaris_default_clutter_height_profile()
        )

        self.assertEqual(
            profile.get_height_m(
                11
            ),
            0.0,
        )

        self.assertEqual(
            profile.get_height_m(
                22
            ),
            10.0,
        )

        self.assertEqual(
            profile.get_height_m(
                23
            ),
            12.0,
        )

        self.assertEqual(
            profile.get_height_m(
                24
            ),
            15.0,
        )

        self.assertEqual(
            profile.get_height_m(
                41
            ),
            15.0,
        )

        self.assertEqual(
            profile.get_height_m(
                81
            ),
            4.0,
        )

        self.assertEqual(
            profile.get_height_m(
                90
            ),
            4.0,
        )

    def test_default_height_mapping_is_read_only(
        self,
    ) -> None:
        with self.assertRaises(
            TypeError
        ):
            GEOVARIS_DEFAULT_CLUTTER_HEIGHTS_M[
                GeoVarisClutterClass.FOREST
            ] = 99.0


if __name__ == "__main__":
    unittest.main()
    