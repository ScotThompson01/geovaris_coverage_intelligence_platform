import { NextResponse } from "next/server";

import { sql } from "@/lib/db";

export async function GET() {
  try {
    const result = await sql`
      SELECT
        current_database() AS database_name,
        PostGIS_Version() AS postgis_version;
    `;

    return NextResponse.json({
      status: "ok",
      database: result[0].database_name,
      postgisVersion: result[0].postgis_version,
    });
  } catch (error) {
    console.error("Database health check failed:", error);

    return NextResponse.json(
      {
        status: "error",
        message: "Unable to connect to the database",
      },
      { status: 500 },
    );
  }
}