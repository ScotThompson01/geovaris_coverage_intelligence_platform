import Link from "next/link";

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

export default async function AdminPage() {
    const authContext =
        await getGeoVarisAuthContext();

    if (!authContext) {
        return (
            <main className="min-h-screen bg-slate-50">
                <div className="mx-auto max-w-5xl px-6 py-10">
                    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h1 className="text-2xl font-semibold text-slate-900">
                            Administrative access required
                        </h1>

                        <p className="mt-2 text-slate-600">
                            Sign in to view usage analytics.
                        </p>
                    </div>
                </div>
            </main>
        );
    }

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
        return (
            <main className="min-h-screen bg-slate-50">
                <div className="mx-auto max-w-5xl px-6 py-10">
                    <Link
                        href="/"
                        className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
                    >
                        ← Back to Coverage Intelligence
                    </Link>

                    <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h1 className="text-2xl font-semibold text-slate-900">
                            Administrative access required
                        </h1>

                        <p className="mt-2 text-slate-600">
                            This dashboard is available only to GeoVaris
                            administrators and customer administrators.
                        </p>
                    </div>
                </div>
            </main>
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

    const statuses =
        statusRows as unknown as
            StatusRow[];

    const models =
        modelRows as unknown as
            ModelRow[];

    const recentRuns =
        recentRunRows as unknown as
            RecentRunRow[];

    const customerUsage =
        customerUsageRows as unknown as
            CustomerUsageRow[];

    return (
        <main className="min-h-screen bg-slate-50">
            <div className="mx-auto max-w-7xl px-6 py-8">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <p className="text-sm font-medium uppercase tracking-wide text-indigo-600">
                            Administration
                        </p>

                        <h1 className="mt-1 text-3xl font-semibold text-slate-900">
                            Usage Analytics
                        </h1>

                        <p className="mt-2 text-slate-600">
                            Coverage run activity, processing usage, and customer
                            adoption.
                        </p>
                    </div>

                    <Link
                        href="/"
                        className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
                    >
                        Back to Coverage Intelligence
                    </Link>
                </div>

                <section className="mt-8 grid gap-4 md:grid-cols-3">
                    <MetricCard
                        label="Total Coverage Runs"
                        value={formatInteger(
                            summary?.total_runs ??
                                0,
                        )}
                    />

                    <MetricCard
                        label="Completed Runs"
                        value={formatInteger(
                            summary?.completed_runs ??
                                0,
                        )}
                    />

                    <MetricCard
                        label="Average Processing Time"
                        value={
                            summary
                                ?.average_processing_time_seconds ===
                            null ||
                            summary
                                ?.average_processing_time_seconds ===
                                undefined
                                ? "—"
                                : `${formatNumber(
                                      summary.average_processing_time_seconds,
                                      1,
                                  )} sec`
                        }
                    />
                </section>

                <section className="mt-8 grid gap-6 lg:grid-cols-2">
                    <Panel
                        title="Runs by Status"
                        description="Current run distribution across recorded workflow states."
                    >
                        <div className="space-y-3">
                            {statuses.map(
                                (row) => (
                                    <StatRow
                                        key={
                                            row.status
                                        }
                                        label={
                                            row.status
                                        }
                                        value={formatInteger(
                                            row.run_count,
                                        )}
                                    />
                                ),
                            )}
                        </div>
                    </Panel>

                    <Panel
                        title="Runs by Model"
                        description="Coverage calculation usage by propagation method."
                    >
                        <div className="space-y-3">
                            {models.map(
                                (row) => (
                                    <StatRow
                                        key={
                                            row.propagation_model ??
                                            "unknown"
                                        }
                                        label={formatPropagationModel(
                                            row.propagation_model,
                                        )}
                                        value={formatInteger(
                                            row.run_count,
                                        )}
                                    />
                                ),
                            )}
                        </div>
                    </Panel>
                </section>

                <section className="mt-8">
                    <Panel
                        title={
                            isGeoVarisAdmin
                                ? "Usage by Customer"
                                : "Customer Usage"
                        }
                        description={
                            isGeoVarisAdmin
                                ? "Platform-wide coverage run activity grouped by customer."
                                : "Coverage run activity for your administered customer workspace."
                        }
                    >
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-slate-200">
                                <thead>
                                    <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                                        <th className="pb-3 pr-6">
                                            Customer
                                        </th>

                                        <th className="pb-3 pr-6">
                                            Total Runs
                                        </th>

                                        <th className="pb-3 pr-6">
                                            Completed
                                        </th>

                                        <th className="pb-3">
                                            Avg Processing
                                        </th>
                                    </tr>
                                </thead>

                                <tbody className="divide-y divide-slate-100">
                                    {customerUsage.map(
                                        (row) => (
                                            <tr
                                                key={
                                                    row.customer_id
                                                }
                                            >
                                                <td className="py-3 pr-6 text-sm font-medium text-slate-900">
                                                    {
                                                        row.customer_name
                                                    }
                                                </td>

                                                <td className="py-3 pr-6 text-sm text-slate-700">
                                                    {formatInteger(
                                                        row.total_runs,
                                                    )}
                                                </td>

                                                <td className="py-3 pr-6 text-sm text-slate-700">
                                                    {formatInteger(
                                                        row.completed_runs,
                                                    )}
                                                </td>

                                                <td className="py-3 text-sm text-slate-700">
                                                    {row.average_processing_time_seconds ===
                                                    null
                                                        ? "—"
                                                        : `${formatNumber(
                                                              row.average_processing_time_seconds,
                                                              1,
                                                          )} sec`}
                                                </td>
                                            </tr>
                                        ),
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </Panel>
                </section>

                <section className="mt-8">
                    <Panel
                        title="Recent Coverage Runs"
                        description="The 25 most recently created coverage runs in your authorized administrative scope."
                    >
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-slate-200">
                                <thead>
                                    <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                                        <th className="pb-3 pr-6">
                                            Customer
                                        </th>

                                        <th className="pb-3 pr-6">
                                            Status
                                        </th>

                                        <th className="pb-3 pr-6">
                                            Model
                                        </th>

                                        <th className="pb-3 pr-6">
                                            Processing
                                        </th>

                                        <th className="pb-3">
                                            Created
                                        </th>
                                    </tr>
                                </thead>

                                <tbody className="divide-y divide-slate-100">
                                    {recentRuns.map(
                                        (run) => (
                                            <tr
                                                key={
                                                    run.id
                                                }
                                            >
                                                <td className="py-3 pr-6 text-sm font-medium text-slate-900">
                                                    {
                                                        run.customer_name
                                                    }
                                                </td>

                                                <td className="py-3 pr-6 text-sm text-slate-700">
                                                    {
                                                        run.status
                                                    }
                                                </td>

                                                <td className="py-3 pr-6 text-sm text-slate-700">
                                                    {formatPropagationModel(
                                                        run.propagation_model,
                                                    )}
                                                </td>

                                                <td className="py-3 pr-6 text-sm text-slate-700">
                                                    {run.processing_time_seconds ===
                                                    null
                                                        ? "—"
                                                        : `${formatNumber(
                                                              run.processing_time_seconds,
                                                              1,
                                                          )} sec`}
                                                </td>

                                                <td className="py-3 text-sm text-slate-700">
                                                    {formatTimestamp(
                                                        run.created_at,
                                                    )}
                                                </td>
                                            </tr>
                                        ),
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </Panel>
                </section>

                <section className="mt-8 rounded-xl border border-indigo-100 bg-indigo-50 p-5">
                    <p className="text-sm font-medium text-indigo-900">
                        Administrative scope
                    </p>

                    <p className="mt-1 text-sm text-indigo-800">
                        {isGeoVarisAdmin
                            ? "You are viewing platform-wide GeoVaris usage analytics."
                            : "You are viewing usage only for customer workspaces where you hold the Customer Admin role."}
                    </p>
                </section>
            </div>
        </main>
    );
}

type MetricCardProps = {
    label: string;
    value: string;
};

function MetricCard({
    label,
    value,
}: MetricCardProps) {
    return (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">
                {label}
            </p>

            <p className="mt-2 text-3xl font-semibold text-slate-900">
                {value}
            </p>
        </div>
    );
}

type PanelProps = {
    title: string;
    description: string;
    children: React.ReactNode;
};

function Panel({
    title,
    description,
    children,
}: PanelProps) {
    return (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">
                {title}
            </h2>

            <p className="mt-1 text-sm text-slate-500">
                {description}
            </p>

            <div className="mt-6">
                {children}
            </div>
        </div>
    );
}

type StatRowProps = {
    label: string;
    value: string;
};

function StatRow({
    label,
    value,
}: StatRowProps) {
    return (
        <div className="flex items-center justify-between gap-4 rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
            <span className="text-sm font-medium text-slate-700">
                {label}
            </span>

            <span className="text-sm font-semibold text-slate-900">
                {value}
            </span>
        </div>
    );
}

function formatPropagationModel(
    model:
        | string
        | null,
): string {
    switch (model) {
        case "rapid_coverage":
            return "Rapid Coverage";

        case "ntia_itm":
            return "NTIA ITM";

        case "free_space_test":
            return "Free Space Test";

        case null:
            return "Unknown";

        default:
            return model;
    }
}

function formatInteger(
    value: number,
): string {
    return Number(
        value,
    ).toLocaleString();
}

function formatNumber(
    value: number,
    maximumFractionDigits = 2,
): string {
    return Number(
        value,
    ).toLocaleString(
        undefined,
        {
            maximumFractionDigits,
        },
    );
}

function formatTimestamp(
    value:
        | string
        | null,
): string {
    if (!value) {
        return "—";
    }

    const date =
        new Date(
            value,
        );

    if (
        Number.isNaN(
            date.getTime(),
        )
    ) {
        return value;
    }

    return date.toLocaleString();
}