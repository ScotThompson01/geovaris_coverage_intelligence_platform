import { NextRequest, NextResponse } from "next/server";

import { sql } from "@/lib/db";

const FREE_SPACE_MODEL = "free_space_test";
const NTIA_ITM_MODEL = "ntia_itm";

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
     * Resolve ownership, RF inputs, site coordinates,
     * propagation assumptions, and governed DEM lineage
     * on the server.
     *
     * The browser supplies only the scenario ID.
     * customer_id and all run parameters are copied
     * directly from the database so the coverage run
     * becomes an immutable calculation snapshot.
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

        sc.itm_climate,
        sc.itm_polarization,
        sc.itm_variability_mode,
        sc.itm_surface_refractivity,
        sc.itm_dielectric_constant,
        sc.itm_conductivity_s_per_m,
        sc.itm_confidence,
        sc.itm_reliability,

        s.latitude AS site_latitude,
        s.longitude AS site_longitude,

        s.ground_elevation_m,
        s.ground_elevation_source,
        s.ground_elevation_version,
        s.ground_elevation_horizontal_crs,
        s.ground_elevation_vertical_datum,
        s.ground_elevation_units,
        s.ground_elevation_resolution_m

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

    let propagationModelVersion: string;

    if (
      scenario.propagation_model === FREE_SPACE_MODEL
    ) {
      propagationModelVersion = "dev-0.1";
    } else if (
      scenario.propagation_model === NTIA_ITM_MODEL
    ) {
      propagationModelVersion = "1.4";

      const requiredItmValues = [
        scenario.itm_climate,
        scenario.itm_polarization,
        scenario.itm_variability_mode,
        scenario.itm_surface_refractivity,
        scenario.itm_dielectric_constant,
        scenario.itm_conductivity_s_per_m,
        scenario.itm_confidence,
        scenario.itm_reliability,
      ];

      if (
        requiredItmValues.some(
          (value) =>
            value === null ||
            value === undefined,
        )
      ) {
        return NextResponse.json(
          {
            error:
              "NTIA ITM scenario is missing required propagation parameters.",
          },
          { status: 400 },
        );
      }
    } else {
      return NextResponse.json(
        {
          error:
            "Scenario uses an unsupported propagation model.",
        },
        { status: 400 },
      );
    }

    const runs = await sql`
      INSERT INTO coverage_runs (
        customer_id,
        scenario_id,
        status,

        site_latitude,
        site_longitude,
        site_ground_elevation_m,

        frequency_mhz,
        eirp_watts,

        antenna_height_m,
        antenna_gain_dbi,

        receiver_height_m,
        receiver_threshold_dbm,

        calculation_radius_m,
        resolution_m,

        propagation_model,
        propagation_model_version,

        itm_climate,
        itm_polarization,
        itm_variability_mode,
        itm_surface_refractivity,
        itm_dielectric_constant,
        itm_conductivity_s_per_m,
        itm_confidence,
        itm_reliability,

        dem_source,
        dem_version,
        dem_horizontal_crs,
        dem_vertical_datum,
        dem_units,
        dem_resolution_m
      )
      VALUES (
        ${scenario.customer_id},
        ${scenario.scenario_id},
        'pending',

        ${scenario.site_latitude},
        ${scenario.site_longitude},
        ${scenario.ground_elevation_m},

        ${scenario.frequency_mhz},
        ${scenario.eirp_watts},

        ${scenario.antenna_height_m},
        ${scenario.antenna_gain_dbi},

        ${scenario.receiver_height_m},
        ${scenario.receiver_threshold_dbm},

        ${scenario.calculation_radius_m},
        ${scenario.resolution_m},

        ${scenario.propagation_model},
        ${propagationModelVersion},

        ${scenario.itm_climate},
        ${scenario.itm_polarization},
        ${scenario.itm_variability_mode},
        ${scenario.itm_surface_refractivity},
        ${scenario.itm_dielectric_constant},
        ${scenario.itm_conductivity_s_per_m},
        ${scenario.itm_confidence},
        ${scenario.itm_reliability},

        ${scenario.ground_elevation_source},
        ${scenario.ground_elevation_version},
        ${scenario.ground_elevation_horizontal_crs},
        ${scenario.ground_elevation_vertical_datum},
        ${scenario.ground_elevation_units},
        ${scenario.ground_elevation_resolution_m}
      )

      RETURNING
        id,
        customer_id,
        scenario_id,
        status,

        site_latitude,
        site_longitude,
        site_ground_elevation_m,

        frequency_mhz,
        eirp_watts,

        antenna_height_m,
        antenna_gain_dbi,

        receiver_height_m,
        receiver_threshold_dbm,

        calculation_radius_m,
        resolution_m,

        propagation_model,
        propagation_model_version,

        itm_climate,
        itm_polarization,
        itm_variability_mode,
        itm_surface_refractivity,
        itm_dielectric_constant,
        itm_conductivity_s_per_m,
        itm_confidence,
        itm_reliability,

        dem_source,
        dem_version,
        dem_horizontal_crs,
        dem_vertical_datum,
        dem_units,
        dem_resolution_m,

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