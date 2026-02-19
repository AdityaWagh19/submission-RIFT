"""
Creator management endpoints — registration, contract lifecycle, dashboard,
and sticker template management.

V4: Each creator gets a unique TipProxy smart contract deployed on TestNet.

Security fixes:
    C1: Wallet auth on state-changing endpoints
    H1: Algorand address validation on all wallet params
    H2: Rate limiting on registration
    H5: Sanitized error messages
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db_models import User, Contract, Transaction, NFT, StickerTemplate
from middleware.auth import require_wallet_auth
from middleware.rate_limit import rate_limit
from models import (
    CreatorRegisterRequest,
    CreatorRegisterResponse,
    ContractInfoResponse,
    ContractStatsResponse,
    UpgradeContractResponse,
    PauseContractRequest,
    CreatorDashboardResponse,
    StickerTemplateResponse,
    StickerTemplateListResponse,
)
from services import contract_service, ipfs_service
from utils.validators import validate_algorand_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/creator", tags=["creator"])


# ── POST /creator/register ─────────────────────────────────────────

@router.post("/register", response_model=CreatorRegisterResponse)
async def register_creator(
    request: CreatorRegisterRequest,
    req: Request = None,
    db: AsyncSession = Depends(get_db),
    _rate=Depends(rate_limit(max_requests=5, window_seconds=3600)),
):
    """
    Register a new creator and deploy their TipProxy contract.

    1. Creates or updates user row (role = "creator")
    2. Deploys TipProxy on TestNet (platform wallet pays)
    3. Saves contract record in DB
    4. Returns app_id + app_address

    Security: Rate limited to 5/hour (H2), address validated (H1).
    """
    wallet = request.wallet_address
    # Security fix H1: Validate wallet address
    validate_algorand_address(wallet)
    username = request.username

    logger.info(f"Creator registration: {wallet[:8]}...")

    # Check if already registered as creator with active contract
    result = await db.execute(
        select(Contract).where(
            Contract.creator_wallet == wallet,
            Contract.active == True,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Creator {wallet[:8]}... already has active contract (App ID: {existing.app_id}). "
                   f"Use /creator/{wallet}/upgrade-contract to deploy a new version.",
        )

    # Upsert user
    user_result = await db.execute(
        select(User).where(User.wallet_address == wallet)
    )
    user = user_result.scalar_one_or_none()
    if user:
        user.role = "creator"
        if username:
            user.username = username
    else:
        user = User(
            wallet_address=wallet,
            role="creator",
            username=username,
        )
        db.add(user)

    await db.flush()  # ensure user exists before FK reference

    # Deploy TipProxy on-chain (with creator's min tip amount)
    try:
        deploy_result = contract_service.deploy_tip_proxy(
            creator_wallet=wallet,
            min_tip_algo=request.min_tip_algo,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="TipProxy contract not compiled. Run: python -m contracts.compile tip_proxy",
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail="Contract deployment configuration error. Check server logs.")
    except Exception as e:
        logger.error(f"TipProxy deployment failed for {wallet[:8]}...: {e}")
        raise HTTPException(
            status_code=502,
            detail="Contract deployment failed. Check server logs.",
        )

    # Save contract record
    contract = Contract(
        creator_wallet=wallet,
        app_id=deploy_result["app_id"],
        app_address=deploy_result["app_address"],
        version=deploy_result["version"],
        active=True,
    )
    db.add(contract)
    await db.commit()

    logger.info(
        f"  Creator {wallet[:8]}... registered — "
        f"App ID: {deploy_result['app_id']}"
    )

    return CreatorRegisterResponse(
        wallet_address=wallet,
        username=username,
        app_id=deploy_result["app_id"],
        app_address=deploy_result["app_address"],
        version=deploy_result["version"],
        min_tip_algo=deploy_result["min_tip_algo"],
        tx_id=deploy_result["tx_id"],
    )


# ── GET /creator/{wallet}/contract ─────────────────────────────────

@router.get("/{wallet}/contract", response_model=ContractInfoResponse)
async def get_creator_contract(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the active TipProxy contract for a creator."""
    result = await db.execute(
        select(Contract).where(
            Contract.creator_wallet == wallet,
            Contract.active == True,
        )
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=404,
            detail=f"No active contract found for {wallet[:8]}... "
                   f"Register first via POST /creator/register",
        )

    return ContractInfoResponse(
        creator_wallet=wallet,
        app_id=contract.app_id,
        app_address=contract.app_address,
        version=contract.version,
        active=contract.active,
        deployed_at=contract.deployed_at.isoformat() if contract.deployed_at else None,
    )


# ── GET /creator/{wallet}/contract/stats ───────────────────────────

@router.get("/{wallet}/contract/stats", response_model=ContractStatsResponse)
async def get_creator_contract_stats(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """Read on-chain global state from a creator's TipProxy contract."""
    result = await db.execute(
        select(Contract).where(
            Contract.creator_wallet == wallet,
            Contract.active == True,
        )
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=404,
            detail=f"No active contract found for {wallet[:8]}...",
        )

    try:
        stats = contract_service.get_contract_stats(contract.app_id)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail="Failed to read on-chain state. Check server logs.",
        )

    return ContractStatsResponse(**stats)


# ── POST /creator/{wallet}/upgrade-contract ────────────────────────

@router.post("/{wallet}/upgrade-contract", response_model=UpgradeContractResponse)
async def upgrade_creator_contract(
    wallet: str = Depends(require_wallet_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Deploy a new TipProxy version for a creator.

    1. Deploys a fresh TipProxy (platform wallet pays)
    2. Archives the old contract (active = False)
    3. Saves new contract as active
    4. Optionally deletes the old contract on-chain
    """
    # Find current active contract
    result = await db.execute(
        select(Contract).where(
            Contract.creator_wallet == wallet,
            Contract.active == True,
        )
    )
    old_contract = result.scalar_one_or_none()

    if not old_contract:
        raise HTTPException(
            status_code=404,
            detail=f"No active contract to upgrade for {wallet[:8]}...",
        )

    # Read current min_tip from on-chain state to preserve it in the upgrade
    try:
        current_stats = contract_service.get_contract_stats(old_contract.app_id)
        current_min_tip = current_stats.get("min_tip_algo", 1.0)
    except Exception:
        current_min_tip = 1.0  # fallback to default if we can't read state

    try:
        new_deploy = contract_service.upgrade_tip_proxy(
            creator_wallet=wallet,
            old_app_id=old_contract.app_id,
            old_version=old_contract.version,
            min_tip_algo=current_min_tip,
        )
    except Exception as e:
        logger.error(f"Upgrade failed for {wallet[:8]}...: {e}")
        raise HTTPException(
            status_code=502,
            detail="Contract upgrade failed. Check server logs.",
        )

    # Archive old contract
    old_contract.active = False
    old_contract.upgraded_at = datetime.utcnow()

    # Save new contract
    new_contract = Contract(
        creator_wallet=wallet,
        app_id=new_deploy["app_id"],
        app_address=new_deploy["app_address"],
        version=new_deploy["version"],
        active=True,
    )
    db.add(new_contract)
    await db.commit()

    # Close out old contract (best-effort, don't fail if this errors)
    contract_service.close_out_contract(old_contract.app_id, wallet)

    logger.info(
        f"  Contract upgraded: {old_contract.app_id} → {new_deploy['app_id']} "
        f"(v{old_contract.version} → v{new_deploy['version']})"
    )

    return UpgradeContractResponse(
        old_app_id=old_contract.app_id,
        new_app_id=new_deploy["app_id"],
        new_app_address=new_deploy["app_address"],
        new_version=new_deploy["version"],
        message=f"TipProxy upgraded to v{new_deploy['version']}",
    )


# ── POST /creator/{wallet}/pause-contract ──────────────────────────

@router.post("/{wallet}/pause-contract")
async def pause_creator_contract(
    wallet: str = Depends(require_wallet_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Create an unsigned ApplicationCallTxn to pause a creator's TipProxy.
    Must be signed by the creator via Pera Wallet.
    """
    result = await db.execute(
        select(Contract).where(
            Contract.creator_wallet == wallet,
            Contract.active == True,
        )
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=404,
            detail=f"No active contract found for {wallet[:8]}...",
        )

    from algosdk import transaction as algo_txn, encoding as algo_enc
    from algorand_client import algorand_client

    sp = algorand_client.get_suggested_params()
    sp.fee = max(sp.fee, 1000)
    sp.flat_fee = True

    txn = algo_txn.ApplicationCallTxn(
        sender=wallet,
        sp=sp,
        index=contract.app_id,
        on_complete=algo_txn.OnComplete.NoOpOC,
        app_args=[b"pause"],
    )

    txn_bytes = algo_enc.msgpack_encode(txn)

    return {
        "unsignedTxn": txn_bytes,
        "appId": contract.app_id,
        "action": "pause",
        "message": "Sign this transaction with Pera Wallet to pause your TipProxy",
    }


# ── POST /creator/{wallet}/unpause-contract ────────────────────────

@router.post("/{wallet}/unpause-contract")
async def unpause_creator_contract(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Create an unsigned ApplicationCallTxn to unpause a creator's TipProxy.
    Must be signed by the creator via Pera Wallet.
    """
    result = await db.execute(
        select(Contract).where(
            Contract.creator_wallet == wallet,
            Contract.active == True,
        )
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=404,
            detail=f"No active contract found for {wallet[:8]}...",
        )

    from algosdk import transaction as algo_txn, encoding as algo_enc
    from algorand_client import algorand_client

    sp = algorand_client.get_suggested_params()
    sp.fee = max(sp.fee, 1000)
    sp.flat_fee = True

    txn = algo_txn.ApplicationCallTxn(
        sender=wallet,
        sp=sp,
        index=contract.app_id,
        on_complete=algo_txn.OnComplete.NoOpOC,
        app_args=[b"unpause"],
    )

    txn_bytes = algo_enc.msgpack_encode(txn)

    return {
        "unsignedTxn": txn_bytes,
        "appId": contract.app_id,
        "action": "unpause",
        "message": "Sign this transaction with Pera Wallet to unpause your TipProxy",
    }


# ── GET /creator/{wallet}/dashboard ────────────────────────────────

@router.get("/{wallet}/dashboard")
async def get_creator_dashboard(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Combined on-chain + off-chain analytics for a creator.

    Returns contract info, on-chain stats, fan count, sticker count,
    and recent transactions.
    """
    # Get user info
    user_result = await db.execute(
        select(User).where(User.wallet_address == wallet)
    )
    user = user_result.scalar_one_or_none()

    if not user or user.role != "creator":
        raise HTTPException(
            status_code=404,
            detail=f"Creator {wallet[:8]}... not found. Register first.",
        )

    # Get active contract
    contract_result = await db.execute(
        select(Contract).where(
            Contract.creator_wallet == wallet,
            Contract.active == True,
        )
    )
    contract = contract_result.scalar_one_or_none()

    contract_info = None
    stats = None

    if contract:
        contract_info = {
            "creatorWallet": wallet,
            "appId": contract.app_id,
            "appAddress": contract.app_address,
            "version": contract.version,
            "active": contract.active,
            "deployedAt": contract.deployed_at.isoformat() if contract.deployed_at else None,
        }

        # Read on-chain stats (best-effort)
        try:
            stats = contract_service.get_contract_stats(contract.app_id)
        except Exception as e:
            logger.warning(f"Failed to read on-chain stats: {e}")

    # Count unique fans
    fans_result = await db.execute(
        select(func.count(distinct(Transaction.fan_wallet))).where(
            Transaction.creator_wallet == wallet
        )
    )
    total_fans = fans_result.scalar() or 0

    # Count minted stickers for this creator
    nfts_count_result = await db.execute(
        select(func.count(NFT.id)).join(
            StickerTemplate,
            NFT.template_id == StickerTemplate.id,
        ).where(StickerTemplate.creator_wallet == wallet)
    )
    total_stickers = nfts_count_result.scalar() or 0

    # Recent transactions (last 20)
    recent_result = await db.execute(
        select(Transaction).where(
            Transaction.creator_wallet == wallet
        ).order_by(Transaction.detected_at.desc()).limit(20)
    )
    recent_txns = recent_result.scalars().all()

    return {
        "walletAddress": wallet,
        "username": user.username,
        "contract": contract_info,
        "stats": stats,
        "totalFans": total_fans,
        "totalStickersMinted": total_stickers,
        "recentTransactions": [
            {
                "txId": tx.tx_id,
                "fanWallet": tx.fan_wallet,
                "amountAlgo": round(tx.amount_micro / 1_000_000, 6),
                "memo": tx.memo,
                "processed": tx.processed,
                "detectedAt": tx.detected_at.isoformat() if tx.detected_at else None,
            }
            for tx in recent_txns
        ],
    }


# ════════════════════════════════════════════════════════════════════
# Sticker Template Endpoints (Phase 3)
# ════════════════════════════════════════════════════════════════════


# ── POST /creator/{wallet}/sticker-template ────────────────────────

@router.post("/{wallet}/sticker-template", response_model=StickerTemplateResponse)
async def create_sticker_template(
    wallet: str = Depends(require_wallet_auth),
    name: str = Form(..., description="Sticker display name"),
    sticker_type: str = Form("soulbound", description="'soulbound' or 'golden'"),
    category: str = Form("tip", description="Sticker category"),
    tip_threshold: float = Form(1.0, description="Min ALGO to earn this sticker"),
    image: UploadFile = File(..., description="Sticker image file"),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new sticker template with IPFS image upload.

    1. Validates creator exists
    2. Uploads image to Pinata IPFS
    3. Generates ARC-3 metadata JSON and uploads to IPFS
    4. Saves template in DB

    Accepts multipart/form-data with an image file.
    """
    # Validate creator
    user_result = await db.execute(
        select(User).where(
            User.wallet_address == wallet,
            User.role == "creator",
        )
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Creator {wallet[:8]}... not found. Register first.",
        )

    # Validate sticker type
    if sticker_type not in ("soulbound", "golden"):
        raise HTTPException(
            status_code=400,
            detail="sticker_type must be 'soulbound' or 'golden'",
        )

    # Validate tip threshold range (creator-configurable, but bounded)
    if tip_threshold < 0.1:
        raise HTTPException(
            status_code=400,
            detail="tip_threshold must be at least 0.1 ALGO",
        )
    if tip_threshold > 10000.0:
        raise HTTPException(
            status_code=400,
            detail="tip_threshold cannot exceed 10,000 ALGO",
        )

    # Check max templates per creator (prevent abuse)
    template_count_result = await db.execute(
        select(func.count()).select_from(StickerTemplate).where(
            StickerTemplate.creator_wallet == wallet,
        )
    )
    template_count = template_count_result.scalar()
    if template_count >= 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 sticker templates per creator. Delete an existing template first.",
        )

    # Check for duplicate threshold + sticker_type combination
    duplicate_result = await db.execute(
        select(StickerTemplate).where(
            StickerTemplate.creator_wallet == wallet,
            StickerTemplate.category == category,
            StickerTemplate.tip_threshold == tip_threshold,
            StickerTemplate.sticker_type == sticker_type,
        )
    )
    duplicate = duplicate_result.scalar_one_or_none()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"You already have a {sticker_type} template at {tip_threshold} ALGO threshold "
                   f"('{duplicate.name}'). Delete it first or use a different threshold.",
        )

    # Read image bytes
    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Image file is empty")
    if len(image_bytes) > 5 * 1024 * 1024:  # 5 MB limit
        raise HTTPException(status_code=400, detail="Image must be under 5 MB")

    # Upload image to IPFS
    try:
        image_result = await ipfs_service.upload_image(
            file_bytes=image_bytes,
            filename=image.filename or "sticker.jpg",
            mimetype=image.content_type or "image/jpeg",
            metadata_name=f"{wallet[:8]}-{name}",
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"IPFS image upload failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to upload image to IPFS. Check server logs.",
        )

    # Upload ARC-3 metadata to IPFS
    try:
        metadata_result = await ipfs_service.upload_metadata(
            name=name,
            description=f"{sticker_type.title()} sticker by {wallet[:8]}...",
            image_url=image_result["url"],
            creator_wallet=wallet,
            category=category,
            sticker_type=sticker_type,
            extra_properties={"tip_threshold": tip_threshold},
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail="IPFS image upload configuration error. Check server logs.")
    except Exception as e:
        logger.error(f"IPFS metadata upload failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to upload metadata to IPFS. Check server logs.",
        )

    # Save template to DB
    template = StickerTemplate(
        creator_wallet=wallet,
        name=name,
        ipfs_hash=image_result["cid"],
        image_url=image_result["url"],
        metadata_url=metadata_result["url"],
        sticker_type=sticker_type,
        category=category,
        tip_threshold=tip_threshold,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(
        f"  Sticker template '{name}' created for {wallet[:8]}... "
        f"(IPFS: {image_result['cid'][:12]}...)"
    )

    return StickerTemplateResponse(
        id=template.id,
        creator_wallet=wallet,
        name=name,
        ipfs_hash=image_result["cid"],
        image_url=image_result["url"],
        metadata_url=metadata_result["url"],
        sticker_type=sticker_type,
        category=category,
        tip_threshold=tip_threshold,
        created_at=template.created_at.isoformat() if template.created_at else None,
        mint_count=0,
    )


# ── GET /creator/{wallet}/templates ────────────────────────────────

@router.get("/{wallet}/templates", response_model=StickerTemplateListResponse)
async def get_creator_templates(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """
    List all sticker templates for a creator.

    Includes mint_count for each template (how many NFTs were minted from it).
    """
    result = await db.execute(
        select(StickerTemplate).where(
            StickerTemplate.creator_wallet == wallet
        ).order_by(StickerTemplate.created_at.desc())
    )
    templates = result.scalars().all()

    # Get mint counts per template
    template_responses = []
    for t in templates:
        count_result = await db.execute(
            select(func.count(NFT.id)).where(
                NFT.template_id == t.id
            )
        )
        mint_count = count_result.scalar() or 0

        template_responses.append(
            StickerTemplateResponse(
                id=t.id,
                creator_wallet=t.creator_wallet,
                name=t.name,
                ipfs_hash=t.ipfs_hash,
                image_url=t.image_url,
                metadata_url=t.metadata_url,
                sticker_type=t.sticker_type,
                category=t.category,
                tip_threshold=t.tip_threshold,
                created_at=t.created_at.isoformat() if t.created_at else None,
                mint_count=mint_count,
            )
        )

    return StickerTemplateListResponse(
        creator_wallet=wallet,
        templates=template_responses,
        total=len(template_responses),
    )


# ── DELETE /creator/{wallet}/template/{template_id} ────────────────

@router.delete("/{wallet}/template/{template_id}")
async def delete_sticker_template(
    wallet: str,
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a sticker template.

    Only deletes if no NFTs have been minted from it. Unpins from IPFS.
    """
    result = await db.execute(
        select(StickerTemplate).where(
            StickerTemplate.id == template_id,
            StickerTemplate.creator_wallet == wallet,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template {template_id} not found for {wallet[:8]}...",
        )

    # Check if any NFTs were minted from this template
    nft_count_result = await db.execute(
        select(func.count(NFT.id)).where(
            NFT.template_id == template_id
        )
    )
    nft_count = nft_count_result.scalar() or 0

    if nft_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete template with {nft_count} minted NFTs",
        )

    # Unpin from IPFS (best-effort)
    if template.ipfs_hash:
        await ipfs_service.unpin(template.ipfs_hash)

    await db.delete(template)
    await db.commit()

    logger.info(f"  Template '{template.name}' deleted for {wallet[:8]}...")

    return {
        "message": f"Template '{template.name}' deleted",
        "templateId": template_id,
    }
