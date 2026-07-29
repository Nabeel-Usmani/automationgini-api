-- Adds a free-text suggestions field to the user_surveys table created by
-- hand alongside gmaps_users.login_count. Apply by hand against DATABASE_URL
-- before deploying the code that uses it (survey.py).
--
-- Safe to re-run: guarded with IF NOT EXISTS.

ALTER TABLE user_surveys ADD COLUMN IF NOT EXISTS suggestions TEXT;
