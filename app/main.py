# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os

from app.routers.core import router as core_router
from app.auth.google import router as google_router
from app import database
from app import asr, summarizer, actions
from app.nlp import tasks as tasks_module

app = FastAPI(title="AI Meeting Notes")

# ---------------------------
# Routers (REGISTER ONCE)
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
# Startup (SINGLE SOURCE)
# ---------------------------
@app.on_event("startup")
def startup():
    # DB
    database.Base.metadata.create_all(bind=database.engine)
    print("[startup] database tables ensured")

    # ASR
    try:
        asr.init_model()
        print("[startup] ASR initialized")
    except Exception as e:
        print("[startup] ASR init failed:", e)

    # Summarizer
    try:
        summarizer.get_summarizer()
        print("[startup] summarizer initialized")
    except Exception as e:
        print("[startup] summarizer init failed:", e)

    # NLP Tasks
    try:
        tasks_module.init_spacy()
        print("[startup] spaCy task extractor initialized")
    except Exception as e:
        print("[startup] spaCy init failed:", e)

    # NER
    try:
        actions.get_ner_pipeline()
        print("[startup] NER pipeline initialized")
    except Exception as e:
        print("[startup] NER init failed:", e)

# ---------------------------
# Root
# ---------------------------
@app.get("/", include_in_schema=False)
def root():
    return {"message": "API running. Visit /docs"}
