import {
    NextRequest,
    NextResponse,
} from "next/server";

import {
    getGeoVarisAuthContext,
} from "@/lib/auth-context";

import { sql } from "@/lib/db";

type SummaryRow = {
    total_runs: number;
    completed_runs: number;
    average_processing_time_seconds:
        | number
        | null;
};

type StatusRow = {
    status: string;
    run_count: number;
};

type ModelRow = {
    propagation_model:
        | string
        | null;
    run_count: number;
};

type RecentRunRow = {
    id: string;
    customer_id: string;
    customer_name: string;
    scenario_id: string;
    status: string;
    propagation_model:
        | string
        | null;
    processing_time_seconds:
        | number
        | null;
    created_at:
        | string
        | null;
    completed_at:
        | string
        | null;
};

type CustomerUsageRow = {
    customer_id: string;
    customer_name: string;
    total_runs: number;
    completed_runs: number;
    average_processing_time_seconds:
        | number
        | null;
};

export async function GET(
    _request: NextRequest,
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

        /*
         * Usage analytics are administrative information.
         *
         * GeoVaris Admin:
         *   may view usage across all customers.
         *
         * Customer Admin:
         *   may view usage only for customers where
         *   they hold customer_admin membership.
         *
         * Engineer / Analyst / Viewer:
         *   may not access this endpoint.
         */
        const customerAdminIds =
            authContext.customerMemberships
                .filter(
                    (membership) =>
                        membership.role ===
                        "customer_admin",
                )
                .map(
                    (membership) =>
                        membership.customerId,
                );

        const isGeoVarisAdmin =
            authContext.isGeoVarisAdmin;

        if (
            !isGeoVarisAdmin &&
            customerAdminIds.length === 0
        ) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Administrative access is required.",
                },
                {
                    status: 403,
                },
            );
        }

        let summaryRows;
        let statusRows;
        let modelRows;
        let recentRunRows;
        let customerUsageRows;

        if (isGeoVarisAdmin) {
            [
                summaryRows,
                statusRows,
                modelRows,
                recentRunRows,
                customerUsageRows,
            ] =
                await Promise.all([
                    sql`
                        SELECT
                            COUNT(*)::integer
                                AS total_runs,

                            COUNT(*) FILTER (
                                WHERE status =
                                    'completed'
                            )::integer
                                AS completed_runs,

                            AVG(
                                processing_time_seconds
                            ) FILTER (
                                WHERE
                                    processing_time_seconds
                                        IS NOT NULL
                            )::double precision
                                AS average_processing_time_seconds

                        FROM coverage_runs;
                    `,

                    sql`
                        SELECT
                            status,

                            COUNT(*)::integer
                                AS run_count

                        FROM coverage_runs

                        GROUP BY
                            status

                        ORDER BY
                            run_count DESC,
                            status;
                    `,

                    sql`
                        SELECT
                            propagation_model,

                            COUNT(*)::integer
                                AS run_count

                        FROM coverage_runs

                        GROUP BY
                            propagation_model

                        ORDER BY
                            run_count DESC,
                            propagation_model
                                NULLS LAST;
                    `,

                    sql`
                        SELECT
                            cr.id,
                            cr.customer_id,
                            c.name
                                AS customer_name,
                            cr.scenario_id,
                            cr.status,
                            cr.propagation_model,

                            cr.processing_time_seconds::double precision
                                AS processing_time_seconds,

                            cr.created_at,
                            cr.completed_at

                        FROM coverage_runs cr

                        JOIN customers c
                            ON c.id =
                                cr.customer_id

                        ORDER BY
                            cr.created_at DESC

                        LIMIT 25;
                    `,

                    sql`
                        SELECT
                            c.id
                                AS customer_id,

                            c.name
                                AS customer_name,

                            COUNT(cr.id)::integer
                                AS total_runs,

                            COUNT(cr.id) FILTER (
                                WHERE cr.status =
                                    'completed'
                            )::integer
                                AS completed_runs,

                            AVG(
                                cr.processing_time_seconds
                            ) FILTER (
                                WHERE
                                    cr.processing_time_seconds
                                        IS NOT NULL
                            )::double precision
                                AS average_processing_time_seconds

                        FROM customers c

                        LEFT JOIN coverage_runs cr
                            ON cr.customer_id =
                                c.id

                        GROUP BY
                            c.id,
                            c.name

                        ORDER BY
                            total_runs DESC,
                            c.name;
                    `,
                ]);
        } else {
            [
                summaryRows,
                statusRows,
                modelRows,
                recentRunRows,
                customerUsageRows,
            ] =
                await Promise.all([
                    sql`
                        SELECT
                            COUNT(*)::integer
                                AS total_runs,

                            COUNT(*) FILTER (
                                WHERE status =
                                    'completed'
                            )::integer
                                AS completed_runs,

                            AVG(
                                processing_time_seconds
                            ) FILTER (
                                WHERE
                                    processing_time_seconds
                                        IS NOT NULL
                            )::double precision
                                AS average_processing_time_seconds

                        FROM coverage_runs

                        WHERE customer_id =
                            ANY(
                                ${customerAdminIds}::uuid[]
                            );
                    `,

                    sql`
                        SELECT
                            status,

                            COUNT(*)::integer
                                AS run_count

                        FROM coverage_runs

                        WHERE customer_id =
                            ANY(
                                ${customerAdminIds}::uuid[]
                            )

                        GROUP BY
                            status

                        ORDER BY
                            run_count DESC,
                            status;
                    `,

                    sql`
                        SELECT
                            propagation_model,

                            COUNT(*)::integer
                                AS run_count

                        FROM coverage_runs

                        WHERE customer_id =
                            ANY(
                                ${customerAdminIds}::uuid[]
                            )

                        GROUP BY
                            propagation_model

                        ORDER BY
                            run_count DESC,
                            propagation_model
                                NULLS LAST;
                    `,

                    sql`
                        SELECT
                            cr.id,
                            cr.customer_id,
                            c.name
                                AS customer_name,
                            cr.scenario_id,
                            cr.status,
                            cr.propagation_model,

                            cr.processing_time_seconds::double precision
                                AS processing_time_seconds,

                            cr.created_at,
                            cr.completed_at

                        FROM coverage_runs cr

                        JOIN customers c
                            ON c.id =
                                cr.customer_id

                        WHERE cr.customer_id =
                            ANY(
                                ${customerAdminIds}::uuid[]
                            )

                        ORDER BY
                            cr.created_at DESC

                        LIMIT 25;
                    `,

                    sql`
                        SELECT
                            c.id
                                AS customer_id,

                            c.name
                                AS customer_name,

                            COUNT(cr.id)::integer
                                AS total_runs,

                            COUNT(cr.id) FILTER (
                                WHERE cr.status =
                                    'completed'
                            )::integer
                                AS completed_runs,

                            AVG(
                                cr.processing_time_seconds
                            ) FILTER (
                                WHERE
                                    cr.processing_time_seconds
                                        IS NOT NULL
                            )::double precision
                                AS average_processing_time_seconds

                        FROM customers c

                        LEFT JOIN coverage_runs cr
                            ON cr.customer_id =
                                c.id

                        WHERE c.id =
                            ANY(
                                ${customerAdminIds}::uuid[]
                            )

                        GROUP BY
                            c.id,
                            c.name

                        ORDER BY
                            total_runs DESC,
                            c.name;
                    `,
                ]);
        }

        const summary =
            (
                summaryRows as unknown as
                    SummaryRow[]
            )[0];

        return NextResponse.json({
            status: "ok",

            scope: {
                platformWide:
                    isGeoVarisAdmin,

                customerIds:
                    isGeoVarisAdmin
                        ? null
                        : customerAdminIds,
            },

            summary: {
                totalRuns:
                    summary?.total_runs ??
                    0,

                completedRuns:
                    summary?.completed_runs ??
                    0,

                averageProcessingTimeSeconds:
                    summary
                        ?.average_processing_time_seconds ??
                    null,
            },

            runsByStatus:
                (
                    statusRows as unknown as
                        StatusRow[]
                ).map(
                    (row) => ({
                        status:
                            row.status,

                        runCount:
                            row.run_count,
                    }),
                ),

            runsByModel:
                (
                    modelRows as unknown as
                        ModelRow[]
                ).map(
                    (row) => ({
                        propagationModel:
                            row.propagation_model,

                        runCount:
                            row.run_count,
                    }),
                ),

            recentRuns:
                (
                    recentRunRows as unknown as
                        RecentRunRow[]
                ).map(
                    (row) => ({
                        id:
                            row.id,

                        customerId:
                            row.customer_id,

                        customerName:
                            row.customer_name,

                        scenarioId:
                            row.scenario_id,

                        status:
                            row.status,

                        propagationModel:
                            row.propagation_model,

                        processingTimeSeconds:
                            row.processing_time_seconds,

                        createdAt:
                            row.created_at,

                        completedAt:
                            row.completed_at,
                    }),
                ),

            usageByCustomer:
                (
                    customerUsageRows as unknown as
                        CustomerUsageRow[]
                ).map(
                    (row) => ({
                        customerId:
                            row.customer_id,

                        customerName:
                            row.customer_name,

                        totalRuns:
                            row.total_runs,

                        completedRuns:
                            row.completed_runs,

                        averageProcessingTimeSeconds:
                            row.average_processing_time_seconds,
                    }),
                ),
        });
    } catch (error) {
        console.error(
            "Usage analytics lookup failed:",
            error,
        );

        return NextResponse.json(
            {
                status: "error",
                error:
                    "Unable to load usage analytics.",
            },
            {
                status: 500,
            },
        );
    }
}