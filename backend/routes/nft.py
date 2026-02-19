"""
NFT management endpoints — minting, transferring, opt-in, and inventory.

Phase 3: Provides endpoints for minting soulbound and golden stickers,
transferring golden stickers between wallets, creating opt-in transactions,
and viewing NFT inventories.

Security fixes:
    H1: Algorand address validation
    H5: Sanitized error messages
    L4: Pagination on inventory endpoint
"""
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db_models import NFT, StickerTemplate, User
from models import (
    MintSoulboundRequest,
    MintGoldenRequest,
    MintResponse,
    TransferNFTRequest,
    TransferNFTResponse,
    OptInRequest,
    NFTInfoResponse,
)
from services import nft_service
from utils.validators import validate_algorand_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nft", tags=["nft"])


# ── POST /nft/mint/soulbound ───────────────────────────────────────

@router.post("/mint/soulbound", response_model=MintResponse)
async def mint_soulbound_nft(
    request: MintSoulboundRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Mint a soulbound (non-transferable) sticker NFT.

    1. Looks up the sticker template
    2. Mints NFT on Algorand with IPFS metadata URL
    3. Transfers NFT to the fan's wallet
    4. Saves NFT record in DB

    Requires: template must exist with metadata_url set (IPFS uploaded).
    """
    template_id = request.template_id
    fan_wallet = request.fan_wallet

    # Get template
    template = await _get_template(db, template_id, expected_type="soulbound")

    # Ensure fan user exists
    await _ensure_user(db, fan_wallet, role="fan")

    # Mint NFT on-chain
    try:
        asset_id = nft_service.mint_soulbound_sticker(
            name=template.name[:32],  # ASA name max 32 chars
            metadata_url=template.metadata_url or template.image_url or "",
            unit_name="STICKER",
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail="NFT minting configuration error. Check server logs.")
    except Exception as e:
        logger.error(f"Soulbound mint failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="NFT minting failed. Check server logs.",
        )

    # Transfer to fan
    tx_id = None
    try:
        tx_id = nft_service.send_nft_to_fan(
            asset_id=asset_id,
            fan_wallet=fan_wallet,
        )
    except Exception as e:
        logger.warning(f"NFT transfer to fan failed (asset {asset_id}): {e}")
        # NFT was minted but transfer failed — record it anyway

    # Save NFT record
    nft = NFT(
        asset_id=asset_id,
        template_id=template_id,
        owner_wallet=fan_wallet,
        sticker_type="soulbound",
        tx_id=tx_id,
    )
    db.add(nft)
    await db.commit()

    logger.info(
        f"  Soulbound NFT minted — Asset: {asset_id}, "
        f"Template: {template.name}, Fan: {fan_wallet[:8]}..."
    )

    return MintResponse(
        asset_id=asset_id,
        sticker_type="soulbound",
        name=template.name,
        metadata_url=template.metadata_url,
        owner_wallet=fan_wallet,
        tx_id=tx_id,
        message=f"Soulbound sticker '{template.name}' minted and sent to {fan_wallet[:8]}...",
    )


# ── POST /nft/mint/golden ─────────────────────────────────────────

@router.post("/mint/golden", response_model=MintResponse)
async def mint_golden_nft(
    request: MintGoldenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Mint a golden (tradable) sticker NFT.

    1. Looks up the sticker template
    2. Mints NFT on Algorand (no freeze/clawback = fully tradable)
    3. Transfers NFT to the fan's wallet
    4. Saves NFT record in DB

    Note: Fan must opt-in to the asset first (via /nft/optin endpoint).
    """
    template_id = request.template_id
    fan_wallet = request.fan_wallet

    # Get template
    template = await _get_template(db, template_id, expected_type="golden")

    # Ensure fan user exists
    await _ensure_user(db, fan_wallet, role="fan")

    # Mint NFT on-chain
    try:
        asset_id = nft_service.mint_golden_sticker(
            name=template.name[:32],
            metadata_url=template.metadata_url or template.image_url or "",
            unit_name="GOLDEN",
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail="NFT minting configuration error. Check server logs.")
    except Exception as e:
        logger.error(f"Golden mint failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="NFT minting failed. Check server logs.",
        )

    # Transfer to fan
    tx_id = None
    try:
        tx_id = nft_service.send_nft_to_fan(
            asset_id=asset_id,
            fan_wallet=fan_wallet,
        )
    except Exception as e:
        logger.warning(
            f"Golden NFT transfer failed (asset {asset_id}): {e}. "
            f"Fan may need to opt-in first via /nft/optin"
        )

    # Save NFT record
    nft = NFT(
        asset_id=asset_id,
        template_id=template_id,
        owner_wallet=fan_wallet,
        sticker_type="golden",
        tx_id=tx_id,
    )
    db.add(nft)
    await db.commit()

    logger.info(
        f"  Golden NFT minted — Asset: {asset_id}, "
        f"Template: {template.name}, Fan: {fan_wallet[:8]}..."
    )

    return MintResponse(
        asset_id=asset_id,
        sticker_type="golden",
        name=template.name,
        metadata_url=template.metadata_url,
        owner_wallet=fan_wallet,
        tx_id=tx_id,
        message=f"Golden sticker '{template.name}' minted for {fan_wallet[:8]}...",
    )


# ── POST /nft/transfer ────────────────────────────────────────────

@router.post("/transfer", response_model=TransferNFTResponse)
async def transfer_nft(
    request: TransferNFTRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Transfer a golden NFT to another wallet.

    Only golden (tradable) NFTs can be transferred.
    Receiver must opt-in to the asset first.
    """
    asset_id = request.asset_id
    receiver_wallet = request.receiver_wallet

    # Verify NFT exists and is golden
    result = await db.execute(
        select(NFT).where(NFT.asset_id == asset_id)
    )
    nft = result.scalar_one_or_none()

    if not nft:
        raise HTTPException(
            status_code=404,
            detail=f"NFT with asset ID {asset_id} not found",
        )

    if nft.sticker_type != "golden":
        raise HTTPException(
            status_code=400,
            detail="Only golden (tradable) stickers can be transferred. "
                   "Soulbound stickers are permanently bound to the original recipient.",
        )

    # Transfer on-chain
    try:
        tx_id = nft_service.send_nft_to_fan(
            asset_id=asset_id,
            fan_wallet=receiver_wallet,
        )
    except Exception as e:
        logger.error(f"NFT transfer failed: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Transfer failed: {str(e)}. "
                   f"Receiver may need to opt-in first via /nft/optin",
        )

    # Update owner in DB
    nft.owner_wallet = receiver_wallet
    await db.commit()

    logger.info(f"  Golden NFT {asset_id} transferred to {receiver_wallet[:8]}...")

    return TransferNFTResponse(
        asset_id=asset_id,
        receiver_wallet=receiver_wallet,
        tx_id=tx_id,
        message=f"NFT {asset_id} transferred to {receiver_wallet[:8]}...",
    )


# ── POST /nft/optin ───────────────────────────────────────────────

@router.post("/optin")
async def create_optin_transaction(request: OptInRequest):
    """
    Create an unsigned ASA opt-in transaction.

    The fan signs this with Pera Wallet before receiving a golden NFT.
    Returns the unsigned transaction as msgpack-encoded bytes.
    """
    try:
        result = nft_service.create_optin_txn(
            asset_id=request.asset_id,
            fan_wallet=request.fan_wallet,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail="Failed to create opt-in transaction. Check server logs.",
        )

    return {
        "unsignedTxn": result["unsignedTxn"],
        "assetId": request.asset_id,
        "fanWallet": request.fan_wallet,
        "message": "Sign this transaction with Pera Wallet to opt-in to the asset",
    }


# ── GET /nft/inventory/{wallet} ───────────────────────────────────

@router.get("/inventory/{wallet}")
async def get_nft_inventory(
    wallet: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all NFTs owned by a wallet.

    Returns sticker details with template info and IPFS URLs.
    Security fix L4: Paginated with skip/limit (max 100 per page).
    Security fix H1: Validates wallet address format.
    """
    # Security fix H1: Validate wallet
    validate_algorand_address(wallet)

    result = await db.execute(
        select(NFT).where(
            NFT.owner_wallet == wallet
        ).order_by(NFT.minted_at.desc()).offset(skip).limit(limit)
    )
    nfts = result.scalars().all()

    # Get total count for pagination metadata
    count_result = await db.execute(
        select(func.count(NFT.id)).where(NFT.owner_wallet == wallet)
    )
    total_count = count_result.scalar() or 0

    inventory = []
    for nft in nfts:
        # Get template info
        template_result = await db.execute(
            select(StickerTemplate).where(
                StickerTemplate.id == nft.template_id
            )
        )
        template = template_result.scalar_one_or_none()

        inventory.append({
            "id": nft.id,
            "assetId": nft.asset_id,
            "templateId": nft.template_id,
            "ownerWallet": nft.owner_wallet,
            "stickerType": nft.sticker_type,
            "txId": nft.tx_id,
            "expiresAt": nft.expires_at.isoformat() if nft.expires_at else None,
            "mintedAt": nft.minted_at.isoformat() if nft.minted_at else None,
            "templateName": template.name if template else None,
            "imageUrl": template.image_url if template else None,
            "metadataUrl": template.metadata_url if template else None,
            "category": template.category if template else None,
        })

    return {
        "wallet": wallet,
        "nfts": inventory,
        "total": len(inventory),
        "totalCount": total_count,
        "skip": skip,
        "limit": limit,
        "hasMore": (skip + limit) < total_count,
        "totalSoulbound": sum(1 for n in inventory if n["stickerType"] == "soulbound"),
        "totalGolden": sum(1 for n in inventory if n["stickerType"] == "golden"),
    }


# ── GET /nft/{asset_id} ──────────────────────────────────────────

@router.get("/{asset_id}")
async def get_nft_details(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific NFT by asset ID."""
    result = await db.execute(
        select(NFT).where(NFT.asset_id == asset_id)
    )
    nft = result.scalar_one_or_none()

    if not nft:
        raise HTTPException(
            status_code=404,
            detail=f"NFT with asset ID {asset_id} not found",
        )

    # Get template
    template_result = await db.execute(
        select(StickerTemplate).where(
            StickerTemplate.id == nft.template_id
        )
    )
    template = template_result.scalar_one_or_none()

    return {
        "id": nft.id,
        "assetId": nft.asset_id,
        "templateId": nft.template_id,
        "ownerWallet": nft.owner_wallet,
        "stickerType": nft.sticker_type,
        "txId": nft.tx_id,
        "expiresAt": nft.expires_at.isoformat() if nft.expires_at else None,
        "mintedAt": nft.minted_at.isoformat() if nft.minted_at else None,
        "templateName": template.name if template else None,
        "imageUrl": template.image_url if template else None,
        "metadataUrl": template.metadata_url if template else None,
        "category": template.category if template else None,
        "creatorWallet": template.creator_wallet if template else None,
    }


# ════════════════════════════════════════════════════════════════════
# Helper functions
# ════════════════════════════════════════════════════════════════════


async def _get_template(
    db: AsyncSession,
    template_id: int,
    expected_type: str = None,
) -> StickerTemplate:
    """
    Look up a sticker template by ID and validate type.

    Raises HTTPException if not found, not IPFS-ready, or wrong type.
    """
    result = await db.execute(
        select(StickerTemplate).where(StickerTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Sticker template {template_id} not found",
        )

    if not template.metadata_url and not template.image_url:
        raise HTTPException(
            status_code=400,
            detail=f"Template '{template.name}' has no IPFS data. "
                   f"Upload an image first via /creator/{{wallet}}/sticker-template",
        )

    if expected_type and template.sticker_type != expected_type:
        raise HTTPException(
            status_code=400,
            detail=f"Template '{template.name}' is type '{template.sticker_type}', "
                   f"expected '{expected_type}'",
        )

    return template


async def _ensure_user(
    db: AsyncSession,
    wallet: str,
    role: str = "fan",
) -> User:
    """
    Ensure a user record exists for a wallet. Creates one if missing.
    """
    result = await db.execute(
        select(User).where(User.wallet_address == wallet)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            wallet_address=wallet,
            role=role,
        )
        db.add(user)
        await db.flush()

    return user
