import { headers } from "next/headers";

import { auth } from "@/lib/auth";
import { sql } from "@/lib/db";

export type GeoVarisPlatformRole =
    | "geovaris_admin";

export type GeoVarisCustomerRole =
    | "customer_admin"
    | "engineer"
    | "analyst"
    | "viewer";

export type GeoVarisCustomerMembership = {
    customerId: string;
    customerName: string;
    role: GeoVarisCustomerRole;
};

export type GeoVarisAuthContext = {
    userId: string;
    userName: string;
    userEmail: string;

    isGeoVarisAdmin: boolean;

    customerMemberships:
        GeoVarisCustomerMembership[];
};

export async function getGeoVarisAuthContext():
    Promise<GeoVarisAuthContext | null> {
    const requestHeaders =
        await headers();

    const session =
        await auth.api.getSession({
            headers:
                requestHeaders,
        });

    if (!session?.user?.id) {
        return null;
    }

    const userId =
        session.user.id;

    const [
        platformRoleRows,
        membershipRows,
    ] =
        await Promise.all([
            sql`
                SELECT
                    role
                FROM user_platform_roles
                WHERE user_id =
                    ${userId};
            `,

            sql`
                SELECT
                    ucm.customer_id,
                    c.name AS customer_name,
                    ucm.role
                FROM user_customer_memberships ucm
                JOIN customers c
                    ON c.id =
                        ucm.customer_id
                WHERE ucm.user_id =
                    ${userId}
                ORDER BY
                    c.name;
            `,
        ]);

    const isGeoVarisAdmin =
        platformRoleRows.some(
            (row) =>
                row.role ===
                "geovaris_admin",
        );

    const customerMemberships =
        membershipRows.map(
            (row) => ({
                customerId:
                    String(
                        row.customer_id,
                    ),

                customerName:
                    String(
                        row.customer_name,
                    ),

                role:
                    row.role as GeoVarisCustomerRole,
            }),
        );

    return {
        userId,

        userName:
            session.user.name,

        userEmail:
            session.user.email,

        isGeoVarisAdmin,

        customerMemberships,
    };
}