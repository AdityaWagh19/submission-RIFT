"""
Smart contract compiler — compiles PyTeal contracts to TEAL.

Usage:
    python -m contracts.compile                   # Compiles all contracts
    python -m contracts.compile payment_proxy     # Compiles a specific contract
"""
import importlib
import json
import os
import sys

from pyteal import compileTeal, Mode


CONTRACTS_DIR = os.path.dirname(__file__)


def compile_contract(contract_name: str) -> None:
    """Compile a single contract by name."""
    contract_dir = os.path.join(CONTRACTS_DIR, contract_name)
    compiled_dir = os.path.join(contract_dir, "compiled")
    contract_module_path = os.path.join(contract_dir, "contract.py")

    if not os.path.exists(contract_module_path):
        print(f"  ⚠ Skipping '{contract_name}' — no contract.py found")
        return

    os.makedirs(compiled_dir, exist_ok=True)

    # Import the contract module
    module_name = f"contracts.{contract_name}.contract"
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        print(f"  ❌ Failed to import '{module_name}': {e}")
        return

    # Get approval and clear programs
    if not hasattr(module, "approval_program") or not hasattr(module, "clear_program"):
        print(f"  ❌ '{module_name}' must export approval_program() and clear_program()")
        return

    print(f"  Compiling approval program...")
    approval_teal = compileTeal(
        module.approval_program(), mode=Mode.Application, version=8
    )

    print(f"  Compiling clear program...")
    clear_teal = compileTeal(
        module.clear_program(), mode=Mode.Application, version=8
    )

    # Write TEAL files
    approval_path = os.path.join(compiled_dir, "approval.teal")
    clear_path = os.path.join(compiled_dir, "clear.teal")

    with open(approval_path, "w") as f:
        f.write(approval_teal)
    with open(clear_path, "w") as f:
        f.write(clear_teal)

    # Write contract info
    info = {
        "name": getattr(module, "CONTRACT_NAME", contract_name),
        "description": getattr(module, "CONTRACT_DESCRIPTION", ""),
        "version": getattr(module, "CONTRACT_VERSION", "1.0.0"),
        "global_uints": getattr(module, "GLOBAL_UINTS", 2),
        "global_bytes": getattr(module, "GLOBAL_BYTES", 1),
        "local_uints": getattr(module, "LOCAL_UINTS", 0),
        "local_bytes": getattr(module, "LOCAL_BYTES", 0),
        "methods": getattr(module, "CONTRACT_METHODS", []),
    }
    info_path = os.path.join(compiled_dir, "contract_info.json")
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)

    print(f"  ✅ '{contract_name}' compiled successfully")
    print(f"     Approval: {os.path.relpath(approval_path)}")
    print(f"     Clear:    {os.path.relpath(clear_path)}")
    print(f"     Info:     {os.path.relpath(info_path)}")


def compile_all() -> None:
    """Compile all contracts in the contracts directory."""
    for entry in os.listdir(CONTRACTS_DIR):
        entry_path = os.path.join(CONTRACTS_DIR, entry)
        if (
            os.path.isdir(entry_path)
            and entry != "__pycache__"
            and os.path.exists(os.path.join(entry_path, "contract.py"))
        ):
            print(f"\n📦 Compiling '{entry}'...")
            compile_contract(entry)


if __name__ == "__main__":
    # Allow running from backend/ directory
    backend_dir = os.path.dirname(CONTRACTS_DIR)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    if len(sys.argv) > 1:
        name = sys.argv[1]
        print(f"📦 Compiling '{name}'...")
        compile_contract(name)
    else:
        print("🔧 Compiling all contracts...")
        compile_all()

    print("\n✅ Done!")
