from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import auth

app = FastAPI(title="AutomationGini API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://automationgini-website.onrender.com",
        "http://localhost:5173",  # local frontend dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}
