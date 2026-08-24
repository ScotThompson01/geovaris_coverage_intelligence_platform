"use client";

import { FormEvent, useEffect, useState } from "react";

type Site = {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  project_name: string;
  customer_name: string;
};

type ScenarioResponse = {
  status?: string;
  error?: string;
  scenario?: {
    id: string;
    name: string;
  };
};

export default function CreateScenarioForm() {
  const [sites, setSites] = useState<Site[]>([]);

  const [siteId, setSiteId] = useState("");
  const [name, setName] = useState("");

  const [frequencyMhz, setFrequencyMhz] = useState("600");
  const [eirpWatts, setEirpWatts] = useState("1000");

  const [antennaHeightFt, setAntennaHeightFt] = useState("180");
  const [antennaGainDbi, setAntennaGainDbi] = useState("0");

  const [receiverHeightM, setReceiverHeightM] = useState("1.5");
  const [receiverThresholdDbm, setReceiverThresholdDbm] =
    useState("-95");

  const [calculationRadiusMiles, setCalculationRadiusMiles] =
    useState("30");

  const [resolutionM, setResolutionM] = useState("30");

  const [propagationModel, setPropagationModel] =
    useState("free_space_test");

  const [isLoadingSites, setIsLoadingSites] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSites() {
      try {
        const response = await fetch("/api/sites");
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error ?? "Unable to load sites.");
        }

        const loadedSites = data.sites ?? [];

        setSites(loadedSites);

        if (loadedSites.length > 0) {
          setSiteId(loadedSites[0].id);
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load sites.");
      } finally {
        setIsLoadingSites(false);
      }
    }

    loadSites();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setMessage("");
    setError("");
    setIsSubmitting(true);

    try {
      const antennaHeightM =
        Number(antennaHeightFt) * 0.3048;

      const calculationRadiusM =
        Number(calculationRadiusMiles) * 1609.344;

      const response = await fetch("/api/scenarios", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          siteId,
          name,

          frequencyMhz: Number(frequencyMhz),
          eirpWatts: Number(eirpWatts),

          antennaHeightM,
          antennaGainDbi: Number(antennaGainDbi),

          receiverHeightM: Number(receiverHeightM),
          receiverThresholdDbm: Number(receiverThresholdDbm),

          calculationRadiusM,
          resolutionM: Number(resolutionM),

          propagationModel,
        }),
      });

      const data = (await response.json()) as ScenarioResponse;

      if (!response.ok) {
        throw new Error(
          data.error ?? "Unable to create scenario.",
        );
      }

      setMessage(
        `Scenario ${data.scenario?.name ?? name} created successfully.`,
      );

      setName("");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to create scenario.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">
          Create Scenario
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          Define RF parameters for a site coverage analysis.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-6"
      >
        <div>
          <label
            htmlFor="scenario-site"
            className="block text-sm font-medium text-slate-700"
          >
            Site
          </label>

          <select
            id="scenario-site"
            value={siteId}
            onChange={(event) => setSiteId(event.target.value)}
            disabled={isLoadingSites}
            required
            className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900"
          >
            {isLoadingSites && (
              <option value="">Loading sites...</option>
            )}

            {!isLoadingSites && sites.length === 0 && (
              <option value="">No sites available</option>
            )}

            {sites.map((site) => (
              <option
                key={site.id}
                value={site.id}
              >
                {site.customer_name} — {site.project_name} — {site.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="scenario-name"
            className="block text-sm font-medium text-slate-700"
          >
            Scenario Name
          </label>

          <input
            id="scenario-name"
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Example: 600 MHz - 180 ft"
            required
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <NumberField
            id="frequency"
            label="Frequency"
            value={frequencyMhz}
            onChange={setFrequencyMhz}
            unit="MHz"
          />

          <NumberField
            id="eirp"
            label="EIRP"
            value={eirpWatts}
            onChange={setEirpWatts}
            unit="W"
          />

          <NumberField
            id="antenna-height"
            label="Antenna Height"
            value={antennaHeightFt}
            onChange={setAntennaHeightFt}
            unit="ft"
          />

          <NumberField
            id="antenna-gain"
            label="Antenna Gain"
            value={antennaGainDbi}
            onChange={setAntennaGainDbi}
            unit="dBi"
          />

          <NumberField
            id="receiver-height"
            label="Receiver Height"
            value={receiverHeightM}
            onChange={setReceiverHeightM}
            unit="m"
          />

          <NumberField
            id="receiver-threshold"
            label="Receiver Threshold"
            value={receiverThresholdDbm}
            onChange={setReceiverThresholdDbm}
            unit="dBm"
          />

          <NumberField
            id="radius"
            label="Calculation Radius"
            value={calculationRadiusMiles}
            onChange={setCalculationRadiusMiles}
            unit="mi"
          />

          <NumberField
            id="resolution"
            label="Raster Resolution"
            value={resolutionM}
            onChange={setResolutionM}
            unit="m"
          />
        </div>

        <div>
          <label
            htmlFor="propagation-model"
            className="block text-sm font-medium text-slate-700"
          >
            Propagation Model
          </label>

          <select
            id="propagation-model"
            value={propagationModel}
            onChange={(event) =>
              setPropagationModel(event.target.value)
            }
            className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900"
          >
            <option value="free_space_test">
              Free Space — Development Test
            </option>
          </select>

          <p className="mt-2 text-xs text-slate-500">
            Free-space is currently available for development testing only.
            Terrain-aware propagation models will be added separately.
          </p>
        </div>

        {message && (
          <div className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">
            {message}
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={
            isSubmitting ||
            isLoadingSites ||
            !siteId
          }
          className="w-full rounded-lg bg-indigo-700 px-4 py-2.5 font-medium text-white hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting
            ? "Creating Scenario..."
            : "Create Scenario"}
        </button>
      </form>
    </div>
  );
}

type NumberFieldProps = {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  unit: string;
};

function NumberField({
  id,
  label,
  value,
  onChange,
  unit,
}: NumberFieldProps) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-slate-700"
      >
        {label}
      </label>

      <div className="mt-2 flex rounded-lg border border-slate-300 bg-white">
        <input
          id={id}
          type="number"
          step="any"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required
          className="min-w-0 flex-1 rounded-l-lg px-3 py-2 text-slate-900 outline-none"
        />

        <span className="flex items-center border-l border-slate-300 bg-slate-50 px-3 text-sm text-slate-500">
          {unit}
        </span>
      </div>
    </div>
  );
}