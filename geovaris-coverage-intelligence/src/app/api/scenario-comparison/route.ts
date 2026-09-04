import {
    NextRequest,
    NextResponse,
} from "next/server";

import {
    getGeoVarisAuthContext,
} from "@/lib/auth-context";

import { sql } from "@/lib/db";

import {
    isUuid,
} from "@/lib/validation";

type ScenarioComparisonRow = {
    scenario_id: string;
    customer_id: string;
    customer_name: string;
    project_name: string;
    site_name: string;
    scenario_name: string;

    frequency_mhz: number;
    eirp_watts: number;
    antenna_height_m: number;
    receiver_threshold_dbm: number;
    propagation_model: string;

    coverage_run_id:
        | string
        | null;

    coverage_area_sq_m:
        | number
        | null;

    covered_population:
        | number
        | null;

    covered_fabric_locations:
        | number
        | null;

    completed_at:
        | string
        | null;
};

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

        const scenarioAId =
            request.nextUrl.searchParams.get(
                "scenarioA",
            );

        const scenarioBId =
            request.nextUrl.searchParams.get(
                "scenarioB",
            );

        if (
            !scenarioAId ||
            !scenarioBId
        ) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Scenario A and Scenario B are required.",
                },
                {
                    status: 400,
                },
            );
        }

        if (
            !isUuid(
                scenarioAId,
            ) ||
            !isUuid(
                scenarioBId,
            )
        ) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Scenario IDs must be valid UUIDs.",
                },
                {
                    status: 400,
                },
            );
        }

        if (
            scenarioAId ===
            scenarioBId
        ) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Choose two different scenarios.",
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

        let rows;

        if (
            authContext.isGeoVarisAdmin
        ) {
            rows =
                await sql`
                    SELECT
                        sc.id AS scenario_id,
                        sc.customer_id,

                        c.name AS customer_name,
                        p.name AS project_name,
                        s.name AS site_name,
                        sc.name AS scenario_name,

                        sc.frequency_mhz,
                        sc.eirp_watts,
                        sc.antenna_height_m,
                        sc.receiver_threshold_dbm,
                        sc.propagation_model,

                        latest_run.id
                            AS coverage_run_id,

                        latest_run.coverage_area_sq_m::double precision
                            AS coverage_area_sq_m,

                        latest_run.covered_population::double precision
                            AS covered_population,

                        latest_run.covered_fabric_locations::double precision
                            AS covered_fabric_locations,

                        latest_run.completed_at

                    FROM scenarios sc

                    JOIN sites s
                        ON s.id =
                            sc.site_id
                        AND s.customer_id =
                            sc.customer_id

                    JOIN projects p
                        ON p.id =
                            s.project_id
                        AND p.customer_id =
                            sc.customer_id

                    JOIN customers c
                        ON c.id =
                            sc.customer_id

                    LEFT JOIN LATERAL (
                        SELECT
                            cr.id,
                            cr.coverage_area_sq_m,
                            cr.covered_population,
                            cr.covered_fabric_locations,
                            cr.completed_at

                        FROM coverage_runs cr

                        WHERE cr.scenario_id =
                            sc.id

                          AND cr.customer_id =
                            sc.customer_id

                          AND cr.status =
                            'completed'

                        ORDER BY
                            cr.completed_at DESC NULLS LAST,
                            cr.created_at DESC

                        LIMIT 1
                    ) latest_run
                        ON TRUE

                    WHERE sc.id
                        IN (
                            ${scenarioAId},
                            ${scenarioBId}
                        );
                `;
        } else {
            if (
                readableCustomerIds.length ===
                0
            ) {
                return NextResponse.json(
                    {
                        status: "error",
                        error:
                            "Scenario was not found.",
                    },
                    {
                        status: 404,
                    },
                );
            }

            rows =
                await sql`
                    SELECT
                        sc.id AS scenario_id,
                        sc.customer_id,

                        c.name AS customer_name,
                        p.name AS project_name,
                        s.name AS site_name,
                        sc.name AS scenario_name,

                        sc.frequency_mhz,
                        sc.eirp_watts,
                        sc.antenna_height_m,
                        sc.receiver_threshold_dbm,
                        sc.propagation_model,

                        latest_run.id
                            AS coverage_run_id,

                        latest_run.coverage_area_sq_m::double precision
                            AS coverage_area_sq_m,

                        latest_run.covered_population::double precision
                            AS covered_population,

                        latest_run.covered_fabric_locations::double precision
                            AS covered_fabric_locations,

                        latest_run.completed_at

                    FROM scenarios sc

                    JOIN sites s
                        ON s.id =
                            sc.site_id
                        AND s.customer_id =
                            sc.customer_id

                    JOIN projects p
                        ON p.id =
                            s.project_id
                        AND p.customer_id =
                            sc.customer_id

                    JOIN customers c
                        ON c.id =
                            sc.customer_id

                    LEFT JOIN LATERAL (
                        SELECT
                            cr.id,
                            cr.coverage_area_sq_m,
                            cr.covered_population,
                            cr.covered_fabric_locations,
                            cr.completed_at

                        FROM coverage_runs cr

                        WHERE cr.scenario_id =
                            sc.id

                          AND cr.customer_id =
                            sc.customer_id

                          AND cr.status =
                            'completed'

                        ORDER BY
                            cr.completed_at DESC NULLS LAST,
                            cr.created_at DESC

                        LIMIT 1
                    ) latest_run
                        ON TRUE

                    WHERE sc.id
                        IN (
                            ${scenarioAId},
                            ${scenarioBId}
                        )

                      AND sc.customer_id =
                        ANY(
                            ${readableCustomerIds}::uuid[]
                        );
                `;
        }

        const typedRows =
            rows as unknown as ScenarioComparisonRow[];

        const scenarioA =
            typedRows.find(
                (row) =>
                    row.scenario_id ===
                    scenarioAId,
            );

        const scenarioB =
            typedRows.find(
                (row) =>
                    row.scenario_id ===
                    scenarioBId,
            );

        /*
         * Missing and unauthorized scenarios intentionally
         * return the same response.
         */
        if (
            !scenarioA ||
            !scenarioB
        ) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Scenario was not found.",
                },
                {
                    status: 404,
                },
            );
        }

        return NextResponse.json({
            status: "ok",
            scenarioA,
            scenarioB,
        });
    } catch (error) {
        console.error(
            "Scenario comparison lookup failed:",
            error,
        );

        return NextResponse.json(
            {
                status: "error",
                error:
                    "Unable to load scenario comparison.",
            },
            {
                status: 500,
            },
        );
    }
}