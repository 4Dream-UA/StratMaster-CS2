from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import UPLOAD_DIR, settings
from backend.app.api.routers import users, strategies, webhooks, referral, promo, admin, subscription, wallet, payments, favorites, uploads, boards


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

# CORS — only the deployed Mini App origin (+ localhost while developing).
# Wildcard "*" is intentionally not used: it's invalid alongside
# allow_credentials=True per the CORS spec, and browsers reject it anyway.
allowed_origins = [origin for origin in [settings.webapp_url] if origin]
if settings.debug:
    allowed_origins += [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(strategies.router, prefix="/api", tags=["strategies"])
app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])
app.include_router(referral.router, prefix="/api", tags=["referral"])
app.include_router(promo.router, prefix="/api", tags=["promo"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(subscription.router, prefix="/api", tags=["subscription"])
app.include_router(wallet.router, prefix="/api", tags=["wallet"])
app.include_router(payments.router, prefix="/api", tags=["payments"])
app.include_router(favorites.router, prefix="/api", tags=["favorites"])
app.include_router(uploads.router, prefix="/api", tags=["uploads"])
app.include_router(boards.router, prefix="/api", tags=["boards"])

# Serves admin-uploaded images back out at the URL the upload endpoint returns.
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/healthcheck", tags=["system"])
async def healthcheck():
    return {"status": "ok", "service": "StratMaster CS2 API"}