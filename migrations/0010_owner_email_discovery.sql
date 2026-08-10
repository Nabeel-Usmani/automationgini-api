CREATE TABLE IF NOT EXISTS lead_owner_emails (
  id SERIAL PRIMARY KEY,
  lead_id INTEGER NOT NULL REFERENCES gmaps_leads(id) ON DELETE CASCADE,
  owner_name TEXT,
  domain TEXT NOT NULL,
  guessed_email TEXT NOT NULL,
  pattern_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unverified', -- 'unverified' | 'sent' | 'confirmed' | 'bounced'
  confidence NUMERIC,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (lead_id)
);

CREATE TABLE IF NOT EXISTS email_pattern_stats (
  id SERIAL PRIMARY KEY,
  domain TEXT NOT NULL DEFAULT '', -- '' = global default prior, not tied to any one domain (kept non-null so the UNIQUE constraint below actually dedupes it - Postgres treats NULL as distinct from NULL)
  pattern_type TEXT NOT NULL,
  confirmed_count INTEGER NOT NULL DEFAULT 0,
  bounced_count INTEGER NOT NULL DEFAULT 0,
  UNIQUE (domain, pattern_type)
);

CREATE INDEX IF NOT EXISTS idx_lead_owner_emails_status ON lead_owner_emails (status);
CREATE INDEX IF NOT EXISTS idx_email_pattern_stats_domain ON email_pattern_stats (domain);

-- Seed global default priors (industry-typical pattern frequency, not domain-specific data).
-- These are starting weights only; confirmed/bounced counts from real sends will overtake them per-domain over time.
INSERT INTO email_pattern_stats (domain, pattern_type, confirmed_count, bounced_count) VALUES
  ('', 'first.last', 35, 0),
  ('', 'flast', 20, 0),
  ('', 'first', 15, 0),
  ('', 'firstlast', 10, 0),
  ('', 'first_last', 6, 0),
  ('', 'f.last', 6, 0),
  ('', 'lastfirst', 4, 0),
  ('', 'last.first', 4, 0)
ON CONFLICT (domain, pattern_type) DO NOTHING;
