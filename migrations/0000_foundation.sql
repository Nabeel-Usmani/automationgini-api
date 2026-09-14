-- RECONSTRUCTED FOUNDATIONAL SCHEMA
--
-- This file did not exist in the original database history. The real
-- foundational schema was created by hand directly against Postgres on
-- Render (never checked into this repo) and was lost when the Render
-- database was suspended for billing. migrations/0001_business_crm.sql
-- through 0012_credits_system.sql are all INCREMENTAL migrations that
-- assume this foundational schema already exists (they ALTER these
-- tables and REFERENCE them as foreign keys, but never CREATE them).
--
-- This file reconstructs that missing foundation by reading:
--   1. Every ALTER TABLE / REFERENCES / trigger target in migrations
--      0001-0012, to see what columns those migrations assume exist.
--   2. Every raw SQL string in the FastAPI route files (auth.py,
--      dashboard.py, leads.py, billing.py, credits.py, search.py,
--      survey.py, preview.py, crm_common.py, demo.py, email_automation.py,
--      inbound_reply.py, admin.py, app_mockup_demo.py, audit.py, build.py,
--      calendly.py, portal_auth.py, portal.py, public_booking.py,
--      agent_ops.py, templates_routes.py) to infer every column, type,
--      and constraint actually used by the running application.
--
-- Columns that a LATER migration adds via ALTER TABLE ... ADD COLUMN are
-- deliberately NOT included here, so that migration still applies cleanly
-- on top of this file (e.g. gmaps_leads.search_channel is added by 0007,
-- not defined here; tenants.credit_balance is added by 0012, not here).
--
-- See migrations/0000_foundation_NOTES.md for a confidence breakdown and
-- open questions a human should review before this goes live.
--
-- Safe to re-run: every statement is guarded (IF NOT EXISTS).
-- Must run BEFORE 0001 (hence the 0000 prefix).

-- ===========================================================================
-- tenants: AutomationGini's own agency/account tenants (one per signup).
-- Referenced as an FK target by 0001 (crm_workspaces.tenant_id), and
-- ALTER'd by 0008 (email_automation_enabled), 0011 (premium_leads_enabled)
-- and 0012 (credit_balance + the grant_signup_credits AFTER INSERT trigger).
-- ===========================================================================
CREATE TABLE IF NOT EXISTS tenants (
    id                  SERIAL PRIMARY KEY,
    company_name        TEXT NOT NULL,
    plan_name           TEXT NOT NULL DEFAULT 'Free', -- 'Free' | 'Starter' | 'Professional' | 'Agency' (billing.py PLAN_DEFINITIONS) - no CHECK: plan names are a business decision (billing.py), not something this schema should hard-block
    subscription_status TEXT NOT NULL DEFAULT 'active', -- gates login/access in auth.py against ('active','trialing'); other values (e.g. 'past_due','canceled') are almost certainly set by a Stripe webhook not in this repo, so left unconstrained
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===========================================================================
-- gmaps_users: AutomationGini's OWN agency users (agency owners + their
-- agents) - explicitly distinct from gmaps_leads (scraped prospects) and
-- from crm_staff (a client business's own staff, added in 0001). Named
-- "gmaps_users" for historical reasons (this product started as a single
-- Google-Maps-lead-scraping tool). Referenced as an FK target by 0001
-- (crm_workspaces.agent_id) and by 0003's comment ("...alongside
-- gmaps_users.login_count").
-- ===========================================================================
CREATE TABLE IF NOT EXISTS gmaps_users (
    id                SERIAL PRIMARY KEY,
    tenant_id         INTEGER NOT NULL REFERENCES tenants(id),
    username          TEXT NOT NULL UNIQUE, -- actually an email address (auth.py logs in via `WHERE username = %s` on a lowercased email) - kept as `username` to match the column name used everywhere in the Python code
    password_hash     TEXT NOT NULL,        -- bcrypt hash; Google-only signups get a random unusable password so this is always set
    full_name         TEXT NOT NULL,
    role              TEXT NOT NULL DEFAULT 'agent' CHECK (role IN ('admin', 'agent')), -- 'admin' = agency owner (signup.py, admin.py create_agency_owner), 'agent' = a team member scoped to only their own leads (dashboard.py/leads.py _scope_clause)
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    is_platform_owner BOOLEAN NOT NULL DEFAULT FALSE, -- AutomationGini's own internal staff flag (admin.py), unrelated to `role`
    phone_number      TEXT,
    country_code      TEXT,   -- best-effort IP geolocation on login (auth.py _capture_login_location)
    country_name      TEXT,
    last_active_at    TIMESTAMPTZ, -- "active now" heartbeat, throttled to once/60s (auth.py get_current_user)
    login_count       INTEGER NOT NULL DEFAULT 0, -- drives survey.py's "show survey from 2nd login onward" rule
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gmaps_users_tenant ON gmaps_users (tenant_id);

-- ===========================================================================
-- user_surveys: per 0003's own comment, this table was "created by hand
-- alongside gmaps_users.login_count" - i.e. it predates migration 0003,
-- which only adds the later `suggestions` column to it. That column is
-- intentionally left out here so 0003's ALTER TABLE ADD COLUMN still has
-- something to do.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS user_surveys (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES gmaps_users(id),
    trigger_type        TEXT NOT NULL CHECK (trigger_type IN ('login', 'logout')),
    session_number      INTEGER, -- login_count at time of submission (survey.py), nullable since the SELECT that produces it can come back empty
    rating              INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    likely_to_reuse     INTEGER NOT NULL CHECK (likely_to_reuse BETWEEN 1 AND 5),
    willingness_to_pay  NUMERIC,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_surveys_user ON user_surveys (user_id);

-- ===========================================================================
-- gmaps_leads: scraped/prospected business leads. The single most-referenced
-- foundational table - FK target in 0001 (crm_workspaces.lead_id), 0008 and
-- 0010 (ON DELETE CASCADE), and columns are added to it by 0005
-- (social_links, qualification_tier, qualification_notes, enriched_at -
-- deliberately NOT included here) and 0007 (search_channel - also NOT
-- included here, so that migration has something to add).
-- ===========================================================================
CREATE TABLE IF NOT EXISTS gmaps_leads (
    id                SERIAL PRIMARY KEY,
    tenant_id         INTEGER NOT NULL REFERENCES tenants(id),
    agent_id          INTEGER NOT NULL REFERENCES gmaps_users(id), -- every code path that creates a lead (search.py /search/run, leads.py custom-listing) always supplies the requesting agent's id
    business_name     TEXT NOT NULL,
    niche             TEXT,    -- nullable: leads.py filter-options explicitly does `AND l.niche IS NOT NULL`
    phone_number      TEXT,
    email             TEXT,
    city              TEXT,    -- nullable: same `IS NOT NULL` filter pattern as niche/country
    country           TEXT,
    country_code      TEXT,
    review_count      INTEGER,
    total_score       NUMERIC, -- a star rating (compared against `< 4`, i.e. out of 5) -- TODO: verify precision/scale
    website           TEXT,
    website_status    TEXT,    -- free-form status set by the scraping/enrichment pipeline (n8n), not enumerated anywhere in this repo's Python code
    call_status       TEXT NOT NULL DEFAULT 'New' CHECK (call_status IN ('New', 'Called', 'Interested', 'Not Interested', 'Follow-up')), -- leads.py STATUS_OPTIONS - the only endpoint that writes this (update_lead_status) enforces the same closed set
    status_updated_at TIMESTAMPTZ,
    source            TEXT,    -- e.g. 'custom_listing' vs the normal scrape pipeline; filterable in leads.py but never enumerated there
    is_archived       BOOLEAN NOT NULL DEFAULT FALSE,
    scraped_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gmaps_leads_tenant_agent ON gmaps_leads (tenant_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_gmaps_leads_scraped_at ON gmaps_leads (tenant_id, scraped_at DESC);

-- ===========================================================================
-- purchases: every paid product (website, voice agent, chatbot subscription,
-- business CRM, app mockup, credit packs). FK target in 0001
-- (crm_workspaces.purchase_id) and ALTER'd by 0012 (credit_amount, not
-- included here since 0012 adds it). preview.py, demo.py, build.py,
-- app_mockup_demo.py and credits.py all read/write this table extensively.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS purchases (
    id                   SERIAL PRIMARY KEY,
    tenant_id            INTEGER NOT NULL REFERENCES tenants(id),
    agent_id             INTEGER REFERENCES gmaps_users(id), -- passed on every checkout payload (build.py, credits.py) alongside tenant_id; not read back directly anywhere in this repo's Python, included for consistency with usage_log/chatbot_configs -- TODO: verify nullability
    lead_id              INTEGER REFERENCES gmaps_leads(id), -- nullable: admin.py LEFT JOINs gmaps_leads on this, and a 'credits' purchase has no associated lead at all
    product_type         TEXT NOT NULL, -- 'website_html' | 'website_react' | 'website_react_video' | 'website_html_nemotron' | 'voice_agent' | 'business_crm' | 'app_mockup' | 'credits' (seen across demo.py/build.py/credits.py) - no CHECK: fulfillment is driven by n8n/Stripe outside this repo and may add more values over time
    price                NUMERIC, -- admin.py SUMs this as revenue
    payment_status       TEXT NOT NULL DEFAULT 'pending', -- compared to 'paid' in admin.py; other values set by the Stripe webhook (not in this repo) - left unconstrained
    fulfillment_status   TEXT NOT NULL DEFAULT 'pending', -- 'building' | 'completed' seen in preview.py/credits.py; likely more values from n8n - left unconstrained
    fulfillment_detail   JSONB, -- {"pages": {...}} for websites (preview.py, build.py jsonb_set on this)
    preview_token        TEXT UNIQUE, -- a UUID string; preview.py looks purchases up by this directly
    preview_expires_at   TIMESTAMPTZ,
    fulfilled_at         TIMESTAMPTZ, -- set once a 'credits' purchase is fulfilled (credits.py /grant)
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_purchases_tenant ON purchases (tenant_id);
CREATE INDEX IF NOT EXISTS idx_purchases_lead ON purchases (lead_id);

-- ===========================================================================
-- chatbot_configs: each deployed/demo AI chatbot. FK target in
-- 0004_chatbot_calendly.sql (chatbot_calendly_connections.chatbot_config_id).
-- ===========================================================================
CREATE TABLE IF NOT EXISTS chatbot_configs (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id),
    agent_id            INTEGER REFERENCES gmaps_users(id),
    lead_id             INTEGER REFERENCES gmaps_leads(id),
    business_name       TEXT,
    chatbot_token       TEXT UNIQUE, -- inferred: a per-chatbot public token, following the same pattern as crm_staff.invite_token in 0001 -- TODO: verify uniqueness/nullability against how the public chatbot widget looks this up (not in this repo)
    is_demo             BOOLEAN NOT NULL DEFAULT FALSE, -- demo.py filters `is_demo = true`
    demo_expires_at     TIMESTAMPTZ,
    status              TEXT NOT NULL DEFAULT 'active', -- build.py filters `status = 'active'`; other values (e.g. 'cancelled') presumably set by a Stripe subscription webhook not in this repo
    current_period_end  TIMESTAMPTZ, -- build.py selects this; implies a recurring Stripe subscription
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chatbot_configs_tenant ON chatbot_configs (tenant_id);

-- ===========================================================================
-- usage_log: every billable/trackable event (zoom calls, demos). Drives
-- billing.py's monthly quota checks and dashboard.py's summary counts.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS usage_log (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id),
    agent_id        INTEGER REFERENCES gmaps_users(id),
    lead_id         INTEGER REFERENCES gmaps_leads(id),
    event_type      TEXT NOT NULL, -- 'zoom_call' | 'vapi_call' | 'chatbot_demo' | 'mockup' | 'app_mockup' | 'business_crm' seen across dashboard.py/billing.py/credits.py - no CHECK: this list is assembled from several files and a missed value would silently break quota accounting, worse than an unconstrained column
    estimated_cost  NUMERIC NOT NULL DEFAULT 0,
    detail          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_log_tenant_created ON usage_log (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_log_event_type ON usage_log (event_type, created_at);

-- ===========================================================================
-- lead_audits: the "Online Presence Audit" PDF report data for one lead
-- (audit.py). One audit per lead in practice (audit_status treats any row
-- as "ready"); regenerating presumably upserts, hence UNIQUE(lead_id).
-- ===========================================================================
CREATE TABLE IF NOT EXISTS lead_audits (
    id                        SERIAL PRIMARY KEY,
    lead_id                   INTEGER NOT NULL UNIQUE REFERENCES gmaps_leads(id) ON DELETE CASCADE,
    has_website               BOOLEAN,
    performance_score         INTEGER,
    seo_score                 INTEGER,
    accessibility_score       INTEGER,
    best_practices_score      INTEGER,
    listing_score             INTEGER,
    listing_score_breakdown   JSONB,
    findings                  JSONB,
    niche_benchmark           JSONB,
    action_plan               JSONB,
    generated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===========================================================================
-- website_revisions: agent-requested edits to a delivered website
-- (build.py /website/{purchase_id}/request-change and /approve, /reject).
-- ===========================================================================
CREATE TABLE IF NOT EXISTS website_revisions (
    id             SERIAL PRIMARY KEY,
    purchase_id    INTEGER NOT NULL REFERENCES purchases(id),
    page_key       TEXT NOT NULL,
    request_text   TEXT NOT NULL,
    requested_by   INTEGER NOT NULL REFERENCES gmaps_users(id),
    revised_html   TEXT,
    status         TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'applied', 'rejected')), -- fully owned/written by this codebase (build.py approve/reject), so a CHECK is safe here unlike purchases.fulfillment_status
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_website_revisions_purchase ON website_revisions (purchase_id);

-- ===========================================================================
-- city_coordinates: geocoding cache for the dashboard map (dashboard.py
-- city_coordinates()). Not an FK target anywhere, but read/written directly.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS city_coordinates (
    id       SERIAL PRIMARY KEY,
    city     TEXT NOT NULL,
    country  TEXT NOT NULL,
    lat      NUMERIC,
    lng      NUMERIC,
    UNIQUE (city, country)
);

-- ===========================================================================
-- template_previews: static HTML preview snapshot for a website template,
-- keyed by the string template ids defined in templates_data.py
-- (templates_routes.py /templates/preview).
-- ===========================================================================
CREATE TABLE IF NOT EXISTS template_previews (
    template_id  TEXT PRIMARY KEY,
    html         TEXT -- TODO: verify whether this is meant to be NOT NULL; templates_routes.py treats an empty/NULL value as "not available yet" either way
);

-- ===========================================================================
-- lead_email_replies: inbound replies to an outreach sequence, matched by
-- the IMAP/Brevo poller (inbound_reply.py, read by email_automation.py
-- /replies). IMPORTANT: this table is used by the app but is referenced by
-- NO migration file at all - it isn't part of the true pre-0001 foundation,
-- because it logically depends on lead_email_sequences, which is only
-- created later by migration 0008_email_automation.sql. Since this file
-- (0000) necessarily runs before 0008, the FK to lead_email_sequences(id)
-- is deliberately omitted here (sequence_id is a plain INTEGER) so table
-- creation doesn't fail for lack of its target. A human should add
-- `ALTER TABLE lead_email_replies ADD CONSTRAINT ... FOREIGN KEY
-- (sequence_id) REFERENCES lead_email_sequences(id) ON DELETE CASCADE`
-- in a follow-up migration once 0008 has run. See the NOTES file.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS lead_email_replies (
    id            SERIAL PRIMARY KEY,
    sequence_id   INTEGER NOT NULL, -- logically REFERENCES lead_email_sequences(id) - FK intentionally omitted, see comment above
    from_email    TEXT NOT NULL,
    subject       TEXT,
    body          TEXT,
    received_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lead_email_replies_sequence ON lead_email_replies (sequence_id);

-- ===========================================================================
-- agent_runs / agent_backlog: the autonomous "agent-ops" monitor/build loop
-- (agent_ops.py). Entirely independent of the tenant/lead schema above -
-- not referenced by any migration, discovered only via agent_ops.py's raw
-- SQL. Included here purely so the API's /agent-ops/* endpoints work
-- against a fresh database.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS agent_runs (
    id                SERIAL PRIMARY KEY,
    category          TEXT NOT NULL CHECK (category IN ('monitor', 'build')),
    skill_used        TEXT,
    target            TEXT,
    task_description  TEXT NOT NULL,
    status            TEXT NOT NULL CHECK (status IN ('success', 'failed', 'blocked')),
    summary           TEXT,
    commit_url        TEXT,
    error_detail      TEXT,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_started_at ON agent_runs (started_at DESC);

CREATE TABLE IF NOT EXISTS agent_backlog (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'done', 'blocked')),
    priority        INTEGER NOT NULL DEFAULT 3,
    blocked_reason  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
