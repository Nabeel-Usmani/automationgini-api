-- Credits system: pay-as-you-go on top of each plan's existing monthly
-- quota (billing.py PLAN_DEFINITIONS). New tenants get 200 credits
-- automatically (trigger below); each demo (website/app/CRM/voice) costs
-- 20 credits once a tenant's plan quota for that type is used up for the
-- current month.

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS credit_balance INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS credit_transactions (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  delta INTEGER NOT NULL, -- positive = grant/purchase, negative = spend
  reason TEXT NOT NULL, -- 'signup_bonus' | 'purchase' | 'demo_vapi_call' | 'demo_mockup' | 'demo_app_mockup' | 'demo_business_crm'
  reference_id INTEGER, -- purchases.id for 'purchase', null otherwise
  balance_after INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_tenant_id ON credit_transactions (tenant_id);

-- Only meaningful when purchases.product_type = 'credits' - how many
-- credits this purchase grants once paid. NULL for every other product_type.
ALTER TABLE purchases
  ADD COLUMN IF NOT EXISTS credit_amount INTEGER;

-- Every new tenant starts with 200 free credits (~10 demos), regardless of
-- which code path inserts the row - a DB trigger is the one place this is
-- guaranteed not to be missed by a future signup code path.
CREATE OR REPLACE FUNCTION grant_signup_credits() RETURNS TRIGGER AS $$
BEGIN
  UPDATE tenants SET credit_balance = 200 WHERE id = NEW.id;
  INSERT INTO credit_transactions (tenant_id, delta, reason, balance_after)
  VALUES (NEW.id, 200, 'signup_bonus', 200);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_grant_signup_credits ON tenants;
CREATE TRIGGER trg_grant_signup_credits
  AFTER INSERT ON tenants
  FOR EACH ROW EXECUTE FUNCTION grant_signup_credits();
