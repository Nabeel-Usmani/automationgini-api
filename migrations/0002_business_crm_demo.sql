-- Adds demo-workspace support to the business-CRM schema from
-- migrations/0001_business_crm.sql. Apply by hand against DATABASE_URL,
-- after 0001, before deploying the code that uses it (demo.py's
-- /demo/business-crm endpoints).
--
-- Safe to re-run: guarded with IF NOT EXISTS.

ALTER TABLE crm_workspaces ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_crm_workspaces_is_demo ON crm_workspaces (is_demo) WHERE is_demo = TRUE;
