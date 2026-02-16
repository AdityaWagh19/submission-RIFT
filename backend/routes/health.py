"""
Health check endpoint.
"""
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from algorand_client import algorand_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check — verifies Algorand node connectivity."""
    try:
        status_info = algorand_client.client.status()
        return {
            "status": "healthy",
            "algorand_connected": True,
            "last_round": status_info.get("last-round"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "algorand_connected": False,
                "error": str(e),
            },
        )
