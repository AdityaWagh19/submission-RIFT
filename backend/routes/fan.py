"""
Fan-facing endpoints — inventory, stats, leaderboard, and golden odds.

Phase 5: Provides read-only endpoints for fans to view their NFT collection,
tipping statistics, creator leaderboards, and golden sticker probabilities.

Security fixes:
    H1: Algorand address validation
    H5: Sanitized error messages
    L4: Pagination on inventory endpoint
"""
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func, distinct, case, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db_models import User, NFT, StickerTemplate, Transaction, Contract
from domain.responses import success_response, paginated_response
from utils.validators import validate_algorand_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fan", tags=["fan"])


# ── GET /fan/{wallet}/inventory ────────────────────────────────────

@router.get("/{wallet}/inventory")
async def get_fan_inventory(
    wallet: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all NFT stickers owned by a fan.

    Returns stickers grouped by type (soulbound/golden) with template details,
    IPFS image URLs, and expiry dates for membership stickers.

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

    # Batch-load templates to avoid N+1 queries
    template_ids = {nft.template_id for nft in nfts}
    templates_by_id = {}
    if template_ids:
        templates_result = await db.execute(
            select(StickerTemplate).where(StickerTemplate.id.in_(template_ids))
        )
        templates = templates_result.scalars().all()
        templates_by_id = {t.id: t for t in templates}

    # Get total count for pagination
    count_result = await db.execute(
        select(func.count(NFT.id)).where(NFT.owner_wallet == wallet)
    )
    total_count = count_result.scalar() or 0

    inventory = []
    for nft in nfts:
        template = templates_by_id.get(nft.template_id)

        inventory.append(
            {
                "id": nft.id,
                "assetId": nft.asset_id,
                "templateId": nft.template_id,
                "ownerWallet": nft.owner_wallet,
                "stickerType": nft.sticker_type,
                "deliveryStatus": nft.delivery_status,
                "txId": nft.tx_id,
                "expiresAt": nft.expires_at.isoformat() if nft.expires_at else None,
                "mintedAt": nft.minted_at.isoformat() if nft.minted_at else None,
                "templateName": template.name if template else None,
                "imageUrl": template.image_url if template else None,
                "metadataUrl": template.metadata_url if template else None,
                "category": template.category if template else None,
                "creatorWallet": template.creator_wallet if template else None,
            }
        )

    # Use paginated_response but include additional stats in meta
    response = paginated_response(
        items=inventory,
        limit=limit,
        skip=skip,
        total=total_count,
    )
    # Add wallet and type counts to meta
    response["meta"]["wallet"] = wallet
    response["meta"]["totalSoulbound"] = sum(1 for n in inventory if n["stickerType"] == "soulbound")
    response["meta"]["totalGolden"] = sum(1 for n in inventory if n["stickerType"] == "golden")
    return response


# ── GET /fan/{wallet}/pending ─────────────────────────────────────

@router.get("/{wallet}/pending")
async def get_pending_nfts(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get NFTs that have been minted for a fan but not yet delivered.

    These are stickers where the fan hasn't opted into the ASA yet.
    Frontend should:
      1. Show these as "claimable" stickers
      2. Create opt-in transactions for each ASA → Pera signs
      3. Call POST /fan/{wallet}/claim/{nft_id} after opt-in
    """
    result = await db.execute(
        select(NFT).where(
            NFT.owner_wallet == wallet,
            NFT.delivery_status == "pending_optin",
        ).order_by(NFT.minted_at.desc())
    )
    pending = result.scalars().all()

    # Batch-load templates to avoid N+1 queries
    template_ids = {nft.template_id for nft in pending}
    templates_by_id = {}
    if template_ids:
        templates_result = await db.execute(
            select(StickerTemplate).where(StickerTemplate.id.in_(template_ids))
        )
        templates = templates_result.scalars().all()
        templates_by_id = {t.id: t for t in templates}

    items = []
    for nft in pending:
        template = templates_by_id.get(nft.template_id)

        items.append(
            {
                "id": nft.id,
                "assetId": nft.asset_id,
                "stickerType": nft.sticker_type,
                "mintedAt": nft.minted_at.isoformat() if nft.minted_at else None,
                "templateName": template.name if template else None,
                "imageUrl": template.image_url if template else None,
                "creatorWallet": template.creator_wallet if template else None,
            }
        )

    return success_response(
        data={
            "wallet": wallet,
            "pending": items,
        },
        meta={"total": len(items)},
    )


# ── POST /fan/{wallet}/claim/{nft_id} ────────────────────────────

@router.post("/{wallet}/claim/{nft_id}")
async def claim_pending_nft(
    wallet: str,
    nft_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Deliver a pending NFT after the fan has opted in via Pera Wallet.

    Flow:
      1. Frontend creates opt-in txn for the ASA → fan signs via Pera → submits
      2. Frontend calls this endpoint
      3. Backend verifies fan has opted in → transfers the NFT
      4. Updates delivery_status to 'delivered'
    """
    from services import nft_service

    # Find the pending NFT
    result = await db.execute(
        select(NFT).where(
            NFT.id == nft_id,
            NFT.owner_wallet == wallet,
            NFT.delivery_status == "pending_optin",
        )
    )
    nft = result.scalar_one_or_none()

    if not nft:
        raise HTTPException(
            status_code=404,
            detail="No pending NFT found with that ID for this wallet",
        )

    # Attempt delivery (no fan_private_key — fan must have opted in via Pera)
    try:
        delivery = nft_service.send_nft_to_fan(
            asset_id=nft.asset_id,
            fan_wallet=wallet,
        )

        if delivery["status"] == "delivered":
            nft.tx_id = delivery["tx_id"]
            nft.delivery_status = "delivered"
            await db.commit()
            logger.info(f"  ✅ Pending NFT {nft.asset_id} claimed by {wallet[:8]}...")
            return {
                "status": "delivered",
                "assetId": nft.asset_id,
                "txId": delivery["tx_id"],
            }
        else:
            # Fan still hasn't opted in
            raise HTTPException(
                status_code=400,
                detail=f"Fan has not opted into ASA {nft.asset_id}. "
                       f"Please opt-in via Pera Wallet first.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Claim failed for NFT {nft.asset_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to deliver NFT. Check server logs.",
        )


# ── GET /fan/{wallet}/stats ───────────────────────────────────────

@router.get("/{wallet}/stats")
async def get_fan_stats(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get tipping statistics for a fan.

    Returns:
    - Total tips sent
    - Total ALGO spent
    - Unique creators supported
    - NFTs collected (by type)
    - Recent tip history
    """
    # Phase 6: Optimize - combine multiple queries into single aggregate query
    # Total tips, ALGO spent, and unique creators in one query
    tips_result = await db.execute(
        select(
            func.count(Transaction.id).label("tip_count"),
            func.coalesce(func.sum(Transaction.amount_micro), 0).label("total_micro"),
            func.count(distinct(Transaction.creator_wallet)).label("unique_creators"),
        ).where(Transaction.fan_wallet == wallet)
    )
    tip_row = tips_result.one()
    total_tips = tip_row.tip_count or 0
    total_algo_spent = (tip_row.total_micro or 0) / 1_000_000  # microAlgos -> ALGO
    unique_creators = tip_row.unique_creators or 0

    # Phase 6: Optimize - combine NFT counts by type into single query with conditional aggregation
    nft_counts_result = await db.execute(
        select(
            func.sum(case((NFT.sticker_type == "soulbound", 1), else_=0)).label("soulbound_count"),
            func.sum(case((NFT.sticker_type == "golden", 1), else_=0)).label("golden_count"),
        ).where(NFT.owner_wallet == wallet)
    )
    nft_row = nft_counts_result.one()
    total_soulbound = nft_row.soulbound_count or 0
    total_golden = nft_row.golden_count or 0

    # Average tip amount
    avg_tip = total_algo_spent / total_tips if total_tips > 0 else 0.0

    # Recent tips (last 10)
    recent_result = await db.execute(
        select(Transaction).where(
            Transaction.fan_wallet == wallet
        ).order_by(Transaction.detected_at.desc()).limit(10)
    )
    recent_tips = recent_result.scalars().all()

    # Per-creator breakdown
    creator_breakdown_result = await db.execute(
        select(
            Transaction.creator_wallet,
            func.count(Transaction.id).label("tip_count"),
            func.sum(Transaction.amount_micro).label("total_micro"),
        ).where(
            Transaction.fan_wallet == wallet
        ).group_by(Transaction.creator_wallet).order_by(
            desc("total_micro")
        ).limit(10)
    )
    creator_breakdown = [
        {
            "creatorWallet": row[0],
            "tipCount": row[1],
            "totalAlgo": round(row[2] / 1_000_000, 6) if row[2] else 0.0,
        }
        for row in creator_breakdown_result.all()
    ]

    return {
        "wallet": wallet,
        "totalTips": total_tips,
        "totalAlgoSpent": round(total_algo_spent, 6),
        "averageTipAlgo": round(avg_tip, 6),
        "uniqueCreators": unique_creators,
        "totalSoulbound": total_soulbound,
        "totalGolden": total_golden,
        "totalNfts": total_soulbound + total_golden,
        "creatorBreakdown": creator_breakdown,
        "recentTips": [
            {
                "txId": tx.tx_id,
                "creatorWallet": tx.creator_wallet,
                "amountAlgo": round(tx.amount_micro / 1_000_000, 6),
                "memo": tx.memo,
                "detectedAt": tx.detected_at.isoformat() if tx.detected_at else None,
            }
            for tx in recent_tips
        ],
    }


# ── GET /fan/{wallet}/golden-odds ─────────────────────────────────

@router.get("/{wallet}/golden-odds")
async def get_golden_odds(
    wallet: str,
    amount_algo: float = 1.0,
):
    """
    Show a fan their current golden sticker probability.

    Takes an optional amount_algo query param to preview whale bonuses.
    """
    from services.probability_service import get_golden_probability

    odds = get_golden_probability(amount_algo)

    return {
        "wallet": wallet,
        "tipAmount": amount_algo,
        **odds,
    }


# ══════════════════════════════════════════════════════════════════
# Leaderboard (under /leaderboard prefix)
# ══════════════════════════════════════════════════════════════════

leaderboard_router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


# ── GET /leaderboard/{creator_wallet} ─────────────────────────────

@leaderboard_router.get("/{creator_wallet}")
async def get_creator_leaderboard(
    creator_wallet: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the top fans for a specific creator, ranked by total ALGO tipped.

    Returns fan wallet, tip count, total ALGO, and NFT count for each fan.
    """
    # Verify creator exists
    creator_result = await db.execute(
        select(User).where(
            User.wallet_address == creator_wallet,
            User.role == "creator",
        )
    )
    creator = creator_result.scalar_one_or_none()
    if not creator:
        raise HTTPException(
            status_code=404,
            detail=f"Creator {creator_wallet[:8]}... not found",
        )

    # Top fans by total ALGO tipped
    cap = min(limit, 100)  # prevent abuse
    fans_result = await db.execute(
        select(
            Transaction.fan_wallet,
            func.count(Transaction.id).label("tip_count"),
            func.sum(Transaction.amount_micro).label("total_micro"),
        ).where(
            Transaction.creator_wallet == creator_wallet
        ).group_by(Transaction.fan_wallet).order_by(
            desc("total_micro")
        ).limit(cap)
    )
    fan_rows = fans_result.all()

    fan_wallets = [row[0] for row in fan_rows]

    # Batch-load NFT counts per fan for this creator
    nft_counts_by_fan = {}
    if fan_wallets:
        nft_counts_result = await db.execute(
            select(
                NFT.owner_wallet,
                func.count(NFT.id).label("nft_count"),
            )
            .join(
                StickerTemplate,
                NFT.template_id == StickerTemplate.id,
            )
            .where(
                NFT.owner_wallet.in_(fan_wallets),
                StickerTemplate.creator_wallet == creator_wallet,
            )
            .group_by(NFT.owner_wallet)
        )
        for owner_wallet, nft_count in nft_counts_result.all():
            nft_counts_by_fan[owner_wallet] = nft_count or 0

    # Batch-load usernames
    usernames_by_wallet = {}
    if fan_wallets:
        usernames_result = await db.execute(
            select(User.wallet_address, User.username).where(
                User.wallet_address.in_(fan_wallets)
            )
        )
        for wallet_addr, username in usernames_result.all():
            usernames_by_wallet[wallet_addr] = username

    # Build leaderboard
    leaderboard = []
    for rank, row in enumerate(fan_rows, start=1):
        fan_wallet = row[0]
        tip_count = row[1]
        total_algo = round(row[2] / 1_000_000, 6) if row[2] else 0.0
        nft_count = nft_counts_by_fan.get(fan_wallet, 0)
        username = usernames_by_wallet.get(fan_wallet)

        leaderboard.append(
            {
                "rank": rank,
                "fanWallet": fan_wallet,
                "username": username,
                "tipCount": tip_count,
                "totalAlgo": round(total_algo, 6),
                "nftCount": nft_count,
            }
        )

    # Creator summary stats
    total_fans = len(fan_rows)
    total_algo_received = sum(entry["totalAlgo"] for entry in leaderboard)

    return success_response(
        data={
            "creatorWallet": creator_wallet,
            "creatorUsername": creator.username,
            "leaderboard": leaderboard,
        },
        meta={
            "totalFans": total_fans,
            "totalAlgoReceived": round(total_algo_received, 6),
        },
    )


# ── GET /leaderboard/global/top-creators ──────────────────────────

@leaderboard_router.get("/global/top-creators")
async def get_global_top_creators(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Global leaderboard — top creators by total ALGO received.
    """
    cap = min(limit, 100)

    creators_result = await db.execute(
        select(
            Transaction.creator_wallet,
            func.count(Transaction.id).label("tip_count"),
            func.sum(Transaction.amount_micro).label("total_micro"),
            func.count(distinct(Transaction.fan_wallet)).label("unique_fans"),
        ).group_by(Transaction.creator_wallet).order_by(
            desc("total_micro")
        ).limit(cap)
    )
    creator_rows = creators_result.all()

    creator_wallets = [row[0] for row in creator_rows]

    # Batch-load usernames
    usernames_by_wallet = {}
    if creator_wallets:
        usernames_result = await db.execute(
            select(User.wallet_address, User.username).where(
                User.wallet_address.in_(creator_wallets)
            )
        )
        for wallet_addr, username in usernames_result.all():
            usernames_by_wallet[wallet_addr] = username

    # Batch-load active contract app_ids
    app_ids_by_creator = {}
    if creator_wallets:
        contracts_result = await db.execute(
            select(Contract.creator_wallet, Contract.app_id).where(
                Contract.creator_wallet.in_(creator_wallets),
                Contract.active == True,
            )
        )
        for wallet_addr, app_id in contracts_result.all():
            # If multiple active rows somehow exist, the last one wins; that's fine for stats.
            app_ids_by_creator[wallet_addr] = app_id

    leaderboard = []
    for rank, row in enumerate(creator_rows, start=1):
        creator_wallet = row[0]
        username = usernames_by_wallet.get(creator_wallet)
        app_id = app_ids_by_creator.get(creator_wallet)

        leaderboard.append(
            {
                "rank": rank,
                "creatorWallet": creator_wallet,
                "username": username,
                "appId": app_id,
                "tipCount": row[1],
                "totalAlgoReceived": round(float(row[2]) / 1_000_000, 6) if row[2] else 0.0,
                "uniqueFans": row[3],
            }
        )

    return success_response(
        data={"leaderboard": leaderboard},
        meta={"total": len(leaderboard)},
    )
