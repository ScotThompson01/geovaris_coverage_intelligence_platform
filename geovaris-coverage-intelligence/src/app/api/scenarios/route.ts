import { NextRequest, NextResponse } from "next/server";

import { sql } from "@/lib/db";

const FREE_SPACE_MODEL = "free_space_test";
const NTIA_ITM_MODEL = "ntia_itm";

type CreateScenarioRequest = {
  siteId?: string;
  name?: string;

  frequencyMhz?: number;
  eirpWatts?: number;

  antennaHeightM?: number;
  antennaGainDbi?: number;

  receiverHeightM?: number;
  receiverThresholdDbm?: number;

  calculationRadiusM?: number;
  resolutionM?: number;

  propagationModel?: string;

  itmClimate?: number;
  itmPolarization?: number;
  itmVariabilityMode?: number;
  itmSurfaceRefractivity?: number;
  itmDielectricConstant?: number;
  itmConductivitySPerM?: number;
  itmConfidence?: number;
  itmReliability?: number;
};

function optionalNumber(
  value: number | undefined,
): number | null {
  if (value === undefined || value === null) {
    return null;
  }

  const numberValue = Number(value);

  return Number.isFinite(numberValue)
    ? numberValue
    : null;
}

export async function POST(request: NextRequest) {
  try {
    const body =
      (await request.json()) as CreateScenarioRequest;

    const siteId = body.siteId;
    const name = body.name?.trim();

    const frequencyMhz = Number(body.frequencyMhz);
    const eirpWatts = Number(body.eirpWatts);

    const antennaHeightM =
      Number(body.antennaHeightM);

    const antennaGainDbi =
      optionalNumber(body.antennaGainDbi);

    const receiverHeightM =
      optionalNumber(body.receiverHeightM);

    const receiverThresholdDbm =
      Number(body.receiverThresholdDbm);

    const calculationRadiusM =
      Number(body.calculationRadiusM);

    const resolutionM =
      Number(body.resolutionM);

    const propagationModel =
      body.propagationModel?.trim();

    if (!siteId) {
      return NextResponse.json(
        { error: "Site is required." },
        { status: 400 },
      );
    }

    if (!name) {
      return NextResponse.json(
        { error: "Scenario name is required." },
        { status: 400 },
      );
    }

    if (
      !Number.isFinite(frequencyMhz) ||
      frequencyMhz <= 0
    ) {
      return NextResponse.json(
        {
          error: "Frequency must be greater than zero.",
        },
        { status: 400 },
      );
    }

    if (
      !Number.isFinite(eirpWatts) ||
      eirpWatts <= 0
    ) {
      return NextResponse.json(
        {
          error: "EIRP must be greater than zero.",
        },
        { status: 400 },
      );
    }

    if (
      !Number.isFinite(antennaHeightM) ||
      antennaHeightM <= 0
    ) {
      return NextResponse.json(
        {
          error:
            "Antenna height must be greater than zero.",
        },
        { status: 400 },
      );
    }

    if (
      !Number.isFinite(receiverThresholdDbm)
    ) {
      return NextResponse.json(
        {
          error:
            "Receiver threshold must be a valid number.",
        },
        { status: 400 },
      );
    }

    if (
      !Number.isFinite(calculationRadiusM) ||
      calculationRadiusM <= 0
    ) {
      return NextResponse.json(
        {
          error:
            "Calculation radius must be greater than zero.",
        },
        { status: 400 },
      );
    }

    if (
      !Number.isFinite(resolutionM) ||
      resolutionM <= 0
    ) {
      return NextResponse.json(
        {
          error:
            "Resolution must be greater than zero.",
        },
        { status: 400 },
      );
    }

    if (
      propagationModel !== FREE_SPACE_MODEL &&
      propagationModel !== NTIA_ITM_MODEL
    ) {
      return NextResponse.json(
        {
          error:
            "Unsupported propagation model.",
        },
        { status: 400 },
      );
    }

    let itmClimate: number | null = null;
    let itmPolarization: number | null = null;
    let itmVariabilityMode: number | null = null;
    let itmSurfaceRefractivity: number | null = null;
    let itmDielectricConstant: number | null = null;
    let itmConductivitySPerM: number | null = null;
    let itmConfidence: number | null = null;
    let itmReliability: number | null = null;

    if (propagationModel === NTIA_ITM_MODEL) {
      itmClimate = optionalNumber(
        body.itmClimate,
      );

      itmPolarization = optionalNumber(
        body.itmPolarization,
      );

      itmVariabilityMode = optionalNumber(
        body.itmVariabilityMode,
      );

      itmSurfaceRefractivity = optionalNumber(
        body.itmSurfaceRefractivity,
      );

      itmDielectricConstant = optionalNumber(
        body.itmDielectricConstant,
      );

      itmConductivitySPerM = optionalNumber(
        body.itmConductivitySPerM,
      );

      itmConfidence = optionalNumber(
        body.itmConfidence,
      );

      itmReliability = optionalNumber(
        body.itmReliability,
      );

      if (
        itmClimate === null ||
        !Number.isInteger(itmClimate) ||
        itmClimate < 1 ||
        itmClimate > 7
      ) {
        return NextResponse.json(
          {
            error:
              "ITM climate must be an integer from 1 through 7.",
          },
          { status: 400 },
        );
      }

      if (
        itmPolarization === null ||
        !Number.isInteger(itmPolarization) ||
        ![0, 1].includes(itmPolarization)
      ) {
        return NextResponse.json(
          {
            error:
              "ITM polarization must be 0 or 1.",
          },
          { status: 400 },
        );
      }

      if (
        itmVariabilityMode === null ||
        !Number.isInteger(itmVariabilityMode) ||
        itmVariabilityMode < 0 ||
        itmVariabilityMode > 3
      ) {
        return NextResponse.json(
          {
            error:
              "ITM variability mode must be an integer from 0 through 3.",
          },
          { status: 400 },
        );
      }

      if (
        itmSurfaceRefractivity === null ||
        itmSurfaceRefractivity < 250 ||
        itmSurfaceRefractivity > 400
      ) {
        return NextResponse.json(
          {
            error:
              "ITM surface refractivity must be between 250 and 400.",
          },
          { status: 400 },
        );
      }

      if (
        itmDielectricConstant === null ||
        itmDielectricConstant <= 1
      ) {
        return NextResponse.json(
          {
            error:
              "ITM dielectric constant must be greater than 1.",
          },
          { status: 400 },
        );
      }

      if (
        itmConductivitySPerM === null ||
        itmConductivitySPerM <= 0
      ) {
        return NextResponse.json(
          {
            error:
              "ITM conductivity must be greater than zero.",
          },
          { status: 400 },
        );
      }

      if (
        itmConfidence === null ||
        itmConfidence <= 0 ||
        itmConfidence >= 1
      ) {
        return NextResponse.json(
          {
            error:
              "ITM confidence must be greater than 0 and less than 1.",
          },
          { status: 400 },
        );
      }

      if (
        itmReliability === null ||
        itmReliability <= 0 ||
        itmReliability >= 1
      ) {
        return NextResponse.json(
          {
            error:
              "ITM reliability must be greater than 0 and less than 1.",
          },
          { status: 400 },
        );
      }
    }

    /*
     * Resolve customer ownership from the site on the server.
     * Never trust customer_id supplied by the browser.
     */
    const sites = await sql`
      SELECT
        id,
        customer_id
      FROM sites
      WHERE id = ${siteId}
      LIMIT 1;
    `;

    const site = sites[0];

    if (!site) {
      return NextResponse.json(
        { error: "Site was not found." },
        { status: 404 },
      );
    }

    const scenarios = await sql`
      INSERT INTO scenarios (
        customer_id,
        site_id,
        name,

        frequency_mhz,
        eirp_watts,

        antenna_height_m,
        antenna_gain_dbi,

        receiver_height_m,
        receiver_threshold_dbm,

        calculation_radius_m,
        resolution_m,

        propagation_model,

        itm_climate,
        itm_polarization,
        itm_variability_mode,
        itm_surface_refractivity,
        itm_dielectric_constant,
        itm_conductivity_s_per_m,
        itm_confidence,
        itm_reliability
      )
      VALUES (
        ${site.customer_id},
        ${site.id},
        ${name},

        ${frequencyMhz},
        ${eirpWatts},

        ${antennaHeightM},
        ${antennaGainDbi},

        ${receiverHeightM},
        ${receiverThresholdDbm},

        ${calculationRadiusM},
        ${resolutionM},

        ${propagationModel},

        ${itmClimate},
        ${itmPolarization},
        ${itmVariabilityMode},
        ${itmSurfaceRefractivity},
        ${itmDielectricConstant},
        ${itmConductivitySPerM},
        ${itmConfidence},
        ${itmReliability}
      )
      RETURNING
        id,
        customer_id,
        site_id,
        name,
        frequency_mhz,
        eirp_watts,
        antenna_height_m,
        antenna_gain_dbi,
        receiver_height_m,
        receiver_threshold_dbm,
        calculation_radius_m,
        resolution_m,
        propagation_model,

        itm_climate,
        itm_polarization,
        itm_variability_mode,
        itm_surface_refractivity,
        itm_dielectric_constant,
        itm_conductivity_s_per_m,
        itm_confidence,
        itm_reliability,

        created_at;
    `;

    return NextResponse.json(
      {
        status: "ok",
        scenario: scenarios[0],
      },
      { status: 201 },
    );
  } catch (error) {
    console.error(
      "Create scenario failed:",
      error,
    );

    return NextResponse.json(
      {
        error: "Unable to create scenario.",
      },
      { status: 500 },
    );
  }
}