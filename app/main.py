# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os
from app.ml_guard import DISABLE_ML

from app.routers.core import router as core_router
from app.auth.google import router as google_router
from app import database

DISABLE_ML = os.getenv("DISABLE_ML", "false").lower() == "true"

# Import ML modules ONLY if enabled


app = FastAPI(title="AI Meeting Notes")

# ---------------------------
# Routers
# ---------------------------
app.include_router(core_router, prefix="/api")
app.include_router(google_router, prefix="/api/auth", tags=["auth"])

# ---------------------------
# Middleware
# ---------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "dev-secret-change-this"),
    same_site="lax",
    https_only=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Startup
# ---------------------------
@app.on_event("startup")
def startup():
    # DB
    database.Base.metadata.create_all(bind=database.engine)
    print("[startup] database tables ensured")

    if DISABLE_ML:
        print("[startup] ML DISABLED — backend running in API-only mode")
        return

    # 🔥 IMPORT ML ONLY HERE
    from app import asr, summarizer, actions
    from app.nlp import tasks as tasks_module

    asr.init_model()
    summarizer.get_summarizer()
    tasks_module.init_spacy()
    actions.get_ner_pipeline()

# ---------------------------
# Root
# ---------------------------
@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "API running",
        "ml_enabled": not DISABLE_ML
    }
