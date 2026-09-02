const BASE_URL =
    process.env.GEOVARIS_TEST_BASE_URL ??
    "http://localhost:3000";

const TENANT_A_EMAIL =
    process.env.GEOVARIS_TEST_TENANT_A_EMAIL;

const TENANT_A_PASSWORD =
    process.env.GEOVARIS_TEST_TENANT_A_PASSWORD;

const TENANT_B_EMAIL =
    process.env.GEOVARIS_TEST_TENANT_B_EMAIL;

const TENANT_B_PASSWORD =
    process.env.GEOVARIS_TEST_TENANT_B_PASSWORD;

const TENANT_B_PROJECT_ID =
    process.env.GEOVARIS_TEST_TENANT_B_PROJECT_ID;

const TENANT_B_SITE_ID =
    process.env.GEOVARIS_TEST_TENANT_B_SITE_ID;

const TENANT_B_SCENARIO_ID =
    process.env.GEOVARIS_TEST_TENANT_B_SCENARIO_ID;

const requiredValues = {
    GEOVARIS_TEST_TENANT_A_EMAIL:
        TENANT_A_EMAIL,
    GEOVARIS_TEST_TENANT_A_PASSWORD:
        TENANT_A_PASSWORD,
    GEOVARIS_TEST_TENANT_B_EMAIL:
        TENANT_B_EMAIL,
    GEOVARIS_TEST_TENANT_B_PASSWORD:
        TENANT_B_PASSWORD,
    GEOVARIS_TEST_TENANT_B_PROJECT_ID:
        TENANT_B_PROJECT_ID,
    GEOVARIS_TEST_TENANT_B_SITE_ID:
        TENANT_B_SITE_ID,
    GEOVARIS_TEST_TENANT_B_SCENARIO_ID:
        TENANT_B_SCENARIO_ID,
};

for (
    const [
        key,
        value,
    ] of Object.entries(
        requiredValues,
    )
) {
    if (!value) {
        throw new Error(
            `${key} is required.`,
        );
    }
}

function assert(
    condition,
    message,
) {
    if (!condition) {
        throw new Error(message);
    }
}

function getSetCookieHeaders(
    response,
) {
    if (
        typeof response.headers.getSetCookie ===
        "function"
    ) {
        return response.headers.getSetCookie();
    }

    const header =
        response.headers.get(
            "set-cookie",
        );

    return header
        ? [header]
        : [];
}

function cookieHeaderFromResponse(
    response,
) {
    const cookies =
        getSetCookieHeaders(
            response,
        )
            .map(
                (cookie) =>
                    cookie.split(
                        ";",
                    )[0],
            )
            .filter(Boolean);

    if (
        cookies.length === 0
    ) {
        throw new Error(
            "Sign-in response did not provide a session cookie.",
        );
    }

    return cookies.join("; ");
}

async function signIn(
    email,
    password,
) {
    const response =
        await fetch(
            `${BASE_URL}/api/auth/sign-in/email`,
            {
                method: "POST",
                headers: {
                    "content-type":
                        "application/json",

                    origin:
                        BASE_URL,
                },
                body:
                    JSON.stringify({
                        email,
                        password,
                    }),
            },
        );

    assert(
        response.ok,
        `Sign-in failed for ${email}: ${response.status}`,
    );

    return cookieHeaderFromResponse(
        response,
    );
}

async function request(
    path,
    {
        method = "GET",
        cookie,
        body,
    } = {},
) {
    const headers = {};

    if (cookie) {
        headers.cookie =
            cookie;
    }

    if (body !== undefined) {
        headers[
            "content-type"
        ] =
            "application/json";
    }

    const response =
        await fetch(
            `${BASE_URL}${path}`,
            {
                method,
                headers,
                body:
                    body === undefined
                        ? undefined
                        : JSON.stringify(
                              body,
                          ),
            },
        );

    let data = null;

    try {
        data =
            await response.json();
    } catch {
        data = null;
    }

    return {
        response,
        data,
    };
}

async function expectStatus(
    label,
    path,
    expectedStatus,
    options = {},
) {
    const {
        response,
        data,
    } =
        await request(
            path,
            options,
        );

    assert(
        response.status ===
            expectedStatus,
        `${label}: expected ${expectedStatus}, received ${response.status}. Response: ${JSON.stringify(
            data,
        )}`,
    );

    console.log(
        `PASS: ${label} (${expectedStatus})`,
    );

    return data;
}

async function main() {
    console.log(
        `GeoVaris tenant isolation verification: ${BASE_URL}`,
    );

    const tenantACookie =
        await signIn(
            TENANT_A_EMAIL,
            TENANT_A_PASSWORD,
        );

    const tenantBCookie =
        await signIn(
            TENANT_B_EMAIL,
            TENANT_B_PASSWORD,
        );

    await expectStatus(
        "Unauthenticated projects request is rejected",
        "/api/projects",
        401,
    );

    const tenantAProjects =
        await expectStatus(
            "Tenant A project list is authorized",
            "/api/projects",
            200,
            {
                cookie:
                    tenantACookie,
            },
        );

    assert(
        Array.isArray(
            tenantAProjects.projects,
        ),
        "Tenant A project response did not contain a projects array.",
    );

    assert(
        !tenantAProjects.projects.some(
            (project) =>
                project.id ===
                TENANT_B_PROJECT_ID,
        ),
        "Tenant A can see Tenant B project.",
    );

    console.log(
        "PASS: Tenant A cannot list Tenant B project",
    );

    const tenantBProjects =
        await expectStatus(
            "Tenant B project list is authorized",
            "/api/projects",
            200,
            {
                cookie:
                    tenantBCookie,
            },
        );

    assert(
        tenantBProjects.projects.some(
            (project) =>
                project.id ===
                TENANT_B_PROJECT_ID,
        ),
        "Tenant B cannot see its own project.",
    );

    console.log(
        "PASS: Tenant B can list its own project",
    );

    await expectStatus(
        "Tenant A cannot create site in Tenant B project",
        "/api/sites",
        404,
        {
            method: "POST",
            cookie:
                tenantACookie,
            body: {
                projectId:
                    TENANT_B_PROJECT_ID,
                name:
                    "Isolation Verification Site",
                latitude:
                    28.7,
                longitude:
                    -81.4,
            },
        },
    );

    await expectStatus(
        "Tenant A cannot create scenario on Tenant B site",
        "/api/scenarios",
        404,
        {
            method: "POST",
            cookie:
                tenantACookie,
            body: {
                siteId:
                    TENANT_B_SITE_ID,
                name:
                    "Isolation Verification Scenario",
                frequencyMhz:
                    600,
                eirpWatts:
                    1000,
                antennaHeightM:
                    60,
                antennaGainDbi:
                    0,
                receiverHeightM:
                    1.5,
                receiverThresholdDbm:
                    -95,
                calculationRadiusM:
                    48280.32,
                resolutionM:
                    30,
                propagationModel:
                    "free_space_test",
            },
        },
    );

    await expectStatus(
        "Tenant A cannot create run from Tenant B scenario",
        "/api/coverage-runs",
        404,
        {
            method: "POST",
            cookie:
                tenantACookie,
            body: {
                scenarioId:
                    TENANT_B_SCENARIO_ID,
                runMethod:
                    "rapid_coverage",
            },
        },
    );

    await expectStatus(
        "Tenant A cannot read Tenant B coverage result",
        `/api/coverage-runs/latest?scenarioId=${encodeURIComponent(
            TENANT_B_SCENARIO_ID,
        )}&includeGeometry=false`,
        404,
        {
            cookie:
                tenantACookie,
        },
    );

    console.log();
    console.log(
        "GeoVaris tenant isolation verification PASSED.",
    );
}

main().catch(
    (error) => {
        console.error();
        console.error(
            "GeoVaris tenant isolation verification FAILED.",
        );
        console.error(error);

        process.exitCode = 1;
    },
);