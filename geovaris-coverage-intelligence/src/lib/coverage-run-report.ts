import { sql } from "@/lib/db";

type CoverageRunReportRow = {
    coverage_run_id: string;
    customer_id: string;
    scenario_id: string;

    customer_name: string;
    project_name: string;
    site_name: string;
    scenario_name: string;

    status: string;

    created_at:
        | string
        | null;

    completed_at:
        | string
        | null;

    processing_time_seconds:
        | number
        | null;

    site_latitude:
        | number
        | null;

    site_longitude:
        | number
        | null;

    site_ground_elevation_m:
        | number
        | null;

    frequency_mhz:
        | number
        | null;

    eirp_watts:
        | number
        | null;

    antenna_height_m:
        | number
        | null;

    antenna_gain_dbi:
        | number
        | null;

    receiver_height_m:
        | number
        | null;

    receiver_threshold_dbm:
        | number
        | null;

    calculation_radius_m:
        | number
        | null;

    resolution_m:
        | number
        | null;

    propagation_model:
        | string
        | null;

    propagation_model_version:
        | string
        | null;

    estimated_coverage_radius_m:
        | number
        | null;

    coverage_area_sq_m:
        | number
        | null;

    itm_climate:
        | number
        | null;

    itm_polarization:
        | number
        | null;

    itm_variability_mode:
        | number
        | null;

    itm_surface_refractivity:
        | number
        | null;

    itm_dielectric_constant:
        | number
        | null;

    itm_conductivity_s_per_m:
        | number
        | null;

    itm_confidence:
        | number
        | null;

    itm_reliability:
        | number
        | null;

    clutter_source:
        | string
        | null;

    clutter_version:
        | string
        | null;

    clutter_model:
        | string
        | null;

    clutter_model_version:
        | string
        | null;

    clutter_percentage_locations:
        | number
        | null;

    clutter_correction_end:
        | string
        | null;

    dem_source:
        | string
        | null;

    dem_version:
        | string
        | null;

    dem_horizontal_crs:
        | string
        | null;

    dem_vertical_datum:
        | string
        | null;

    dem_units:
        | string
        | null;

    dem_resolution_m:
        | number
        | null;

    covered_population:
        | number
        | null;

    census_vintage:
        | string
        | null;

    population_dataset_source:
        | string
        | null;

    population_dataset_version:
        | string
        | null;

    population_allocation_method:
        | string
        | null;

    population_geometry_basis:
        | string
        | null;

    population_intersecting_blocks:
        | number
        | null;

    population_fully_covered_blocks:
        | number
        | null;

    population_partially_covered_blocks:
        | number
        | null;

    population_calculated_at:
        | string
        | null;

    covered_fabric_locations:
        | number
        | null;

    fabric_version:
        | string
        | null;

    fabric_dataset_source:
        | string
        | null;

    fabric_dataset_vintage:
        | string
        | null;

    fabric_geometry_basis:
        | string
        | null;

    fabric_calculated_at:
        | string
        | null;

    location_dataset_id:
        | string
        | null;

    location_dataset_name:
        | string
        | null;

    location_dataset_type:
        | string
        | null;

    location_dataset_is_mock:
        | boolean
        | null;
};

export type CoverageRunReport = {
    identity: {
        customerId: string;
        customerName: string;
        projectName: string;
        siteName: string;
        scenarioId: string;
        scenarioName: string;
        coverageRunId: string;
    };

    run: {
        status: string;
        createdAt:
            | string
            | null;
        completedAt:
            | string
            | null;
        processingTimeSeconds:
            | number
            | null;
        methodology: string;
    };

    site: {
        latitude:
            | number
            | null;
        longitude:
            | number
            | null;
        groundElevationM:
            | number
            | null;
    };

    rfInputs: {
        frequencyMHz:
            | number
            | null;
        eirpWatts:
            | number
            | null;
        antennaHeightM:
            | number
            | null;
        antennaGainDbi:
            | number
            | null;
        receiverHeightM:
            | number
            | null;
        receiverThresholdDbm:
            | number
            | null;
        calculationRadiusM:
            | number
            | null;
        resolutionM:
            | number
            | null;
        propagationModel:
            | string
            | null;
        propagationModelVersion:
            | string
            | null;
    };

    results: {
        estimatedCoverageRadiusM:
            | number
            | null;
        coverageAreaSqM:
            | number
            | null;
        coveredPopulation:
            | number
            | null;
        coveredLocations:
            | number
            | null;
    };

    terrain: {
        source:
            | string
            | null;
        version:
            | string
            | null;
        horizontalCrs:
            | string
            | null;
        verticalDatum:
            | string
            | null;
        units:
            | string
            | null;
        resolutionM:
            | number
            | null;
    };

    clutter: {
        source:
            | string
            | null;
        version:
            | string
            | null;
        model:
            | string
            | null;
        modelVersion:
            | string
            | null;
        percentageLocations:
            | number
            | null;
        correctionEnd:
            | string
            | null;
    };

    itm: {
        climate:
            | number
            | null;
        polarization:
            | number
            | null;
        variabilityMode:
            | number
            | null;
        surfaceRefractivity:
            | number
            | null;
        dielectricConstant:
            | number
            | null;
        conductivitySPerM:
            | number
            | null;
        confidence:
            | number
            | null;
        reliability:
            | number
            | null;
    };

    population: {
        coveredPopulation:
            | number
            | null;
        censusVintage:
            | string
            | null;
        datasetSource:
            | string
            | null;
        datasetVersion:
            | string
            | null;
        allocationMethod:
            | string
            | null;
        geometryBasis:
            | string
            | null;
        intersectingBlocks:
            | number
            | null;
        fullyCoveredBlocks:
            | number
            | null;
        partiallyCoveredBlocks:
            | number
            | null;
        calculatedAt:
            | string
            | null;
    };

    locations: {
        coveredLocations:
            | number
            | null;
        locationDatasetId:
            | string
            | null;
        locationDatasetName:
            | string
            | null;
        locationDatasetType:
            | string
            | null;
        locationDatasetIsMock:
            | boolean
            | null;
        datasetSource:
            | string
            | null;
        datasetVersion:
            | string
            | null;
        datasetVintage:
            | string
            | null;
        geometryBasis:
            | string
            | null;
        calculatedAt:
            | string
            | null;
    };

    disclaimer: {
        rfEstimate: string;
        populationEstimate: string;
        locationEstimate: string;
    };
};

type GetCoverageRunReportOptions = {
    runId: string;
    isGeoVarisAdmin: boolean;
    readableCustomerIds: string[];
};

function getMethodologyLabel(
    propagationModel:
        | string
        | null,
) {
    if (
        propagationModel ===
        "rapid_coverage"
    ) {
        return (
            "Terrain/Clutter LOS + Free-Space Link Budget"
        );
    }

    if (
        propagationModel ===
        "ntia_itm"
    ) {
        return "NTIA Longley-Rice ITM";
    }

    if (
        propagationModel ===
        "free_space_test"
    ) {
        return "Free-Space Test Model";
    }

    return (
        propagationModel ??
        "Unknown"
    );
}

export async function getCoverageRunReport(
    options: GetCoverageRunReportOptions,
): Promise<
    CoverageRunReport
    | null
> {
    const {
        runId,
        isGeoVarisAdmin,
        readableCustomerIds,
    } = options;

    /*
     * Authorization is enforced in the query itself.
     *
     * GeoVaris Admin may access any customer.
     * Other users may access only customer IDs resolved
     * from their authenticated memberships.
     *
     * An empty readableCustomerIds array therefore
     * produces no match for a non-admin user.
     */
    const rows =
        await sql`
            SELECT
                cr.id
                    AS coverage_run_id,

                cr.customer_id,
                cr.scenario_id,

                c.name
                    AS customer_name,

                p.name
                    AS project_name,

                s.name
                    AS site_name,

                sc.name
                    AS scenario_name,

                cr.status,

                cr.created_at,
                cr.completed_at,

                cr.processing_time_seconds::double precision
                    AS processing_time_seconds,

                cr.site_latitude::double precision
                    AS site_latitude,

                cr.site_longitude::double precision
                    AS site_longitude,

                cr.site_ground_elevation_m::double precision
                    AS site_ground_elevation_m,

                cr.frequency_mhz::double precision
                    AS frequency_mhz,

                cr.eirp_watts::double precision
                    AS eirp_watts,

                cr.antenna_height_m::double precision
                    AS antenna_height_m,

                cr.antenna_gain_dbi::double precision
                    AS antenna_gain_dbi,

                cr.receiver_height_m::double precision
                    AS receiver_height_m,

                cr.receiver_threshold_dbm::double precision
                    AS receiver_threshold_dbm,

                cr.calculation_radius_m::double precision
                    AS calculation_radius_m,

                cr.resolution_m::double precision
                    AS resolution_m,

                cr.propagation_model,
                cr.propagation_model_version,

                cr.estimated_coverage_radius_m::double precision
                    AS estimated_coverage_radius_m,

                cr.coverage_area_sq_m::double precision
                    AS coverage_area_sq_m,

                cr.itm_climate,
                cr.itm_polarization,
                cr.itm_variability_mode,

                cr.itm_surface_refractivity::double precision
                    AS itm_surface_refractivity,

                cr.itm_dielectric_constant::double precision
                    AS itm_dielectric_constant,

                cr.itm_conductivity_s_per_m::double precision
                    AS itm_conductivity_s_per_m,

                cr.itm_confidence::double precision
                    AS itm_confidence,

                cr.itm_reliability::double precision
                    AS itm_reliability,

                cr.clutter_source,
                cr.clutter_version,
                cr.clutter_model,
                cr.clutter_model_version,

                cr.clutter_percentage_locations::double precision
                    AS clutter_percentage_locations,

                cr.clutter_correction_end,

                cr.dem_source,
                cr.dem_version,
                cr.dem_horizontal_crs,
                cr.dem_vertical_datum,
                cr.dem_units,

                cr.dem_resolution_m::double precision
                    AS dem_resolution_m,

                cr.covered_population::double precision
                    AS covered_population,

                cr.census_vintage,
                cr.population_dataset_source,
                cr.population_dataset_version,
                cr.population_allocation_method,
                cr.population_geometry_basis,

                cr.population_intersecting_blocks,
                cr.population_fully_covered_blocks,
                cr.population_partially_covered_blocks,
                cr.population_calculated_at,

                cr.covered_fabric_locations::double precision
                    AS covered_fabric_locations,

                cr.fabric_version,
                cr.fabric_dataset_source,
                cr.fabric_dataset_vintage,
                cr.fabric_geometry_basis,
                cr.fabric_calculated_at,

                cr.location_dataset_id,

                ld.name
                    AS location_dataset_name,

                ld.dataset_type
                    AS location_dataset_type,

                ld.is_mock
                    AS location_dataset_is_mock

            FROM coverage_runs cr

            JOIN scenarios sc
                ON sc.id =
                    cr.scenario_id
                AND sc.customer_id =
                    cr.customer_id

            JOIN sites s
                ON s.id =
                    sc.site_id
                AND s.customer_id =
                    cr.customer_id

            JOIN projects p
                ON p.id =
                    s.project_id
                AND p.customer_id =
                    cr.customer_id

            JOIN customers c
                ON c.id =
                    cr.customer_id

            LEFT JOIN location_datasets ld
                ON ld.id =
                    cr.location_dataset_id
                AND ld.customer_id =
                    cr.customer_id

            WHERE cr.id =
                ${runId}

              AND cr.status =
                'completed'

              AND (
                    ${isGeoVarisAdmin}::boolean
                    OR cr.customer_id =
                        ANY(
                            ${readableCustomerIds}::uuid[]
                        )
              )

            LIMIT 1;
        `;

    const reportRow =
        (
            rows as unknown as
                CoverageRunReportRow[]
        )[0];

    if (!reportRow) {
        return null;
    }

    const methodology =
        getMethodologyLabel(
            reportRow.propagation_model,
        );

    return {
        identity: {
            customerId:
                reportRow.customer_id,

            customerName:
                reportRow.customer_name,

            projectName:
                reportRow.project_name,

            siteName:
                reportRow.site_name,

            scenarioId:
                reportRow.scenario_id,

            scenarioName:
                reportRow.scenario_name,

            coverageRunId:
                reportRow.coverage_run_id,
        },

        run: {
            status:
                reportRow.status,

            createdAt:
                reportRow.created_at,

            completedAt:
                reportRow.completed_at,

            processingTimeSeconds:
                reportRow.processing_time_seconds,

            methodology,
        },

        site: {
            latitude:
                reportRow.site_latitude,

            longitude:
                reportRow.site_longitude,

            groundElevationM:
                reportRow.site_ground_elevation_m,
        },

        rfInputs: {
            frequencyMHz:
                reportRow.frequency_mhz,

            eirpWatts:
                reportRow.eirp_watts,

            antennaHeightM:
                reportRow.antenna_height_m,

            antennaGainDbi:
                reportRow.antenna_gain_dbi,

            receiverHeightM:
                reportRow.receiver_height_m,

            receiverThresholdDbm:
                reportRow.receiver_threshold_dbm,

            calculationRadiusM:
                reportRow.calculation_radius_m,

            resolutionM:
                reportRow.resolution_m,

            propagationModel:
                reportRow.propagation_model,

            propagationModelVersion:
                reportRow.propagation_model_version,
        },

        results: {
            estimatedCoverageRadiusM:
                reportRow.estimated_coverage_radius_m,

            coverageAreaSqM:
                reportRow.coverage_area_sq_m,

            coveredPopulation:
                reportRow.covered_population,

            coveredLocations:
                reportRow.covered_fabric_locations,
        },

        terrain: {
            source:
                reportRow.dem_source,

            version:
                reportRow.dem_version,

            horizontalCrs:
                reportRow.dem_horizontal_crs,

            verticalDatum:
                reportRow.dem_vertical_datum,

            units:
                reportRow.dem_units,

            resolutionM:
                reportRow.dem_resolution_m,
        },

        clutter: {
            source:
                reportRow.clutter_source,

            version:
                reportRow.clutter_version,

            model:
                reportRow.clutter_model,

            modelVersion:
                reportRow.clutter_model_version,

            percentageLocations:
                reportRow.clutter_percentage_locations,

            correctionEnd:
                reportRow.clutter_correction_end,
        },

        itm: {
            climate:
                reportRow.itm_climate,

            polarization:
                reportRow.itm_polarization,

            variabilityMode:
                reportRow.itm_variability_mode,

            surfaceRefractivity:
                reportRow.itm_surface_refractivity,

            dielectricConstant:
                reportRow.itm_dielectric_constant,

            conductivitySPerM:
                reportRow.itm_conductivity_s_per_m,

            confidence:
                reportRow.itm_confidence,

            reliability:
                reportRow.itm_reliability,
        },

        population: {
            coveredPopulation:
                reportRow.covered_population,

            censusVintage:
                reportRow.census_vintage,

            datasetSource:
                reportRow.population_dataset_source,

            datasetVersion:
                reportRow.population_dataset_version,

            allocationMethod:
                reportRow.population_allocation_method,

            geometryBasis:
                reportRow.population_geometry_basis,

            intersectingBlocks:
                reportRow.population_intersecting_blocks,

            fullyCoveredBlocks:
                reportRow.population_fully_covered_blocks,

            partiallyCoveredBlocks:
                reportRow.population_partially_covered_blocks,

            calculatedAt:
                reportRow.population_calculated_at,
        },

        locations: {
            coveredLocations:
                reportRow.covered_fabric_locations,

            locationDatasetId:
                reportRow.location_dataset_id,

            locationDatasetName:
                reportRow.location_dataset_name,

            locationDatasetType:
                reportRow.location_dataset_type,

            locationDatasetIsMock:
                reportRow.location_dataset_is_mock,

            datasetSource:
                reportRow.fabric_dataset_source,

            datasetVersion:
                reportRow.fabric_version,

            datasetVintage:
                reportRow.fabric_dataset_vintage,

            geometryBasis:
                reportRow.fabric_geometry_basis,

            calculatedAt:
                reportRow.fabric_calculated_at,
        },

        disclaimer: {
            rfEstimate:
                "Coverage results are engineering estimates and do not guarantee actual service availability.",

            populationEstimate:
                "Population coverage is an estimated geospatial allocation and is not an exact count of people receiving service.",

            locationEstimate:
                "Covered location counts represent geospatial intersection with the modeled coverage footprint and do not guarantee service at those locations.",
        },
    };
}