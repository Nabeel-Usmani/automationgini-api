CREATE TABLE IF NOT EXISTS gmaps_search_jobs (
  id TEXT PRIMARY KEY,
  tenant_id INTEGER NOT NULL,
  agent_id INTEGER,
  niche TEXT NOT NULL,
  city TEXT NOT NULL,
  target_leads INTEGER NOT NULL,
  leads_found INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'running',
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_gmaps_search_jobs_tenant ON gmaps_search_jobs (tenant_id, started_at DESC);
