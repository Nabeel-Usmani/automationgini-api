ALTER TABLE gmaps_leads
  ADD COLUMN IF NOT EXISTS social_links TEXT,
  ADD COLUMN IF NOT EXISTS qualification_tier TEXT,
  ADD COLUMN IF NOT EXISTS qualification_notes TEXT,
  ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;
