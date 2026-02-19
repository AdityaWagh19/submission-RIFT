"""
Contract management endpoints — info, deploy, fund.
"""
import logging

from fastapi import APIRouter, HTTPException

from models import DeployContractRequest, FundContractRequest
from services import contract_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contract", tags=["contract"])


@router.get("/info")
async def get_contract_info(name: str = "tip_proxy"):
    """Get contract compilation status and metadata."""
    try:
        return contract_service.get_contract_info(name)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve contract info. Check server logs.")


@router.get("/list")
async def list_contracts():
    """List all available contracts."""
    try:
        return {"contracts": contract_service.list_contracts()}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list contracts. Check server logs.")


@router.post("/deploy")
async def deploy_contract(request: DeployContractRequest):
    """
    Create an unsigned ApplicationCreateTxn.
    Frontend signs with Pera Wallet and submits via /submit.
    """
    try:
        contract_name = request.contract_name or "tip_proxy"
        return contract_service.create_deploy_txn(request.sender, contract_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Contract files not found. Check server logs.")
    except Exception as e:
        logger.error(f"Deploy failed: {e}")
        raise HTTPException(status_code=500, detail="Contract deployment failed. Check server logs.")


@router.post("/fund")
async def fund_contract(request: FundContractRequest):
    """
    Create an unsigned PaymentTxn to fund the contract.
    Contract needs ALGO for minimum balance and inner transaction fees.
    """
    try:
        return contract_service.create_fund_txn(
            sender=request.sender,
            app_id=request.app_id,
            amount=request.amount,
        )
    except Exception as e:
        logger.error(f"Fund failed: {e}")
        raise HTTPException(status_code=500, detail="Contract funding failed. Check server logs.")
