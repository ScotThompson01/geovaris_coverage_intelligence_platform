import {
    NextRequest,
    NextResponse,
} from "next/server";

import {
    getGeoVarisAuthContext,
} from "@/lib/auth-context";

import {
    getCoverageRunReport,
} from "@/lib/coverage-run-report";

import {
    isUuid,
} from "@/lib/validation";

function csvValue(
    value:
        | string
        | number
        | boolean
        | null
        | undefined,
) {
    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    const text =
        String(value);

    return (
        `"${text.replaceAll(
            "\"",
            "\"\"",
        )}"`
    );
}

export async function GET(
    request: NextRequest,
) {
    try {
        const authContext =
            await getGeoVarisAuthContext();

        if (!authContext) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Authentication is required.",
                },
                {
                    status: 401,
                },
            );
        }

        const runId =
            request.nextUrl.searchParams.get(
                "runId",
            );

        if (!runId) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Coverage run ID is required.",
                },
                {
                    status: 400,
                },
            );
        }

        if (!isUuid(runId)) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Coverage run ID must be a valid UUID.",
                },
                {
                    status: 400,
                },
            );
        }

        const readableCustomerIds =
            authContext.customerMemberships.map(
                (membership) =>
                    membership.customerId,
            );

        const report =
            await getCoverageRunReport({
                runId,
                isGeoVarisAdmin:
                    authContext.isGeoVarisAdmin,
                readableCustomerIds,
            });

        /*
         * Missing and unauthorized coverage runs
         * intentionally return the same response.
         */
        if (!report) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Coverage run was not found.",
                },
                {
                    status: 404,
                },
            );
        }

        const coverageAreaKm2 =
            report.results.coverageAreaSqM ===
            null
                ? null
                : (
                    report.results.coverageAreaSqM /
                    1_000_000
                );

        const headers = [
            "Customer",
            "Project",
            "Site",
            "Scenario",
            "Coverage Run ID",
            "Run Status",
            "Created At",
            "Completed At",
            "Processing Time Seconds",
            "Methodology",

            "Site Latitude",
            "Site Longitude",
            "Ground Elevation m",

            "Frequency MHz",
            "EIRP Watts",
            "Antenna Height m",
            "Antenna Gain dBi",
            "Receiver Height m",
            "Receiver Threshold dBm",
            "Calculation Radius m",
            "Resolution m",
            "Propagation Model",
            "Propagation Model Version",

            "Estimated Coverage Radius m",
            "Coverage Area sq m",
            "Coverage Area km2",
            "Covered Population",
            "Covered Locations",

            "DEM Source",
            "DEM Version",
            "DEM Horizontal CRS",
            "DEM Vertical Datum",
            "DEM Units",
            "DEM Resolution m",

            "Clutter Source",
            "Clutter Version",
            "Clutter Model",
            "Clutter Model Version",

            "Population Census Vintage",
            "Population Dataset Source",
            "Population Dataset Version",
            "Population Allocation Method",
            "Population Geometry Basis",

            "Location Dataset ID",
            "Location Dataset Name",
            "Location Dataset Type",
            "Location Dataset Is Mock",
            "Location Dataset Source",
            "Location Dataset Version",
            "Location Dataset Vintage",
            "Location Geometry Basis",

            "RF Estimate Disclaimer",
            "Population Estimate Disclaimer",
            "Location Estimate Disclaimer",
        ];

        const values = [
            report.identity.customerName,
            report.identity.projectName,
            report.identity.siteName,
            report.identity.scenarioName,
            report.identity.coverageRunId,
            report.run.status,
            report.run.createdAt,
            report.run.completedAt,
            report.run.processingTimeSeconds,
            report.run.methodology,

            report.site.latitude,
            report.site.longitude,
            report.site.groundElevationM,

            report.rfInputs.frequencyMHz,
            report.rfInputs.eirpWatts,
            report.rfInputs.antennaHeightM,
            report.rfInputs.antennaGainDbi,
            report.rfInputs.receiverHeightM,
            report.rfInputs.receiverThresholdDbm,
            report.rfInputs.calculationRadiusM,
            report.rfInputs.resolutionM,
            report.rfInputs.propagationModel,
            report.rfInputs.propagationModelVersion,

            report.results.estimatedCoverageRadiusM,
            report.results.coverageAreaSqM,
            coverageAreaKm2,
            report.results.coveredPopulation,
            report.results.coveredLocations,

            report.terrain.source,
            report.terrain.version,
            report.terrain.horizontalCrs,
            report.terrain.verticalDatum,
            report.terrain.units,
            report.terrain.resolutionM,

            report.clutter.source,
            report.clutter.version,
            report.clutter.model,
            report.clutter.modelVersion,

            report.population.censusVintage,
            report.population.datasetSource,
            report.population.datasetVersion,
            report.population.allocationMethod,
            report.population.geometryBasis,

            report.locations.locationDatasetId,
            report.locations.locationDatasetName,
            report.locations.locationDatasetType,
            report.locations.locationDatasetIsMock,
            report.locations.datasetSource,
            report.locations.datasetVersion,
            report.locations.datasetVintage,
            report.locations.geometryBasis,

            report.disclaimer.rfEstimate,
            report.disclaimer.populationEstimate,
            report.disclaimer.locationEstimate,
        ];

        const csv = [
            headers
                .map(csvValue)
                .join(","),
            values
                .map(csvValue)
                .join(","),
        ].join("\r\n");

        /*
         * UTF-8 BOM improves compatibility when the CSV
         * is opened directly in Microsoft Excel.
         */
        const body =
            `\uFEFF${csv}\r\n`;

        const filename =
            `geovaris-coverage-run-${runId}.csv`;

        return new NextResponse(
            body,
            {
                status: 200,
                headers: {
                    "Content-Type":
                        "text/csv; charset=utf-8",

                    "Content-Disposition":
                        `attachment; filename="${filename}"`,

                    "Cache-Control":
                        "private, no-store",
                },
            },
        );
    } catch (error) {
        console.error(
            "Coverage run CSV export failed:",
            error,
        );

        return NextResponse.json(
            {
                status: "error",
                error:
                    "Unable to export coverage run CSV.",
            },
            {
                status: 500,
            },
        );
    }
}