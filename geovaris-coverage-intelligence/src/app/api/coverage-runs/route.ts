import {
    NextRequest,
    NextResponse,
} from "next/server";

import {
    getGeoVarisAuthContext,
} from "@/lib/auth-context";

import { sql } from "@/lib/db";

const FREE_SPACE_MODEL =
    "free_space_test";

const NTIA_ITM_MODEL =
    "ntia_itm";

const RAPID_COVERAGE_MODEL =
    "rapid_coverage";

const COVERAGE_RUN_CREATE_ROLES =
    new Set([
        "customer_admin",
        "engineer",
    ]);

const RAPID_COVERAGE_MODEL_VERSION =
    "demo-2026.1";

const RAPID_COVERAGE_RESOLUTION_M =
    30;

const RAPID_CLUTTER_SOURCE =
    "USGS/MRLC Annual NLCD Land Cover";

const RAPID_CLUTTER_VERSION =
    "2025 C1V2";

const RAPID_CLUTTER_MODEL =
    "GeoVaris Default Clutter Height Profile";

const RAPID_CLUTTER_MODEL_VERSION =
    "2026.1-demo";

const P2108_CLUTTER_MODEL =
    "ITU-R P.2108 Terrestrial Statistical Clutter";

const P2108_CLUTTER_MODEL_VERSION =
    "P.2108-1 (09/2021) §3.2";

const P2108_CORRECTION_END =
    "receiver";

type CreateCoverageRunRequest = {
    scenarioId?: string;
    runMethod?: string;
};

export async function POST(
    request: NextRequest,
) {
    try {
        const authContext =
            await getGeoVarisAuthContext();

        if (!authContext) {
            return NextResponse.json(
                {
                    error:
                        "Authentication is required.",
                },
                {
                    status: 401,
                },
            );
        }

        const body =
            (await request.json()) as CreateCoverageRunRequest;

        const scenarioId =
            body.scenarioId;

        const runMethod =
            body.runMethod?.trim() ??
            null;

        if (!scenarioId) {
            return NextResponse.json(
                {
                    error:
                        "Scenario is required.",
                },
                {
                    status: 400,
                },
            );
        }

        if (
            runMethod !== null &&
            runMethod !==
                RAPID_COVERAGE_MODEL
        ) {
            return NextResponse.json(
                {
                    error:
                        "Unsupported coverage run method.",
                },
                {
                    status: 400,
                },
            );
        }

        /*
         * Resolve the scenario only within the caller's
         * authorized tenant scope.
         *
         * GeoVaris Admin may run any scenario.
         *
         * Customer users may create coverage runs only
         * for scenarios belonging to customers where they
         * hold a write-capable tenant role.
         *
         * The browser supplies only scenarioId and an
         * optional run methodology. customer_id and all
         * calculation inputs are resolved on the server.
         */
        let scenarios;

        if (
            authContext.isGeoVarisAdmin
        ) {
            scenarios =
                await sql`
                    SELECT
                        sc.id AS scenario_id,
                        sc.customer_id,

                        sc.frequency_mhz,
                        sc.eirp_watts,

                        sc.antenna_height_m,
                        sc.antenna_gain_dbi,

                        sc.receiver_height_m,
                        sc.receiver_threshold_dbm,

                        sc.calculation_radius_m,
                        sc.resolution_m,

                        sc.propagation_model,

                        sc.itm_climate,
                        sc.itm_polarization,
                        sc.itm_variability_mode,
                        sc.itm_surface_refractivity,
                        sc.itm_dielectric_constant,
                        sc.itm_conductivity_s_per_m,
                        sc.itm_confidence,
                        sc.itm_reliability,

                        sc.clutter_source,
                        sc.clutter_version,
                        sc.clutter_model,
                        sc.clutter_model_version,
                        sc.clutter_percentage_locations,
                        sc.clutter_correction_end,

                        s.latitude AS site_latitude,
                        s.longitude AS site_longitude,

                        s.ground_elevation_m,
                        s.ground_elevation_source,
                        s.ground_elevation_version,
                        s.ground_elevation_horizontal_crs,
                        s.ground_elevation_vertical_datum,
                        s.ground_elevation_units,
                        s.ground_elevation_resolution_m

                    FROM scenarios sc

                    JOIN sites s
                        ON s.id =
                            sc.site_id
                        AND s.customer_id =
                            sc.customer_id

                    WHERE sc.id =
                        ${scenarioId}

                    LIMIT 1;
                `;
        } else {
            const writableCustomerIds =
                authContext.customerMemberships
                    .filter(
                        (membership) =>
                            COVERAGE_RUN_CREATE_ROLES.has(
                                membership.role,
                            ),
                    )
                    .map(
                        (membership) =>
                            membership.customerId,
                    );

            if (
                writableCustomerIds.length === 0
            ) {
                return NextResponse.json(
                    {
                        error:
                            "Scenario was not found.",
                    },
                    {
                        status: 404,
                    },
                );
            }

            scenarios =
                await sql`
                    SELECT
                        sc.id AS scenario_id,
                        sc.customer_id,

                        sc.frequency_mhz,
                        sc.eirp_watts,

                        sc.antenna_height_m,
                        sc.antenna_gain_dbi,

                        sc.receiver_height_m,
                        sc.receiver_threshold_dbm,

                        sc.calculation_radius_m,
                        sc.resolution_m,

                        sc.propagation_model,

                        sc.itm_climate,
                        sc.itm_polarization,
                        sc.itm_variability_mode,
                        sc.itm_surface_refractivity,
                        sc.itm_dielectric_constant,
                        sc.itm_conductivity_s_per_m,
                        sc.itm_confidence,
                        sc.itm_reliability,

                        sc.clutter_source,
                        sc.clutter_version,
                        sc.clutter_model,
                        sc.clutter_model_version,
                        sc.clutter_percentage_locations,
                        sc.clutter_correction_end,

                        s.latitude AS site_latitude,
                        s.longitude AS site_longitude,

                        s.ground_elevation_m,
                        s.ground_elevation_source,
                        s.ground_elevation_version,
                        s.ground_elevation_horizontal_crs,
                        s.ground_elevation_vertical_datum,
                        s.ground_elevation_units,
                        s.ground_elevation_resolution_m

                    FROM scenarios sc

                    JOIN sites s
                        ON s.id =
                            sc.site_id
                        AND s.customer_id =
                            sc.customer_id

                    WHERE sc.id =
                        ${scenarioId}

                      AND sc.customer_id =
                        ANY(
                            ${writableCustomerIds}::uuid[]
                        )

                    LIMIT 1;
                `;
        }

        const scenario =
            scenarios[0];

        /*
         * A nonexistent scenario and a scenario outside
         * the caller's authorized tenant scope intentionally
         * return the same response.
         */
        if (!scenario) {
            return NextResponse.json(
                {
                    error:
                        "Scenario was not found.",
                },
                {
                    status: 404,
                },
            );
        }

        /*
         * Rapid Coverage is a distinct calculation methodology.
         *
         * The saved scenario remains the engineering-input record,
         * while the coverage run snapshots the actual method used
         * for this calculation.
         *
         * Rapid Coverage uses:
         *
         * - 30 m working resolution
         * - governed NLCD land-cover lineage
         * - governed GeoVaris clutter-height profile
         * - no ITM assumptions
         * - no P.2108 statistical clutter correction
         */
        if (
            runMethod ===
            RAPID_COVERAGE_MODEL
        ) {
            const runs =
                await sql`
                    INSERT INTO coverage_runs (
                        customer_id,
                        scenario_id,
                        status,

                        site_latitude,
                        site_longitude,
                        site_ground_elevation_m,

                        frequency_mhz,
                        eirp_watts,

                        antenna_height_m,
                        antenna_gain_dbi,

                        receiver_height_m,
                        receiver_threshold_dbm,

                        calculation_radius_m,
                        resolution_m,

                        propagation_model,
                        propagation_model_version,

                        itm_climate,
                        itm_polarization,
                        itm_variability_mode,
                        itm_surface_refractivity,
                        itm_dielectric_constant,
                        itm_conductivity_s_per_m,
                        itm_confidence,
                        itm_reliability,

                        clutter_source,
                        clutter_version,
                        clutter_model,
                        clutter_model_version,
                        clutter_percentage_locations,
                        clutter_correction_end,

                        dem_source,
                        dem_version,
                        dem_horizontal_crs,
                        dem_vertical_datum,
                        dem_units,
                        dem_resolution_m
                    )
                    VALUES (
                        ${scenario.customer_id},
                        ${scenario.scenario_id},
                        'pending',

                        ${scenario.site_latitude},
                        ${scenario.site_longitude},
                        ${scenario.ground_elevation_m},

                        ${scenario.frequency_mhz},
                        ${scenario.eirp_watts},

                        ${scenario.antenna_height_m},
                        ${scenario.antenna_gain_dbi},

                        ${scenario.receiver_height_m},
                        ${scenario.receiver_threshold_dbm},

                        ${scenario.calculation_radius_m},
                        ${RAPID_COVERAGE_RESOLUTION_M},

                        ${RAPID_COVERAGE_MODEL},
                        ${RAPID_COVERAGE_MODEL_VERSION},

                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,

                        ${RAPID_CLUTTER_SOURCE},
                        ${RAPID_CLUTTER_VERSION},
                        ${RAPID_CLUTTER_MODEL},
                        ${RAPID_CLUTTER_MODEL_VERSION},
                        NULL,
                        NULL,

                        ${scenario.ground_elevation_source},
                        ${scenario.ground_elevation_version},
                        ${scenario.ground_elevation_horizontal_crs},
                        ${scenario.ground_elevation_vertical_datum},
                        ${scenario.ground_elevation_units},
                        ${scenario.ground_elevation_resolution_m}
                    )

                    RETURNING
                        id,
                        customer_id,
                        scenario_id,
                        status,

                        site_latitude,
                        site_longitude,

                        frequency_mhz,
                        eirp_watts,

                        antenna_height_m,
                        antenna_gain_dbi,

                        receiver_height_m,
                        receiver_threshold_dbm,

                        calculation_radius_m,
                        resolution_m,

                        propagation_model,
                        propagation_model_version,

                        clutter_source,
                        clutter_version,
                        clutter_model,
                        clutter_model_version,

                        dem_source,
                        dem_version,
                        dem_horizontal_crs,
                        dem_vertical_datum,
                        dem_units,
                        dem_resolution_m,

                        created_at;
                `;

            return NextResponse.json(
                {
                    status: "ok",
                    coverageRun:
                        runs[0],
                },
                {
                    status: 201,
                },
            );
        }

        /*
         * Existing Free Space / NTIA ITM path.
         *
         * Requests that do not explicitly select Rapid Coverage
         * continue to use the scenario's stored propagation model.
         */
        let propagationModelVersion:
            string;

        if (
            scenario.propagation_model ===
            FREE_SPACE_MODEL
        ) {
            propagationModelVersion =
                "dev-0.1";
        } else if (
            scenario.propagation_model ===
            NTIA_ITM_MODEL
        ) {
            propagationModelVersion =
                "1.4";

            const requiredItmValues = [
                scenario.itm_climate,
                scenario.itm_polarization,
                scenario.itm_variability_mode,
                scenario.itm_surface_refractivity,
                scenario.itm_dielectric_constant,
                scenario.itm_conductivity_s_per_m,
                scenario.itm_confidence,
                scenario.itm_reliability,
            ];

            if (
                requiredItmValues.some(
                    (value) =>
                        value === null ||
                        value === undefined,
                )
            ) {
                return NextResponse.json(
                    {
                        error:
                            "NTIA ITM scenario is missing required propagation parameters.",
                    },
                    {
                        status: 400,
                    },
                );
            }
        } else {
            return NextResponse.json(
                {
                    error:
                        "Scenario uses an unsupported propagation model.",
                },
                {
                    status: 400,
                },
            );
        }

        const clutterValues = [
            scenario.clutter_source,
            scenario.clutter_version,
            scenario.clutter_model,
            scenario.clutter_model_version,
            scenario.clutter_percentage_locations,
            scenario.clutter_correction_end,
        ];

        const clutterRequested =
            clutterValues.some(
                (value) =>
                    value !== null &&
                    value !== undefined,
            );

        if (
            clutterRequested &&
            scenario.propagation_model !==
                NTIA_ITM_MODEL
        ) {
            return NextResponse.json(
                {
                    error:
                        "Clutter modeling is currently supported only with NTIA ITM scenarios.",
                },
                {
                    status: 400,
                },
            );
        }

        if (clutterRequested) {
            const clutterIsComplete =
                clutterValues.every(
                    (value) =>
                        value !== null &&
                        value !== undefined,
                );

            if (!clutterIsComplete) {
                return NextResponse.json(
                    {
                        error:
                            "Scenario has incomplete clutter dataset or model parameters.",
                    },
                    {
                        status: 400,
                    },
                );
            }

            if (
                scenario.clutter_model !==
                P2108_CLUTTER_MODEL
            ) {
                return NextResponse.json(
                    {
                        error:
                            "Scenario uses an unsupported clutter model.",
                    },
                    {
                        status: 400,
                    },
                );
            }

            if (
                scenario.clutter_model_version !==
                P2108_CLUTTER_MODEL_VERSION
            ) {
                return NextResponse.json(
                    {
                        error:
                            "Scenario uses an unsupported clutter model version.",
                    },
                    {
                        status: 400,
                    },
                );
            }

            const clutterPercentageLocations =
                Number(
                    scenario.clutter_percentage_locations,
                );

            if (
                !Number.isFinite(
                    clutterPercentageLocations,
                ) ||
                clutterPercentageLocations <= 0 ||
                clutterPercentageLocations >= 100
            ) {
                return NextResponse.json(
                    {
                        error:
                            "Scenario clutter percentage of locations must be greater than 0 and less than 100.",
                    },
                    {
                        status: 400,
                    },
                );
            }

            if (
                scenario.clutter_correction_end !==
                P2108_CORRECTION_END
            ) {
                return NextResponse.json(
                    {
                        error:
                            "Current GeoVaris coverage calculations support receiver-side P.2108 clutter correction only.",
                    },
                    {
                        status: 400,
                    },
                );
            }
        }

        const runs =
            await sql`
                INSERT INTO coverage_runs (
                    customer_id,
                    scenario_id,
                    status,

                    site_latitude,
                    site_longitude,
                    site_ground_elevation_m,

                    frequency_mhz,
                    eirp_watts,

                    antenna_height_m,
                    antenna_gain_dbi,

                    receiver_height_m,
                    receiver_threshold_dbm,

                    calculation_radius_m,
                    resolution_m,

                    propagation_model,
                    propagation_model_version,

                    itm_climate,
                    itm_polarization,
                    itm_variability_mode,
                    itm_surface_refractivity,
                    itm_dielectric_constant,
                    itm_conductivity_s_per_m,
                    itm_confidence,
                    itm_reliability,

                    clutter_source,
                    clutter_version,
                    clutter_model,
                    clutter_model_version,
                    clutter_percentage_locations,
                    clutter_correction_end,

                    dem_source,
                    dem_version,
                    dem_horizontal_crs,
                    dem_vertical_datum,
                    dem_units,
                    dem_resolution_m
                )
                VALUES (
                    ${scenario.customer_id},
                    ${scenario.scenario_id},
                    'pending',

                    ${scenario.site_latitude},
                    ${scenario.site_longitude},
                    ${scenario.ground_elevation_m},

                    ${scenario.frequency_mhz},
                    ${scenario.eirp_watts},

                    ${scenario.antenna_height_m},
                    ${scenario.antenna_gain_dbi},

                    ${scenario.receiver_height_m},
                    ${scenario.receiver_threshold_dbm},

                    ${scenario.calculation_radius_m},
                    ${scenario.resolution_m},

                    ${scenario.propagation_model},
                    ${propagationModelVersion},

                    ${scenario.itm_climate},
                    ${scenario.itm_polarization},
                    ${scenario.itm_variability_mode},
                    ${scenario.itm_surface_refractivity},
                    ${scenario.itm_dielectric_constant},
                    ${scenario.itm_conductivity_s_per_m},
                    ${scenario.itm_confidence},
                    ${scenario.itm_reliability},

                    ${scenario.clutter_source},
                    ${scenario.clutter_version},
                    ${scenario.clutter_model},
                    ${scenario.clutter_model_version},
                    ${scenario.clutter_percentage_locations},
                    ${scenario.clutter_correction_end},

                    ${scenario.ground_elevation_source},
                    ${scenario.ground_elevation_version},
                    ${scenario.ground_elevation_horizontal_crs},
                    ${scenario.ground_elevation_vertical_datum},
                    ${scenario.ground_elevation_units},
                    ${scenario.ground_elevation_resolution_m}
                )

                RETURNING
                    id,
                    customer_id,
                    scenario_id,
                    status,

                    site_latitude,
                    site_longitude,
                    site_ground_elevation_m,

                    frequency_mhz,
                    eirp_watts,

                    antenna_height_m,
                    antenna_gain_dbi,

                    receiver_height_m,
                    receiver_threshold_dbm,

                    calculation_radius_m,
                    resolution_m,

                    propagation_model,
                    propagation_model_version,

                    itm_climate,
                    itm_polarization,
                    itm_variability_mode,
                    itm_surface_refractivity,
                    itm_dielectric_constant,
                    itm_conductivity_s_per_m,
                    itm_confidence,
                    itm_reliability,

                    clutter_source,
                    clutter_version,
                    clutter_model,
                    clutter_model_version,
                    clutter_percentage_locations,
                    clutter_correction_end,

                    dem_source,
                    dem_version,
                    dem_horizontal_crs,
                    dem_vertical_datum,
                    dem_units,
                    dem_resolution_m,

                    created_at;
            `;

        return NextResponse.json(
            {
                status: "ok",
                coverageRun:
                    runs[0],
            },
            {
                status: 201,
            },
        );
    } catch (error) {
        console.error(
            "Create coverage run failed:",
            error,
        );

        return NextResponse.json(
            {
                error:
                    "Unable to create coverage run.",
            },
            {
                status: 500,
            },
        );
    }
}