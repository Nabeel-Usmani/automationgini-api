-- Phase 1 schema for the "Build My Business CRM" product: a per-client
-- mini-CRM (staff portal + public booking page) built for a lead's business,
-- distinct from AutomationGini's own agency tenants/users.
--
-- This repo has no migration runner - apply this by hand against the
-- database referenced by DATABASE_URL before deploying the code that uses
-- it (portal_auth.py, portal.py, public_booking.py, and the
-- /build/business-crm/* endpoints in build.py).
--
-- Safe to re-run: every statement is guarded (IF NOT EXISTS / DO block).

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS crm_workspaces (
    id            SERIAL PRIMARY KEY,
    purchase_id   INTEGER REFERENCES purchases(id),
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id),
    agent_id      INTEGER NOT NULL REFERENCES gmaps_users(id),
    lead_id       INTEGER NOT NULL REFERENCES gmaps_leads(id),
    business_name TEXT NOT NULL,
    slug          TEXT NOT NULL UNIQUE,
    timezone      TEXT NOT NULL DEFAULT 'UTC',
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crm_workspaces_tenant ON crm_workspaces (tenant_id);

-- Staff logins for the client business itself - intentionally separate from
-- gmaps_users (AutomationGini's own agency users). email is globally unique
-- (not per-workspace) so /portal/auth/login can find the right account
-- without asking which workspace first; real-world staff won't need the
-- same email at two different client businesses in v1.
CREATE TABLE IF NOT EXISTS crm_staff (
    id                 SERIAL PRIMARY KEY,
    workspace_id       INTEGER NOT NULL REFERENCES crm_workspaces(id),
    email              TEXT NOT NULL UNIQUE,
    password_hash      TEXT,
    full_name          TEXT NOT NULL,
    role               TEXT NOT NULL DEFAULT 'staff' CHECK (role IN ('owner', 'staff')),
    invite_token       TEXT UNIQUE,
    invite_expires_at  TIMESTAMPTZ,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crm_staff_workspace ON crm_staff (workspace_id);

CREATE TABLE IF NOT EXISTS crm_services (
    id               SERIAL PRIMARY KEY,
    workspace_id     INTEGER NOT NULL REFERENCES crm_workspaces(id),
    name             TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    price_cents      INTEGER,
    active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crm_services_workspace ON crm_services (workspace_id);

-- Weekly recurring hours. staff_id is NULL for v1 (one shared calendar per
-- workspace, no per-staff-member schedules yet) but the column exists so
-- per-staff hours can be added later without a schema change.
CREATE TABLE IF NOT EXISTS crm_availability (
    id           SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES crm_workspaces(id),
    staff_id     INTEGER REFERENCES crm_staff(id),
    day_of_week  SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Monday
    start_time   TIME NOT NULL,
    end_time     TIME NOT NULL CHECK (end_time > start_time)
);

CREATE INDEX IF NOT EXISTS idx_crm_availability_workspace ON crm_availability (workspace_id);

CREATE TABLE IF NOT EXISTS crm_blackouts (
    id           SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES crm_workspaces(id),
    staff_id     INTEGER REFERENCES crm_staff(id),
    date         DATE NOT NULL,
    reason       TEXT
);

CREATE INDEX IF NOT EXISTS idx_crm_blackouts_workspace_date ON crm_blackouts (workspace_id, date);

CREATE TABLE IF NOT EXISTS crm_appointments (
    id             SERIAL PRIMARY KEY,
    workspace_id   INTEGER NOT NULL REFERENCES crm_workspaces(id),
    service_id     INTEGER NOT NULL REFERENCES crm_services(id),
    staff_id       INTEGER REFERENCES crm_staff(id),
    customer_name  TEXT NOT NULL,
    customer_email TEXT,
    customer_phone TEXT,
    starts_at      TIMESTAMPTZ NOT NULL,
    ends_at        TIMESTAMPTZ NOT NULL CHECK (ends_at > starts_at),
    status         TEXT NOT NULL DEFAULT 'booked' CHECK (status IN ('booked', 'cancelled', 'completed', 'no_show')),
    source         TEXT NOT NULL DEFAULT 'staff_manual' CHECK (source IN ('public_booking', 'staff_manual')),
    notes          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crm_appointments_workspace_time ON crm_appointments (workspace_id, starts_at);

-- The actual double-booking guard: two 'booked' appointments for the same
-- workspace + staff member (or the same workspace's shared calendar, when
-- staff_id is NULL - hence the COALESCE, since NULL <> NULL would otherwise
-- let two null-staff bookings overlap freely) can never have overlapping
-- time ranges. Enforced by Postgres itself, so it holds even under
-- concurrent requests from the public booking page - app-level
-- check-then-insert has a race window this doesn't.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'crm_appointments_no_overlap'
    ) THEN
        ALTER TABLE crm_appointments
            ADD CONSTRAINT crm_appointments_no_overlap
            EXCLUDE USING gist (
                workspace_id WITH =,
                COALESCE(staff_id, -1) WITH =,
                tstzrange(starts_at, ends_at) WITH &&
            ) WHERE (status = 'booked');
    END IF;
END $$;
