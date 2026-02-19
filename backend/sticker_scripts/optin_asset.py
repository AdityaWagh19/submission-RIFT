"""
ASA opt-in helper for Algorand.

A wallet must opt in to an ASA before it can receive it.
Opt-in = 0-amount AssetTransferTxn from the wallet to itself.
"""
import logging

from algosdk.transaction import AssetTransferTxn, wait_for_confirmation

logger = logging.getLogger(__name__)


def optin_asset(
    client,
    account_address: str,
    account_private_key: str,
    asset_id: int,
) -> str:
    """
    Opt a wallet into an Algorand Standard Asset.

    Args:
        client: algod.AlgodClient instance.
        account_address: Wallet address opting in.
        account_private_key: Wallet private key.
        asset_id: ASA to opt into.

    Returns:
        str: Transaction ID.
    """
    params = client.suggested_params()
    params.fee = max(params.fee, 1000)
    params.flat_fee = True

    txn = AssetTransferTxn(
        sender=account_address,
        sp=params,
        receiver=account_address,  # self-transfer = opt-in
        amt=0,
        index=asset_id,
    )

    signed_txn = txn.sign(account_private_key)
    txid = client.send_transaction(signed_txn)
    logger.info(f"Opt-in to Asset {asset_id} for {account_address[:8]}... TXID: {txid}")

    wait_for_confirmation(client, txid, 4)
    logger.info(f"Opt-in confirmed for Asset {asset_id}")

    return txid
