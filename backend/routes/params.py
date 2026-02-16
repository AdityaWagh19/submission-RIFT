"""
Transaction parameters endpoint.
"""
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, HTTPException, status

from algorand_client import algorand_client
from models import TransactionParamsResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["params"])

# Simple cache for transaction parameters (60-second TTL)
_cache = {"data": None, "timestamp": None}
_CACHE_TTL_SECONDS = 60


@router.get("/params", response_model=TransactionParamsResponse)
async def get_transaction_params():
    """
    Fetch suggested transaction parameters from Algorand TestNet.
    Results are cached for 60 seconds.
    """
    try:
        now = datetime.now(timezone.utc)
        if (
            _cache["data"] is not None
            and _cache["timestamp"] is not None
            and (now - _cache["timestamp"]).total_seconds() < _CACHE_TTL_SECONDS
        ):
            logger.info("Returning cached transaction parameters")
            return _cache["data"]

        logger.info("Fetching transaction parameters from Algorand TestNet")
        params = algorand_client.get_suggested_params()

        response_data = TransactionParamsResponse(
            fee=params.fee,
            firstValidRound=params.first,
            lastValidRound=params.last,
            genesisId=params.gen,
            genesisHash=params.gh,
        )

        _cache["data"] = response_data
        _cache["timestamp"] = now

        return response_data

    except Exception as e:
        logger.error(f"Error fetching transaction parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch transaction parameters: {str(e)}",
        )
