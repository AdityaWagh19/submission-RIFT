"""
Transaction service — handles base64 processing, submission, and error classification.
"""
import base64
import logging

from algorand_client import algorand_client

logger = logging.getLogger(__name__)


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


def submit_single(signed_txn_b64: str) -> str:
    """
    Submit a single signed transaction to Algorand TestNet.

    Args:
        signed_txn_b64: Base64-encoded signed transaction

    Returns:
        Transaction ID from the network
    """
    b64_str = fix_base64_padding(signed_txn_b64)

    # Validate
    decoded = validate_base64(b64_str)
    logger.info(f"Submitting single txn: {len(decoded)} bytes")

    # send_raw_transaction expects base64 string (it decodes internally)
    tx_id = algorand_client.client.send_raw_transaction(b64_str)
    logger.info(f"Transaction submitted: {tx_id}")
    return tx_id


def submit_group(signed_txns_b64: list[str]) -> str:
    """
    Submit an atomic group of signed transactions.

    Args:
        signed_txns_b64: List of base64-encoded signed transactions

    Returns:
        First transaction ID from the group
    """
    logger.info(f"Submitting transaction group ({len(signed_txns_b64)} txns)")

    # Decode and concatenate all signed transaction bytes
    all_bytes = []
    for i, txn_b64 in enumerate(signed_txns_b64):
        txn_bytes = validate_base64(txn_b64)
        all_bytes.append(txn_bytes)
        logger.info(f"  Txn {i}: {len(txn_bytes)} bytes")

    combined = b''.join(all_bytes)
    combined_b64 = base64.b64encode(combined).decode()

    tx_id = algorand_client.client.send_raw_transaction(combined_b64)
    logger.info(f"Group submitted: {tx_id}")
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
