"use client";

import {
    useEffect,
    useState,
} from "react";

type CoverageResultKpisProps = {
    scenarioId: string;
};

type CoverageRun = {
    id: string;
    status: string;

    estimated_coverage_radius_m:
        | number
        | null;

    coverage_area_sq_m:
        | number
        | null;

    processing_time_seconds:
        | number
        | null;

    propagation_model: string;

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
};

type CoverageRunResponse = {
    status: string;
    coverageRun: CoverageRun | null;
    error?: string;
};

const METERS_PER_MILE =
    1609.344;

const SQUARE_METERS_PER_SQUARE_MILE =
    2_589_988.110336;

const POLL_INTERVAL_MS =
    3000;

const RAPID_COVERAGE_MODEL =
    "rapid_coverage";

const RAPID_COVERAGE_METHODOLOGY =
    "Terrain/Clutter LOS + Free-Space Link Budget";

const POPULATION_ALLOCATION_METHOD =
    "block_area_weighted";

const POPULATION_GEOMETRY_BASIS =
    "display_geometry";

const FABRIC_GEOMETRY_BASIS =
    "display_geometry";

const SYNTHETIC_FABRIC_DATASET_SOURCE =
    "GeoVaris Synthetic Test Data";

export default function CoverageResultKpis({
    scenarioId,
}: CoverageResultKpisProps) {
    const [
        coverageRun,
        setCoverageRun,
    ] = useState<CoverageRun | null>(
        null,
    );

    const [
        isLoading,
        setIsLoading,
    ] = useState(true);

    const [
        error,
        setError,
    ] = useState("");

    useEffect(() => {
        let isActive = true;

        const abortController =
            new AbortController();

        async function loadCoverageResult(): Promise<void> {
            try {
                const response =
                    await fetch(
                        `/api/coverage-runs/latest?scenarioId=${encodeURIComponent(
                            scenarioId,
                        )}&includeGeometry=false`,
                        {
                            cache:
                                "no-store",
                            signal:
                                abortController.signal,
                        },
                    );

                const data =
                    (await response.json()) as CoverageRunResponse;

                if (!response.ok) {
                    throw new Error(
                        data.error ??
                            "Unable to load coverage result.",
                    );
                }

                if (!isActive) {
                    return;
                }

                setCoverageRun(
                    data.coverageRun,
                );

                setError("");
                setIsLoading(false);
            } catch (err) {
                if (
                    abortController
                        .signal
                        .aborted
                ) {
                    return;
                }

                console.error(
                    "Coverage KPI lookup failed:",
                    err,
                );

                if (isActive) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Unable to load coverage result.",
                    );

                    setIsLoading(
                        false,
                    );
                }
            }
        }

        void loadCoverageResult();

        const intervalId =
            window.setInterval(
                () => {
                    void loadCoverageResult();
                },
                POLL_INTERVAL_MS,
            );

        return () => {
            isActive = false;

            abortController.abort();

            window.clearInterval(
                intervalId,
            );
        };
    }, [
        scenarioId,
    ]);

    if (isLoading) {
        return (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-sm text-slate-500">
                    Loading coverage results...
                </p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6">
                <p className="text-sm text-red-700">
                    {error}
                </p>
            </div>
        );
    }

    if (!coverageRun) {
        return (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-sm font-medium text-slate-700">
                    Waiting for a completed coverage result...
                </p>

                <p className="mt-1 text-sm text-slate-500">
                    Coverage results will update automatically when processing
                    finishes.
                </p>
            </div>
        );
    }

    const isRapidCoverage =
        coverageRun.propagation_model ===
        RAPID_COVERAGE_MODEL;

    const radiusMiles =
        coverageRun.estimated_coverage_radius_m ===
        null
            ? null
            : coverageRun.estimated_coverage_radius_m /
              METERS_PER_MILE;

    const areaSquareMiles =
        coverageRun.coverage_area_sq_m ===
        null
            ? null
            : coverageRun.coverage_area_sq_m /
              SQUARE_METERS_PER_SQUARE_MILE;

    const processingTime =
        coverageRun.processing_time_seconds;

    const hasPopulationEstimate =
        coverageRun.covered_population !==
        null;

    const usesCurrentPopulationMethod =
        coverageRun.population_allocation_method ===
            POPULATION_ALLOCATION_METHOD &&
        coverageRun.population_geometry_basis ===
            POPULATION_GEOMETRY_BASIS;

    const hasLocationAnalytics =
        coverageRun.covered_fabric_locations !==
        null;

    const isSyntheticLocationDataset =
        coverageRun.fabric_dataset_source ===
        SYNTHETIC_FABRIC_DATASET_SOURCE;

    const usesDisplayGeometryForLocations =
        coverageRun.fabric_geometry_basis ===
        FABRIC_GEOMETRY_BASIS;

    const locationKpiLabel =
        isSyntheticLocationDataset
            ? "Synthetic Test Locations Covered"
            : "Estimated Fabric Locations Covered";

    return (
        <div>
            <div className="mb-4 flex items-end justify-between">
                <div>
                    <p className="text-sm font-medium uppercase tracking-wide text-indigo-600">
                        Coverage Results
                    </p>

                    <h3 className="mt-1 text-xl font-semibold text-slate-900">
                        Latest Completed Run
                    </h3>
                </div>

                <p className="text-xs text-slate-400">
                    Auto-refreshing
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
                <ResultCard
                    label="Coverage Area"
                    value={
                        areaSquareMiles ===
                        null
                            ? "—"
                            : `${areaSquareMiles.toLocaleString(
                                  undefined,
                                  {
                                      maximumFractionDigits: 1,
                                  },
                              )} mi²`
                    }
                />

                <ResultCard
                    label="Estimated Population Covered"
                    value={
                        coverageRun.covered_population ===
                        null
                            ? "—"
                            : Math.round(
                                  coverageRun.covered_population,
                              ).toLocaleString()
                    }
                />

                <ResultCard
                    label={locationKpiLabel}
                    value={
                        coverageRun.covered_fabric_locations ===
                        null
                            ? "—"
                            : Math.round(
                                  coverageRun.covered_fabric_locations,
                              ).toLocaleString()
                    }
                />

                <ResultCard
                    label="Run Status"
                    value={formatStatus(
                        coverageRun.status,
                    )}
                />

                <ResultCard
                    label="Processing Time"
                    value={
                        processingTime ===
                        null
                            ? "—"
                            : `${processingTime.toFixed(
                                  3,
                              )} sec`
                    }
                />

                {isRapidCoverage ? (
                    <ResultCard
                        label="Methodology"
                        value={
                            RAPID_COVERAGE_METHODOLOGY
                        }
                        compact
                    />
                ) : (
                    <ResultCard
                        label="Estimated Radius"
                        value={
                            radiusMiles ===
                            null
                                ? "—"
                                : `${radiusMiles.toFixed(
                                      1,
                                  )} mi`
                        }
                    />
                )}
            </div>

            {hasPopulationEstimate ? (
                <p className="mt-3 text-xs text-slate-500">
                    Estimated population coverage uses{" "}
                    {coverageRun.census_vintage ??
                        "the recorded"}{" "}
                    Census block population
                    {usesCurrentPopulationMethod
                        ? ", area-weighted by the portion of each block intersecting the stored coverage display geometry."
                        : "."}
                    {" "}
                    Population coverage is an estimate and does not represent
                    confirmed service to individual people or locations.
                </p>
            ) : null}

            {hasLocationAnalytics &&
            isSyntheticLocationDataset ? (
                <p className="mt-2 text-xs text-amber-700">
                    Synthetic test location analytics use{" "}
                    {coverageRun.fabric_version ??
                        "the recorded synthetic dataset"}
                    {usesDisplayGeometryForLocations
                        ? " and count synthetic points intersecting the stored coverage display geometry."
                        : "."}
                    {" "}
                    These locations are GeoVaris test data and are not FCC
                    Broadband Serviceable Location Fabric records.
                </p>
            ) : null}

            {hasLocationAnalytics &&
            !isSyntheticLocationDataset ? (
                <p className="mt-2 text-xs text-slate-500">
                    Estimated Fabric location coverage counts governed point
                    locations intersecting the stored coverage footprint.
                    {" "}
                    This result is an engineering/GIS estimate and does not
                    establish actual service availability at any location.
                </p>
            ) : null}

            {isRapidCoverage ? (
                <p className="mt-2 text-xs text-slate-500">
                    Rapid Coverage is an engineering estimate based on
                    terrain/clutter line-of-sight and a free-space link budget.
                    It does not guarantee actual service availability.
                </p>
            ) : (
                <p className="mt-2 text-xs text-slate-500">
                    Coverage results are engineering estimates and do not
                    guarantee actual service availability.
                </p>
            )}
        </div>
    );
}

type ResultCardProps = {
    label: string;
    value: string;
    compact?: boolean;
};

function ResultCard({
    label,
    value,
    compact = false,
}: ResultCardProps) {
    return (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">
                {label}
            </p>

            <p
                className={
                    compact
                        ? "mt-2 text-base font-semibold leading-snug text-slate-900"
                        : "mt-2 text-2xl font-semibold text-slate-900"
                }
            >
                {value}
            </p>
        </div>
    );
}

function formatStatus(
    status: string,
): string {
    return status
        .split("_")
        .map(
            (word) =>
                word
                    .charAt(0)
                    .toUpperCase() +
                word.slice(1),
        )
        .join(" ");
}