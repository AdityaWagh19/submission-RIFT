"""
Mint a Soulbound (non-transferable) sticker NFT on Algorand.

Creates an ASA with:
    total=1, decimals=0, default_frozen=True
This makes the NFT effectively soulbound — the holder cannot transfer it.
"""
import logging

from algosdk.transaction import AssetConfigTxn, wait_for_confirmation

logger = logging.getLogger(__name__)


def mint_soulbound(
    client,
    sender_address: str,
    sender_private_key: str,
    name: str,
    unit_name: str = "STICKER",
    url: str = "",
    metadata_hash: bytes | None = None,
) -> int:
    """
    Mint a soulbound NFT.

    Args:
        client: algod.AlgodClient instance.
        sender_address: Platform wallet address (minter).
        sender_private_key: Platform wallet private key.
        name: ASA asset name (e.g., "Day One Badge").
        unit_name: ASA unit name (default "STICKER").
        url: IPFS metadata URL (ARC-3 JSON).
        metadata_hash: Optional 32-byte metadata hash.

    Returns:
        int: Created asset ID.
    """
    params = client.suggested_params()
    params.fee = max(params.fee, 1000)
    params.flat_fee = True

    txn = AssetConfigTxn(
        sender=sender_address,
        sp=params,
        total=1,
        decimals=0,
        default_frozen=True,  # soulbound — non-transferable
        unit_name=unit_name,
        asset_name=name,
        manager=sender_address,
        reserve=sender_address,
        freeze=sender_address,
        clawback=sender_address,
        url=url,
        metadata_hash=metadata_hash,
    )

    signed_txn = txn.sign(sender_private_key)
    txid = client.send_transaction(signed_txn)
    logger.info(f"Minting soulbound '{name}'... TXID: {txid}")

    result = wait_for_confirmation(client, txid, 4)
    asset_id = result["asset-index"]
    logger.info(f"Soulbound NFT '{name}' created — Asset ID: {asset_id}")

    return asset_id
