"""
Mint a Golden (tradable) sticker NFT on Algorand.

Creates an ASA with:
    total=1, decimals=0, default_frozen=False
This makes the NFT freely transferable — a collectible with real value.
"""
import logging

from algosdk.transaction import AssetConfigTxn, wait_for_confirmation

logger = logging.getLogger(__name__)


def mint_golden(
    client,
    sender_address: str,
    sender_private_key: str,
    name: str,
    unit_name: str = "GOLDEN",
    url: str = "",
    metadata_hash: bytes | None = None,
) -> int:
    """
    Mint a golden (tradable) NFT.

    Args:
        client: algod.AlgodClient instance.
        sender_address: Platform wallet address (minter).
        sender_private_key: Platform wallet private key.
        name: ASA asset name (e.g., "Rare Golden Star").
        unit_name: ASA unit name (default "GOLDEN").
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
        default_frozen=False,  # tradable — Golden Stickers can be transferred
        unit_name=unit_name,
        asset_name=name,
        manager=sender_address,
        reserve=sender_address,
        freeze="",     # no freeze authority — truly transferable
        clawback="",   # no clawback — truly owned by holder
        url=url,
        metadata_hash=metadata_hash,
        strict_empty_address_check=False,
    )

    signed_txn = txn.sign(sender_private_key)
    txid = client.send_transaction(signed_txn)
    logger.info(f"Minting golden '{name}'... TXID: {txid}")

    result = wait_for_confirmation(client, txid, 4)
    asset_id = result["asset-index"]
    logger.info(f"Golden NFT '{name}' created — Asset ID: {asset_id}")

    return asset_id
