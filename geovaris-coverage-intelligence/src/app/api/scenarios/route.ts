import { NextRequest, NextResponse } from "next/server";

import { sql } from "@/lib/db";

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
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as CreateScenarioRequest;

    const siteId = body.siteId;
    const name = body.name?.trim();

    const frequencyMhz = Number(body.frequencyMhz);
    const eirpWatts = Number(body.eirpWatts);

    const antennaHeightM = Number(body.antennaHeightM);

    const antennaGainDbi =
      body.antennaGainDbi === undefined ||
      body.antennaGainDbi === null
        ? null
        : Number(body.antennaGainDbi);

    const receiverHeightM =
      body.receiverHeightM === undefined ||
      body.receiverHeightM === null
        ? null
        : Number(body.receiverHeightM);

    const receiverThresholdDbm = Number(
      body.receiverThresholdDbm,
    );

    const calculationRadiusM = Number(
      body.calculationRadiusM,
    );

    const resolutionM = Number(body.resolutionM);

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
        { error: "Frequency must be greater than zero." },
        { status: 400 },
      );
    }

    if (
      !Number.isFinite(eirpWatts) ||
      eirpWatts <= 0
    ) {
      return NextResponse.json(
        { error: "EIRP must be greater than zero." },
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

    if (!propagationModel) {
      return NextResponse.json(
        {
          error: "Propagation model is required.",
        },
        { status: 400 },
      );
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

        propagation_model
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

        ${propagationModel}
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
    console.error("Create scenario failed:", error);

    return NextResponse.json(
      {
        error: "Unable to create scenario.",
      },
      { status: 500 },
    );
  }
}