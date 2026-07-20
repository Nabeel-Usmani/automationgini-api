from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import auth
import dashboard
import leads
import demo
import build
import search
import billing
import preview
import templates_routes
import admin
import audit
import app_mockup_demo

ALLOWED_ORIGINS = [
    "https://automationgini-website.onrender.com",
    "https://automationgini-crmv2.onrender.com",
    "http://localhost:5173",
    "http://localhost:5174",
]

app = FastAPI(title="AutomationGini API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Explicit fallback for CORS preflight requests. CORSMiddleware normally
# handles this automatically, but Render's reverse proxy layer has been
# observed interfering with that automatic handling - this guarantees the
# right headers regardless.
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str = ""):
    origin = request.headers.get("origin", "")
    response = Response(status_code=200)
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,PATCH,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = request.headers.get(
            "access-control-request-headers", "*"
        )
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(leads.router)
app.include_router(demo.router)
app.include_router(build.router)
app.include_router(search.router)
app.include_router(billing.router)
app.include_router(preview.router)
app.include_router(templates_routes.router)
app.include_router(admin.router)
app.include_router(audit.router)
app.include_router(app_mockup_demo.router)


@app.get("/health")
def health():
    return {"status": "ok"}
