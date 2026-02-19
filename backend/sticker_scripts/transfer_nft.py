"""
NFT transfer helper for Algorand.

Transfers an ASA from one wallet to another.
The receiver MUST have already opted in to the asset.
"""
import logging

from algosdk.transaction import AssetTransferTxn, wait_for_confirmation

logger = logging.getLogger(__name__)


def transfer_nft(
    client,
    sender_address: str,
    sender_private_key: str,
    receiver_address: str,
    asset_id: int,
    amount: int = 1,
) -> str:
    """
    Transfer an NFT (ASA) to another wallet.

    Args:
        client: algod.AlgodClient instance.
        sender_address: Current holder's wallet address.
        sender_private_key: Current holder's private key.
        receiver_address: Recipient wallet address (must be opted in).
        asset_id: ASA to transfer.
        amount: Number of units to transfer (1 for NFTs).

    Returns:
        str: Transaction ID.
    """
    params = client.suggested_params()
    params.fee = max(params.fee, 1000)
    params.flat_fee = True

    txn = AssetTransferTxn(
        sender=sender_address,
        sp=params,
        receiver=receiver_address,
        amt=amount,
        index=asset_id,
    )

    signed_txn = txn.sign(sender_private_key)
    txid = client.send_transaction(signed_txn)
    logger.info(f"Transferring Asset {asset_id}: {sender_address[:8]}→{receiver_address[:8]}... TXID: {txid}")

    wait_for_confirmation(client, txid, 4)
    logger.info(f"Transfer confirmed for Asset {asset_id}")

    return txid
