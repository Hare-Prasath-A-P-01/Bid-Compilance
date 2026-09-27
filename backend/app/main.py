import logging
import time
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings, cors_origins
from app.database import Base, engine, ensure_schema
from app.routers import auth, tenders, bids, documents, compliance, dashboard, reviews, notifications, ai

Base.metadata.create_all(bind=engine)
ensure_schema()

app = FastAPI(
    title="AI Bid Compliance Checker",
    description="Byte Busters — SIH 2026 (PS ID: SIH26100) — AI-powered bid document compliance verification",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("bid_compliance.api")


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error", extra={"request_id": request_id, "path": request.url.path})
        response = JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    if settings.APP_ENV.lower() == "production":
        response.headers["Strict-Transport-Security"] = f"max-age={settings.HSTS_SECONDS}; includeSubDomains; preload"
    logger.info("%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, duration_ms, extra={"request_id": request_id})
    return response


app.include_router(auth.router)
app.include_router(tenders.router)
app.include_router(bids.router)
app.include_router(documents.router)
app.include_router(compliance.router)
app.include_router(dashboard.router)
app.include_router(reviews.router)
app.include_router(notifications.router)
app.include_router(ai.router)


@app.get("/api/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed")
        return JSONResponse(status_code=503, content={"status": "degraded", "service": "AI Bid Compliance Checker"})
    return {"status": "ok", "service": "AI Bid Compliance Checker", "database": "ok"}


@app.get("/api/ready")
def ready():
    return health()
