"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


# ── Transaction Models ──────────────────────────────────────────────

class SubmitTransactionRequest(BaseModel):
    """Request model for single transaction submission."""
    signed_txn: str = Field(
        ...,
        description="Base64-encoded signed transaction",
        min_length=1,
    )


class SubmitMultiTxnRequest(BaseModel):
    """Request model for submitting an atomic group of signed transactions."""
    signed_txns: List[str] = Field(
        ...,
        description="List of base64-encoded signed transactions",
        min_length=1,
    )


class SubmitTransactionResponse(BaseModel):
    """Response model for transaction submission."""
    tx_id: str = Field(
        ...,
        alias="txId",
        description="Transaction ID returned by Algorand network",
    )


class TransactionParamsResponse(BaseModel):
    """Response model for suggested transaction parameters."""
    fee: int = Field(..., description="Minimum transaction fee in microAlgos")
    first_valid_round: int = Field(..., alias="firstValidRound")
    last_valid_round: int = Field(..., alias="lastValidRound")
    genesis_id: str = Field(..., alias="genesisId")
    genesis_hash: str = Field(..., alias="genesisHash")


# ── Contract Models ─────────────────────────────────────────────────

class DeployContractRequest(BaseModel):
    """Request model for contract deployment."""
    sender: str = Field(..., description="Deployer wallet address")
    contract_name: Optional[str] = Field(
        default="payment_proxy",
        alias="contractName",
        description="Contract to deploy (folder name under contracts/)",
    )


class FundContractRequest(BaseModel):
    """Request model for funding a deployed contract."""
    sender: str = Field(..., description="Funder wallet address")
    app_id: int = Field(..., alias="appId", description="Deployed application ID")
    amount: int = Field(
        default=200_000,
        description="Amount to fund in microAlgos (default: 0.2 ALGO)",
    )


# ── Error Models ────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    detail: str = Field(default="", description="Detailed error information")
