import {
    NextRequest,
    NextResponse,
} from "next/server";

import {
    getGeoVarisAuthContext,
} from "@/lib/auth-context";

import { sql } from "@/lib/db";

const PROJECT_WRITE_ROLES =
    new Set([
        "customer_admin",
        "engineer",
    ]);

export async function GET(
    request: NextRequest,
) {
    try {
        const authContext =
            await getGeoVarisAuthContext();

        if (!authContext) {
            return NextResponse.json(
                {
                    status: "error",
                    error:
                        "Authentication is required.",
                },
                {
                    status: 401,
                },
            );
        }

        const access =
            request.nextUrl.searchParams.get(
                "access",
            );

        const writeOnly =
            access === "write";

        if (
            authContext.isGeoVarisAdmin
        ) {
            const projects =
                await sql`
                    SELECT
                        p.id,
                        p.name,
                        c.name AS customer_name

                    FROM projects p

                    JOIN customers c
                        ON c.id =
                            p.customer_id

                    ORDER BY
                        c.name,
                        p.name;
                `;

            return NextResponse.json({
                status: "ok",
                projects,
            });
        }

        const customerIds =
            authContext.customerMemberships
                .filter(
                    (membership) =>
                        !writeOnly ||
                        PROJECT_WRITE_ROLES.has(
                            membership.role,
                        ),
                )
                .map(
                    (membership) =>
                        membership.customerId,
                );

        if (
            customerIds.length === 0
        ) {
            return NextResponse.json({
                status: "ok",
                projects: [],
            });
        }

        const projects =
            await sql`
                SELECT
                    p.id,
                    p.name,
                    c.name AS customer_name

                FROM projects p

                JOIN customers c
                    ON c.id =
                        p.customer_id

                WHERE p.customer_id =
                    ANY(
                        ${customerIds}::uuid[]
                    )

                ORDER BY
                    c.name,
                    p.name;
            `;

        return NextResponse.json({
            status: "ok",
            projects,
        });
    } catch (error) {
        console.error(
            "Project lookup failed:",
            error,
        );

        return NextResponse.json(
            {
                status: "error",
                error:
                    "Unable to load projects.",
            },
            {
                status: 500,
            },
        );
    }
}