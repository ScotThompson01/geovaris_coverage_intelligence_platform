import { NextResponse } from "next/server";

import { sql } from "@/lib/db";

export async function GET() {
  try {
    const projects = await sql`
      SELECT
        p.id,
        p.name,
        c.name AS customer_name
      FROM projects p
      JOIN customers c
        ON c.id = p.customer_id
      ORDER BY c.name, p.name;
    `;

    return NextResponse.json({
      status: "ok",
      projects,
    });
  } catch (error) {
    console.error("Project lookup failed:", error);

    return NextResponse.json(
      {
        status: "error",
        error: "Unable to load projects.",
      },
      { status: 500 },
    );
  }
}