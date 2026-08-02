ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS email_automation_enabled BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS lead_email_sequences (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL,
  agent_id INTEGER,
  lead_id INTEGER NOT NULL REFERENCES gmaps_leads(id) ON DELETE CASCADE,
  sequence_type TEXT NOT NULL,           -- 'website_demo' | 'chatbot_demo'
  demo_url TEXT,
  screenshot_url TEXT,
  step INTEGER NOT NULL DEFAULT 0,       -- 0 = enrolled, 1 = initial sent, 2-5 = follow-ups 1-4 sent
  status TEXT NOT NULL DEFAULT 'active', -- 'active' | 'replied' | 'completed_no_reply' | 'failed'
  last_sent_at TIMESTAMPTZ,
  replied_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (lead_id)
);

CREATE TABLE IF NOT EXISTS lead_email_sends (
  id SERIAL PRIMARY KEY,
  sequence_id INTEGER NOT NULL REFERENCES lead_email_sequences(id) ON DELETE CASCADE,
  step INTEGER NOT NULL,
  email_type TEXT NOT NULL,              -- 'initial' | 'followup_1' | 'followup_2' | 'followup_3' | 'followup_4'
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  message_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_lead_email_sequences_tenant ON lead_email_sequences (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_lead_email_sequences_followup_due ON lead_email_sequences (status, last_sent_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_lead_email_sends_sequence ON lead_email_sends (sequence_id);
