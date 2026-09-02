-- GeoVaris Coverage Intelligence
-- Migration 011
--
-- Adds Better Auth identity/session tables plus GeoVaris
-- platform-role and customer-membership authorization.
--
-- Better Auth owns authentication identity and session state.
-- GeoVaris owns application authorization.

CREATE TABLE "user" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "email" TEXT NOT NULL UNIQUE,
    "emailVerified" BOOLEAN NOT NULL,
    "image" TEXT,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "session" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "expiresAt" TIMESTAMPTZ NOT NULL,
    "token" TEXT NOT NULL UNIQUE,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ NOT NULL,
    "ipAddress" TEXT,
    "userAgent" TEXT,
    "userId" TEXT NOT NULL
        REFERENCES "user" ("id")
        ON DELETE CASCADE
);

CREATE TABLE "account" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "issuer" TEXT NOT NULL,
    "accountId" TEXT NOT NULL,
    "providerId" TEXT NOT NULL,
    "userId" TEXT NOT NULL
        REFERENCES "user" ("id")
        ON DELETE CASCADE,
    "accessToken" TEXT,
    "refreshToken" TEXT,
    "idToken" TEXT,
    "accessTokenExpiresAt" TIMESTAMPTZ,
    "refreshTokenExpiresAt" TIMESTAMPTZ,
    "scope" TEXT,
    "password" TEXT,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ NOT NULL
);

CREATE TABLE "verification" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "identifier" TEXT NOT NULL,
    "value" TEXT NOT NULL,
    "expiresAt" TIMESTAMPTZ NOT NULL,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX "session_userId_idx"
    ON "session" ("userId");

CREATE INDEX "account_userId_idx"
    ON "account" ("userId");

CREATE INDEX "verification_identifier_idx"
    ON "verification" ("identifier");

CREATE UNIQUE INDEX "account_issuer_accountId_uidx"
    ON "account" ("issuer", "accountId");


-- GeoVaris platform-level authorization.
--
-- Platform roles are intentionally separate from customer membership.
-- A GeoVaris Admin does not need to belong to a customer tenant.

CREATE TABLE user_platform_roles (
    user_id TEXT NOT NULL
        REFERENCES "user" ("id")
        ON DELETE CASCADE,

    role TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT user_platform_roles_pk
        PRIMARY KEY (
            user_id,
            role
        ),

    CONSTRAINT user_platform_roles_role_check
        CHECK (
            role IN (
                'geovaris_admin'
            )
        )
);

CREATE INDEX user_platform_roles_user_idx
    ON user_platform_roles (
        user_id
    );

COMMENT ON TABLE user_platform_roles IS
    'GeoVaris platform-level authorization roles independent of customer membership.';

COMMENT ON COLUMN user_platform_roles.role IS
    'GeoVaris platform role. Currently supports geovaris_admin.';


-- GeoVaris customer-level authorization.
--
-- A user may belong to one or more customer tenants.
-- Each membership carries the user's role within that customer.
--
-- The MVP UI may initially operate with one active customer at a time,
-- while the schema safely supports future multi-customer membership.

CREATE TABLE user_customer_memberships (
    user_id TEXT NOT NULL
        REFERENCES "user" ("id")
        ON DELETE CASCADE,

    customer_id UUID NOT NULL
        REFERENCES customers (id)
        ON DELETE CASCADE,

    role TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT user_customer_memberships_pk
        PRIMARY KEY (
            user_id,
            customer_id
        ),

    CONSTRAINT user_customer_memberships_role_check
        CHECK (
            role IN (
                'customer_admin',
                'engineer',
                'analyst',
                'viewer'
            )
        )
);

CREATE INDEX user_customer_memberships_customer_idx
    ON user_customer_memberships (
        customer_id
    );

CREATE INDEX user_customer_memberships_user_idx
    ON user_customer_memberships (
        user_id
    );

COMMENT ON TABLE user_customer_memberships IS
    'GeoVaris customer-tenant authorization linking Better Auth users to customers and tenant roles.';

COMMENT ON COLUMN user_customer_memberships.role IS
    'Customer-level role: customer_admin, engineer, analyst, or viewer.';