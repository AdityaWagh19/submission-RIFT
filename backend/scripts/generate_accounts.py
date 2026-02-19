"""Generate 3 Algorand TestNet demo accounts and save to file."""
from algosdk import account, mnemonic
import json
import os

accounts = {}
for role in ["creator", "fan1", "fan2"]:
    pk, addr = account.generate_account()
    mn = mnemonic.from_private_key(pk)
    accounts[role] = {"address": addr, "mnemonic": mn}

# Save to file
out_path = os.path.join(os.path.dirname(__file__), "demo_accounts.json")
with open(out_path, "w") as f:
    json.dump(accounts, f, indent=2)

print(f"Accounts saved to: {out_path}")
for role, info in accounts.items():
    print(f"\n{role.upper()}:")
    print(f"  {info['address']}")
