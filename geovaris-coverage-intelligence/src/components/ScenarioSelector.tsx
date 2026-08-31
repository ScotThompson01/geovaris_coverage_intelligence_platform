"use client";

import { useRouter } from "next/navigation";
import {
    useEffect,
    useState,
} from "react";

type ScenarioOption = {
    scenario_id: string;
    scenario_name: string;
    site_name: string;
    project_name: string;
    customer_name: string;
};

type ScenarioSelectorProps = {
    selectedScenarioId: string;
    options: ScenarioOption[];
};

export default function ScenarioSelector({
    selectedScenarioId,
    options,
}: ScenarioSelectorProps) {
    const router = useRouter();

    const [isLoading, setIsLoading] =
        useState(false);

    useEffect(() => {
        setIsLoading(false);
    }, [
        selectedScenarioId,
    ]);

    function handleScenarioChange(
        event: React.ChangeEvent<HTMLSelectElement>,
    ): void {
        const nextScenarioId =
            event.target.value;

        if (
            !nextScenarioId ||
            nextScenarioId === selectedScenarioId
        ) {
            return;
        }

        setIsLoading(true);

        router.push(
            `/?scenarioId=${encodeURIComponent(
                nextScenarioId,
            )}`,
        );
    }

    return (
        <div className="mt-3 max-w-2xl">
            <label
                htmlFor="dashboard-scenario"
                className="block text-sm font-medium text-slate-700"
            >
                Display Scenario
            </label>

            <div className="mt-2">
                <select
                    id="dashboard-scenario"
                    value={selectedScenarioId}
                    onChange={handleScenarioChange}
                    disabled={isLoading}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 disabled:cursor-wait disabled:bg-slate-100"
                >
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
                                    option.customer_name
                                }
                                {" — "}
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

                <p className="mt-2 text-xs text-slate-500">
                    {isLoading
                        ? "Loading selected scenario..."
                        : "Changing the selection loads that scenario immediately."}
                </p>
            </div>
        </div>
    );
}