import { betterAuth } from "better-auth";
import { Pool } from "pg";

if (!process.env.DATABASE_URL) {
    throw new Error(
        "DATABASE_URL is not configured",
    );
}

const authDatabasePool =
    new Pool({
        connectionString:
            process.env.DATABASE_URL,
    });

export const auth =
    betterAuth({
        database:
            authDatabasePool,

        emailAndPassword: {
            enabled: true,
        },
    });