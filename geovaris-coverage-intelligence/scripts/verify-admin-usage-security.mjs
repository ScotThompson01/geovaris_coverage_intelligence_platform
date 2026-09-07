import fs from "node:fs";
import path from "node:path";

const routePath =
    path.resolve(
        process.cwd(),
        "src/app/api/admin/usage/route.ts",
    );

const source =
    fs.readFileSync(
        routePath,
        "utf8",
    );

const requiredPatterns = [
    {
        description:
            "uses the authenticated GeoVaris context",
        pattern:
            /getGeoVarisAuthContext/,
    },
    {
        description:
            "checks GeoVaris admin status",
        pattern:
            /isGeoVarisAdmin/,
    },
    {
        description:
            "limits customer administrators to customer_admin memberships",
        pattern:
            /membership\.role\s*===\s*"customer_admin"/,
    },
    {
        description:
            "scopes non-admin coverage runs by authorized customer IDs",
        pattern:
            /customer_id\s*=\s*ANY\s*\(/,
    },
    {
        description:
            "returns 403 for non-administrative users",
        pattern:
            /status:\s*403/,
    },
];

const forbiddenPatterns = [
    {
        description:
            "must not trust a browser-supplied customerId query parameter",
        pattern:
            /searchParams\.get\(\s*["']customerId["']\s*\)/,
    },
    {
        description:
            "must not trust a browser-supplied customer_id query parameter",
        pattern:
            /searchParams\.get\(\s*["']customer_id["']\s*\)/,
    },
];

const failures = [];

for (
    const {
        description,
        pattern,
    } of requiredPatterns
) {
    if (!pattern.test(source)) {
        failures.push(
            `Missing requirement: ${description}`,
        );
    }
}

for (
    const {
        description,
        pattern,
    } of forbiddenPatterns
) {
    if (pattern.test(source)) {
        failures.push(
            `Forbidden pattern found: ${description}`,
        );
    }
}

if (failures.length > 0) {
    console.error(
        "Admin usage security verification FAILED.",
    );

    for (const failure of failures) {
        console.error(
            `- ${failure}`,
        );
    }

    process.exit(1);
}

console.log(
    "Admin usage security verification passed.",
);