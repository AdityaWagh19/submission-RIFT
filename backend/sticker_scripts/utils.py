"""
Utility helpers for sticker scripts.

Provides account derivation from mnemonic, replacing the old LocalNet-only
utils that relied on KMD.
"""
import logging

from algosdk import mnemonic, account

logger = logging.getLogger(__name__)


def get_account_from_mnemonic(mnemonic_phrase: str) -> dict:
    """
    Derive private key and address from a 25-word mnemonic.

    Args:
        mnemonic_phrase: Space-separated 25-word Algorand mnemonic.

    Returns:
        dict with 'address' and 'private_key'.
    """
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    address = account.address_from_private_key(private_key)
    logger.debug(f"Derived account: {address[:8]}...")
    return {"address": address, "private_key": private_key}
