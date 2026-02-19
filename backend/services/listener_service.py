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

logger = logging.getLogger(__name__)

# TODO FOR JULES:
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

    except Exception as e:
        logger.warning(f"Indexer query failed for app {app_id}: {e}")

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
    Route a verified tip through the minting pipeline.

    Decision tree:
    1. If memo starts with MEMBERSHIP:*, try membership sticker
    2. Otherwise, find matching tip template (by amount threshold)
    3. Run golden probability check -> maybe mint golden too

    Args:
        tx_record: Transaction DB record
        db: AsyncSession
    """
    from db_models import StickerTemplate, NFT
    from services import membership_service, probability_service, nft_service
    from sqlalchemy import select

    memo = tx_record.memo or ""
    creator_wallet = tx_record.creator_wallet
    fan_wallet = tx_record.fan_wallet
    amount_micro = tx_record.amount_micro
    amount_algo = amount_micro / 1_000_000  # Convert for threshold comparison

    # ── Path 1: Membership sticker ─────────────────────────────
    if membership_service.is_membership_memo(memo):
        tier = membership_service.get_tier(memo)
        if tier and amount_algo >= tier["min_algo"]:
            # Find matching membership template
            result = await db.execute(
                select(StickerTemplate).where(
                    StickerTemplate.creator_wallet == creator_wallet,
                    StickerTemplate.category == tier["category"],
                )
            )
            template = result.scalar_one_or_none()

            if template and template.metadata_url:
                try:
                    asset_id = nft_service.mint_soulbound_sticker(
                        name=template.name[:32],
                        metadata_url=template.metadata_url,
                    )
                    nft = NFT(
                        asset_id=asset_id,
                        template_id=template.id,
                        owner_wallet=fan_wallet,
                        sticker_type="soulbound",
                        expires_at=membership_service.calculate_expiry(tier),
                    )
                    db.add(nft)

                    # Transfer to fan (auto opt-in only in demo mode)
                    try:
                        fan_pk = _get_demo_fan_key(fan_wallet)
                        result = nft_service.send_nft_to_fan(asset_id, fan_wallet, fan_private_key=fan_pk)
                        nft.tx_id = result["tx_id"]
                        nft.delivery_status = result["status"]
                    except Exception as e:
                        nft.delivery_status = "failed"
                        logger.warning(f"Membership NFT transfer failed: {e}")

                    logger.info(
                        f"  Membership sticker minted: {membership_service.get_tier_name(memo)} "
                        f"for {fan_wallet[:8]}... (Asset: {asset_id})"
                    )
                except Exception as e:
                    logger.error(f"Membership mint failed: {e}")
        return  # membership tips don't also trigger normal stickers

    # ── Path 2: Regular tip sticker (threshold-based) ─────────────
    # Find the best matching tip template: highest threshold the tip meets.
    # Tip thresholds are stored in ALGO (Float), so we compare with amount_algo.
    result = await db.execute(
        select(StickerTemplate).where(
            StickerTemplate.creator_wallet == creator_wallet,
            StickerTemplate.category == "tip",
            StickerTemplate.tip_threshold <= amount_algo,
        ).order_by(StickerTemplate.tip_threshold.desc())
    )
    tip_template = result.scalars().first()

    if tip_template and tip_template.metadata_url:
        is_golden = tip_template.sticker_type == "golden"

        try:
            if is_golden:
                asset_id = nft_service.mint_golden_sticker(
                    name=tip_template.name[:32],
                    metadata_url=tip_template.metadata_url,
                )
            else:
                asset_id = nft_service.mint_soulbound_sticker(
                    name=tip_template.name[:32],
                    metadata_url=tip_template.metadata_url,
                )

            nft = NFT(
                asset_id=asset_id,
                template_id=tip_template.id,
                owner_wallet=fan_wallet,
                sticker_type=tip_template.sticker_type,
            )
            db.add(nft)

            try:
                fan_pk = _get_demo_fan_key(fan_wallet)
                result = nft_service.send_nft_to_fan(asset_id, fan_wallet, fan_private_key=fan_pk)
                nft.tx_id = result["tx_id"]
                nft.delivery_status = result["status"]
            except Exception as e:
                nft.delivery_status = "failed"
                logger.warning(f"Tip NFT transfer failed: {e}")

            emoji = "* " if is_golden else "# "
            logger.info(
                f"  {emoji} Tip sticker minted: '{tip_template.name}' "
                f"({tip_template.sticker_type}) for {fan_wallet[:8]}... "
                f"({amount_algo:.2f} ALGO -> threshold {tip_template.tip_threshold})"
            )
        except Exception as e:
            logger.error(f"Tip sticker mint failed: {e}")

    # ── Path 3: Rare sticker probability check (RESERVED) ───────
    # This path is reserved for a future "rare collection" feature.
    # When enabled, rare stickers will be minted based on probability
    # (separate from the threshold-based tip stickers above).
    # The probability_service is still available for this purpose.
    #
    # To enable: create templates with category="rare" and use
    # probability_service.should_mint_golden() to decide.


# ════════════════════════════════════════════════════════════════════
# Retry Task — Fix #4: Dead-letter recovery for failed mints
# ════════════════════════════════════════════════════════════════════

MAX_RETRY_ATTEMPTS = 3
RETRY_INTERVAL_SECONDS = 60  # Check for failed mints every 60 seconds


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

    logger.info(f"Retry task started (checking every {RETRY_INTERVAL_SECONDS}s, max {MAX_RETRY_ATTEMPTS} attempts)")

    while _is_running:
        try:
            await asyncio.sleep(RETRY_INTERVAL_SECONDS)

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
                        logger.info(
                            f"  Retry SUCCESS: tx {tx_record.tx_id} "
                            f"(attempt {retry_count + 1})"
                        )
                    except Exception as e:
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
                            select(Transaction).where(
                                Transaction.tx_id == tx_id
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue

                        # Parse the TipProxy log
                        log_data = parse_tip_log(txn)
                        if not log_data:
                            continue  # not a tip() call (e.g., pause/unpause)

                        # Record transaction (Fix #11: store microAlgos as integer)
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
                        await db.flush()  # get ID before routing

                        # Route through minting pipeline
                        try:
                            await route_tip(tx_record, db)
                            tx_record.processed = True
                        except Exception as e:
                            logger.error(
                                f"Minting pipeline error for tx {tx_id}: {e}"
                            )
                            # Leave processed=False for retry task (Fix #4)

                        new_tip_count += 1

                # Commit all changes for this cycle
                await db.commit()

                # Fix #5: Persist last processed round to DB
                if max_round_seen > _last_processed_round:
                    _last_processed_round = max_round_seen
                    await _save_last_round(max_round_seen)

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
    return {
        "running": _is_running,
        "lastProcessedRound": _last_processed_round,
        "errorsCount": _errors_count,
        "pollIntervalSeconds": settings.listener_poll_seconds,
        "retryEnabled": True,
        "maxRetryAttempts": MAX_RETRY_ATTEMPTS,
    }
