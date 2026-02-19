"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime


class V4Base(BaseModel):
    """Shared base for V4 models — allows construction by Python name or alias."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)



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
        default="tip_proxy",
        alias="contractName",
        description="Contract to deploy (folder name under contracts/)",
    )


class FundContractRequest(BaseModel):
    """Request model for funding a deployed contract."""
    sender: str = Field(..., description="Funder wallet address")
    app_id: int = Field(..., alias="appId", description="Deployed application ID")
    amount: int = Field(
        default=100_000,
        description="Amount to fund in microAlgos (default: 0.1 ALGO)",
    )


# ── V4 Creator Models ──────────────────────────────────────────────

class CreatorRegisterRequest(V4Base):
    """Register a new creator — deploys a TipProxy contract."""
    wallet_address: str = Field(
        ...,
        alias="walletAddress",
        description="Creator's Algorand wallet address",
    )
    username: Optional[str] = Field(
        default=None,
        description="Display name for the creator",
    )
    min_tip_algo: float = Field(
        default=1.0,
        alias="minTipAlgo",
        ge=0.1,
        le=1000.0,
        description="Minimum tip amount in ALGO for this creator's contract (0.1 - 1000)",
    )


class CreatorRegisterResponse(V4Base):
    """Response after successful creator registration."""
    wallet_address: str = Field(..., alias="walletAddress")
    username: Optional[str] = None
    app_id: int = Field(..., alias="appId")
    app_address: str = Field(..., alias="appAddress")
    version: int = 1
    min_tip_algo: float = Field(..., alias="minTipAlgo")
    tx_id: str = Field(..., alias="txId")
    message: str = "Creator registered and TipProxy deployed"


class ContractInfoResponse(V4Base):
    """Active contract details for a creator."""
    creator_wallet: str = Field(..., alias="creatorWallet")
    app_id: int = Field(..., alias="appId")
    app_address: str = Field(..., alias="appAddress")
    version: int
    active: bool = True
    deployed_at: Optional[str] = Field(None, alias="deployedAt")


class ContractStatsResponse(V4Base):
    """On-chain TipProxy global state."""
    app_id: int = Field(..., alias="appId")
    total_tips: int = Field(..., alias="totalTips")
    total_amount_algo: float = Field(..., alias="totalAmountAlgo")
    min_tip_algo: float = Field(..., alias="minTipAlgo")
    paused: bool
    contract_version: int = Field(..., alias="contractVersion")


class UpgradeContractResponse(V4Base):
    """Response after upgrading a creator's TipProxy."""
    old_app_id: int = Field(..., alias="oldAppId")
    new_app_id: int = Field(..., alias="newAppId")
    new_app_address: str = Field(..., alias="newAppAddress")
    new_version: int = Field(..., alias="newVersion")
    message: str


class PauseContractRequest(V4Base):
    """Request to pause/unpause a contract (signed by creator via Pera)."""
    wallet_address: str = Field(
        ...,
        alias="walletAddress",
        description="Creator wallet (must match contract's creator_address)",
    )


class CreatorDashboardResponse(V4Base):
    """Combined on-chain + off-chain analytics for a creator."""
    wallet_address: str = Field(..., alias="walletAddress")
    username: Optional[str] = None
    contract: Optional[ContractInfoResponse] = None
    stats: Optional[ContractStatsResponse] = None
    total_fans: int = Field(0, alias="totalFans")
    total_stickers_minted: int = Field(0, alias="totalStickersMinted")
    recent_transactions: list = Field(default_factory=list, alias="recentTransactions")


# ── V4 Sticker Template Models ─────────────────────────────────────

class StickerTemplateResponse(V4Base):
    """Response model for a sticker template."""
    id: int
    creator_wallet: str = Field(..., alias="creatorWallet")
    name: str
    ipfs_hash: Optional[str] = Field(None, alias="ipfsHash")
    image_url: Optional[str] = Field(None, alias="imageUrl")
    metadata_url: Optional[str] = Field(None, alias="metadataUrl")
    sticker_type: str = Field(..., alias="stickerType")
    category: str
    tip_threshold: float = Field(..., alias="tipThreshold")
    created_at: Optional[str] = Field(None, alias="createdAt")
    mint_count: int = Field(0, alias="mintCount")


class StickerTemplateListResponse(V4Base):
    """Response model for listing sticker templates."""
    creator_wallet: str = Field(..., alias="creatorWallet")
    templates: List[StickerTemplateResponse]
    total: int


# ── V4 NFT Models ──────────────────────────────────────────────────

class MintSoulboundRequest(V4Base):
    """Request to mint a soulbound sticker NFT."""
    template_id: int = Field(..., alias="templateId", description="Sticker template ID")
    fan_wallet: str = Field(..., alias="fanWallet", description="Recipient fan wallet")


class MintGoldenRequest(V4Base):
    """Request to mint a golden (tradable) sticker NFT."""
    template_id: int = Field(..., alias="templateId", description="Sticker template ID")
    fan_wallet: str = Field(..., alias="fanWallet", description="Recipient fan wallet")


class MintResponse(V4Base):
    """Response after minting an NFT."""
    asset_id: int = Field(..., alias="assetId")
    sticker_type: str = Field(..., alias="stickerType")
    name: str
    metadata_url: Optional[str] = Field(None, alias="metadataUrl")
    owner_wallet: str = Field(..., alias="ownerWallet")
    tx_id: Optional[str] = Field(None, alias="txId")
    message: str


class TransferNFTRequest(V4Base):
    """Request to transfer a golden NFT."""
    asset_id: int = Field(..., alias="assetId", description="ASA ID to transfer")
    receiver_wallet: str = Field(..., alias="receiverWallet", description="Recipient address")


class TransferNFTResponse(V4Base):
    """Response after transferring an NFT."""
    asset_id: int = Field(..., alias="assetId")
    receiver_wallet: str = Field(..., alias="receiverWallet")
    tx_id: str = Field(..., alias="txId")
    message: str


class OptInRequest(V4Base):
    """Request to create an unsigned opt-in transaction."""
    asset_id: int = Field(..., alias="assetId")
    fan_wallet: str = Field(..., alias="fanWallet")


class NFTInfoResponse(V4Base):
    """Response model for an NFT instance."""
    id: int
    asset_id: int = Field(..., alias="assetId")
    template_id: int = Field(..., alias="templateId")
    owner_wallet: str = Field(..., alias="ownerWallet")
    sticker_type: str = Field(..., alias="stickerType")
    tx_id: Optional[str] = Field(None, alias="txId")
    expires_at: Optional[str] = Field(None, alias="expiresAt")
    minted_at: Optional[str] = Field(None, alias="mintedAt")
    template_name: Optional[str] = Field(None, alias="templateName")
    image_url: Optional[str] = Field(None, alias="imageUrl")


# ── Error Models ────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    detail: str = Field(default="", description="Detailed error information")


