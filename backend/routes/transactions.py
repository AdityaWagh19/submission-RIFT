"""
Transaction submission endpoints — single and atomic group.
"""
import logging

from fastapi import APIRouter, HTTPException, status

from models import (
    SubmitTransactionRequest,
    SubmitTransactionResponse,
    SubmitMultiTxnRequest,
)
from services import transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["transactions"])


@router.post("/submit", response_model=SubmitTransactionResponse)
async def submit_transaction(request: SubmitTransactionRequest):
    """Submit a single signed transaction to Algorand TestNet."""
    try:
        logger.info(f"Received single txn submission ({len(request.signed_txn)} chars)")
        tx_id = transaction_service.submit_single(request.signed_txn)
        return SubmitTransactionResponse(txId=tx_id)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid transaction format")
    except Exception as e:
        code, detail = transaction_service.classify_error(str(e))
        raise HTTPException(status_code=code, detail="Transaction submission failed. Check server logs.")


@router.post("/submit-group", response_model=SubmitTransactionResponse)
async def submit_group(request: SubmitMultiTxnRequest):
    """Submit an atomic group of signed transactions."""
    try:
        logger.info(f"Received group submission ({len(request.signed_txns)} txns)")
        tx_id = transaction_service.submit_group(request.signed_txns)
        return SubmitTransactionResponse(txId=tx_id)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid group transaction format")
    except Exception as e:
        code, detail = transaction_service.classify_error(str(e))
        raise HTTPException(status_code=code, detail="Group transaction submission failed. Check server logs.")
