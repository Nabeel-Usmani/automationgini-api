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

| File | Webhook path | Purpose |
|---|---|---|
| `business-crm-demo.json` | `POST /webhook/business-crm-demo` | Provisions a free demo Business CRM workspace (staff portal + booking page) for a lead. Called by `POST /demo/business-crm` in this repo. |
| `checkout-router.json` | `POST /webhook/checkout` | Shared checkout endpoint for all Build products (`CHECKOUT_WEBHOOK_URL`). Routes by `product_type`. Only `business_crm` is implemented so far (real workspace + owner invite link); `voice_agent` and `website_*` return 501 until Vapi.ai / Anthropic credentials are set up in n8n. See the file's `notes` field for what's still missing (e.g. the `services` list from `build_config` isn't inserted yet). |
