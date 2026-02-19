"""
Transaction submission endpoints — single and atomic group.
"""
import logging

from fastapi import APIRouter, HTTPException, Header, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import (
    SubmitTransactionRequest,
    SubmitTransactionResponse,
    SubmitMultiTxnRequest,
)
from services import transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["transactions"])


@router.post("/submit", response_model=SubmitTransactionResponse)
async def submit_transaction(
    request: SubmitTransactionRequest,
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Submit a single signed transaction to Algorand TestNet."""
    try:
        logger.info(f"Received single txn submission ({len(request.signed_txn)} chars)")
        tx_id = await transaction_service.submit_single(db, request.signed_txn, idempotency_key=x_idempotency_key)
        await db.commit()
        return SubmitTransactionResponse(txId=tx_id)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid transaction format")
    except Exception as e:
        code, detail = transaction_service.classify_error(str(e))
        raise HTTPException(status_code=code, detail="Transaction submission failed. Check server logs.")


@router.post("/submit-group", response_model=SubmitTransactionResponse)
async def submit_group(
    request: SubmitMultiTxnRequest,
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Submit an atomic group of signed transactions."""
    try:
        logger.info(f"Received group submission ({len(request.signed_txns)} txns)")
        tx_id = await transaction_service.submit_group(db, request.signed_txns, idempotency_key=x_idempotency_key)
        await db.commit()
        return SubmitTransactionResponse(txId=tx_id)

    except ValueError as e:
        logger.error(f"submit_group ValueError: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid group transaction format: {e}")
    except Exception as e:
        logger.error(f"submit_group failed: {type(e).__name__}: {e}", exc_info=True)
        code, detail = transaction_service.classify_error(str(e))
        raise HTTPException(status_code=code, detail=f"Group submission failed: {e}")
