"use client";

import { useState } from "react";

type CreateCoverageRunButtonProps = {
  scenarioId: string;
};

type CoverageRunResponse = {
  status?: string;
  error?: string;
  coverageRun?: {
    id: string;
    status: string;
    propagation_model?: string;
  };
};

const RAPID_COVERAGE_METHOD = "rapid_coverage";

export default function CreateCoverageRunButton({
  scenarioId,
}: CreateCoverageRunButtonProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleRunCoverage() {
    setMessage("");
    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/coverage-runs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          scenarioId,
          runMethod: RAPID_COVERAGE_METHOD,
        }),
      });

      const data =
        (await response.json()) as CoverageRunResponse;

      if (!response.ok) {
        throw new Error(
          data.error ??
            "Unable to create Rapid Coverage run.",
        );
      }

      setMessage(
        `Rapid Coverage run created: ${
          data.coverageRun?.id ?? "unknown run"
        }`,
      );
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(
          "Unable to create Rapid Coverage run.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleRunCoverage}
        disabled={isSubmitting}
        className="rounded-lg bg-indigo-700 px-5 py-2.5 font-medium text-white hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting
          ? "Creating Rapid Run..."
          : "Run Rapid Coverage"}
      </button>

      <p className="mt-2 text-sm text-slate-500">
        Terrain/Clutter LOS + Free-Space Link Budget
      </p>

      {message && (
        <div className="mt-3 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">
          {message}
        </div>
      )}

      {error && (
        <div className="mt-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  );
}