ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS premium_leads_enabled BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE gmaps_search_jobs
  ADD COLUMN IF NOT EXISTS want_premium_leads BOOLEAN NOT NULL DEFAULT false;
