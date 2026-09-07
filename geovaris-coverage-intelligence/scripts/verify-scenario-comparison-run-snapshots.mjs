import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const routePath = path.resolve(
    process.cwd(),
    "src",
    "app",
    "api",
    "scenario-comparison",
    "route.ts",
);

const source = fs.readFileSync(
    routePath,
    "utf8",
);

const requiredFragments = [
    "latest_run.frequency_mhz::double precision",
    "latest_run.eirp_watts::double precision",
    "latest_run.antenna_height_m::double precision",
    "latest_run.receiver_threshold_dbm::double precision",
    "latest_run.propagation_model",
    "cr.frequency_mhz",
    "cr.eirp_watts",
    "cr.antenna_height_m",
    "cr.receiver_threshold_dbm",
    "cr.propagation_model",
];

const forbiddenFragments = [
    "sc.frequency_mhz",
    "sc.eirp_watts",
    "sc.antenna_height_m",
    "sc.receiver_threshold_dbm",
    "sc.propagation_model",
];

let failed = false;

for (const fragment of requiredFragments) {
    if (!source.includes(fragment)) {
        console.error(
            `Missing required run-snapshot reference: ${fragment}`,
        );

        failed = true;
    }
}

for (const fragment of forbiddenFragments) {
    if (source.includes(fragment)) {
        console.error(
            `Found mutable scenario RF input in comparison query: ${fragment}`,
        );

        failed = true;
    }
}

if (failed) {
    console.error(
        "Scenario comparison run-snapshot verification failed.",
    );

    process.exit(1);
}

console.log(
    "Scenario comparison run-snapshot verification passed.",
);
