import { NextRequest, NextResponse } from "next/server";

import { sql } from "@/lib/db";

type CreateCoverageRunRequest = {
  scenarioId?: string;
};

export async function POST(request: NextRequest) {
  try {
    const body =
      (await request.json()) as CreateCoverageRunRequest;

    const scenarioId = body.scenarioId;

    if (!scenarioId) {
      return NextResponse.json(
        {
          error: "Scenario is required.",
        },
        { status: 400 },
      );
    }

    /*
     * Resolve all ownership and RF inputs on the server.
     *
     * The browser supplies only the scenario ID.
     * customer_id and all run parameters are copied
     * directly from the database.
     */
    const scenarios = await sql`
      SELECT
        sc.id AS scenario_id,
        sc.customer_id,

        sc.frequency_mhz,
        sc.eirp_watts,
        sc.antenna_height_m,
        sc.antenna_gain_dbi,

        sc.receiver_height_m,
        sc.receiver_threshold_dbm,

        sc.calculation_radius_m,
        sc.resolution_m,

        sc.propagation_model,

        s.latitude AS site_latitude,
        s.longitude AS site_longitude

      FROM scenarios sc

      JOIN sites s
        ON s.id = sc.site_id
        AND s.customer_id = sc.customer_id

      WHERE sc.id = ${scenarioId}

      LIMIT 1;
    `;

    const scenario = scenarios[0];

    if (!scenario) {
      return NextResponse.json(
        {
          error: "Scenario was not found.",
        },
        { status: 404 },
      );
    }

    const runs = await sql`
      INSERT INTO coverage_runs (
        customer_id,
        scenario_id,
        status,

        site_latitude,
        site_longitude,

        frequency_mhz,
        eirp_watts,

        antenna_height_m,
        antenna_gain_dbi,

        receiver_height_m,
        receiver_threshold_dbm,

        calculation_radius_m,
        resolution_m,

        propagation_model,
        propagation_model_version
      )
      VALUES (
        ${scenario.customer_id},
        ${scenario.scenario_id},
        'pending',

        ${scenario.site_latitude},
        ${scenario.site_longitude},

        ${scenario.frequency_mhz},
        ${scenario.eirp_watts},

        ${scenario.antenna_height_m},
        ${scenario.antenna_gain_dbi},

        ${scenario.receiver_height_m},
        ${scenario.receiver_threshold_dbm},

        ${scenario.calculation_radius_m},
        ${scenario.resolution_m},

        ${scenario.propagation_model},
        'dev-0.1'
      )

      RETURNING
        id,
        customer_id,
        scenario_id,
        status,
        site_latitude,
        site_longitude,
        frequency_mhz,
        eirp_watts,
        antenna_height_m,
        receiver_threshold_dbm,
        calculation_radius_m,
        resolution_m,
        propagation_model,
        propagation_model_version,
        created_at;
    `;

    return NextResponse.json(
      {
        status: "ok",
        coverageRun: runs[0],
      },
      { status: 201 },
    );
  } catch (error) {
    console.error(
      "Create coverage run failed:",
      error,
    );

    return NextResponse.json(
      {
        error: "Unable to create coverage run.",
      },
      { status: 500 },
    );
  }
}
