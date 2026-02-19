"""
Transaction service — handles base64 processing, submission, and error classification.
"""
import base64
import hashlib
import logging
from datetime import datetime, timedelta

from algorand_client import algorand_client

logger = logging.getLogger(__name__)

# TODO FOR JULES:
# 1. Add type safety — use Pydantic models for all inputs/outputs instead of raw strings
# 2. Add wait_for_confirmation() wrapper with configurable timeout + retry
#    - Currently the frontend has no way to know if a txn was confirmed
#    - Return confirmed round number and asset-id (for NFT mints)
# 3. Add idempotency key support to prevent duplicate submissions:
#    - Accept optional X-Idempotency-Key header
#    - Cache recent tx_ids by idempotency key (5-min TTL)
#    - Return cached result on duplicate key instead of resubmitting
# 4. Add atomic group validation — verify group ID matches across all txns before submission
# 5. Add transaction simulation (algod.dryrun) before submission to catch errors early
# END TODO


_IDEMPOTENCY_TTL = timedelta(minutes=5)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def _idempotency_get_db(db, *, key: str) -> str | None:
    from sqlalchemy import select, delete
    from db_models import SubmittedTransaction

    now = datetime.utcnow()
    res = await db.execute(
        select(SubmittedTransaction).where(SubmittedTransaction.idempotency_key == key)
    )
    row = res.scalar_one_or_none()
    if not row:
        return None
    if row.expires_at <= now:
        await db.execute(delete(SubmittedTransaction).where(SubmittedTransaction.id == row.id))
        return None
    return row.tx_id


async def _idempotency_set_db(
    db,
    *,
    key: str,
    tx_id: str,
    request_hash: str | None,
    kind: str,
) -> None:
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError
    from db_models import SubmittedTransaction

    now = datetime.utcnow()
    row = SubmittedTransaction(
        idempotency_key=key,
        tx_id=tx_id,
        request_hash=request_hash,
        kind=kind,
        status="submitted",
        created_at=now,
        expires_at=now + _IDEMPOTENCY_TTL,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError:
        # Race: another request stored it first. Keep the first tx_id.
        existing = await db.execute(
            select(SubmittedTransaction).where(SubmittedTransaction.idempotency_key == key)
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row:
            return
        raise


def fix_base64_padding(b64_str: str) -> str:
    """Ensure proper base64 padding (must be multiple of 4)."""
    padding_needed = len(b64_str) % 4
    if padding_needed:
        b64_str += '=' * (4 - padding_needed)
    return b64_str


def validate_base64(b64_str: str) -> bytes:
    """Validate and decode a base64 string. Returns raw bytes."""
    padded = fix_base64_padding(b64_str)
    try:
        decoded = base64.b64decode(padded)
        return decoded
    except Exception as e:
        raise ValueError(f"Invalid base64 encoding: {e}")


async def submit_single(db, signed_txn_b64: str, *, idempotency_key: str | None = None) -> str:
    """
    Submit a single signed transaction to Algorand TestNet.

    Args:
        signed_txn_b64: Base64-encoded signed transaction

    Returns:
        Transaction ID from the network
    """
    if idempotency_key:
        cached = await _idempotency_get_db(db, key=idempotency_key)
        if cached:
            return cached

    b64_str = fix_base64_padding(signed_txn_b64)

    # Validate
    decoded = validate_base64(b64_str)
    request_hash = _sha256_hex(decoded)
    logger.info(f"Submitting single txn: {len(decoded)} bytes")

    # send_raw_transaction expects base64 string (it decodes internally)
    tx_id = algorand_client.client.send_raw_transaction(b64_str)
    logger.info(f"Transaction submitted: {tx_id}")
    if idempotency_key:
        await _idempotency_set_db(
            db,
            key=idempotency_key,
            tx_id=tx_id,
            request_hash=request_hash,
            kind="single",
        )
    return tx_id


async def submit_group(db, signed_txns_b64: list[str], *, idempotency_key: str | None = None) -> str:
    """
    Submit an atomic group of signed transactions.

    Args:
        signed_txns_b64: List of base64-encoded signed transactions

    Returns:
        First transaction ID from the group
    """
    if idempotency_key:
        cached = await _idempotency_get_db(db, key=idempotency_key)
        if cached:
            return cached

    logger.info(f"Submitting transaction group ({len(signed_txns_b64)} txns)")

    # Decode and concatenate all signed transaction bytes
    all_bytes = []
    for i, txn_b64 in enumerate(signed_txns_b64):
        txn_bytes = validate_base64(txn_b64)
        all_bytes.append(txn_bytes)
        logger.info(f"  Txn {i}: {len(txn_bytes)} bytes")

    combined = b''.join(all_bytes)
    combined_b64 = base64.b64encode(combined).decode()
    request_hash = _sha256_hex(combined)

    tx_id = algorand_client.client.send_raw_transaction(combined_b64)
    logger.info(f"Group submitted: {tx_id}")
    if idempotency_key:
        await _idempotency_set_db(
            db,
            key=idempotency_key,
            tx_id=tx_id,
            request_hash=request_hash,
            kind="group",
        )
    return tx_id


def classify_error(error_msg: str) -> tuple[int, str]:
    """
    Classify a transaction error into HTTP status code and user-friendly message.

    Returns:
        Tuple of (status_code, detail_message)
    """
    lower = error_msg.lower()

    if "insufficient balance" in lower or "below min" in lower:
        return 400, "Insufficient balance for this transaction"
    elif "invalid signature" in lower:
        return 400, "Invalid transaction signature"
    elif "already in ledger" in lower:
        return 409, "Transaction already submitted"
    elif "transaction pool" in lower and "full" in lower:
        return 503, "Network busy — transaction pool full. Try again shortly."
    else:
        return 500, f"Transaction submission failed: {error_msg}"
