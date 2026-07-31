ALTER TABLE gmaps_leads ADD COLUMN IF NOT EXISTS search_channel TEXT NOT NULL DEFAULT 'google_maps';

ALTER TABLE gmaps_search_jobs ADD COLUMN IF NOT EXISTS search_channel TEXT NOT NULL DEFAULT 'google_maps';

CREATE INDEX IF NOT EXISTS idx_gmaps_leads_search_channel ON gmaps_leads (tenant_id, search_channel);
