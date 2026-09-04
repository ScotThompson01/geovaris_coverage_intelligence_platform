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

            revokeSessionsOnPasswordReset:
                true,

            resetPasswordTokenExpiresIn:
                60 * 60,

            sendResetPassword:
                async ({
                    user,
                    url,
                }) => {
                    /*
                     * Development/demo behavior.
                     *
                     * Do not log passwords or reset tokens
                     * separately. Better Auth provides the
                     * complete reset URL.
                     *
                     * Replace this with a transactional
                     * email provider before production.
                     */
                    console.info(
                        [
                            "",
                            "========================================",
                            "GeoVaris password reset requested",
                            `User: ${user.email}`,
                            `Reset URL: ${url}`,
                            "========================================",
                            "",
                        ].join("\n"),
                    );
                },

            onPasswordReset:
                async ({
                    user,
                }) => {
                    console.info(
                        `Password reset completed for ${user.email}.`,
                    );
                },
        },
    });