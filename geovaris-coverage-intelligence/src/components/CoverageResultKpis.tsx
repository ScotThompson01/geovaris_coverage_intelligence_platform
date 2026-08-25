"use client";

import { useEffect, useState } from "react";

type CoverageResultKpisProps = {
  scenarioId: string;
};

type CoverageRun = {
  id: string;
  status: string;
  estimated_coverage_radius_m: number | null;
  coverage_area_sq_m: number | null;
  processing_time_seconds: number | null;
  propagation_model: string;
};

type CoverageRunResponse = {
  status: string;
  coverageRun: CoverageRun | null;
  error?: string;
};

const METERS_PER_MILE = 1609.344;
const SQUARE_METERS_PER_SQUARE_MILE = 2_589_988.110336;

export default function CoverageResultKpis({
  scenarioId,
}: CoverageResultKpisProps) {
  const [coverageRun, setCoverageRun] =
    useState<CoverageRun | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadCoverageResult() {
      setIsLoading(true);
      setError("");

      try {
        const response = await fetch(
          `/api/coverage-runs/latest?scenarioId=${encodeURIComponent(
            scenarioId,
          )}`,
        );

        const data =
          (await response.json()) as CoverageRunResponse;

        if (!response.ok) {
          throw new Error(
            data.error ?? "Unable to load coverage result.",
          );
        }

        setCoverageRun(data.coverageRun);
      } catch (err) {
        console.error(
          "Coverage KPI lookup failed:",
          err,
        );

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load coverage result.",
        );
      } finally {
        setIsLoading(false);
      }
    }

    loadCoverageResult();
  }, [scenarioId]);

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
          No completed coverage result is available yet.
        </p>

        <p className="mt-1 text-sm text-slate-500">
          Create and process a coverage run to display result metrics.
        </p>
      </div>
    );
  }

  const radiusMiles =
    coverageRun.estimated_coverage_radius_m === null
      ? null
      : coverageRun.estimated_coverage_radius_m /
        METERS_PER_MILE;

  const areaSquareMiles =
    coverageRun.coverage_area_sq_m === null
      ? null
      : coverageRun.coverage_area_sq_m /
        SQUARE_METERS_PER_SQUARE_MILE;

  const processingTime =
    coverageRun.processing_time_seconds === null
      ? null
      : coverageRun.processing_time_seconds;

  return (
    <div>
      <div className="mb-4">
        <p className="text-sm font-medium uppercase tracking-wide text-indigo-600">
          Coverage Results
        </p>

        <h3 className="mt-1 text-xl font-semibold text-slate-900">
          Latest Completed Run
        </h3>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <ResultCard
          label="Coverage Area"
          value={
            areaSquareMiles === null
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
          label="Estimated Radius"
          value={
            radiusMiles === null
              ? "—"
              : `${radiusMiles.toFixed(1)} mi`
          }
        />

        <ResultCard
          label="Run Status"
          value={formatStatus(coverageRun.status)}
        />

        <ResultCard
          label="Processing Time"
          value={
            processingTime === null
              ? "—"
              : `${processingTime.toFixed(3)} sec`
          }
        />
      </div>

      <p className="mt-3 text-xs text-slate-500">
        Current results use the free-space development model and do not
        represent terrain-aware or guaranteed service coverage.
      </p>
    </div>
  );
}

type ResultCardProps = {
  label: string;
  value: string;
};

function ResultCard({
  label,
  value,
}: ResultCardProps) {
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

function formatStatus(status: string) {
  return status
    .split("_")
    .map(
      (word) =>
        word.charAt(0).toUpperCase() +
        word.slice(1),
    )
    .join(" ");
}