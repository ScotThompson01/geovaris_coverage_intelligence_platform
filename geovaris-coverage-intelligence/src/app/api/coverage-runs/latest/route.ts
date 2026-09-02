import {
    NextRequest,
    NextResponse,
} from "next/server";

import { sql } from "@/lib/db";

export async function GET(
    request: NextRequest,
) {
    try {
        const scenarioId =
            request.nextUrl.searchParams.get(
                "scenarioId",
            );

        if (!scenarioId) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Scenario ID is required.",
                },
                {
                    status: 400,
                },
            );
        }

        const includeGeometry =
            request.nextUrl.searchParams.get(
                "includeGeometry",
            ) !== "false";

        if (includeGeometry) {
            const rows = await sql`
                SELECT
                    cr.id,
                    cr.status,
                    cr.estimated_coverage_radius_m,
                    cr.coverage_area_sq_m,
                    cr.processing_time_seconds,
                    cr.frequency_mhz,
                    cr.eirp_watts,
                    cr.antenna_height_m,
                    cr.receiver_threshold_dbm,
                    cr.propagation_model,

                    cr.covered_population::double precision
                        AS covered_population,

                    cr.census_vintage,
                    cr.population_dataset_source,
                    cr.population_dataset_version,
                    cr.population_allocation_method,
                    cr.population_geometry_basis,

                    cr.covered_fabric_locations::double precision
                        AS covered_fabric_locations,

                    cr.fabric_version,
                    cr.fabric_dataset_source,
                    cr.fabric_dataset_vintage,
                    cr.fabric_geometry_basis,
                    cr.fabric_calculated_at,

                    ST_AsGeoJSON(
                        ST_ForcePolygonCCW(
                            cr.coverage_geometry
                        )
                    )::json AS coverage_geometry,

                    s.name AS site_name

                FROM coverage_runs cr

                JOIN scenarios sc
                    ON sc.id = cr.scenario_id
                    AND sc.customer_id =
                        cr.customer_id

                JOIN sites s
                    ON s.id = sc.site_id
                    AND s.customer_id =
                        cr.customer_id

                WHERE cr.status = 'completed'
                    AND cr.coverage_geometry
                        IS NOT NULL
                    AND cr.scenario_id =
                        ${scenarioId}

                ORDER BY
                    cr.completed_at DESC

                LIMIT 1;
            `;

            return NextResponse.json({
                status: "ok",
                coverageRun:
                    rows[0] ?? null,
            });
        }

        const rows = await sql`
            SELECT
                cr.id,
                cr.status,
                cr.estimated_coverage_radius_m,
                cr.coverage_area_sq_m,
                cr.processing_time_seconds,
                cr.frequency_mhz,
                cr.eirp_watts,
                cr.antenna_height_m,
                cr.receiver_threshold_dbm,
                cr.propagation_model,

                cr.covered_population::double precision
                    AS covered_population,

                cr.census_vintage,
                cr.population_dataset_source,
                cr.population_dataset_version,
                cr.population_allocation_method,
                cr.population_geometry_basis,

                cr.covered_fabric_locations::double precision
                    AS covered_fabric_locations,

                cr.fabric_version,
                cr.fabric_dataset_source,
                cr.fabric_dataset_vintage,
                cr.fabric_geometry_basis,
                cr.fabric_calculated_at,

                s.name AS site_name

            FROM coverage_runs cr

            JOIN scenarios sc
                ON sc.id = cr.scenario_id
                AND sc.customer_id =
                    cr.customer_id

            JOIN sites s
                ON s.id = sc.site_id
                AND s.customer_id =
                    cr.customer_id

            WHERE cr.status = 'completed'
                AND cr.coverage_geometry
                    IS NOT NULL
                AND cr.scenario_id =
                    ${scenarioId}

            ORDER BY
                cr.completed_at DESC

            LIMIT 1;
        `;

        return NextResponse.json({
            status: "ok",
            coverageRun:
                rows[0] ?? null,
        });
    } catch (error) {
        console.error(
            "Latest coverage run lookup failed:",
            error,
        );

        return NextResponse.json(
            {
                status: "error",
                error:
                    "Unable to load coverage result.",
            },
            {
                status: 500,
            },
        );
    }
}