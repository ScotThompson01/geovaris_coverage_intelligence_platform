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

const VIEWER_EMAIL =
    process.env.GEOVARIS_TEST_VIEWER_EMAIL;

const VIEWER_PASSWORD =
    process.env.GEOVARIS_TEST_VIEWER_PASSWORD;

const TENANT_B_PROJECT_ID =
    process.env.GEOVARIS_TEST_TENANT_B_PROJECT_ID;

const TENANT_B_SITE_ID =
    process.env.GEOVARIS_TEST_TENANT_B_SITE_ID;

const TENANT_B_SCENARIO_ID =
    process.env.GEOVARIS_TEST_TENANT_B_SCENARIO_ID;

const TENANT_A_SCENARIO_ID =
    process.env.GEOVARIS_TEST_TENANT_A_SCENARIO_ID;

const requiredValues = {
    GEOVARIS_TEST_TENANT_A_EMAIL:
        TENANT_A_EMAIL,

    GEOVARIS_TEST_TENANT_A_PASSWORD:
        TENANT_A_PASSWORD,

    GEOVARIS_TEST_TENANT_B_EMAIL:
        TENANT_B_EMAIL,

    GEOVARIS_TEST_TENANT_B_PASSWORD:
        TENANT_B_PASSWORD,

    GEOVARIS_TEST_VIEWER_EMAIL:
        VIEWER_EMAIL,

    GEOVARIS_TEST_VIEWER_PASSWORD:
        VIEWER_PASSWORD,

    GEOVARIS_TEST_TENANT_B_PROJECT_ID:
        TENANT_B_PROJECT_ID,

    GEOVARIS_TEST_TENANT_B_SITE_ID:
        TENANT_B_SITE_ID,

    GEOVARIS_TEST_TENANT_B_SCENARIO_ID:
        TENANT_B_SCENARIO_ID,

    GEOVARIS_TEST_TENANT_A_SCENARIO_ID:
        TENANT_A_SCENARIO_ID,
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

    const viewerCookie =
        await signIn(
            VIEWER_EMAIL,
            VIEWER_PASSWORD,
        );

    /*
     * Authentication boundary
     */

    await expectStatus(
        "Unauthenticated projects request is rejected",
        "/api/projects",
        401,
    );

    /*
     * Tenant A read isolation
     */

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
        tenantAProjects.projects.length >
            0,
        "Tenant A does not have any projects available for verification.",
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

    /*
     * Tenant B read isolation
     */

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

    /*
     * Cross-tenant write isolation
     */

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

    /*
     * Viewer read authorization
     */

    const viewerProjects =
        await expectStatus(
            "Viewer project list is authorized",
            "/api/projects",
            200,
            {
                cookie:
                    viewerCookie,
            },
        );

    assert(
        Array.isArray(
            viewerProjects.projects,
        ),
        "Viewer project response did not contain a projects array.",
    );

    assert(
        viewerProjects.projects.length >
            0,
        "Viewer cannot read its authorized Tenant A projects.",
    );

    assert(
        !viewerProjects.projects.some(
            (project) =>
                project.id ===
                TENANT_B_PROJECT_ID,
        ),
        "Viewer can see Tenant B project.",
    );

    console.log(
        "PASS: Viewer can read Tenant A projects without seeing Tenant B",
    );

    const viewerSites =
        await expectStatus(
            "Viewer site list is authorized",
            "/api/sites",
            200,
            {
                cookie:
                    viewerCookie,
            },
        );

    assert(
        Array.isArray(
            viewerSites.sites,
        ),
        "Viewer site response did not contain a sites array.",
    );

    assert(
        viewerSites.sites.length >
            0,
        "Viewer cannot read its authorized Tenant A sites.",
    );

    assert(
        !viewerSites.sites.some(
            (site) =>
                site.id ===
                TENANT_B_SITE_ID,
        ),
        "Viewer can see Tenant B site.",
    );

    console.log(
        "PASS: Viewer can read Tenant A sites without seeing Tenant B",
    );

const viewerWritableProjects =
    await expectStatus(
        "Viewer writable project list request is authorized",
        "/api/projects?access=write",
        200,
        {
            cookie:
                viewerCookie,
        },
    );

assert(
    Array.isArray(
        viewerWritableProjects.projects,
    ),
    "Viewer writable project response did not contain a projects array.",
);

assert(
    viewerWritableProjects.projects.length ===
        0,
    "Viewer received writable projects despite having read-only access.",
);

console.log(
    "PASS: Viewer writable project list is empty",
);

const viewerWritableSites =
    await expectStatus(
        "Viewer writable site list request is authorized",
        "/api/sites?access=write",
        200,
        {
            cookie:
                viewerCookie,
        },
    );

assert(
    Array.isArray(
        viewerWritableSites.sites,
    ),
    "Viewer writable site response did not contain a sites array.",
);

assert(
    viewerWritableSites.sites.length ===
        0,
    "Viewer received writable sites despite having read-only access.",
);

console.log(
    "PASS: Viewer writable site list is empty",
);

    /*
     * Viewer write denial
     */

    const tenantAProjectId =
        viewerProjects.projects[0].id;

    const tenantASiteId =
        viewerSites.sites[0].id;

    await expectStatus(
        "Viewer cannot create site in its own customer",
        "/api/sites",
        404,
        {
            method: "POST",
            cookie:
                viewerCookie,
            body: {
                projectId:
                    tenantAProjectId,

                name:
                    "Viewer Write Denial Site",

                latitude:
                    28.61,

                longitude:
                    -81.31,
            },
        },
    );

    await expectStatus(
        "Viewer cannot create scenario on its own customer site",
        "/api/scenarios",
        404,
        {
            method: "POST",
            cookie:
                viewerCookie,
            body: {
                siteId:
                    tenantASiteId,

                name:
                    "Viewer Write Denial Scenario",

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
        "Viewer cannot create coverage run in its own customer",
        "/api/coverage-runs",
        404,
        {
            method: "POST",
            cookie:
                viewerCookie,
            body: {
                scenarioId:
                    TENANT_A_SCENARIO_ID,

                runMethod:
                    "rapid_coverage",
            },
        },
    );

    /*
     * Viewer may read an authorized coverage result.
     *
     * We accept 200 or 404 here because the selected authorized
     * scenario may legitimately have no completed coverage run.
     * The important security condition is that it must not be
     * rejected as unauthenticated or cross-tenant access.
     */

    const viewerCoverageResult =
        await request(
            `/api/coverage-runs/latest?scenarioId=${encodeURIComponent(
                TENANT_A_SCENARIO_ID,
            )}&includeGeometry=false`,
            {
                cookie:
                    viewerCookie,
            },
        );

    assert(
        viewerCoverageResult.response.status ===
            200 ||
            viewerCoverageResult.response.status ===
                404,
        `Viewer coverage read returned unexpected status ${viewerCoverageResult.response.status}. Response: ${JSON.stringify(
            viewerCoverageResult.data,
        )}`,
    );

    console.log(
        `PASS: Viewer coverage read reached authorized tenant scope (${viewerCoverageResult.response.status})`,
    );

    console.log();
    console.log(
        "GeoVaris tenant isolation and role authorization verification PASSED.",
    );
}

main().catch(
    (error) => {
        console.error();

        console.error(
            "GeoVaris tenant isolation and role authorization verification FAILED.",
        );

        console.error(error);

        process.exitCode = 1;
    },
);