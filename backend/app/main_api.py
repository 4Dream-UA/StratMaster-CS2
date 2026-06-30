from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.routers import users, strategies, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="StratMaster CS2 API",
    version="0.1.0",
    description="Backend API for StratMaster CS2 Telegram Mini App",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS — allow Telegram WebApp origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(strategies.router, prefix="/api", tags=["strategies"])
app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])


@app.get("/healthcheck", tags=["system"])
async def healthcheck():
    return {"status": "ok", "service": "StratMaster CS2 API"}