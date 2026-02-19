"""
Contract service — handles TEAL loading, compilation, deployment, and funding.

V4 additions: deploy_tip_proxy, upgrade_tip_proxy, get_contract_stats,
close_out_contract, decode_global_state.
"""
import base64
import json
import logging
import os
from datetime import datetime

from algosdk import transaction, encoding, logic, account

from algorand_client import algorand_client
from config import settings

logger = logging.getLogger(__name__)

# Path to contracts directory
CONTRACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "contracts")


def _get_contract_dir(contract_name: str) -> str:
    """Get the directory for a specific contract."""
    return os.path.join(CONTRACTS_DIR, contract_name)


def _get_compiled_dir(contract_name: str) -> str:
    """Get the compiled output directory for a contract."""
    return os.path.join(_get_contract_dir(contract_name), "compiled")


def load_teal(contract_name: str, filename: str) -> str:
    """
    Load a compiled TEAL file for a given contract.

    Args:
        contract_name: Name of the contract (folder name under contracts/)
        filename: TEAL filename (e.g., 'approval.teal')

    Returns:
        TEAL source code as string
    """
    teal_path = os.path.join(_get_compiled_dir(contract_name), filename)
    if not os.path.exists(teal_path):
        raise FileNotFoundError(
            f"Compiled TEAL file not found: {teal_path}. "
            f"Run: python -m contracts.compile {contract_name}"
        )
    with open(teal_path, "r") as f:
        return f.read()


def get_contract_info(contract_name: str) -> dict:
    """
    Get contract metadata from contract_info.json.

    Returns:
        Dict with contract info, or {"compiled": False} if not compiled.
    """
    info_path = os.path.join(_get_compiled_dir(contract_name), "contract_info.json")
    if os.path.exists(info_path):
        with open(info_path) as f:
            info = json.load(f)
        return {"compiled": True, **info}
    return {"compiled": False, "error": f"Contract '{contract_name}' not compiled yet"}


def list_contracts() -> list[dict]:
    """List all available contracts in the contracts directory."""
    contracts = []
    if not os.path.exists(CONTRACTS_DIR):
        return contracts

    for entry in os.listdir(CONTRACTS_DIR):
        contract_dir = os.path.join(CONTRACTS_DIR, entry)
        if os.path.isdir(contract_dir) and entry != "__pycache__":
            info = get_contract_info(entry)
            contracts.append({"name": entry, **info})
    return contracts


def create_deploy_txn(sender: str, contract_name: str) -> dict:
    """
    Create an unsigned ApplicationCreateTxn for deploying a contract.

    Args:
        sender: Deployer wallet address
        contract_name: Name of the contract to deploy

    Returns:
        Dict with unsigned transaction and schema info
    """
    logger.info(f"Creating deploy txn for '{contract_name}' from {sender}")

    # Load and compile TEAL
    approval_teal = load_teal(contract_name, "approval.teal")
    clear_teal = load_teal(contract_name, "clear.teal")

    approval_compiled = algorand_client.client.compile(approval_teal)
    clear_compiled = algorand_client.client.compile(clear_teal)

    approval_program = base64.b64decode(approval_compiled["result"])
    clear_program = base64.b64decode(clear_compiled["result"])

    # Load contract info for schemas
    info = get_contract_info(contract_name)
    num_global_uints = info.get("global_uints", 2)
    num_global_bytes = info.get("global_bytes", 1)
    num_local_uints = info.get("local_uints", 0)
    num_local_bytes = info.get("local_bytes", 0)

    # Get params
    sp = algorand_client.get_suggested_params()
    sp.fee = max(sp.fee, 1000)
    sp.flat_fee = True

    global_schema = transaction.StateSchema(
        num_uints=num_global_uints, num_byte_slices=num_global_bytes
    )
    local_schema = transaction.StateSchema(
        num_uints=num_local_uints, num_byte_slices=num_local_bytes
    )

    txn = transaction.ApplicationCreateTxn(
        sender=sender,
        sp=sp,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program,
        global_schema=global_schema,
        local_schema=local_schema,
    )

    txn_bytes = encoding.msgpack_encode(txn)
    logger.info(f"Deploy txn created for '{contract_name}'")

    return {
        "unsignedTxn": txn_bytes,
        "contractName": contract_name,
        "appArgs": {
            "globalSchema": {"numUints": num_global_uints, "numBytes": num_global_bytes},
            "localSchema": {"numUints": num_local_uints, "numBytes": num_local_bytes},
        },
    }


def create_fund_txn(sender: str, app_id: int, amount: int = 100_000) -> dict:
    """
    Create an unsigned PaymentTxn to fund a deployed contract.

    Args:
        sender: Funder wallet address
        app_id: Deployed application ID
        amount: Amount in microAlgos (default 0.1 ALGO)

    Returns:
        Dict with unsigned transaction and contract address
    """
    app_address = logic.get_application_address(app_id)
    logger.info(f"Creating fund txn: {sender} -> {app_address} ({amount} microAlgos)")

    sp = algorand_client.get_suggested_params()
    sp.fee = max(sp.fee, 1000)
    sp.flat_fee = True

    txn = transaction.PaymentTxn(
        sender=sender,
        sp=sp,
        receiver=app_address,
        amt=amount,
    )

    txn_bytes = encoding.msgpack_encode(txn)

    return {
        "unsignedTxn": txn_bytes,
        "appAddress": app_address,
        "amount": amount,
    }


# ════════════════════════════════════════════════════════════════════
# V4 — TipProxy Contract Management
# ════════════════════════════════════════════════════════════════════


def _get_platform_account() -> dict:
    """
    Get the platform wallet's private key and address.

    Security fix H4: Uses settings.platform_private_key (cached)
    instead of re-deriving from mnemonic on every call.

    Returns:
        dict with 'address' and 'private_key'
    """
    private_key = settings.platform_private_key  # Cached in config.py
    address = account.address_from_private_key(private_key)
    return {"address": address, "private_key": private_key}


def deploy_tip_proxy(creator_wallet: str, min_tip_algo: float = 1.0) -> dict:
    """
    Deploy a new TipProxy smart contract for a creator.

    1. Loads compiled TipProxy TEAL
    2. Creates ApplicationCreateTxn with creator + platform as app args
    3. Signs with platform wallet and submits
    4. Funds the contract with minimum balance (0.1 ALGO)
    5. Returns {app_id, app_address, version, min_tip_algo}

    Args:
        creator_wallet: Creator's Algorand address (set as contract owner)
        min_tip_algo: Minimum tip amount in ALGO (default: 1.0, range: 0.1 - 1000)

    Returns:
        dict: {app_id, app_address, version, min_tip_algo}
    """
    platform = _get_platform_account()
    client = algorand_client.client

    # Validate min_tip_algo range
    if min_tip_algo < 0.1 or min_tip_algo > 1000.0:
        raise ValueError(f"min_tip_algo must be between 0.1 and 1000 ALGO, got {min_tip_algo}")

    # Convert ALGO to microAlgos
    min_tip_micro = int(min_tip_algo * 1_000_000)

    logger.info(f"Deploying TipProxy for creator {creator_wallet[:8]}... (min_tip: {min_tip_algo} ALGO)")

    # Load and compile TEAL
    approval_teal = load_teal("tip_proxy", "approval.teal")
    clear_teal = load_teal("tip_proxy", "clear.teal")

    approval_compiled = client.compile(approval_teal)
    clear_compiled = client.compile(clear_teal)

    approval_program = base64.b64decode(approval_compiled["result"])
    clear_program = base64.b64decode(clear_compiled["result"])

    # Global schema: 5 uints + 2 bytes (from contract spec)
    global_schema = transaction.StateSchema(num_uints=5, num_byte_slices=2)
    local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    # Suggested params
    sp = client.suggested_params()
    sp.fee = max(sp.fee, 2000)  # extra fee covers inner txn
    sp.flat_fee = True

    # App args: [creator_address_raw, platform_address_raw, min_tip_amount, version]
    txn = transaction.ApplicationCreateTxn(
        sender=platform["address"],
        sp=sp,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program,
        global_schema=global_schema,
        local_schema=local_schema,
        app_args=[
            encoding.decode_address(creator_wallet),       # 32 bytes: creator address
            encoding.decode_address(platform["address"]),  # 32 bytes: platform address
            min_tip_micro.to_bytes(8, "big"),               # 8 bytes: min tip (creator-configurable)
            (1).to_bytes(8, "big"),                        # 8 bytes: version = 1
        ],
    )


    # Sign and submit
    signed_txn = txn.sign(platform["private_key"])
    tx_id = client.send_transaction(signed_txn)
    logger.info(f"  TipProxy deploy txn sent: {tx_id}")

    result = transaction.wait_for_confirmation(client, tx_id, 4)
    app_id = result["application-index"]
    app_address = logic.get_application_address(app_id)

    logger.info(f"  TipProxy deployed — App ID: {app_id}, Address: {app_address[:8]}...")

    # Fund the contract with minimum balance so it can send inner txns
    fund_amount = settings.contract_fund_amount
    fund_sp = client.suggested_params()
    fund_sp.fee = max(fund_sp.fee, 1000)
    fund_sp.flat_fee = True

    fund_txn = transaction.PaymentTxn(
        sender=platform["address"],
        sp=fund_sp,
        receiver=app_address,
        amt=fund_amount,
    )
    signed_fund = fund_txn.sign(platform["private_key"])
    fund_tx_id = client.send_transaction(signed_fund)
    transaction.wait_for_confirmation(client, fund_tx_id, 4)
    logger.info(f"  TipProxy funded with {fund_amount} microALGO")

    return {
        "app_id": app_id,
        "app_address": app_address,
        "version": 1,
        "min_tip_algo": min_tip_algo,
        "tx_id": tx_id,
    }


def upgrade_tip_proxy(
    creator_wallet: str,
    old_app_id: int,
    old_version: int,
    min_tip_algo: float = 1.0,
) -> dict:
    """
    Deploy a new TipProxy version for a creator, replacing the old one.

    1. Deploys a fresh TipProxy with the same min_tip setting
    2. Returns the new contract info (caller updates DB)

    Args:
        creator_wallet: Creator's Algorand address
        old_app_id: The app_id being replaced
        old_version: Current version number
        min_tip_algo: Min tip amount to preserve from old contract

    Returns:
        dict: {app_id, app_address, version, min_tip_algo}
    """
    logger.info(f"Upgrading TipProxy for {creator_wallet[:8]}... (v{old_version} → v{old_version + 1})")

    new_contract = deploy_tip_proxy(creator_wallet, min_tip_algo=min_tip_algo)
    new_contract["version"] = old_version + 1

    logger.info(f"  New TipProxy: App ID {new_contract['app_id']} (v{new_contract['version']})")

    return new_contract


def close_out_contract(old_app_id: int, creator_wallet: str) -> str | None:
    """
    Delete an old TipProxy contract and return remaining ALGO to creator.

    Args:
        old_app_id: Application ID to delete
        creator_wallet: Address to receive remaining ALGO

    Returns:
        Transaction ID of the delete, or None on failure
    """
    platform = _get_platform_account()
    client = algorand_client.client

    try:
        sp = client.suggested_params()
        sp.fee = max(sp.fee, 1000)
        sp.flat_fee = True

        txn = transaction.ApplicationDeleteTxn(
            sender=platform["address"],
            sp=sp,
            index=old_app_id,
        )

        signed_txn = txn.sign(platform["private_key"])
        tx_id = client.send_transaction(signed_txn)
        transaction.wait_for_confirmation(client, tx_id, 4)

        logger.info(f"  Old TipProxy {old_app_id} deleted. Remaining ALGO returned to creator.")
        return tx_id

    except Exception as e:
        logger.warning(f"  Failed to close out contract {old_app_id}: {e}")
        return None


def decode_global_state(global_state: list) -> dict:
    """
    Decode Algorand application global state from the raw format.

    The Algorand API returns global state as a list of
    {key: base64, value: {bytes: base64, uint: int, type: int}}.

    Args:
        global_state: Raw global-state list from algod application_info()

    Returns:
        dict mapping human-readable key names to decoded values
    """
    result = {}
    for item in global_state:
        key = base64.b64decode(item["key"]).decode("utf-8", errors="ignore")
        value = item["value"]

        if value["type"] == 1:
            # bytes value
            result[key] = base64.b64decode(value.get("bytes", ""))
        elif value["type"] == 2:
            # uint value
            result[key] = value.get("uint", 0)
        else:
            result[key] = value

    return result


def get_contract_stats(app_id: int) -> dict:
    """
    Read on-chain global state from a TipProxy contract.

    Returns:
        dict: {total_tips, total_amount_algo, min_tip_algo, paused, contract_version}
    """
    client = algorand_client.client

    try:
        app_info = client.application_info(app_id)
        raw_state = app_info.get("params", {}).get("global-state", [])
        global_state = decode_global_state(raw_state)

        return {
            "app_id": app_id,
            "total_tips": global_state.get("total_tips", 0),
            "total_amount_algo": global_state.get("total_amount", 0) / 1_000_000,
            "min_tip_algo": global_state.get("min_tip_amount", 1_000_000) / 1_000_000,
            "paused": bool(global_state.get("paused", 0)),
            "contract_version": global_state.get("contract_version", 1),
        }
    except Exception as e:
        logger.error(f"Failed to read contract stats for app {app_id}: {e}")
        raise

