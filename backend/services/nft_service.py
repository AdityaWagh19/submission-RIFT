"""
NFT Service — wraps sticker_scripts with IPFS-aware minting pipeline.

This service bridges the gap between sticker_scripts (low-level ASA operations)
and the platform's higher-level concept of sticker templates with IPFS metadata.

Flow:
    1. Template already has image + metadata on IPFS (via ipfs_service)
    2. nft_service.mint_sticker() picks the right minting function
    3. Platform wallet mints the ASA with the IPFS metadata URL
    4. Platform wallet opts-in fan and transfers the NFT
    5. Returns asset_id for DB storage
"""
import logging
from typing import Optional

from algosdk import account

from algorand_client import algorand_client
from config import settings
from sticker_scripts.mint_soulbound import mint_soulbound
from sticker_scripts.mint_golden import mint_golden
from sticker_scripts.optin_asset import optin_asset
from sticker_scripts.transfer_nft import transfer_nft

logger = logging.getLogger(__name__)


def _get_platform_account() -> dict:
    """
    Get the platform wallet's private key and address.

    Security fix H4: Uses settings.platform_private_key (cached)
    instead of re-deriving from mnemonic on every call.
    """
    private_key = settings.platform_private_key  # Cached in config.py
    address = account.address_from_private_key(private_key)
    return {"address": address, "private_key": private_key}


def mint_soulbound_sticker(
    name: str,
    metadata_url: str,
    unit_name: str = "STICKER",
    metadata_hash: Optional[bytes] = None,
) -> int:
    """
    Mint a soulbound (non-transferable) sticker NFT.

    The NFT is created with default_frozen=True, making it permanently
    bound to the recipient's wallet.

    Args:
        name: ASA name (max 32 chars)
        metadata_url: IPFS URL pointing to ARC-3 metadata JSON
        unit_name: ASA unit name (max 8 chars, default: 'STICKER')
        metadata_hash: Optional 32-byte metadata hash for ARC-3

    Returns:
        int: Algorand asset ID of the minted NFT
    """
    platform = _get_platform_account()
    client = algorand_client.client

    logger.info(f"Minting soulbound sticker: {name}")

    asset_id = mint_soulbound(
        client=client,
        sender_address=platform["address"],
        sender_private_key=platform["private_key"],
        name=name,
        unit_name=unit_name,
        url=metadata_url,
        metadata_hash=metadata_hash,
    )

    logger.info(f"  Soulbound NFT minted — Asset ID: {asset_id}")
    return asset_id


def mint_golden_sticker(
    name: str,
    metadata_url: str,
    unit_name: str = "GOLDEN",
    metadata_hash: Optional[bytes] = None,
) -> int:
    """
    Mint a golden (tradable) sticker NFT.

    The NFT is created with default_frozen=False and no freeze/clawback
    authority, enabling true ownership and free transfer between wallets.

    Args:
        name: ASA name (max 32 chars)
        metadata_url: IPFS URL pointing to ARC-3 metadata JSON
        unit_name: ASA unit name (max 8 chars, default: 'GOLDEN')
        metadata_hash: Optional 32-byte metadata hash for ARC-3

    Returns:
        int: Algorand asset ID of the minted NFT
    """
    platform = _get_platform_account()
    client = algorand_client.client

    logger.info(f"Minting golden sticker: {name}")

    asset_id = mint_golden(
        client=client,
        sender_address=platform["address"],
        sender_private_key=platform["private_key"],
        name=name,
        unit_name=unit_name,
        url=metadata_url,
        metadata_hash=metadata_hash,
    )

    logger.info(f"  Golden NFT minted — Asset ID: {asset_id}")
    return asset_id


def mint_sticker(
    name: str,
    metadata_url: str,
    sticker_type: str,
    unit_name: Optional[str] = None,
    metadata_hash: Optional[bytes] = None,
) -> int:
    """
    Mint a sticker NFT based on type.

    Args:
        name: ASA name
        metadata_url: IPFS metadata URL
        sticker_type: 'soulbound' or 'golden'
        unit_name: Optional unit name override
        metadata_hash: Optional ARC-3 metadata hash

    Returns:
        int: Asset ID
    """
    if sticker_type == "golden":
        return mint_golden_sticker(
            name=name,
            metadata_url=metadata_url,
            unit_name=unit_name or "GOLDEN",
            metadata_hash=metadata_hash,
        )
    else:
        return mint_soulbound_sticker(
            name=name,
            metadata_url=metadata_url,
            unit_name=unit_name or "STICKER",
            metadata_hash=metadata_hash,
        )


def send_nft_to_fan(
    asset_id: int,
    fan_wallet: str,
    fan_private_key: Optional[str] = None,
) -> dict:
    """
    Transfer a minted NFT to a fan.

    For soulbound stickers (default_frozen=True):
        - If fan has opted in → uses clawback transfer (revocation from platform)
        - If fan hasn't opted in → returns pending_optin status
          (fan claims later via frontend opt-in + backend delivery)

    For golden stickers (default_frozen=False):
        - Normal AssetTransferTxn if fan has opted in
        - If fan hasn't opted in → returns pending_optin status

    Args:
        asset_id: Algorand ASA ID
        fan_wallet: Recipient's Algorand address
        fan_private_key: DEPRECATED — only used in demo mode for auto opt-in.
                         In production, fans opt-in via Pera Wallet.

    Returns:
        dict: {status: 'delivered'|'pending_optin', tx_id: str|None}
    """
    from algosdk import transaction as algo_txn

    platform = _get_platform_account()
    client = algorand_client.client

    logger.info(f"Transferring NFT {asset_id} to {fan_wallet[:8]}...")

    # Check if the asset is frozen (soulbound)
    asset_info = client.asset_info(asset_id)
    is_frozen = asset_info.get("params", {}).get("default-frozen", False)

    # Check if fan has opted in
    fan_info = client.account_info(fan_wallet)
    fan_opted_in = any(
        a["asset-id"] == asset_id for a in fan_info.get("assets", [])
    )

    if not fan_opted_in:
        if fan_private_key:
            # Auto opt-in if we have the fan's key (demo/testing mode ONLY)
            optin_asset(
                client=client,
                account_address=fan_wallet,
                account_private_key=fan_private_key,
                asset_id=asset_id,
            )
            logger.info(f"  Auto opt-in completed for {fan_wallet[:8]}... (demo mode)")
        else:
            # Production mode: fan must opt-in via Pera Wallet first
            logger.info(
                f"  Fan {fan_wallet[:8]}... not opted in to ASA {asset_id}. "
                f"NFT saved as pending — fan can claim via frontend."
            )
            return {"status": "pending_optin", "tx_id": None}

    if is_frozen:
        # Soulbound: use clawback transfer (platform is clawback authority)
        sp = client.suggested_params()
        sp.fee = max(sp.fee, 1000)
        sp.flat_fee = True

        txn = algo_txn.AssetTransferTxn(
            sender=platform["address"],         # clawback authority
            sp=sp,
            receiver=fan_wallet,                # fan receives
            amt=1,
            index=asset_id,
            revocation_target=platform["address"],  # revoke from platform
        )

        signed_txn = txn.sign(platform["private_key"])
        tx_id = client.send_transaction(signed_txn)
        algo_txn.wait_for_confirmation(client, tx_id, 4)

        logger.info(f"  Soulbound NFT {asset_id} clawback-transferred — TX: {tx_id}")
    else:
        # Golden: regular transfer
        tx_id = transfer_nft(
            client=client,
            sender_address=platform["address"],
            sender_private_key=platform["private_key"],
            receiver_address=fan_wallet,
            asset_id=asset_id,
            amount=1,
        )
        logger.info(f"  Golden NFT {asset_id} transferred — TX: {tx_id}")

    return {"status": "delivered", "tx_id": tx_id}


def create_optin_txn(asset_id: int, fan_wallet: str) -> dict:
    """
    Create an unsigned ASA opt-in transaction for a fan.

    The fan must sign this with Pera Wallet before they can receive
    golden (tradable) stickers.

    Args:
        asset_id: ASA ID to opt into
        fan_wallet: Fan's Algorand address

    Returns:
        dict: {unsignedTxn, assetId}
    """
    from algosdk import transaction, encoding

    client = algorand_client.client
    sp = client.suggested_params()
    sp.fee = max(sp.fee, 1000)
    sp.flat_fee = True

    txn = transaction.AssetTransferTxn(
        sender=fan_wallet,
        sp=sp,
        receiver=fan_wallet,  # self-transfer = opt-in
        amt=0,
        index=asset_id,
    )

    txn_bytes = encoding.msgpack_encode(txn)

    return {
        "unsignedTxn": txn_bytes,
        "assetId": asset_id,
    }
