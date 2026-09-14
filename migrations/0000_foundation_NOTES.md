Notes on migrations/0000_foundation.sql (reconstructed schema)

Tables created (14): tenants, gmaps_users, user_surveys, gmaps_leads,
purchases, chatbot_configs, usage_log, lead_audits, website_revisions,
city_coordinates, template_previews, lead_email_replies, agent_runs,
agent_backlog.

Validated: ran all 13 files (0000-0012) against a fresh local Postgres 16
database - every statement succeeded with no errors, and a smoke-tested
tenant signup (INSERT INTO tenants -> grant_signup_credits trigger -> 200
credit balance -> auth.py's exact get_current_user join query) worked
end-to-end. All 27 tables referenced anywhere in migrations/*.sql or the 20
audited Python route files now have exactly one CREATE TABLE.

HIGH CONFIDENCE (column list/types read directly off Python SQL strings or
migration ALTER statements): tenants, gmaps_users, user_surveys,
gmaps_leads (call_status CHECK matches leads.py STATUS_OPTIONS exactly),
purchases, chatbot_configs, lead_audits and website_revisions (both match
audit.py/build.py SELECTs column-for-column), city_coordinates, agent_runs,
agent_backlog (match agent_ops.py exactly).

BEST-EFFORT / GUESSED (flagged inline in the SQL):
- gmaps_leads.agent_id (NOT NULL) and total_score (NUMERIC): inferred from
  usage, not proven by any CREATE/ALTER.
- purchases.agent_id: sent on every checkout payload but never read back by
  SQL in this repo - included for consistency, existence is a guess.
- chatbot_configs.chatbot_token: inferred UNIQUE/TEXT by analogy with
  crm_staff.invite_token; presumably read by a public widget endpoint
  outside this repo.
- template_previews: only one query exists anywhere, so its exact shape is
  a best guess.
- CHECK constraints were deliberately omitted on columns written by
  external systems not visible in this repo (n8n/Stripe): plan_name,
  subscription_status, product_type, payment_status, fulfillment_status,
  event_type, source, website_status - constraining these risks breaking a
  working integration this reconstruction can't see.

UNRESOLVED - NEEDS HUMAN REVIEW:
- lead_email_replies (used by email_automation.py /replies) is not a
  CREATE/ALTER target of any of the 12 existing migrations, and logically
  depends on lead_email_sequences, which migration 0008 creates - i.e.
  AFTER this file runs. Its FK to lead_email_sequences(id) was left off on
  purpose (sequence_id is a bare INTEGER) so 0000 doesn't fail. Add that FK
  by hand once 0008 has run, and double check this table's real columns -
  it's reconstructed only from inbound_reply.py + one query in
  email_automation.py.
- No Python file here ever inserts gmaps_users with role='agent' (only
  'admin'). The CHECK still allows it since other files branch on it, but
  the code that creates an agent account (n8n? a missing endpoint?) was not
  found in this repo.
