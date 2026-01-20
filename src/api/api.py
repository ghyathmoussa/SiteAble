"""SiteAble API Server.

FastAPI application for accessibility scanning service.
"""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import OptionalAuth, is_auth_enabled
from api.routes.dashboard import router as dashboard_router
from api.routes.scan import router as scan_router

# Try to import version
try:
    from ai.accessibility.__version__ import __version__
except ImportError:
    __version__ = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"🚀 SiteAble API v{__version__} starting...")
    if is_auth_enabled():
        print("🔐 API authentication is enabled")
    else:
        print("⚠️  API authentication is disabled (no SITEABLE_API_KEYS set)")
    yield
    # Shutdown
    print("👋 SiteAble API shutting down...")


app = FastAPI(
    title="SiteAble API",
    description="""
## SiteAble - Accessibility Scanner API

Scan websites for accessibility issues using WCAG guidelines.

### Features
- Single page and site-wide scanning
- 12 built-in accessibility analyzers
- Severity scoring (Critical, Major, Minor)
- WCAG criterion references
- AI-powered fix suggestions (optional)

### Authentication
If `SITEABLE_API_KEYS` environment variable is set, API key authentication is required.
Pass your API key in the `X-API-Key` header.
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(scan_router, prefix="/api", tags=["Scanning"])


@app.get("/", tags=["Health"])
def read_root():
    """Health check and API info."""
    return {
        "message": "Welcome to the SiteAble API",
        "version": __version__,
        "docs": "/docs",
        "auth_enabled": is_auth_enabled(),
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": __version__}


@app.get("/api/analyzers", tags=["Info"])
def list_analyzers():
    """List available accessibility analyzers."""
    from ai.accessibility.analyzer_plugin import list_analyzers as get_analyzers

    analyzers = get_analyzers()
    return {
        "count": len(analyzers),
        "analyzers": [
            {"name": name, "description": desc}
            for name, desc in analyzers.items()
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
    )