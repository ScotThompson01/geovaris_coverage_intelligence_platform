import CoverageMap from "@/components/CoverageMap";
import CoverageResultKpis from "@/components/CoverageResultKpis";
import CreateCoverageRunButton from "@/components/CreateCoverageRunButton";
import CreateScenarioForm from "@/components/CreateScenarioForm";
import CreateSiteForm from "@/components/CreateSiteForm";
import ScenarioSelector from "@/components/ScenarioSelector";
import SignInForm from "@/components/SignInForm";
import SignOutButton from "@/components/SignOutButton";

import {
    getGeoVarisAuthContext,
} from "@/lib/auth-context";

import { sql } from "@/lib/db";

type ScenarioRow = {
    scenario_id: string;
    customer_id: string;
    customer_name: string;
    project_name: string;
    site_name: string;
    latitude: number;
    longitude: number;
    scenario_name: string;
    frequency_mhz: number;
    eirp_watts: number;
    antenna_height_m: number;
    receiver_threshold_dbm: number;
    propagation_model: string;
};

type ScenarioOptionRow = {
    scenario_id: string;
    scenario_name: string;
    site_name: string;
    project_name: string;
    customer_name: string;
};

type LatestCoverageRunRow = {
    propagation_model: string;
    propagation_model_version: string | null;
};

type HomeProps = {
    searchParams?: Promise<{
        scenarioId?: string;
    }>;
};

export default async function Home({
    searchParams,
}: HomeProps) {
    const authContext =
        await getGeoVarisAuthContext();

    if (!authContext) {
        return <SignInForm />;
    }

    const resolvedSearchParams =
        (await searchParams) ?? {};

    const requestedScenarioId =
        resolvedSearchParams.scenarioId;

    const readableCustomerIds =
        authContext.customerMemberships.map(
            (membership) =>
                membership.customerId,
        );

    const writableRoles =
        new Set([
            "customer_admin",
            "engineer",
        ]);

    const writableCustomerIds =
        authContext.customerMemberships
            .filter(
                (membership) =>
                    writableRoles.has(
                        membership.role,
                    ),
            )
            .map(
                (membership) =>
                    membership.customerId,
            );

    const canCreateResources =
        authContext.isGeoVarisAdmin ||
        writableCustomerIds.length > 0;

    let scenarioOptions:
        ScenarioOptionRow[];

    if (
        authContext.isGeoVarisAdmin
    ) {
        scenarioOptions = (await sql`
            SELECT
                sc.id AS scenario_id,
                sc.name AS scenario_name,
                s.name AS site_name,
                p.name AS project_name,
                c.name AS customer_name

            FROM customers c

            JOIN projects p
                ON p.customer_id =
                    c.id

            JOIN sites s
                ON s.project_id =
                    p.id
                AND s.customer_id =
                    c.id

            JOIN scenarios sc
                ON sc.site_id =
                    s.id
                AND sc.customer_id =
                    c.id

            ORDER BY
                sc.created_at DESC;
        `) as unknown as ScenarioOptionRow[];
    } else if (
        readableCustomerIds.length === 0
    ) {
        scenarioOptions = [];
    } else {
        scenarioOptions = (await sql`
            SELECT
                sc.id AS scenario_id,
                sc.name AS scenario_name,
                s.name AS site_name,
                p.name AS project_name,
                c.name AS customer_name

            FROM customers c

            JOIN projects p
                ON p.customer_id =
                    c.id

            JOIN sites s
                ON s.project_id =
                    p.id
                AND s.customer_id =
                    c.id

            JOIN scenarios sc
                ON sc.site_id =
                    s.id
                AND sc.customer_id =
                    c.id

            WHERE c.id =
                ANY(
                    ${readableCustomerIds}::uuid[]
                )

            ORDER BY
                sc.created_at DESC;
        `) as unknown as ScenarioOptionRow[];
    }

    if (
        scenarioOptions.length === 0
    ) {
        return (
            <main className="min-h-screen bg-slate-50">
                <AppHeader
                    userName={
                        authContext.userName
                    }
                />

                <div className="mx-auto max-w-7xl px-6 py-8">
                    <p className="text-slate-600">
                        No coverage scenario data was found for your authorized
                        customer workspace.
                    </p>

                    {canCreateResources ? (
                        <>
                            <section className="mt-8">
                                <CreateSiteForm />
                            </section>

                            <section className="mt-8">
                                <CreateScenarioForm />
                            </section>
                        </>
                    ) : (
                        <div className="mt-8 rounded-lg border border-slate-200 bg-white px-4 py-3">
                            <p className="text-sm font-medium text-slate-700">
                                Read-only access
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                                Your role does not permit creating sites or
                                scenarios.
                            </p>
                        </div>
                    )}
                </div>
            </main>
        );
    }

    const selectedScenarioId =
        requestedScenarioId &&
        scenarioOptions.some(
            (option) =>
                option.scenario_id ===
                requestedScenarioId,
        )
            ? requestedScenarioId
            : scenarioOptions[0].scenario_id;

    let rows:
        ScenarioRow[];

    if (
        authContext.isGeoVarisAdmin
    ) {
        rows = (await sql`
            SELECT
                c.id AS customer_id,
                c.name AS customer_name,
                p.name AS project_name,
                s.name AS site_name,
                s.latitude,
                s.longitude,

                sc.id AS scenario_id,
                sc.name AS scenario_name,
                sc.frequency_mhz,
                sc.eirp_watts,
                sc.antenna_height_m,
                sc.receiver_threshold_dbm,
                sc.propagation_model

            FROM customers c

            JOIN projects p
                ON p.customer_id =
                    c.id

            JOIN sites s
                ON s.project_id =
                    p.id
                AND s.customer_id =
                    c.id

            JOIN scenarios sc
                ON sc.site_id =
                    s.id
                AND sc.customer_id =
                    c.id

            WHERE sc.id =
                ${selectedScenarioId}

            LIMIT 1;
        `) as unknown as ScenarioRow[];
    } else {
        rows = (await sql`
            SELECT
                c.id AS customer_id,
                c.name AS customer_name,
                p.name AS project_name,
                s.name AS site_name,
                s.latitude,
                s.longitude,

                sc.id AS scenario_id,
                sc.name AS scenario_name,
                sc.frequency_mhz,
                sc.eirp_watts,
                sc.antenna_height_m,
                sc.receiver_threshold_dbm,
                sc.propagation_model

            FROM customers c

            JOIN projects p
                ON p.customer_id =
                    c.id

            JOIN sites s
                ON s.project_id =
                    p.id
                AND s.customer_id =
                    c.id

            JOIN scenarios sc
                ON sc.site_id =
                    s.id
                AND sc.customer_id =
                    c.id

            WHERE sc.id =
                ${selectedScenarioId}

              AND c.id =
                ANY(
                    ${readableCustomerIds}::uuid[]
                )

            LIMIT 1;
        `) as unknown as ScenarioRow[];
    }

    const scenario =
        rows[0];

    if (!scenario) {
        return (
            <main className="min-h-screen bg-slate-50">
                <AppHeader
                    userName={
                        authContext.userName
                    }
                />

                <div className="mx-auto max-w-7xl px-6 py-8">
                    <p className="text-slate-600">
                        The selected scenario could not be found in your
                        authorized customer workspace.
                    </p>
                </div>
            </main>
        );
    }

    const canWriteSelectedScenario =
        authContext.isGeoVarisAdmin ||
        writableCustomerIds.includes(
            scenario.customer_id,
        );

    const latestCoverageRuns = (await sql`
        SELECT
            propagation_model,
            propagation_model_version

        FROM coverage_runs

        WHERE scenario_id =
            ${scenario.scenario_id}

          AND customer_id =
            ${scenario.customer_id}

          AND status =
            'completed'

        ORDER BY
            completed_at DESC NULLS LAST,
            created_at DESC

        LIMIT 1;
    `) as unknown as LatestCoverageRunRow[];

    const latestCoverageRun =
        latestCoverageRuns[0] ??
        null;

    return (
        <main className="min-h-screen bg-slate-50">
            <AppHeader
                userName={
                    authContext.userName
                }
            />

            <div className="mx-auto max-w-7xl px-6 py-8">
                <section className="mb-8">
                    <p className="text-sm font-medium uppercase tracking-wide text-indigo-600">
                        Coverage Scenario
                    </p>

                    <ScenarioSelector
                        selectedScenarioId={
                            scenario.scenario_id
                        }
                        options={
                            scenarioOptions
                        }
                    />

                    <h2 className="mt-5 text-3xl font-semibold text-slate-900">
                        {scenario.site_name}
                    </h2>

                    <p className="mt-2 text-slate-600">
                        {scenario.customer_name}
                        {" · "}
                        {scenario.project_name}
                        {" · "}
                        {scenario.scenario_name}
                    </p>
                </section>

                <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                    <MetricCard
                        label="Frequency"
                        value={`${formatNumber(
                            scenario.frequency_mhz,
                        )} MHz`}
                    />

                    <MetricCard
                        label="EIRP"
                        value={`${formatNumber(
                            scenario.eirp_watts,
                        )} W`}
                    />

                    <MetricCard
                        label="Antenna Height"
                        value={`${formatNumber(
                            scenario.antenna_height_m,
                            3,
                        )} m`}
                    />

                    <MetricCard
                        label="Receiver Threshold"
                        value={`${formatNumber(
                            scenario.receiver_threshold_dbm,
                        )} dBm`}
                    />
                </section>

                {canWriteSelectedScenario ? (
                    <section className="mt-6">
                        <CreateCoverageRunButton
                            scenarioId={
                                scenario.scenario_id
                            }
                        />
                    </section>
                ) : (
                    <section className="mt-6">
                        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
                            <p className="text-sm font-medium text-slate-700">
                                Read-only access
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                                Your role allows you to view this coverage
                                analysis, but not create new coverage runs.
                            </p>
                        </div>
                    </section>
                )}

                <section className="mt-8">
                    <CoverageResultKpis
                        scenarioId={
                            scenario.scenario_id
                        }
                    />
                </section>

                <section className="mt-8 grid gap-6 lg:grid-cols-3">
                    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
                        <div>
                            <h3 className="text-lg font-semibold text-slate-900">
                                Coverage Map
                            </h3>

                            <p className="mt-1 text-sm text-slate-500">
                                Interactive site and RF coverage visualization.
                            </p>
                        </div>

                        <div className="mt-6 overflow-hidden rounded-lg border border-slate-200">
                            <CoverageMap
                                latitude={
                                    scenario.latitude
                                }
                                longitude={
                                    scenario.longitude
                                }
                                siteName={
                                    scenario.site_name
                                }
                                scenarioId={
                                    scenario.scenario_id
                                }
                            />
                        </div>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h3 className="text-lg font-semibold text-slate-900">
                            Site Details
                        </h3>

                        <dl className="mt-6 space-y-5">
                            <DetailRow
                                label="Latitude"
                                value={Number(
                                    scenario.latitude,
                                ).toFixed(4)}
                            />

                            <DetailRow
                                label="Longitude"
                                value={Number(
                                    scenario.longitude,
                                ).toFixed(4)}
                            />

                            <DetailRow
                                label="Scenario Model"
                                value={formatPropagationModel(
                                    scenario.propagation_model,
                                )}
                            />

                            <DetailRow
                                label="Latest Run Method"
                                value={
                                    latestCoverageRun
                                        ? formatPropagationModel(
                                              latestCoverageRun.propagation_model,
                                          )
                                        : "No completed run"
                                }
                            />

                            {latestCoverageRun?.propagation_model_version ? (
                                <DetailRow
                                    label="Run Method Version"
                                    value={
                                        latestCoverageRun.propagation_model_version
                                    }
                                />
                            ) : null}

                            <DetailRow
                                label="Scenario"
                                value={
                                    scenario.scenario_name
                                }
                            />

                            <DetailRow
                                label="Project"
                                value={
                                    scenario.project_name
                                }
                            />
                        </dl>
                    </div>
                </section>

                {canCreateResources ? (
                    <>
                        <section className="mt-8">
                            <CreateSiteForm />
                        </section>

                        <section className="mt-8">
                            <CreateScenarioForm />
                        </section>
                    </>
                ) : null}
            </div>
        </main>
    );
}

type AppHeaderProps = {
    userName: string;
};

function AppHeader({
    userName,
}: AppHeaderProps) {
    return (
        <header className="border-b border-slate-200 bg-white">
            <div className="mx-auto max-w-7xl px-6 py-5">
                <div className="flex items-center justify-between gap-6">
                    <div>
                        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
                            GeoVaris Coverage Intelligence
                        </h1>

                        <p className="mt-1 text-sm text-slate-500">
                            Clean data. Confident results.
                        </p>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="hidden text-right sm:block">
                            <p className="text-sm font-medium text-slate-800">
                                {userName}
                            </p>

                            <p className="text-xs text-slate-500">
                                Authenticated
                            </p>
                        </div>

                        <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                            Development
                        </span>

                        <SignOutButton />
                    </div>
                </div>
            </div>
        </header>
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

            <p className="mt-2 text-2xl font-semibold text-slate-900">
                {value}
            </p>
        </div>
    );
}

type DetailRowProps = {
    label: string;
    value: string;
};

function DetailRow({
    label,
    value,
}: DetailRowProps) {
    return (
        <div>
            <dt className="text-sm font-medium text-slate-500">
                {label}
            </dt>

            <dd className="mt-1 break-words text-sm font-medium text-slate-900">
                {value}
            </dd>
        </div>
    );
}

function formatPropagationModel(
    model: string,
): string {
    switch (model) {
        case "rapid_coverage":
            return "Rapid Coverage";

        case "ntia_itm":
            return "NTIA ITM";

        case "free_space_test":
            return "Free Space Test";

        default:
            return model;
    }
}

function formatNumber(
    value: number,
    maximumFractionDigits = 3,
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