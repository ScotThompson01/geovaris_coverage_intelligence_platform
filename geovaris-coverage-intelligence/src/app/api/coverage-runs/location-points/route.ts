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

        if (!isUuid(scenarioId)) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Scenario ID must be a valid UUID.",
                },
                {
                    status: 400,
                },
            );
        }

        let authorizedScenarioRows;

        if (
            authContext.isGeoVarisAdmin
        ) {
            authorizedScenarioRows =
                await sql`
                    SELECT
                        id,
                        customer_id

                    FROM scenarios

                    WHERE id =
                        ${scenarioId}

                    LIMIT 1;
                `;
        } else {
            const readableCustomerIds =
                authContext.customerMemberships.map(
                    (membership) =>
                        membership.customerId,
                );

            if (
                readableCustomerIds.length === 0
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

            authorizedScenarioRows =
                await sql`
                    SELECT
                        id,
                        customer_id

                    FROM scenarios

                    WHERE id =
                        ${scenarioId}

                      AND customer_id =
                        ANY(
                            ${readableCustomerIds}::uuid[]
                        )

                    LIMIT 1;
                `;
        }

        const authorizedScenario =
            authorizedScenarioRows[0];

        if (!authorizedScenario) {
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

        /*
         * Resolve the latest completed coverage run only
         * within the authorized customer's scope.
         *
         * The location dataset must already be linked to
         * the coverage run and must belong to the same
         * customer.
         */
        const runRows =
            await sql`
                SELECT
                    cr.id AS coverage_run_id,
                    cr.location_dataset_id,

                    ld.name
                        AS dataset_name,

                    ld.dataset_type,
                    ld.is_mock,

                    ld.row_count

                FROM coverage_runs cr

                JOIN location_datasets ld
                    ON ld.id =
                        cr.location_dataset_id
                    AND ld.customer_id =
                        cr.customer_id

                WHERE cr.scenario_id =
                    ${scenarioId}

                  AND cr.customer_id =
                    ${authorizedScenario.customer_id}

                  AND cr.status =
                    'completed'

                  AND cr.coverage_geometry
                    IS NOT NULL

                  AND cr.location_dataset_id
                    IS NOT NULL

                ORDER BY
                    cr.completed_at DESC NULLS LAST,
                    cr.created_at DESC

                LIMIT 1;
            `;

        const run =
            runRows[0];

        if (!run) {
            return NextResponse.json({
                status: "ok",

                dataset: null,

                points: [],
            });
        }

        /*
         * Determine covered/uncovered status directly
         * from the same stored coverage geometry used by
         * the location KPI.
         *
         * The browser never supplies customer_id or
         * location_dataset_id.
         */
        const pointRows =
            await sql`
                SELECT
                    ldp.source_location_id
                        AS id,

                    ldp.latitude::double precision
                        AS latitude,

                    ldp.longitude::double precision
                        AS longitude,

                    ST_Intersects(
                        cr.coverage_geometry,
                        ldp.location
                    )
                        AS covered

                FROM coverage_runs cr

                JOIN location_dataset_points ldp
                    ON ldp.dataset_id =
                        cr.location_dataset_id

                WHERE cr.id =
                    ${run.coverage_run_id}

                  AND cr.customer_id =
                    ${authorizedScenario.customer_id}

                ORDER BY
                    ldp.source_location_id;
            `;

        return NextResponse.json({
            status: "ok",

            dataset: {
                id:
                    run.location_dataset_id,

                name:
                    run.dataset_name,

                type:
                    run.dataset_type,

                isMock:
                    run.is_mock,

                totalLocations:
                    run.row_count,
            },

            points:
                pointRows,
        });
    } catch (error) {
        console.error(
            "Coverage location point lookup failed:",
            error,
        );

        return NextResponse.json(
            {
                status: "error",
                error:
                    "Unable to load coverage location points.",
            },
            {
                status: 500,
            },
        );
    }
}