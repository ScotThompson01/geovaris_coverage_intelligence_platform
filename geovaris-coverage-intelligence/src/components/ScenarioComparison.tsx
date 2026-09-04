"use client";

import {
    useEffect,
    useMemo,
    useState,
} from "react";

type ScenarioOption = {
    scenario_id: string;
    scenario_name: string;
    site_name: string;
    project_name: string;
    customer_id: string;
    customer_name: string;
};

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

type ScenarioComparisonResponse = {
    status: string;
    scenarioA?: ScenarioComparisonRow;
    scenarioB?: ScenarioComparisonRow;
    error?: string;
};

type ScenarioComparisonProps = {
    selectedScenarioId: string;
    options: ScenarioOption[];
};

const SQUARE_METERS_PER_SQUARE_MILE =
    2_589_988.110336;

export default function ScenarioComparison({
    selectedScenarioId,
    options,
}: ScenarioComparisonProps) {
    const selectedScenario =
        options.find(
            (option) =>
                option.scenario_id ===
                selectedScenarioId,
        );

    const customerOptions =
        useMemo(
            () =>
                selectedScenario
                    ? options.filter(
                          (option) =>
                              option.customer_id ===
                              selectedScenario.customer_id,
                      )
                    : [],
            [
                options,
                selectedScenario,
            ],
        );

    const [
        scenarioAId,
        setScenarioAId,
    ] = useState(
        selectedScenarioId,
    );

    const [
        scenarioBId,
        setScenarioBId,
    ] = useState("");

    const [
        comparison,
        setComparison,
    ] = useState<{
        scenarioA: ScenarioComparisonRow;
        scenarioB: ScenarioComparisonRow;
    } | null>(
        null,
    );

    const [
        isLoading,
        setIsLoading,
    ] = useState(false);

    const [
        error,
        setError,
    ] = useState("");

    useEffect(() => {
        setScenarioAId(
            selectedScenarioId,
        );

        const firstAlternative =
            customerOptions.find(
                (option) =>
                    option.scenario_id !==
                    selectedScenarioId,
            );

        setScenarioBId(
            firstAlternative?.scenario_id ??
                "",
        );

        setComparison(
            null,
        );

        setError(
            "",
        );
    }, [
        selectedScenarioId,
        customerOptions,
    ]);

    async function loadComparison(): Promise<void> {
        if (
            !scenarioAId ||
            !scenarioBId
        ) {
            setError(
                "Choose two scenarios to compare.",
            );

            return;
        }

        if (
            scenarioAId ===
            scenarioBId
        ) {
            setError(
                "Choose two different scenarios.",
            );

            return;
        }

        setError(
            "",
        );

        setIsLoading(
            true,
        );

        try {
            const response =
                await fetch(
                    `/api/scenario-comparison?scenarioA=${encodeURIComponent(
                        scenarioAId,
                    )}&scenarioB=${encodeURIComponent(
                        scenarioBId,
                    )}`,
                    {
                        cache:
                            "no-store",
                    },
                );

            const data =
                (await response.json()) as ScenarioComparisonResponse;

            if (
                !response.ok ||
                !data.scenarioA ||
                !data.scenarioB
            ) {
                throw new Error(
                    data.error ??
                        "Unable to load scenario comparison.",
                );
            }

            setComparison({
                scenarioA:
                    data.scenarioA,

                scenarioB:
                    data.scenarioB,
            });
        } catch (err) {
            console.error(
                "Scenario comparison failed:",
                err,
            );

            setComparison(
                null,
            );

            setError(
                err instanceof Error
                    ? err.message
                    : "Unable to load scenario comparison.",
            );
        } finally {
            setIsLoading(
                false,
            );
        }
    }

    if (
        customerOptions.length <
        2
    ) {
        return (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-sm font-medium uppercase tracking-wide text-indigo-600">
                    Scenario Comparison
                </p>

                <h3 className="mt-1 text-xl font-semibold text-slate-900">
                    Compare Coverage Scenarios
                </h3>

                <p className="mt-3 text-sm text-slate-500">
                    At least two scenarios are required within this customer
                    workspace before a comparison can be created.
                </p>
            </div>
        );
    }

    return (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div>
                <p className="text-sm font-medium uppercase tracking-wide text-indigo-600">
                    Scenario Comparison
                </p>

                <h3 className="mt-1 text-xl font-semibold text-slate-900">
                    Compare Coverage Scenarios
                </h3>

                <p className="mt-2 text-sm text-slate-500">
                    Compare engineering inputs and the latest completed coverage
                    results for two scenarios within the same customer workspace.
                </p>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_1fr_auto]">
                <ScenarioSelect
                    id="scenario-comparison-a"
                    label="Scenario A"
                    value={
                        scenarioAId
                    }
                    options={
                        customerOptions
                    }
                    onChange={
                        (value) => {
                            setScenarioAId(
                                value,
                            );

                            setComparison(
                                null,
                            );
                        }
                    }
                />

                <ScenarioSelect
                    id="scenario-comparison-b"
                    label="Scenario B"
                    value={
                        scenarioBId
                    }
                    options={
                        customerOptions
                    }
                    onChange={
                        (value) => {
                            setScenarioBId(
                                value,
                            );

                            setComparison(
                                null,
                            );
                        }
                    }
                />

                <div className="flex items-end">
                    <button
                        type="button"
                        onClick={
                            () => {
                                void loadComparison();
                            }
                        }
                        disabled={
                            isLoading ||
                            !scenarioAId ||
                            !scenarioBId ||
                            scenarioAId ===
                                scenarioBId
                        }
                        className="w-full rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:from-violet-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 lg:w-auto"
                    >
                        {isLoading
                            ? "Comparing..."
                            : "Compare"}
                    </button>
                </div>
            </div>

            {error ? (
                <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    {error}
                </p>
            ) : null}

            {comparison ? (
                <div className="mt-8">
                    <ComparisonTable
                        scenarioA={
                            comparison.scenarioA
                        }
                        scenarioB={
                            comparison.scenarioB
                        }
                    />
                </div>
            ) : null}
        </div>
    );
}

type ScenarioSelectProps = {
    id: string;
    label: string;
    value: string;
    options: ScenarioOption[];
    onChange: (
        value: string,
    ) => void;
};

function ScenarioSelect({
    id,
    label,
    value,
    options,
    onChange,
}: ScenarioSelectProps) {
    return (
        <div>
            <label
                htmlFor={
                    id
                }
                className="block text-sm font-medium text-slate-700"
            >
                {label}
            </label>

            <select
                id={
                    id
                }
                value={
                    value
                }
                onChange={
                    (event) =>
                        onChange(
                            event.target.value,
                        )
                }
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900"
            >
                <option value="">
                    Select scenario
                </option>

                {options.map(
                    (option) => (
                        <option
                            key={
                                option.scenario_id
                            }
                            value={
                                option.scenario_id
                            }
                        >
                            {
                                option.project_name
                            }
                            {" — "}
                            {
                                option.site_name
                            }
                            {" — "}
                            {
                                option.scenario_name
                            }
                        </option>
                    ),
                )}
            </select>
        </div>
    );
}

type ComparisonTableProps = {
    scenarioA: ScenarioComparisonRow;
    scenarioB: ScenarioComparisonRow;
};

function ComparisonTable({
    scenarioA,
    scenarioB,
}: ComparisonTableProps) {
    return (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                    <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Metric
                        </th>

                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Scenario A
                        </th>

                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Scenario B
                        </th>

                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Change B − A
                        </th>
                    </tr>
                </thead>

                <tbody className="divide-y divide-slate-100 bg-white">
                    <TextRow
                        label="Scenario"
                        valueA={
                            scenarioA.scenario_name
                        }
                        valueB={
                            scenarioB.scenario_name
                        }
                    />

                    <TextRow
                        label="Site"
                        valueA={
                            scenarioA.site_name
                        }
                        valueB={
                            scenarioB.site_name
                        }
                    />

                    <NumericRow
                        label="Frequency"
                        valueA={
                            scenarioA.frequency_mhz
                        }
                        valueB={
                            scenarioB.frequency_mhz
                        }
                        suffix=" MHz"
                        maximumFractionDigits={
                            3
                        }
                    />

                    <NumericRow
                        label="EIRP"
                        valueA={
                            scenarioA.eirp_watts
                        }
                        valueB={
                            scenarioB.eirp_watts
                        }
                        suffix=" W"
                        maximumFractionDigits={
                            3
                        }
                    />

                    <NumericRow
                        label="Antenna Height"
                        valueA={
                            scenarioA.antenna_height_m
                        }
                        valueB={
                            scenarioB.antenna_height_m
                        }
                        suffix=" m"
                        maximumFractionDigits={
                            3
                        }
                    />

                    <NumericRow
                        label="Receiver Threshold"
                        valueA={
                            scenarioA.receiver_threshold_dbm
                        }
                        valueB={
                            scenarioB.receiver_threshold_dbm
                        }
                        suffix=" dBm"
                        maximumFractionDigits={
                            1
                        }
                    />

                    <TextRow
                        label="Propagation Model"
                        valueA={
                            formatPropagationModel(
                                scenarioA.propagation_model,
                            )
                        }
                        valueB={
                            formatPropagationModel(
                                scenarioB.propagation_model,
                            )
                        }
                    />

                    <NumericRow
                        label="Coverage Area"
                        valueA={
                            toSquareMiles(
                                scenarioA.coverage_area_sq_m,
                            )
                        }
                        valueB={
                            toSquareMiles(
                                scenarioB.coverage_area_sq_m,
                            )
                        }
                        suffix=" mi²"
                        maximumFractionDigits={
                            1
                        }
                    />

                    <NumericRow
                        label="Estimated Population Covered"
                        valueA={
                            scenarioA.covered_population
                        }
                        valueB={
                            scenarioB.covered_population
                        }
                        maximumFractionDigits={
                            0
                        }
                    />

                    <NumericRow
                        label="Fabric / Location Points Covered"
                        valueA={
                            scenarioA.covered_fabric_locations
                        }
                        valueB={
                            scenarioB.covered_fabric_locations
                        }
                        maximumFractionDigits={
                            0
                        }
                    />
                </tbody>
            </table>

            <div className="border-t border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs text-slate-500">
                    Comparison values are based on each scenario&apos;s latest
                    completed coverage run. RF and GIS results are engineering
                    estimates and do not guarantee actual service availability.
                </p>
            </div>
        </div>
    );
}

type TextRowProps = {
    label: string;
    valueA: string;
    valueB: string;
};

function TextRow({
    label,
    valueA,
    valueB,
}: TextRowProps) {
    return (
        <tr>
            <MetricLabel>
                {label}
            </MetricLabel>

            <ValueCell>
                {valueA}
            </ValueCell>

            <ValueCell>
                {valueB}
            </ValueCell>

            <ValueCell>
                —
            </ValueCell>
        </tr>
    );
}

type NumericRowProps = {
    label: string;

    valueA:
        | number
        | null;

    valueB:
        | number
        | null;

    suffix?: string;

    maximumFractionDigits?: number;
};

function NumericRow({
    label,
    valueA,
    valueB,
    suffix = "",
    maximumFractionDigits = 2,
}: NumericRowProps) {
    const delta =
        valueA === null ||
        valueB === null
            ? null
            : valueB -
              valueA;

    return (
        <tr>
            <MetricLabel>
                {label}
            </MetricLabel>

            <ValueCell>
                {formatMetric(
                    valueA,
                    suffix,
                    maximumFractionDigits,
                )}
            </ValueCell>

            <ValueCell>
                {formatMetric(
                    valueB,
                    suffix,
                    maximumFractionDigits,
                )}
            </ValueCell>

            <td className="whitespace-nowrap px-4 py-3 text-sm font-semibold">
                <DeltaValue
                    value={
                        delta
                    }
                    suffix={
                        suffix
                    }
                    maximumFractionDigits={
                        maximumFractionDigits
                    }
                />
            </td>
        </tr>
    );
}

function MetricLabel({
    children,
}: {
    children:
        React.ReactNode;
}) {
    return (
        <th
            scope="row"
            className="whitespace-nowrap px-4 py-3 text-left text-sm font-medium text-slate-700"
        >
            {children}
        </th>
    );
}

function ValueCell({
    children,
}: {
    children:
        React.ReactNode;
}) {
    return (
        <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-700">
            {children}
        </td>
    );
}

type DeltaValueProps = {
    value:
        | number
        | null;

    suffix: string;

    maximumFractionDigits:
        number;
};

function DeltaValue({
    value,
    suffix,
    maximumFractionDigits,
}: DeltaValueProps) {
    if (value === null) {
        return (
            <span className="text-slate-400">
                —
            </span>
        );
    }

    const className =
        value > 0
            ? "text-emerald-700"
            : value < 0
              ? "text-red-700"
              : "text-slate-500";

    const prefix =
        value > 0
            ? "+"
            : "";

    return (
        <span
            className={
                className
            }
        >
            {prefix}
            {value.toLocaleString(
                undefined,
                {
                    maximumFractionDigits,
                },
            )}
            {suffix}
        </span>
    );
}

function formatMetric(
    value:
        | number
        | null,
    suffix: string,
    maximumFractionDigits:
        number,
): string {
    if (value === null) {
        return "—";
    }

    return `${value.toLocaleString(
        undefined,
        {
            maximumFractionDigits,
        },
    )}${suffix}`;
}

function toSquareMiles(
    squareMeters:
        | number
        | null,
): number | null {
    if (
        squareMeters === null
    ) {
        return null;
    }

    return (
        squareMeters /
        SQUARE_METERS_PER_SQUARE_MILE
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