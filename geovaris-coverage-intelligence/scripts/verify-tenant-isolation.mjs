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

const ANALYST_EMAIL =
    process.env.GEOVARIS_TEST_ANALYST_EMAIL;

const ANALYST_PASSWORD =
    process.env.GEOVARIS_TEST_ANALYST_PASSWORD;

const ADMIN_EMAIL =
    process.env.GEOVARIS_TEST_ADMIN_EMAIL;

const ADMIN_PASSWORD =
    process.env.GEOVARIS_TEST_ADMIN_PASSWORD;

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

    GEOVARIS_TEST_ANALYST_EMAIL:
        ANALYST_EMAIL,

    GEOVARIS_TEST_ANALYST_PASSWORD:
        ANALYST_PASSWORD,

    GEOVARIS_TEST_ADMIN_EMAIL:
        ADMIN_EMAIL,

    GEOVARIS_TEST_ADMIN_PASSWORD:
        ADMIN_PASSWORD,

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
        throw new Error(
            message,
        );
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

    return cookies.join(
        "; ",
    );
}

async function signIn(
    email,
    password,
) {
    const response =
        await fetch(
            `${BASE_URL}/api/auth/sign-in/email`,
            {
                method:
                    "POST",

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

    if (
        body !== undefined
    ) {
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
        data =
            null;
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

    const analystCookie =
        await signIn(
            ANALYST_EMAIL,
            ANALYST_PASSWORD,
        );

    const adminCookie =
        await signIn(
            ADMIN_EMAIL,
            ADMIN_PASSWORD,
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
        Array.isArray(
            tenantBProjects.projects,
        ),
        "Tenant B project response did not contain a projects array.",
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
     * Cross-tenant isolation
     */

    await expectStatus(
        "Tenant A cannot create site in Tenant B project",
        "/api/sites",
        404,
        {
            method:
                "POST",

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
            method:
                "POST",

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
            method:
                "POST",

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

    /*
     * Viewer writable-resource filtering
     */

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
            method:
                "POST",

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
            method:
                "POST",

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
            method:
                "POST",

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

    /*
     * Analyst read authorization
     */

    const analystProjects =
        await expectStatus(
            "Analyst project list is authorized",
            "/api/projects",
            200,
            {
                cookie:
                    analystCookie,
            },
        );

    assert(
        Array.isArray(
            analystProjects.projects,
        ),
        "Analyst project response did not contain a projects array.",
    );

    assert(
        analystProjects.projects.length >
            0,
        "Analyst cannot read its authorized Tenant A projects.",
    );

    assert(
        !analystProjects.projects.some(
            (project) =>
                project.id ===
                TENANT_B_PROJECT_ID,
        ),
        "Analyst can see Tenant B project.",
    );

    console.log(
        "PASS: Analyst can read Tenant A projects without seeing Tenant B",
    );

    const analystSites =
        await expectStatus(
            "Analyst site list is authorized",
            "/api/sites",
            200,
            {
                cookie:
                    analystCookie,
            },
        );

    assert(
        Array.isArray(
            analystSites.sites,
        ),
        "Analyst site response did not contain a sites array.",
    );

    assert(
        analystSites.sites.length >
            0,
        "Analyst cannot read its authorized Tenant A sites.",
    );

    assert(
        !analystSites.sites.some(
            (site) =>
                site.id ===
                TENANT_B_SITE_ID,
        ),
        "Analyst can see Tenant B site.",
    );

    console.log(
        "PASS: Analyst can read Tenant A sites without seeing Tenant B",
    );

    /*
     * Analyst writable-resource filtering
     */

    const analystWritableProjects =
        await expectStatus(
            "Analyst writable project list request is authorized",
            "/api/projects?access=write",
            200,
            {
                cookie:
                    analystCookie,
            },
        );

    assert(
        Array.isArray(
            analystWritableProjects.projects,
        ),
        "Analyst writable project response did not contain a projects array.",
    );

    assert(
        analystWritableProjects.projects.length ===
            0,
        "Analyst received writable projects despite having read-only access.",
    );

    console.log(
        "PASS: Analyst writable project list is empty",
    );

    const analystWritableSites =
        await expectStatus(
            "Analyst writable site list request is authorized",
            "/api/sites?access=write",
            200,
            {
                cookie:
                    analystCookie,
            },
        );

    assert(
        Array.isArray(
            analystWritableSites.sites,
        ),
        "Analyst writable site response did not contain a sites array.",
    );

    assert(
        analystWritableSites.sites.length ===
            0,
        "Analyst received writable sites despite having read-only access.",
    );

    console.log(
        "PASS: Analyst writable site list is empty",
    );

    /*
     * Analyst write denial
     */

    const analystProjectId =
        analystProjects.projects[0].id;

    const analystSiteId =
        analystSites.sites[0].id;

    await expectStatus(
        "Analyst cannot create site in its own customer",
        "/api/sites",
        404,
        {
            method:
                "POST",

            cookie:
                analystCookie,

            body: {
                projectId:
                    analystProjectId,

                name:
                    "Analyst Write Denial Site",

                latitude:
                    28.62,

                longitude:
                    -81.32,
            },
        },
    );

    await expectStatus(
        "Analyst cannot create scenario on its own customer site",
        "/api/scenarios",
        404,
        {
            method:
                "POST",

            cookie:
                analystCookie,

            body: {
                siteId:
                    analystSiteId,

                name:
                    "Analyst Write Denial Scenario",

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
        "Analyst cannot create coverage run in its own customer",
        "/api/coverage-runs",
        404,
        {
            method:
                "POST",

            cookie:
                analystCookie,

            body: {
                scenarioId:
                    TENANT_A_SCENARIO_ID,

                runMethod:
                    "rapid_coverage",
            },
        },
    );

    const analystCoverageResult =
        await request(
            `/api/coverage-runs/latest?scenarioId=${encodeURIComponent(
                TENANT_A_SCENARIO_ID,
            )}&includeGeometry=false`,
            {
                cookie:
                    analystCookie,
            },
        );

    assert(
        analystCoverageResult.response.status ===
            200 ||
            analystCoverageResult.response.status ===
                404,
        `Analyst coverage read returned unexpected status ${analystCoverageResult.response.status}. Response: ${JSON.stringify(
            analystCoverageResult.data,
        )}`,
    );

    console.log(
        `PASS: Analyst coverage read reached authorized tenant scope (${analystCoverageResult.response.status})`,
    );

    /*
     * GeoVaris Admin platform-wide authorization
     */

    const adminProjects =
        await expectStatus(
            "GeoVaris Admin project list is authorized",
            "/api/projects",
            200,
            {
                cookie:
                    adminCookie,
            },
        );

    assert(
        Array.isArray(
            adminProjects.projects,
        ),
        "GeoVaris Admin project response did not contain a projects array.",
    );

    assert(
        adminProjects.projects.some(
            (project) =>
                project.id ===
                TENANT_B_PROJECT_ID,
        ),
        "GeoVaris Admin cannot see Tenant B project.",
    );

    assert(
        adminProjects.projects.some(
            (project) =>
                tenantAProjects.projects.some(
                    (tenantAProject) =>
                        tenantAProject.id ===
                        project.id,
                ),
        ),
        "GeoVaris Admin cannot see Tenant A project.",
    );

    console.log(
        "PASS: GeoVaris Admin can read projects across Tenant A and Tenant B",
    );

    const adminWritableProjects =
        await expectStatus(
            "GeoVaris Admin writable project list is authorized",
            "/api/projects?access=write",
            200,
            {
                cookie:
                    adminCookie,
            },
        );

    assert(
        Array.isArray(
            adminWritableProjects.projects,
        ),
        "GeoVaris Admin writable project response did not contain a projects array.",
    );

    assert(
        adminWritableProjects.projects.some(
            (project) =>
                project.id ===
                TENANT_B_PROJECT_ID,
        ),
        "GeoVaris Admin writable project list does not include Tenant B.",
    );

    console.log(
        "PASS: GeoVaris Admin can access writable projects across tenants",
    );

    const adminSites =
        await expectStatus(
            "GeoVaris Admin site list is authorized",
            "/api/sites",
            200,
            {
                cookie:
                    adminCookie,
            },
        );

    assert(
        Array.isArray(
            adminSites.sites,
        ),
        "GeoVaris Admin site response did not contain a sites array.",
    );

    assert(
        adminSites.sites.some(
            (site) =>
                site.id ===
                TENANT_B_SITE_ID,
        ),
        "GeoVaris Admin cannot see Tenant B site.",
    );

    assert(
        adminSites.sites.some(
            (site) =>
                viewerSites.sites.some(
                    (tenantASite) =>
                        tenantASite.id ===
                        site.id,
                ),
        ),
        "GeoVaris Admin cannot see Tenant A site.",
    );

    console.log(
        "PASS: GeoVaris Admin can read sites across Tenant A and Tenant B",
    );

    const adminWritableSites =
        await expectStatus(
            "GeoVaris Admin writable site list is authorized",
            "/api/sites?access=write",
            200,
            {
                cookie:
                    adminCookie,
            },
        );

    assert(
        Array.isArray(
            adminWritableSites.sites,
        ),
        "GeoVaris Admin writable site response did not contain a sites array.",
    );

    assert(
        adminWritableSites.sites.some(
            (site) =>
                site.id ===
                TENANT_B_SITE_ID,
        ),
        "GeoVaris Admin writable site list does not include Tenant B.",
    );

    console.log(
        "PASS: GeoVaris Admin can access writable sites across tenants",
    );

    const adminTenantACoverage =
        await request(
            `/api/coverage-runs/latest?scenarioId=${encodeURIComponent(
                TENANT_A_SCENARIO_ID,
            )}&includeGeometry=false`,
            {
                cookie:
                    adminCookie,
            },
        );

    assert(
        adminTenantACoverage.response.status ===
            200 ||
            adminTenantACoverage.response.status ===
                404,
        `GeoVaris Admin Tenant A coverage read returned unexpected status ${adminTenantACoverage.response.status}. Response: ${JSON.stringify(
            adminTenantACoverage.data,
        )}`,
    );

    console.log(
        `PASS: GeoVaris Admin can reach Tenant A coverage scope (${adminTenantACoverage.response.status})`,
    );

    const adminTenantBCoverage =
        await request(
            `/api/coverage-runs/latest?scenarioId=${encodeURIComponent(
                TENANT_B_SCENARIO_ID,
            )}&includeGeometry=false`,
            {
                cookie:
                    adminCookie,
            },
        );

    assert(
        adminTenantBCoverage.response.status ===
            200 ||
            adminTenantBCoverage.response.status ===
                404,
        `GeoVaris Admin Tenant B coverage read returned unexpected status ${adminTenantBCoverage.response.status}. Response: ${JSON.stringify(
            adminTenantBCoverage.data,
        )}`,
    );

    console.log(
        `PASS: GeoVaris Admin can reach Tenant B coverage scope (${adminTenantBCoverage.response.status})`,
    );

    /*
     * Reconfirm ordinary tenant isolation after admin checks
     */

    await expectStatus(
        "Tenant A remains isolated from Tenant B after GeoVaris Admin checks",
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
        "GeoVaris tenant isolation and role authorization verification PASSED.",
    );
}

main().catch(
    (error) => {
        console.error();

        console.error(
            "GeoVaris tenant isolation and role authorization verification FAILED.",
        );

        console.error(
            error,
        );

        process.exitCode =
            1;
    },
);