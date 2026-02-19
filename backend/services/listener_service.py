"""
Transaction Listener Service — polls Algorand Indexer for TipProxy events.

V4 Architecture:
    - Queries Indexer for ApplicationCall txns to all active TipProxy app_ids
    - Parses the structured binary log emitted by TipProxy.tip()
    - Records transactions in the DB
    - Routes tips through the minting pipeline (soulbound/golden/membership)
    - Marks transactions as processed

Log format (from TipProxy.tip()):
    fan_address (32 bytes) + amount (8 bytes uint64 big-endian) + memo (remaining)

This runs as an asyncio background task during the FastAPI app lifespan.

Fixes applied:
    #5:  Listener state persisted to DB (survives restarts)
    #12: Indexer query uses next-token pagination (no missed txns)
    #11: Amounts stored as microAlgos (BigInteger, exact arithmetic)
    #4:  Background retry task for failed mints (dead-letter recovery)
"""
import asyncio
import base64
import json
import logging
import os

from datetime import datetime
from typing import Optional

import httpx
from algosdk import encoding as algo_encoding, mnemonic as algo_mnemonic

from config import settings
from database import async_session
from services.listener_metrics import get_listener_metrics

logger = logging.getLogger(__name__)

# Phase 7: Remaining TODOs (optional enhancements):
# 1. Migrate minting from synchronous (blocks event loop ~4.5s/mint) to task queue:
#    - Option A: Celery + Redis broker (mature, well-documented)
#    - Option B: ARQ (async-native, lighter weight, better for this project)
#    - Listener enqueues mint tasks → workers process independently
# 2. Add heartbeat mechanism — update timestamp every poll cycle
#    - Health endpoint returns "unhealthy" if heartbeat stale (> 2x poll interval)
#    - Auto-restart listener task on detected hang
# 3. Add WebSocket support to push real-time tip notifications to connected frontend clients
# 4. Add retry with exponential backoff for failed Indexer queries (currently linear)
# 5. Add Prometheus metrics: tips_processed_total, mint_duration_seconds, listener_lag_rounds
# END TODO

# ════════════════════════════════════════════════════════════════════
# Demo Mode — Fan Private Key Resolver
# ════════════════════════════════════════════════════════════════════

_demo_accounts_cache: Optional[dict] = None


def _get_demo_fan_key(fan_wallet: str) -> Optional[str]:
    """
    Look up a fan's private key from demo_accounts.json (demo mode only).

    In production (DEMO_MODE=False), always returns None.
    The frontend handles opt-in via Pera Wallet instead.

    Returns:
        Private key string, or None if not found / not in demo mode.
    """
    global _demo_accounts_cache

    if not settings.demo_mode:
        return None

    # Load + cache demo accounts on first call
    if _demo_accounts_cache is None:
        path = settings.demo_accounts_file
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
        try:
            with open(path) as f:
                _demo_accounts_cache = json.load(f)
            logger.info(f"  Demo accounts loaded from {path}")
        except FileNotFoundError:
            logger.warning(f"  Demo accounts file not found: {path}")
            _demo_accounts_cache = {}
            return None

    # Search all accounts for a matching wallet address
    for label, acct in _demo_accounts_cache.items():
        if acct.get("address") == fan_wallet and acct.get("mnemonic"):
            try:
                return algo_mnemonic.to_private_key(acct["mnemonic"])
            except Exception:
                return None

    return None

# Listener state
_listener_task: Optional[asyncio.Task] = None
_retry_task: Optional[asyncio.Task] = None
_is_running: bool = False
_errors_count: int = 0

# In-memory cache of last round (DB is source of truth)
_last_processed_round: int = 0

# Periodic membership expiry cleanup (Phase 3)
_last_membership_expiry_cleanup: Optional[datetime] = None


# ════════════════════════════════════════════════════════════════════
# Persistent State — Fix #5
# ════════════════════════════════════════════════════════════════════


async def _load_last_round() -> int:
    """Load last processed round from DB. Returns 0 if no state exists."""
    from db_models import ListenerState
    from sqlalchemy import select

    async with async_session() as db:
        result = await db.execute(select(ListenerState).where(ListenerState.id == 1))
        state = result.scalar_one_or_none()
        if state:
            return state.last_processed_round
    return 0


async def _save_last_round(round_num: int):
    """Persist last processed round to DB."""
    from db_models import ListenerState
    from sqlalchemy import select

    async with async_session() as db:
        result = await db.execute(select(ListenerState).where(ListenerState.id == 1))
        state = result.scalar_one_or_none()
        if state:
            state.last_processed_round = round_num
            state.updated_at = datetime.utcnow()
        else:
            state = ListenerState(id=1, last_processed_round=round_num)
            db.add(state)
        await db.commit()


# ════════════════════════════════════════════════════════════════════
# Indexer Client — Fix #12: Pagination
# ════════════════════════════════════════════════════════════════════


async def _query_indexer(
    app_id: int,
    min_round: int,
) -> list:
    """
    Query Algorand Indexer for ApplicationCall transactions to a specific app.

    Uses the /v2/transactions endpoint with application-id and min-round filters.
    Follows next-token pagination to ensure no transactions are missed when
    more results exist than fit in a single page.

    Phase 7: Exponential backoff retry on transient failures.

    Args:
        app_id: TipProxy application ID
        min_round: Minimum round to search from

    Returns:
        List of transaction dicts from the Indexer
    """
    url = f"{settings.algorand_indexer_url}/v2/transactions"
    base_params = {
        "application-id": app_id,
        "tx-type": "appl",
        "min-round": min_round,
    }

    all_transactions = []
    next_token = None
    max_retries = 4
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                while True:
                    params = {**base_params}
                    if next_token:
                        params["next"] = next_token

                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    txns = data.get("transactions", [])
                    all_transactions.extend(txns)

                    # Check for more pages
                    next_token = data.get("next-token")
                    if not next_token or not txns:
                        break

                    # Safety: cap at 1000 txns per cycle to prevent runaway loops
                    if len(all_transactions) >= 1000:
                        logger.warning(
                            f"Indexer pagination cap reached for app {app_id} "
                            f"({len(all_transactions)} txns). Remaining will be caught next cycle."
                        )
                        break

            return all_transactions

        except Exception as e:
            get_listener_metrics().record_indexer_error()
            is_transient = isinstance(
                e,
                (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout, ConnectionError),
            )
            if attempt < max_retries - 1 and is_transient:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Indexer query failed for app {app_id} (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                all_transactions = []
                next_token = None
            else:
                logger.warning(f"Indexer query failed for app {app_id}: {e}")
                return all_transactions

    return all_transactions


# ════════════════════════════════════════════════════════════════════
# Log Parser
# ════════════════════════════════════════════════════════════════════


def parse_tip_log(txn: dict) -> Optional[dict]:
    """
    Parse the binary log emitted by TipProxy.tip().

    Log format:
        fan_address  — 32 bytes (raw Algorand public key)
        amount       — 8 bytes (uint64, big-endian, in microAlgos)
        memo         — remaining bytes (UTF-8 string)

    Args:
        txn: Transaction dict from the Indexer

    Returns:
        dict: {fan_wallet, amount_micro, memo} or None
    """
    logs = txn.get("logs", [])
    if not logs:
        return None

    try:
        raw = base64.b64decode(logs[0])
    except Exception:
        return None

    # Minimum: 32 (address) + 8 (uint64) = 40 bytes
    if len(raw) < 40:
        return None

    fan_address_bytes = raw[:32]
    amount_micro = int.from_bytes(raw[32:40], "big")
    memo_bytes = raw[40:]

    try:
        fan_wallet = algo_encoding.encode_address(fan_address_bytes)
    except Exception:
        return None

    return {
        "fan_wallet": fan_wallet,
        "amount_micro": amount_micro,
        "memo": memo_bytes.decode("utf-8", errors="ignore"),
    }


# ════════════════════════════════════════════════════════════════════
# Minting Pipeline
# ════════════════════════════════════════════════════════════════════


async def route_tip(tx_record, db):
    """
    Route a verified tip through the structured NFT utility pipeline.

    Three NFT types with distinct behavior:

    BUTKI (Loyalty Badge):
        - >= 0.5 ALGO tip qualifies for loyalty increment
        - Every 5th tip earns 1 Butki badge NFT (soulbound)
        - Badge count is per creator (not global)

    BAUNI (Membership NFT):
        - Triggered by MEMBERSHIP:BAUNI memo with >= 5 ALGO
        - Non-transferable (soulbound), 30-day validity
        - Renewal extends expiry by +30 days
        - Expired NFTs automatically revoke access

    SHAWTY (Transactional Utility NFT):
        - Triggered by PURCHASE:SHAWTY memo with >= 2 ALGO
        - Transferable (golden), no expiration
        - Can be burned for merch or locked for discount

    Args:
        tx_record: Transaction DB record
        db: AsyncSession
    """
    from db_models import StickerTemplate, NFT
    from services import nft_service
    from services import butki_service, bauni_service, shawty_service, merch_service
    from sqlalchemy import select

    memo = tx_record.memo or ""
    creator_wallet = tx_record.creator_wallet
    fan_wallet = tx_record.fan_wallet
    amount_micro = tx_record.amount_micro
    amount_algo = amount_micro / 1_000_000
    memo_upper = memo.strip().upper()

    # ── Path 0: MERCH ORDER settlement (does not short-circuit other rewards) ──
    from domain.constants import MEMO_ORDER_PREFIX, MEMO_BAUNI_PREFIX, MEMO_SHAWTY_PREFIX

    if memo_upper.startswith(MEMO_ORDER_PREFIX):
        try:
            order_id_str = memo_upper.split(MEMO_ORDER_PREFIX)[1].split()[0]
            order_id = int(order_id_str)
        except Exception:
            order_id = None

        if order_id is not None:
            settled = await merch_service.settle_order_payment(
                db=db,
                order_id=order_id,
                fan_wallet=fan_wallet,
                creator_wallet=creator_wallet,
                amount_algo=amount_algo,
                tx_id=tx_record.tx_id,
            )
            if settled:
                logger.info(
                    f"  [MERCH] Order {order_id} settled from tip {tx_record.tx_id} "
                    f"({amount_algo:.2f} ALGO)"
                )

    # ── Path 1: BAUNI Membership Purchase ──────────────────────
    # Triggered by memo "MEMBERSHIP:BAUNI" with >= 5 ALGO
    if memo_upper.startswith(MEMO_BAUNI_PREFIX):
        # Idempotency: if this tip tx already created a membership, do nothing
        try:
            from db_models import Membership
            existing_membership = await db.execute(
                select(Membership).where(Membership.purchase_tx_id == tx_record.tx_id)
            )
            if existing_membership.scalar_one_or_none():
                logger.info(f"  Bauni: already processed tx {tx_record.tx_id}, skipping")
                return
        except Exception:
            # Best-effort; if the check fails, proceed and rely on DB constraints downstream
            pass

        if amount_algo < bauni_service.BAUNI_COST_ALGO:
            logger.warning(
                f"  Bauni: insufficient amount {amount_algo:.2f} ALGO "
                f"(need {bauni_service.BAUNI_COST_ALGO}) from {fan_wallet[:8]}..."
            )
            return

        # Find Bauni template
        result = await db.execute(
            select(StickerTemplate).where(
                StickerTemplate.creator_wallet == creator_wallet,
                StickerTemplate.category == "bauni_membership",
            )
        )
        template = result.scalar_one_or_none()

        if not template or not template.metadata_url:
            logger.warning(f"  Bauni: no template found for creator {creator_wallet[:8]}...")
            return

        try:
            asset_id = await nft_service.mint_soulbound_sticker_async(
                name=template.name[:32],
                metadata_url=template.metadata_url,
                unit_name="BAUNI",
            )

            nft = NFT(
                asset_id=asset_id,
                template_id=template.id,
                owner_wallet=fan_wallet,
                sticker_type="soulbound",
                nft_class="bauni",
            )
            db.add(nft)

            # Transfer to fan (Phase 7: async to avoid blocking event loop)
            try:
                fan_pk = _get_demo_fan_key(fan_wallet)
                xfer = await nft_service.send_nft_to_fan_async(asset_id, fan_wallet, fan_private_key=fan_pk)
                nft.tx_id = xfer["tx_id"]
                nft.delivery_status = xfer["status"]
            except Exception as e:
                nft.delivery_status = "failed"
                logger.warning(f"Bauni transfer failed: {e}")

            # Record membership (handles renewal logic)
            membership_result = await bauni_service.purchase_membership(
                db=db,
                fan_wallet=fan_wallet,
                creator_wallet=creator_wallet,
                asset_id=asset_id,
                purchase_tx_id=tx_record.tx_id,
                amount_paid_micro=amount_micro,
            )

            nft.expires_at = membership_result["expires_at"]
            renewal_str = "RENEWAL" if membership_result["is_renewal"] else "NEW"
            logger.info(
                f"  [BAUNI {renewal_str}] Membership minted for {fan_wallet[:8]}... "
                f"(ASA: {asset_id}, expires: {membership_result['expires_at'].isoformat()})"
            )
        except Exception as e:
            logger.error(f"Bauni mint failed: {e}")
            raise
        return

    # ── Path 2: SHAWTY Store Purchase ──────────────────────────
    # Triggered by memo "PURCHASE:SHAWTY" with >= 2 ALGO
    if memo_upper.startswith(MEMO_SHAWTY_PREFIX):
        # Idempotency: if this tip tx already registered a token, do nothing
        try:
            from db_models import ShawtyToken
            existing_token = await db.execute(
                select(ShawtyToken).where(ShawtyToken.purchase_tx_id == tx_record.tx_id)
            )
            if existing_token.scalar_one_or_none():
                logger.info(f"  Shawty: already processed tx {tx_record.tx_id}, skipping")
                return
        except Exception:
            pass

        if amount_algo < shawty_service.SHAWTY_COST_ALGO:
            logger.warning(
                f"  Shawty: insufficient amount {amount_algo:.2f} ALGO "
                f"(need {shawty_service.SHAWTY_COST_ALGO}) from {fan_wallet[:8]}..."
            )
            return

        # Find Shawty template
        result = await db.execute(
            select(StickerTemplate).where(
                StickerTemplate.creator_wallet == creator_wallet,
                StickerTemplate.category == "shawty_collectible",
            )
        )
        template = result.scalar_one_or_none()

        if not template or not template.metadata_url:
            logger.warning(f"  Shawty: no template found for creator {creator_wallet[:8]}...")
            return

        try:
            asset_id = await nft_service.mint_golden_sticker_async(
                name=template.name[:32],
                metadata_url=template.metadata_url,
                unit_name="SHAWTY",
            )

            nft = NFT(
                asset_id=asset_id,
                template_id=template.id,
                owner_wallet=fan_wallet,
                sticker_type="golden",
                nft_class="shawty",
            )
            db.add(nft)

            # Transfer to fan (Phase 7: async)
            try:
                fan_pk = _get_demo_fan_key(fan_wallet)
                xfer = await nft_service.send_nft_to_fan_async(asset_id, fan_wallet, fan_private_key=fan_pk)
                nft.tx_id = xfer["tx_id"]
                nft.delivery_status = xfer["status"]
            except Exception as e:
                nft.delivery_status = "failed"
                logger.warning(f"Shawty transfer failed: {e}")

            # Register in Shawty tracking table
            await shawty_service.register_purchase(
                db=db,
                asset_id=asset_id,
                owner_wallet=fan_wallet,
                creator_wallet=creator_wallet,
                purchase_tx_id=tx_record.tx_id,
                amount_paid_micro=amount_micro,
            )

            logger.info(
                f"  [SHAWTY] Golden collectible minted for {fan_wallet[:8]}... "
                f"(ASA: {asset_id}, cost: {amount_algo:.2f} ALGO)"
            )
        except Exception as e:
            logger.error(f"Shawty mint failed: {e}")
            raise
        return

    # ── Path 3: BUTKI Loyalty Tip (default for regular tips) ───
    # Any tip >= 0.5 ALGO increments the fan's loyalty counter.
    # Every 5th tip earns a Butki loyalty badge NFT.
    if amount_algo < butki_service.BUTKI_MIN_TIP_ALGO:
        logger.debug(
            f"  Tip {amount_algo:.2f} ALGO below Butki threshold "
            f"({butki_service.BUTKI_MIN_TIP_ALGO} ALGO) from {fan_wallet[:8]}..."
        )
        return

    # Record tip and check if badge earned
    loyalty_result = await butki_service.record_tip(
        db=db,
        fan_wallet=fan_wallet,
        creator_wallet=creator_wallet,
        tx_id=tx_record.tx_id,
        amount_micro=amount_micro,
    )

    tip_count = loyalty_result["tip_count"]
    earned_badge = loyalty_result["earned_badge"]

    logger.info(
        f"  [BUTKI] tip #{tip_count} from {fan_wallet[:8]}... "
        f"({amount_algo:.2f} ALGO)"
    )

    # Mint a Butki badge only on every 5th tip
    if earned_badge:
        result = await db.execute(
            select(StickerTemplate).where(
                StickerTemplate.creator_wallet == creator_wallet,
                StickerTemplate.category == "butki_badge",
            )
        )
        butki_template = result.scalar_one_or_none()

        if butki_template and butki_template.metadata_url:
            try:
                badge_number = loyalty_result["badges_total"]
                asset_id = await nft_service.mint_soulbound_sticker_async(
                    name=f"Butki Badge #{badge_number}"[:32],
                    metadata_url=butki_template.metadata_url,
                    unit_name="BUTKI",
                )
                nft = NFT(
                    asset_id=asset_id,
                    template_id=butki_template.id,
                    owner_wallet=fan_wallet,
                    sticker_type="soulbound",
                    nft_class="butki",
                )
                db.add(nft)

                try:
                    fan_pk = _get_demo_fan_key(fan_wallet)
                    xfer = await nft_service.send_nft_to_fan_async(asset_id, fan_wallet, fan_private_key=fan_pk)
                    nft.tx_id = xfer["tx_id"]
                    nft.delivery_status = xfer["status"]
                except Exception as e:
                    nft.delivery_status = "failed"
                    logger.warning(f"Butki badge transfer failed: {e}")

                # Store asset ID in loyalty record
                await butki_service.record_badge_asset(
                    db=db,
                    fan_wallet=fan_wallet,
                    creator_wallet=creator_wallet,
                    asset_id=asset_id,
                )

                logger.info(
                    f"  🏆 [BUTKI BADGE #{badge_number}] "
                    f"Minted for {fan_wallet[:8]}... (ASA: {asset_id}, tip #{tip_count})"
                )
            except Exception as e:
                logger.error(f"Butki badge mint failed: {e}")
                raise
        else:
            logger.warning(
                f"  No Butki badge template for creator {creator_wallet[:8]}... — "
                f"badge earned at tip #{tip_count} but not minted"
            )


# ════════════════════════════════════════════════════════════════════
# Retry Task — Fix #4: Dead-letter recovery for failed mints
# ════════════════════════════════════════════════════════════════════

MAX_RETRY_ATTEMPTS = 3
# Phase 7: Exponential backoff base (60, 120, 240 seconds)
RETRY_BASE_SECONDS = 60
RETRY_MAX_SECONDS = 300


def _retry_delay_for_attempt(attempt: int) -> float:
    """Exponential backoff: 60s, 120s, 240s (capped at RETRY_MAX_SECONDS)."""
    return min(RETRY_BASE_SECONDS * (2**attempt), RETRY_MAX_SECONDS)


def _is_transient_error(e: Exception) -> bool:
    """Classify as transient (retry) vs permanent (give up)."""
    err_str = str(e).lower()
    transient_keywords = ("timeout", "connection", "network", "unavailable", "503", "502")
    return any(kw in err_str for kw in transient_keywords)


async def _retry_failed_mints():
    """
    Background task that periodically retries failed mint operations.

    Scans for transactions where processed=False (minting failed) and
    retries the minting pipeline up to MAX_RETRY_ATTEMPTS times.
    After max attempts, marks as processed with a logged error to
    prevent infinite retry loops.
    """
    from db_models import Transaction
    from sqlalchemy import select

    logger.info(f"Retry task started (exponential backoff, max {MAX_RETRY_ATTEMPTS} attempts)")

    cycle = 0
    while _is_running:
        try:
            delay = _retry_delay_for_attempt(min(cycle // 3, 2))  # 0,1,2 -> 60s; 3,4,5 -> 120s; 6+ -> 240s
            await asyncio.sleep(delay)
            cycle += 1

            async with async_session() as db:
                # Find unprocessed transactions (failed mints)
                result = await db.execute(
                    select(Transaction).where(
                        Transaction.processed == False
                    ).limit(10)  # Process in small batches
                )
                failed_txns = result.scalars().all()

                if not failed_txns:
                    continue

                logger.info(f"  Retrying {len(failed_txns)} failed mint(s)...")

                for tx_record in failed_txns:
                    # Track retry count via memo prefix (lightweight approach)
                    retry_count = _get_retry_count(tx_record)

                    if retry_count >= MAX_RETRY_ATTEMPTS:
                        tx_record.processed = True  # Give up — prevent infinite loop
                        get_listener_metrics().record_retry_fail()
                        logger.error(
                            f"  ABANDONED: tx {tx_record.tx_id} failed after "
                            f"{MAX_RETRY_ATTEMPTS} retries. Fan {tx_record.fan_wallet[:8]}... "
                            f"tipped {tx_record.amount_micro / 1_000_000:.2f} ALGO but "
                            f"never received NFT. Manual intervention required."
                        )
                        continue

                    try:
                        await route_tip(tx_record, db)
                        tx_record.processed = True
                        get_listener_metrics().record_retry_success()
                        logger.info(
                            f"  Retry SUCCESS: tx {tx_record.tx_id} "
                            f"(attempt {retry_count + 1})"
                        )
                    except Exception as e:
                        get_listener_metrics().record_retry_fail()
                        if not _is_transient_error(e) and retry_count >= 1:
                            tx_record.processed = True
                            logger.error(
                                f"  Permanent error on tx {tx_record.tx_id}, abandoning: {e}"
                            )
                        else:
                            _increment_retry_count(tx_record)
                            logger.warning(
                                f"  Retry FAILED: tx {tx_record.tx_id} "
                                f"(attempt {retry_count + 1}/{MAX_RETRY_ATTEMPTS}): {e}"
                            )

                await db.commit()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Retry task error: {e}")


def _get_retry_count(tx_record) -> int:
    """Extract retry count from memo (stored as __RETRY:N suffix)."""
    memo = tx_record.memo or ""
    if "__RETRY:" in memo:
        try:
            return int(memo.split("__RETRY:")[-1])
        except (ValueError, IndexError):
            return 0
    return 0


def _increment_retry_count(tx_record):
    """Increment the retry counter stored in the memo field."""
    memo = tx_record.memo or ""
    current = _get_retry_count(tx_record)
    if "__RETRY:" in memo:
        # Replace existing count
        prefix = memo.split("__RETRY:")[0]
        tx_record.memo = f"{prefix}__RETRY:{current + 1}"
    else:
        tx_record.memo = f"{memo}__RETRY:{current + 1}"


# ════════════════════════════════════════════════════════════════════
# Main Listener Loop
# ════════════════════════════════════════════════════════════════════


async def _listener_loop():
    """
    Main polling loop. Runs forever as a background asyncio task.

    Each cycle:
    1. Gets all active TipProxy app_ids from DB
    2. Queries Indexer for new ApplicationCall txns since last_round
    3. Parses tip logs and deduplicates against DB
    4. Routes new tips through the minting pipeline
    5. Persists last_processed_round to DB (survives restarts)
    """
    global _last_processed_round, _is_running, _errors_count

    from db_models import Contract, Transaction
    from sqlalchemy import select

    _is_running = True
    poll_interval = settings.listener_poll_seconds

    # Fix #5: Load persisted round from DB instead of starting at 0
    _last_processed_round = await _load_last_round()

    logger.info(
        f"Listener started (polling every {poll_interval}s, "
        f"resuming from round {_last_processed_round})"
    )

    while _is_running:
        try:
            await asyncio.sleep(poll_interval)

            async with async_session() as db:
                # Phase 3: periodic membership expiry cleanup (best-effort)
                try:
                    global _last_membership_expiry_cleanup
                    now = datetime.utcnow()
                    if (
                        _last_membership_expiry_cleanup is None
                        or (now - _last_membership_expiry_cleanup).total_seconds() >= 300
                    ):
                        from services import bauni_service
                        expired_count = await bauni_service.expire_memberships(db)
                        if expired_count:
                            logger.info(f"  Bauni expiry cleanup: expired {expired_count} membership(s)")
                        _last_membership_expiry_cleanup = now
                except Exception as e:
                    logger.debug(f"Membership expiry cleanup skipped: {e}")

                # Get all active TipProxy contracts
                result = await db.execute(
                    select(Contract).where(Contract.active == True)
                )
                active_contracts = result.scalars().all()

                if not active_contracts:
                    continue  # no contracts to monitor

                new_tip_count = 0
                max_round_seen = _last_processed_round

                for contract in active_contracts:
                    # Query Indexer for new txns (with pagination — Fix #12)
                    txns = await _query_indexer(
                        app_id=contract.app_id,
                        min_round=_last_processed_round,
                    )

                    for txn in txns:
                        tx_id = txn.get("id")
                        if not tx_id:
                            continue

                        # Track the highest round we've seen
                        txn_round = txn.get("confirmed-round", 0)
                        if txn_round > max_round_seen:
                            max_round_seen = txn_round

                        # Deduplication: skip if already recorded
                        existing = await db.execute(
                            select(Transaction).where(Transaction.tx_id == tx_id)
                        )
                        if existing.scalar_one_or_none():
                            continue

                        # Parse the TipProxy log
                        log_data = parse_tip_log(txn)
                        if not log_data:
                            continue  # not a tip() call (e.g., pause/unpause)

                        # Record transaction row first, so failures still leave processed=False for retry task
                        tx_record = Transaction(
                            tx_id=tx_id,
                            fan_wallet=log_data["fan_wallet"],
                            creator_wallet=contract.creator_wallet,
                            app_id=contract.app_id,
                            amount_micro=log_data["amount_micro"],
                            memo=log_data["memo"],
                            processed=False,
                        )
                        db.add(tx_record)
                        try:
                            await db.flush()
                        except Exception:
                            # Most commonly a unique constraint race; skip and continue.
                            continue

                        # Process downstream actions inside a SAVEPOINT.
                        # If minting fails, we keep the Transaction row and leave processed=False.
                        try:
                            async with db.begin_nested():
                                await route_tip(tx_record, db)
                                tx_record.processed = True
                            get_listener_metrics().record_tip_processed()
                        except Exception as e:
                            get_listener_metrics().record_mint_failed()
                            logger.error(f"Minting pipeline error for tx {tx_id}: {e}")
                            # Leave processed=False for retry task.

                        new_tip_count += 1

                # Commit all changes for this cycle
                await db.commit()

                # Fix #5: Persist last processed round to DB
                if max_round_seen > _last_processed_round:
                    _last_processed_round = max_round_seen
                    await _save_last_round(max_round_seen)

                # Phase 7: Metrics + listener lag (fetch current round from algod)
                m = get_listener_metrics()
                m.set_last_round(_last_processed_round)
                m.heartbeat()
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        r = await client.get(f"{settings.algorand_algod_address}/v2/status")
                        if r.status_code == 200:
                            data = r.json()
                            m.current_round = data.get("last-round")
                except Exception:
                    pass

                if new_tip_count > 0:
                    logger.info(
                        f"  Listener processed {new_tip_count} new tip(s) "
                        f"(round -> {_last_processed_round})"
                    )

        except asyncio.CancelledError:
            logger.info("Listener cancelled")
            break
        except Exception as e:
            _errors_count += 1
            logger.error(f"Listener cycle error: {e}")
            # Backoff on repeated errors
            if _errors_count > 5:
                backoff = min(60, poll_interval * 2)
                logger.warning(f"  Too many errors, backing off {backoff}s")
                await asyncio.sleep(backoff)

    _is_running = False
    logger.info("Listener stopped")


# ════════════════════════════════════════════════════════════════════
# Public API — Start / Stop / Status
# ════════════════════════════════════════════════════════════════════


async def start():
    """Start the listener and retry task as background asyncio tasks."""
    global _listener_task, _retry_task, _is_running
    _is_running = True

    if _listener_task and not _listener_task.done():
        logger.warning("Listener already running")
        return

    _listener_task = asyncio.create_task(_listener_loop())
    _retry_task = asyncio.create_task(_retry_failed_mints())
    logger.info("Listener + retry tasks created")


async def stop():
    """Stop the listener and retry task gracefully."""
    global _listener_task, _retry_task, _is_running
    _is_running = False

    for task in [_listener_task, _retry_task]:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    _listener_task = None
    _retry_task = None
    logger.info("Listener + retry tasks stopped")


def get_status() -> dict:
    """Get listener status for the /listener/status endpoint."""
    base = {
        "running": _is_running,
        "lastProcessedRound": _last_processed_round,
        "errorsCount": _errors_count,
        "pollIntervalSeconds": settings.listener_poll_seconds,
        "retryEnabled": True,
        "maxRetryAttempts": MAX_RETRY_ATTEMPTS,
    }
    try:
        base["metrics"] = get_listener_metrics().to_dict()
    except Exception:
        base["metrics"] = {}
    return base
