# n8n Workflows

This folder is the source-of-truth backup for AutomationGini's n8n workflows.
n8n's community edition has no built-in git sync, and the last set of
workflows was lost entirely when the old hosting was suspended - so every
workflow built going forward gets exported here right after it's built.

## Storage convention

One file per workflow: `<kebab-case-name>.json`, containing the raw exported
`nodes`/`connections`/`settings` plus an `n8nWorkflowId` field recording the
live workflow's ID on the current n8n instance (`https://app.automationgini.com`)
so it can be cross-referenced or re-imported.

Credentials are never stored here (n8n doesn't export secret values) - each
file references credentials by name only (e.g. `"AutomationGini Postgres"`),
which must be recreated in n8n's UI if the instance is ever rebuilt from
scratch.

## Re-importing after a rebuild

1. In n8n: Workflows -> Import from File -> pick the JSON file.
2. Recreate any named credentials the workflow references (see each file's
   `credentials` blocks) and re-link them on the imported nodes.
3. Publish the workflow.

## Workflows

| File | Trigger | Purpose |
|---|---|---|
| `business-crm-demo.json` | `POST /webhook/business-crm-demo` | Provisions a free demo Business CRM workspace (staff portal + booking page) for a lead. Called by `POST /demo/business-crm` in this repo. |
| `checkout-router.json` | `POST /webhook/checkout` | Shared checkout endpoint for all Build products (`CHECKOUT_WEBHOOK_URL`). Routes by `product_type`. `business_crm` (real workspace + owner invite link) and `voice_agent` (real Vapi Assistant + phone number on the client's own BYOK account) are implemented and free for now - no Stripe wired up yet, by design. `website_*` still returns 501 until Anthropic has billing configured. See the file's `notes` field for details. |
| `voice-demo.json` | `POST /webhook/voice-demo` | Places a bilingual AI voice-agent demo call via Vapi and logs it to `usage_log`. Called by `POST /demo/voice`. Fully wired with real Vapi assistant/phone number IDs and tested end-to-end (routing + DB logic); the live call itself hasn't been test-fired since the user opted to verify via a real lead in the CRM instead. |
| `email-automation-send-engine.json` | Schedule (hourly) | Sends the next due email (initial, or a 24h follow-up up to 4 times) for every `active` row in `lead_email_sequences`, via Brevo. Logs each send to `lead_email_sends` and advances `step`/`status`, auto-completing after follow-up 4. **Built and DB-verified but NOT YET PUBLISHED** - needs a Brevo credential (`sendInBlueApi`, named `Brevo`) created in n8n and attached to the `Send Outreach Email` node first. See the file's `notes` field for the full status and scope. |

## Free-for-now products (no Stripe yet)

`business_crm` ($199 in the CRM UI) and `voice_agent` ($50) both currently
provision immediately for free - Checkout Router never talks to Stripe. The
CRM's own Build pages (`BusinessCrm.jsx`, `VoiceAgent.jsx` in
automationgini-crmv2) were updated to match: they show the created
result/invite link/phone number inline instead of expecting a `checkout_url`
redirect, since the API's checkout endpoints only return `checkout_url` once
Stripe is actually wired up. When Stripe is added, `Checkout Router` should
create a real Checkout Session and return `checkout_url` for these two
product types too, and actual provisioning should move to a Stripe webhook
receiver workflow that runs after payment confirms.

## Email Automation - what's built vs. what's missing

`email-automation-send-engine.json` handles sending only: it assumes a lead
is already enrolled (a row exists in `lead_email_sequences` with
`step = 0`, `status = 'active'`) and takes it from there. It does **not**
decide which leads get enrolled or generate the website mockup / chatbot demo
a sequence links to - that "auto-enrollment" piece needs the same Anthropic
billing fix as the blocked Website Preview / Chatbot Demo workflows, since a
real demo has to exist before a lead can be meaningfully enrolled. Until
that's built, sequences need to be inserted into `lead_email_sequences` some
other way for the Send Engine to have anything to process.

Inbound reply capture (flipping a sequence to `status = 'replied'` so
follow-ups stop) is already fully implemented server-side via
`POST /webhooks/inbound-reply` in this repo - no n8n component was needed
for that piece.
