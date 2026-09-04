import { betterAuth } from "better-auth";
import pg from "pg";

const {
    Pool,
} = pg;

const databaseUrl =
    process.env.DATABASE_URL;

const email =
    process.env.GEOVARIS_ADMIN_EMAIL;

const password =
    process.env.GEOVARIS_ADMIN_TEMP_PASSWORD;

const name =
    process.env.GEOVARIS_ADMIN_NAME ??
    "Scot Thompson";

if (!databaseUrl) {
    throw new Error(
        "DATABASE_URL is not configured.",
    );
}

if (!email) {
    throw new Error(
        "GEOVARIS_ADMIN_EMAIL is not configured.",
    );
}

if (!password) {
    throw new Error(
        "GEOVARIS_ADMIN_TEMP_PASSWORD is not configured.",
    );
}

const pool =
    new Pool({
        connectionString:
            databaseUrl,
    });

const auth =
    betterAuth({
        database:
            pool,

        emailAndPassword: {
            enabled: true,
        },
    });

async function main() {
    const existingUserResult =
        await pool.query(
            `
            SELECT
                id,
                email,
                name
            FROM "user"
            WHERE lower(email) =
                lower($1)
            LIMIT 1;
            `,
            [
                email,
            ],
        );

    if (
        existingUserResult.rows.length >
        0
    ) {
        const existingUser =
            existingUserResult.rows[0];

        console.log(
            "User already exists.",
        );

        console.log(
            `User ID: ${existingUser.id}`,
        );

        console.log(
            `Email: ${existingUser.email}`,
        );

        console.log(
            "",
        );

        console.log(
            "No password was changed.",
        );

        process.exitCode = 2;

        return;
    }

    const signUpResult =
        await auth.api.signUpEmail({
            body: {
                name,
                email,
                password,
            },
        });

    if (
        !signUpResult?.user?.id
    ) {
        throw new Error(
            "Better Auth did not return a created user.",
        );
    }

    const userId =
        signUpResult.user.id;

    await pool.query(
        `
        INSERT INTO user_platform_roles (
            user_id,
            role
        )
        VALUES (
            $1,
            'geovaris_admin'
        )
        ON CONFLICT DO NOTHING;
        `,
        [
            userId,
        ],
    );

    const roleResult =
        await pool.query(
            `
            SELECT
                u.id,
                u.email,
                u.name,
                upr.role
            FROM "user" u

            LEFT JOIN user_platform_roles upr
                ON upr.user_id =
                    u.id

            WHERE u.id =
                $1;
            `,
            [
                userId,
            ],
        );

    const createdUser =
        roleResult.rows[0];

    console.log(
        "GeoVaris admin test user created.",
    );

    console.log(
        `User ID: ${createdUser.id}`,
    );

    console.log(
        `Email: ${createdUser.email}`,
    );

    console.log(
        `Name: ${createdUser.name}`,
    );

    console.log(
        `Platform role: ${createdUser.role}`,
    );
}

try {
    await main();
} finally {
    await pool.end();
}
