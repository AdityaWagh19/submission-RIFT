"""
Creator Sticker Platform — FastAPI Application (V4)

Per-creator TipProxy smart contracts, atomic group transactions,
NFT minting pipeline, and on-chain tip validation.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from routes import health, params, transactions, contracts

# ── Logging ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables, start listener. Shutdown: stop listener."""
    # Ensure data/ directory exists for SQLite
    os.makedirs("data", exist_ok=True)

    # Security fix M2/H3/M5: Validate settings before starting
    settings.validate_production_settings()

    from database import init_db
    await init_db()
    logger.info("Database initialized")

    # Start the transaction listener (Phase 4)
    try:
        from services import listener_service
        await listener_service.start()
        logger.info("Transaction listener started")
    except Exception as e:
        logger.warning(f"Listener failed to start (non-fatal): {e}")

    yield  # app runs here

    # Stop listener on shutdown
    try:
        from services import listener_service
        await listener_service.stop()
    except Exception:
        pass

    # Phase 7: Shutdown thread pool executor for blocking Algorand calls
    try:
        from services.async_executor import shutdown_executor
        shutdown_executor()
    except Exception:
        pass

    logger.info("Shutting down")


# ── App Factory ─────────────────────────────────────────────────────

app = FastAPI(
    title="Creator Sticker Platform API",
    description="Per-creator TipProxy smart contracts with NFT sticker rewards on Algorand",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────────────

# Existing boilerplate routes
app.include_router(health.router)
app.include_router(params.router)
app.include_router(transactions.router)
app.include_router(contracts.router)

# V4 routes — registered individually so partial availability works
_v4_routes = []

try:
    from routes import auth
    app.include_router(auth.router)
    _v4_routes.append("auth")
except ImportError as e:
    logger.debug(f"Auth routes not available: {e}")

try:
    from routes import creator
    app.include_router(creator.router)
    _v4_routes.append("creator")
except ImportError as e:
    logger.warning(f"Creator routes not available: {e}")

try:
    from routes import nft
    app.include_router(nft.router)
    _v4_routes.append("nft")
except ImportError as e:
    logger.debug(f"NFT routes not yet available (Phase 3): {e}")

try:
    from routes import fan
    app.include_router(fan.router)
    app.include_router(fan.leaderboard_router)
    _v4_routes.append("fan")
    _v4_routes.append("leaderboard")
except ImportError as e:
    logger.debug(f"Fan routes not yet available (Phase 5): {e}")

try:
    from routes import onramp
    app.include_router(onramp.router)
    app.include_router(onramp.sim_router)  # /simulate/fund-wallet
    _v4_routes.append("onramp")
    if settings.simulation_mode:
        _v4_routes.append("simulate")
except ImportError as e:
    logger.debug(f"On-ramp routes not available: {e}")

# V5 NFT Utility routes — Butki, Bauni, Shawty
try:
    from routes import butki
    app.include_router(butki.router)
    _v4_routes.append("butki")
except ImportError as e:
    logger.debug(f"Butki routes not available: {e}")

try:
    from routes import bauni
    app.include_router(bauni.router)
    _v4_routes.append("bauni")
except ImportError as e:
    logger.debug(f"Bauni routes not available: {e}")

try:
    from routes import shawty
    app.include_router(shawty.router)
    _v4_routes.append("shawty")
except ImportError as e:
    logger.debug(f"Shawty routes not available: {e}")

try:
    from routes import merch
    app.include_router(merch.router)
    _v4_routes.append("merch")
except ImportError as e:
    logger.debug(f"Merch routes not available: {e}")

if _v4_routes:
    logger.info(f"V4 routes registered: {', '.join(_v4_routes)}")


# ── Listener Status Endpoint ───────────────────────────────────────

@app.get("/listener/status", tags=["listener"])
async def get_listener_status():
    """Get the current status of the transaction listener."""
    try:
        from services import listener_service
        return listener_service.get_status()
    except ImportError:
        return {"running": False, "error": "Listener service not available"}

# ── Static Files (frontend) ────────────────────────────────────────

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# ── Exception Handler ───────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Catch-all for unhandled exceptions.

    Security fix H5: Never return raw exception details to clients.
    The full traceback is logged server-side for debugging.
    """
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "internal_server_error",
                "message": "Internal server error",
            },
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """
    Standardize HTTPException responses for frontend consumers.

    Keeps the original HTTP status code, but wraps the payload.
    """
    # Check if this is a DomainError (which is a subclass of HTTPException)
    if hasattr(exc, "message") and hasattr(exc, "details"):
        # DomainError with structured error info
        error_code = exc.__class__.__name__.replace("Error", "").lower()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    # Regular HTTPException
    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "http_error",
                "message": message,
                "details": detail if not isinstance(detail, str) else None,
            },
        },
    )


# ── Entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
