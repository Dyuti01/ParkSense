"""
ParkSense AI — FastAPI Application Entry Point

AI-driven parking intelligence platform for Bangalore Traffic Police.
Detects illegal parking hotspots and quantifies their impact on traffic flow.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print(f"[START] Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"[ENV] Environment: {settings.APP_ENV}")
    await init_db()
    print("[OK] Database tables verified")
    yield
    # Shutdown
    print("[STOP] Shutting down ParkSense AI")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-driven parking intelligence platform for Bangalore Traffic Police. "
        "Detects illegal parking hotspots, quantifies congestion impact, "
        "and provides targeted enforcement recommendations."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from sqladmin import Admin
from app.database import async_engine
from app.admin import AdminAuth, UserAdmin, ViolationAdmin, HotspotAdmin, StationStatsAdmin, PipelineRunAdmin, HeatmapGridAdmin

authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
admin = Admin(app, async_engine, title="ParkSense AI Admin", authentication_backend=authentication_backend)
admin.add_view(UserAdmin)
admin.add_view(ViolationAdmin)
admin.add_view(HotspotAdmin)
admin.add_view(StationStatsAdmin)
admin.add_view(PipelineRunAdmin)
admin.add_view(HeatmapGridAdmin)


# ── Import and include routers ──────────────────────────────
from app.routers import overview, violations, hotspots, temporal, stations, enforcement, ingestion, export, auth

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(overview.router, prefix="/api/overview", tags=["Overview"])
app.include_router(violations.router, prefix="/api/violations", tags=["Violations"])
app.include_router(hotspots.router, prefix="/api/hotspots", tags=["Hotspots"])
app.include_router(temporal.router, prefix="/api/temporal", tags=["Temporal Analysis"])
app.include_router(stations.router, prefix="/api/stations", tags=["Police Stations"])
app.include_router(enforcement.router, prefix="/api/enforcement", tags=["Enforcement"])
app.include_router(ingestion.router, prefix="/api/ingest", tags=["Data Ingestion"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }
