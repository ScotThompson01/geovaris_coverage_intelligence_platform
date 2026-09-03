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

const FREE_SPACE_MODEL = "free_space_test";
const NTIA_ITM_MODEL = "ntia_itm";

const CLUTTER_SOURCE =
  "USGS/MRLC Annual NLCD Land Cover";

const CLUTTER_VERSION =
  "2025 C1V2";

const P2108_CLUTTER_MODEL =
  "ITU-R P.2108 Terrestrial Statistical Clutter";

const P2108_CLUTTER_MODEL_VERSION =
  "P.2108-1 (09/2021) §3.2";

const P2108_CORRECTION_END =
  "receiver";

export default function CreateScenarioForm() {
  const [sites, setSites] = useState<Site[]>([]);

  const [siteId, setSiteId] = useState("");
  const [name, setName] = useState("");

  const [frequencyMhz, setFrequencyMhz] =
    useState("600");

  const [eirpWatts, setEirpWatts] =
    useState("1000");

  const [antennaHeightFt, setAntennaHeightFt] =
    useState("180");

  const [antennaGainDbi, setAntennaGainDbi] =
    useState("0");

  const [receiverHeightM, setReceiverHeightM] =
    useState("1.5");

  const [
    receiverThresholdDbm,
    setReceiverThresholdDbm,
  ] = useState("-95");

  const [
    calculationRadiusMiles,
    setCalculationRadiusMiles,
  ] = useState("30");

  const [resolutionM, setResolutionM] =
    useState("30");

  const [
    propagationModel,
    setPropagationModel,
  ] = useState(FREE_SPACE_MODEL);

  const [itmClimate, setItmClimate] =
    useState("");

  const [
    itmPolarization,
    setItmPolarization,
  ] = useState("");

  const [
    itmVariabilityMode,
    setItmVariabilityMode,
  ] = useState("");

  const [
    itmSurfaceRefractivity,
    setItmSurfaceRefractivity,
  ] = useState("");

  const [
    itmDielectricConstant,
    setItmDielectricConstant,
  ] = useState("");

  const [
    itmConductivity,
    setItmConductivity,
  ] = useState("");

  const [
    itmConfidence,
    setItmConfidence,
  ] = useState("");

  const [
    itmReliability,
    setItmReliability,
  ] = useState("");

  const [
    clutterEnabled,
    setClutterEnabled,
  ] = useState(true);

  const [
    clutterPercentageLocations,
    setClutterPercentageLocations,
  ] = useState("50");

  const [
    isLoadingSites,
    setIsLoadingSites,
  ] = useState(true);

  const [
    isSubmitting,
    setIsSubmitting,
  ] = useState(false);

  const [message, setMessage] =
    useState("");

  const [error, setError] =
    useState("");

  const isItm =
    propagationModel === NTIA_ITM_MODEL;

  useEffect(() => {
    async function loadSites() {
      try {
        const response =
          await fetch(
            "/api/sites?access=write",
          );

        const data =
          await response.json();

        if (!response.ok) {
          throw new Error(
            data.error ??
            "Unable to load sites.",
          );
        }

        const loadedSites =
          data.sites ?? [];

        setSites(
          loadedSites,
        );

        if (
          loadedSites.length > 0
        ) {
          setSiteId(
            loadedSites[0].id,
          );
        }
      } catch (err) {
        console.error(
          err,
        );

        setError(
          "Unable to load sites.",
        );
      } finally {
        setIsLoadingSites(
          false,
        );
      }
    }

    loadSites();
  }, []);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setMessage("");
    setError("");
    setIsSubmitting(true);

    try {
      const antennaHeightM =
        Number(
          antennaHeightFt,
        ) * 0.3048;

      const calculationRadiusM =
        Number(
          calculationRadiusMiles,
        ) * 1609.344;

      const payload: Record<
        string,
        unknown
      > = {
        siteId,
        name,

        frequencyMhz:
          Number(
            frequencyMhz,
          ),

        eirpWatts:
          Number(
            eirpWatts,
          ),

        antennaHeightM,

        antennaGainDbi:
          Number(
            antennaGainDbi,
          ),

        receiverHeightM:
          Number(
            receiverHeightM,
          ),

        receiverThresholdDbm:
          Number(
            receiverThresholdDbm,
          ),

        calculationRadiusM,

        resolutionM:
          Number(
            resolutionM,
          ),

        propagationModel,
      };

      if (isItm) {
        const requiredItmValues = [
          itmClimate,
          itmPolarization,
          itmVariabilityMode,
          itmSurfaceRefractivity,
          itmDielectricConstant,
          itmConductivity,
          itmConfidence,
          itmReliability,
        ];

        if (
          requiredItmValues.some(
            (value) =>
              value === "",
          )
        ) {
          throw new Error(
            "All NTIA ITM parameters are required for an ITM scenario.",
          );
        }

        payload.itmClimate =
          Number(
            itmClimate,
          );

        payload.itmPolarization =
          Number(
            itmPolarization,
          );

        payload.itmVariabilityMode =
          Number(
            itmVariabilityMode,
          );

        payload.itmSurfaceRefractivity =
          Number(
            itmSurfaceRefractivity,
          );

        payload.itmDielectricConstant =
          Number(
            itmDielectricConstant,
          );

        payload.itmConductivitySPerM =
          Number(
            itmConductivity,
          );

        payload.itmConfidence =
          Number(
            itmConfidence,
          );

        payload.itmReliability =
          Number(
            itmReliability,
          );

        if (clutterEnabled) {
          const percentageLocations =
            Number(
              clutterPercentageLocations,
            );

          if (
            !Number.isFinite(
              percentageLocations,
            ) ||
            percentageLocations <= 0 ||
            percentageLocations >= 100
          ) {
            throw new Error(
              "Clutter percentage of locations must be greater than 0 and less than 100.",
            );
          }

          payload.clutterSource =
            CLUTTER_SOURCE;

          payload.clutterVersion =
            CLUTTER_VERSION;

          payload.clutterModel =
            P2108_CLUTTER_MODEL;

          payload.clutterModelVersion =
            P2108_CLUTTER_MODEL_VERSION;

          payload.clutterPercentageLocations =
            percentageLocations;

          payload.clutterCorrectionEnd =
            P2108_CORRECTION_END;
        }
      }

      const response =
        await fetch(
          "/api/scenarios",
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify(
              payload,
            ),
          },
        );

      const data =
        (await response.json()) as
        ScenarioResponse;

      if (!response.ok) {
        throw new Error(
          data.error ??
          "Unable to create scenario.",
        );
      }

      setMessage(
        `Scenario ${data.scenario?.name ??
        name
        } created successfully.`,
      );

      setName("");
    } catch (err) {
      if (
        err instanceof Error
      ) {
        setError(
          err.message,
        );
      } else {
        setError(
          "Unable to create scenario.",
        );
      }
    } finally {
      setIsSubmitting(
        false,
      );
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">
          Create Scenario
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          Define RF parameters and propagation
          assumptions for a site coverage analysis.
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
            onChange={(event) =>
              setSiteId(
                event.target.value,
              )
            }
            disabled={
              isLoadingSites
            }
            required
            className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900"
          >
            {isLoadingSites && (
              <option value="">
                Loading sites...
              </option>
            )}

            {!isLoadingSites &&
              sites.length === 0 && (
                <option value="">
                  No sites available
                </option>
              )}

            {sites.map(
              (site) => (
                <option
                  key={site.id}
                  value={site.id}
                >
                  {
                    site.customer_name
                  }{" "}
                  —{" "}
                  {
                    site.project_name
                  }{" "}
                  — {site.name}
                </option>
              ),
            )}
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
            onChange={(event) =>
              setName(
                event.target.value,
              )
            }
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
            onChange={
              setFrequencyMhz
            }
            unit="MHz"
          />

          <NumberField
            id="eirp"
            label="EIRP"
            value={eirpWatts}
            onChange={
              setEirpWatts
            }
            unit="W"
          />

          <NumberField
            id="antenna-height"
            label="Antenna Height"
            value={antennaHeightFt}
            onChange={
              setAntennaHeightFt
            }
            unit="ft"
          />

          <NumberField
            id="antenna-gain"
            label="Antenna Gain"
            value={antennaGainDbi}
            onChange={
              setAntennaGainDbi
            }
            unit="dBi"
          />

          <NumberField
            id="receiver-height"
            label="Receiver Height"
            value={receiverHeightM}
            onChange={
              setReceiverHeightM
            }
            unit="m"
          />

          <NumberField
            id="receiver-threshold"
            label="Receiver Threshold"
            value={
              receiverThresholdDbm
            }
            onChange={
              setReceiverThresholdDbm
            }
            unit="dBm"
          />

          <NumberField
            id="radius"
            label="Calculation Radius"
            value={
              calculationRadiusMiles
            }
            onChange={
              setCalculationRadiusMiles
            }
            unit="mi"
          />

          <NumberField
            id="resolution"
            label="Raster Resolution"
            value={resolutionM}
            onChange={
              setResolutionM
            }
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
            value={
              propagationModel
            }
            onChange={(event) =>
              setPropagationModel(
                event.target.value,
              )
            }
            className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900"
          >
            <option
              value={
                FREE_SPACE_MODEL
              }
            >
              Free Space —
              Development Test
            </option>

            <option
              value={
                NTIA_ITM_MODEL
              }
            >
              NTIA ITM 1.4
            </option>
          </select>

          <p className="mt-2 text-xs text-slate-500">
            Free-space remains a development
            baseline. NTIA ITM uses terrain-aware
            propagation and explicit engineering
            assumptions.
          </p>
        </div>

        {isItm && (
          <>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
              <div>
                <h4 className="font-semibold text-slate-900">
                  NTIA ITM Parameters
                </h4>

                <p className="mt-1 text-xs text-slate-500">
                  These values affect the propagation
                  result and are stored with the scenario
                  and each coverage run for
                  reproducibility.
                </p>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <SelectField
                  id="itm-climate"
                  label="Radio Climate"
                  value={
                    itmClimate
                  }
                  onChange={
                    setItmClimate
                  }
                  options={[
                    [
                      "",
                      "Select climate",
                    ],
                    [
                      "1",
                      "1 — Equatorial",
                    ],
                    [
                      "2",
                      "2 — Continental Subtropical",
                    ],
                    [
                      "3",
                      "3 — Maritime Subtropical",
                    ],
                    [
                      "4",
                      "4 — Desert",
                    ],
                    [
                      "5",
                      "5 — Continental Temperate",
                    ],
                    [
                      "6",
                      "6 — Maritime Temperate Over Land",
                    ],
                    [
                      "7",
                      "7 — Maritime Temperate Over Sea",
                    ],
                  ]}
                />

                <SelectField
                  id="itm-polarization"
                  label="Polarization"
                  value={
                    itmPolarization
                  }
                  onChange={
                    setItmPolarization
                  }
                  options={[
                    [
                      "",
                      "Select polarization",
                    ],
                    [
                      "0",
                      "Horizontal",
                    ],
                    [
                      "1",
                      "Vertical",
                    ],
                  ]}
                />

                <SelectField
                  id="itm-variability"
                  label="Variability Mode"
                  value={
                    itmVariabilityMode
                  }
                  onChange={
                    setItmVariabilityMode
                  }
                  options={[
                    [
                      "",
                      "Select variability mode",
                    ],
                    [
                      "0",
                      "Single Message",
                    ],
                    [
                      "1",
                      "Accidental",
                    ],
                    [
                      "2",
                      "Mobile",
                    ],
                    [
                      "3",
                      "Broadcast",
                    ],
                  ]}
                />

                <NumberField
                  id="itm-refractivity"
                  label="Surface Refractivity"
                  value={
                    itmSurfaceRefractivity
                  }
                  onChange={
                    setItmSurfaceRefractivity
                  }
                  unit="N-units"
                />

                <NumberField
                  id="itm-dielectric"
                  label="Ground Dielectric Constant"
                  value={
                    itmDielectricConstant
                  }
                  onChange={
                    setItmDielectricConstant
                  }
                  unit=""
                />

                <NumberField
                  id="itm-conductivity"
                  label="Ground Conductivity"
                  value={
                    itmConductivity
                  }
                  onChange={
                    setItmConductivity
                  }
                  unit="S/m"
                />

                <NumberField
                  id="itm-confidence"
                  label="Confidence"
                  value={
                    itmConfidence
                  }
                  onChange={
                    setItmConfidence
                  }
                  unit="0–1"
                />

                <NumberField
                  id="itm-reliability"
                  label="Reliability"
                  value={
                    itmReliability
                  }
                  onChange={
                    setItmReliability
                  }
                  unit="0–1"
                />
              </div>
            </div>

            <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-5">
              <div className="flex items-start gap-3">
                <input
                  id="clutter-enabled"
                  type="checkbox"
                  checked={
                    clutterEnabled
                  }
                  onChange={(event) =>
                    setClutterEnabled(
                      event.target.checked,
                    )
                  }
                  className="mt-1 h-4 w-4 rounded border-slate-300"
                />

                <div>
                  <label
                    htmlFor="clutter-enabled"
                    className="font-semibold text-slate-900"
                  >
                    Apply clutter
                    modeling
                  </label>

                  <p className="mt-1 text-xs text-slate-600">
                    Apply governed
                    land-cover data and
                    receiver-side
                    ITU-R P.2108 clutter
                    correction where the
                    GeoVaris clutter policy
                    considers P.2108
                    applicable.
                  </p>
                </div>
              </div>

              {clutterEnabled && (
                <div className="mt-5 space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <ReadOnlyField
                      label="Land Cover Dataset"
                      value={
                        CLUTTER_SOURCE
                      }
                    />

                    <ReadOnlyField
                      label="Dataset Version"
                      value={
                        CLUTTER_VERSION
                      }
                    />

                    <ReadOnlyField
                      label="Clutter Model"
                      value={
                        P2108_CLUTTER_MODEL
                      }
                    />

                    <ReadOnlyField
                      label="Model Version"
                      value={
                        P2108_CLUTTER_MODEL_VERSION
                      }
                    />

                    <NumberField
                      id="clutter-percentage-locations"
                      label="Percentage of Locations"
                      value={
                        clutterPercentageLocations
                      }
                      onChange={
                        setClutterPercentageLocations
                      }
                      unit="%"
                    />

                    <ReadOnlyField
                      label="Correction End"
                      value="Receiver"
                    />
                  </div>

                  <div className="rounded-lg border border-indigo-100 bg-white px-4 py-3 text-xs leading-5 text-slate-600">
                    P.2108 is a
                    statistical terminal
                    clutter correction. It
                    is not applied as a
                    universal land-cover
                    loss. GeoVaris applies
                    it only to supported
                    clutter classes.
                    Forest clutter remains
                    reserved for a future
                    vegetation-specific
                    model.
                  </div>
                </div>
              )}
            </div>
          </>
        )}

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
  onChange: (
    value: string,
  ) => void;
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
          onChange={(event) =>
            onChange(
              event.target.value,
            )
          }
          required
          className="min-w-0 flex-1 rounded-l-lg px-3 py-2 text-slate-900 outline-none"
        />

        {unit && (
          <span className="flex items-center border-l border-slate-300 bg-slate-50 px-3 text-sm text-slate-500">
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}

type SelectFieldProps = {
  id: string;
  label: string;
  value: string;
  onChange: (
    value: string,
  ) => void;
  options: Array<
    [string, string]
  >;
};

function SelectField({
  id,
  label,
  value,
  onChange,
  options,
}: SelectFieldProps) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-slate-700"
      >
        {label}
      </label>

      <select
        id={id}
        value={value}
        onChange={(event) =>
          onChange(
            event.target.value,
          )
        }
        required
        className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900"
      >
        {options.map(
          ([
            optionValue,
            optionLabel,
          ]) => (
            <option
              key={`${id}-${optionValue ||
                "empty"
                }`}
              value={
                optionValue
              }
            >
              {
                optionLabel
              }
            </option>
          ),
        )}
      </select>
    </div>
  );
}

type ReadOnlyFieldProps = {
  label: string;
  value: string;
};

function ReadOnlyField({
  label,
  value,
}: ReadOnlyFieldProps) {
  return (
    <div>
      <div className="block text-sm font-medium text-slate-700">
        {label}
      </div>

      <div className="mt-2 min-h-[42px] rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800">
        {value}
      </div>
    </div>
  );
}