# AutomationGini API

FastAPI backend for the React CRM frontend. Wraps the same business logic
already proven in the Streamlit CRM's `common.py`, exposed as real HTTP
endpoints instead of direct Python function calls.

## Local setup
```
pip install -r requirements.txt
export DATABASE_URL="<same value as your Streamlit CRM's DATABASE_URL>"
export JWT_SECRET="<a random secret, see below>"
uvicorn main:app --reload
```

## Environment variables needed on Render
- `DATABASE_URL` — copy this exact value from your existing CRM's Render
  environment variables (Render dashboard → CRM service → Environment tab)
- `JWT_SECRET` — a random secret used to sign login sessions. Do not reuse
  any other secret. Generate one with:
  `python3 -c "import secrets; print(secrets.token_hex(32))"`
