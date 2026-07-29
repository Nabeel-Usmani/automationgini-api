-- Real (non-demo) client Calendly integration: each deployed chatbot
-- (chatbot_configs row) can connect its own business's Calendly account,
-- distinct from the hardcoded personal-token demo tool-use in the
-- "Chatbot Send Message" n8n workflow. Apply by hand against DATABASE_URL
-- before deploying the code that uses it (calendly.py).
--
-- Safe to re-run: guarded with IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS chatbot_calendly_connections (
  id SERIAL PRIMARY KEY,
  chatbot_config_id INTEGER NOT NULL UNIQUE REFERENCES chatbot_configs(id) ON DELETE CASCADE,
  access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  token_expires_at TIMESTAMPTZ NOT NULL,
  calendly_user_uri TEXT NOT NULL,
  scheduling_url TEXT NOT NULL,
  connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
