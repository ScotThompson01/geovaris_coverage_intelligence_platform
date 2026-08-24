import { NextRequest, NextResponse } from "next/server";

import { sql } from "@/lib/db";

type CreateSiteRequest = {
  projectId?: string;
  name?: string;
  latitude?: number;
  longitude?: number;
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as CreateSiteRequest;

    const projectId = body.projectId;
    const name = body.name?.trim();
    const latitude = Number(body.latitude);
    const longitude = Number(body.longitude);

    if (!projectId) {
      return NextResponse.json(
        { error: "Project is required." },
        { status: 400 },
      );
    }

    if (!name) {
      return NextResponse.json(
        { error: "Site name is required." },
        { status: 400 },
      );
    }

    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
      return NextResponse.json(
        { error: "Latitude must be between -90 and 90." },
        { status: 400 },
      );
    }

    if (
      !Number.isFinite(longitude) ||
      longitude < -180 ||
      longitude > 180
    ) {
      return NextResponse.json(
        { error: "Longitude must be between -180 and 180." },
        { status: 400 },
      );
    }

    /*
     * Resolve customer ownership from the project on the server.
     * Do not trust a customer_id supplied by the browser.
     */
    const projects = await sql`
      SELECT
        id,
        customer_id
      FROM projects
      WHERE id = ${projectId}
      LIMIT 1;
    `;

    const project = projects[0];

    if (!project) {
      return NextResponse.json(
        { error: "Project was not found." },
        { status: 404 },
      );
    }

    const sites = await sql`
      INSERT INTO sites (
        customer_id,
        project_id,
        name,
        latitude,
        longitude
      )
      VALUES (
        ${project.customer_id},
        ${project.id},
        ${name},
        ${latitude},
        ${longitude}
      )
      RETURNING
        id,
        customer_id,
        project_id,
        name,
        latitude,
        longitude,
        ST_AsText(location::geometry) AS location;
    `;

    return NextResponse.json(
      {
        status: "ok",
        site: sites[0],
      },
      { status: 201 },
    );
  } catch (error) {
    console.error("Create site failed:", error);

    return NextResponse.json(
      {
        error: "Unable to create site.",
      },
      { status: 500 },
    );
  }
}
export async function GET() {
  try {
    const sites = await sql`
      SELECT
        s.id,
        s.name,
        s.latitude,
        s.longitude,
        p.name AS project_name,
        c.name AS customer_name
      FROM sites s
      JOIN projects p
        ON p.id = s.project_id
        AND p.customer_id = s.customer_id
      JOIN customers c
        ON c.id = s.customer_id
      ORDER BY c.name, p.name, s.name;
    `;

    return NextResponse.json({
      status: "ok",
      sites,
    });
  } catch (error) {
    console.error("Site lookup failed:", error);

    return NextResponse.json(
      {
        status: "error",
        error: "Unable to load sites.",
      },
      { status: 500 },
    );
  }
}