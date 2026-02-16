"""
Contract service — handles TEAL loading, compilation, deployment, and funding.
"""
import base64
import json
import logging
import os

from algosdk import transaction, encoding, logic

from algorand_client import algorand_client

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


def create_fund_txn(sender: str, app_id: int, amount: int = 200_000) -> dict:
    """
    Create an unsigned PaymentTxn to fund a deployed contract.

    Args:
        sender: Funder wallet address
        app_id: Deployed application ID
        amount: Amount in microAlgos (default 0.2 ALGO)

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
