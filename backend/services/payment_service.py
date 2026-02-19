"""
Payment service — thin wrapper around Algorand SDK payment sending.

Phase 1 (plan.md): keep low-level algosdk usage out of routes.
"""

from __future__ import annotations

from algosdk import transaction

from algorand_client import algorand_client


def send_payment(
    *,
    sender_address: str,
    sender_private_key: str,
    receiver_address: str,
    amount_micro: int,
    note: bytes | None = None,
) -> str:
    client = algorand_client.client
    sp = client.suggested_params()
    txn = transaction.PaymentTxn(
        sender=sender_address,
        sp=sp,
        receiver=receiver_address,
        amt=amount_micro,
        note=note,
    )
    signed = txn.sign(sender_private_key)
    tx_id = client.send_transaction(signed)
    transaction.wait_for_confirmation(client, tx_id, 4)
    return tx_id

