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
const POLL_INTERVAL_MS = 3000;

export default function CoverageResultKpis({
  scenarioId,
}: CoverageResultKpisProps) {
  const [coverageRun, setCoverageRun] =
    useState<CoverageRun | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isActive = true;

    async function loadCoverageResult() {
      try {
        const response = await fetch(
          `/api/coverage-runs/latest?scenarioId=${encodeURIComponent(
            scenarioId,
          )}`,
          {
            cache: "no-store",
          },
        );

        const data =
          (await response.json()) as CoverageRunResponse;

        if (!response.ok) {
          throw new Error(
            data.error ?? "Unable to load coverage result.",
          );
        }

        if (isActive) {
          setCoverageRun(data.coverageRun);
          setError("");
          setIsLoading(false);
        }
      } catch (err) {
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

          setIsLoading(false);
        }
      }
    }

    loadCoverageResult();

    const intervalId = window.setInterval(
      loadCoverageResult,
      POLL_INTERVAL_MS,
    );

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
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
          Waiting for a completed coverage result...
        </p>

        <p className="mt-1 text-sm text-slate-500">
          Coverage results will update automatically when processing
          finishes.
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
    coverageRun.processing_time_seconds;

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