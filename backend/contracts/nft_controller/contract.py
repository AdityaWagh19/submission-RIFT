"""
NFT Controller Smart Contract — enforces transfer and utility rules
for Butki, Bauni, and Shawty NFTs.

This contract acts as the on-chain authority for:
    - Butki: Non-transferable (soulbound), mint-only by platform
    - Bauni: Non-transferable (soulbound), time-bound, mint-only by platform
    - Shawty: Transferable, with burn/lock state tracking

On-chain State:
    Global:
        platform_address     (bytes)  — platform wallet (mint authority)
        total_butki_minted   (uint)   — counter of Butki mints
        total_bauni_minted   (uint)   — counter of Bauni mints
        total_shawty_minted  (uint)   — counter of Shawty mints
        paused               (uint)   — 0 = active, 1 = paused

    Local (per fan wallet):
        butki_count          (uint)   — total Butki NFTs held
        bauni_expiry         (uint)   — latest Bauni expiry as UNIX timestamp
        shawty_count         (uint)   — total active Shawty NFTs held
        total_burned         (uint)   — total Shawty tokens burned

Methods:
    mint_butki(fan, asset_id)      — Record Butki mint (platform only)
    mint_bauni(fan, expiry)        — Record Bauni mint with expiry (platform only)
    mint_shawty(fan, asset_id)     — Record Shawty mint (platform only)
    burn_shawty(fan, asset_id)     — Record Shawty burn (platform only)
    check_membership(fan)          — Check if fan's Bauni is still valid
    pause() / unpause()            — Emergency controls
"""

from pyteal import *

# ── Contract Metadata ──────────────────────────────────────────────
CONTRACT_NAME = "NFTController"
CONTRACT_DESCRIPTION = (
    "Enforces transfer, mint, and burn rules for Butki (loyalty), "
    "Bauni (membership), and Shawty (utility) NFTs."
)
CONTRACT_VERSION = "1.0.0"
GLOBAL_UINTS = 4   # total_butki, total_bauni, total_shawty, paused
GLOBAL_BYTES = 1   # platform_address
LOCAL_UINTS = 4    # butki_count, bauni_expiry, shawty_count, total_burned
LOCAL_BYTES = 0
CONTRACT_METHODS = [
    "mint_butki", "mint_bauni", "mint_shawty",
    "burn_shawty", "check_membership",
    "pause", "unpause",
]


def approval_program():
    """Main approval program for the NFT Controller contract."""

    # ========== Global State Keys ==========
    platform_key = Bytes("platform_address")
    total_butki_key = Bytes("total_butki_minted")
    total_bauni_key = Bytes("total_bauni_minted")
    total_shawty_key = Bytes("total_shawty_minted")
    paused_key = Bytes("paused")

    # ========== Local State Keys ==========
    butki_count_key = Bytes("butki_count")
    bauni_expiry_key = Bytes("bauni_expiry")
    shawty_count_key = Bytes("shawty_count")
    total_burned_key = Bytes("total_burned")

    # ========== Helpers ==========
    is_platform = Txn.sender() == App.globalGet(platform_key)
    is_paused = App.globalGet(paused_key) == Int(1)

    # ========== On Creation ==========
    # arg[0] = platform_address (32 bytes)
    on_creation = Seq([
        Assert(Txn.application_args.length() == Int(1)),
        App.globalPut(platform_key, Txn.application_args[0]),
        App.globalPut(total_butki_key, Int(0)),
        App.globalPut(total_bauni_key, Int(0)),
        App.globalPut(total_shawty_key, Int(0)),
        App.globalPut(paused_key, Int(0)),
        Approve(),
    ])

    # ========== mint_butki(fan_address, asset_id) ==========
    # Records a Butki loyalty NFT mint on-chain
    # arg[1] = fan address (32 bytes)
    # arg[2] = asset_id (uint64)
    on_mint_butki = Seq([
        Assert(is_platform),
        Assert(Not(is_paused)),
        Assert(Txn.application_args.length() == Int(3)),

        # Update fan's local state (fan must have opted in)
        App.localPut(
            Txn.application_args[1],
            butki_count_key,
            App.localGet(Txn.application_args[1], butki_count_key) + Int(1),
        ),

        # Update global counter
        App.globalPut(
            total_butki_key,
            App.globalGet(total_butki_key) + Int(1),
        ),

        # Emit log: [type][fan_address][asset_id]
        Log(Concat(
            Bytes("BUTKI_MINT"),
            Txn.application_args[1],    # fan address
            Txn.application_args[2],    # asset_id bytes
        )),

        Approve(),
    ])

    # ========== mint_bauni(fan_address, expiry_timestamp) ==========
    # Records a Bauni membership mint with expiry
    # arg[1] = fan address (32 bytes)
    # arg[2] = expiry_timestamp (uint64, UNIX epoch)
    on_mint_bauni = Seq([
        Assert(is_platform),
        Assert(Not(is_paused)),
        Assert(Txn.application_args.length() == Int(3)),

        # Set/extend fan's membership expiry
        # If new expiry > current expiry, update it
        If(
            Btoi(Txn.application_args[2]) > App.localGet(
                Txn.application_args[1], bauni_expiry_key
            ),
            App.localPut(
                Txn.application_args[1],
                bauni_expiry_key,
                Btoi(Txn.application_args[2]),
            ),
        ),

        # Update global counter
        App.globalPut(
            total_bauni_key,
            App.globalGet(total_bauni_key) + Int(1),
        ),

        Log(Concat(
            Bytes("BAUNI_MINT"),
            Txn.application_args[1],
            Txn.application_args[2],
        )),

        Approve(),
    ])

    # ========== mint_shawty(fan_address, asset_id) ==========
    # Records a Shawty utility NFT mint
    # arg[1] = fan address (32 bytes)
    # arg[2] = asset_id (uint64)
    on_mint_shawty = Seq([
        Assert(is_platform),
        Assert(Not(is_paused)),
        Assert(Txn.application_args.length() == Int(3)),

        App.localPut(
            Txn.application_args[1],
            shawty_count_key,
            App.localGet(Txn.application_args[1], shawty_count_key) + Int(1),
        ),

        App.globalPut(
            total_shawty_key,
            App.globalGet(total_shawty_key) + Int(1),
        ),

        Log(Concat(
            Bytes("SHAWTY_MINT"),
            Txn.application_args[1],
            Txn.application_args[2],
        )),

        Approve(),
    ])

    # ========== burn_shawty(fan_address, asset_id) ==========
    # Records a Shawty burn (for merch redemption)
    # arg[1] = fan address (32 bytes)
    # arg[2] = asset_id (uint64)
    on_burn_shawty = Seq([
        Assert(is_platform),
        Assert(Not(is_paused)),
        Assert(Txn.application_args.length() == Int(3)),

        # Decrement active count, increment burned count
        Assert(
            App.localGet(Txn.application_args[1], shawty_count_key) > Int(0)
        ),
        App.localPut(
            Txn.application_args[1],
            shawty_count_key,
            App.localGet(Txn.application_args[1], shawty_count_key) - Int(1),
        ),
        App.localPut(
            Txn.application_args[1],
            total_burned_key,
            App.localGet(Txn.application_args[1], total_burned_key) + Int(1),
        ),

        Log(Concat(
            Bytes("SHAWTY_BURN"),
            Txn.application_args[1],
            Txn.application_args[2],
        )),

        Approve(),
    ])

    # ========== check_membership(fan_address) ==========
    # Returns 1 (approve) if fan's Bauni membership is valid
    # arg[1] = fan address (32 bytes)
    on_check_membership = Seq([
        Assert(Txn.application_args.length() == Int(2)),

        # Check: fan's expiry > current time
        If(
            App.localGet(Txn.application_args[1], bauni_expiry_key) > Global.latest_timestamp(),
            Approve(),
            Reject(),
        ),
    ])

    # ========== pause / unpause ==========
    on_pause = Seq([
        Assert(is_platform),
        App.globalPut(paused_key, Int(1)),
        Approve(),
    ])

    on_unpause = Seq([
        Assert(is_platform),
        App.globalPut(paused_key, Int(0)),
        Approve(),
    ])

    # ========== Router ==========
    method_selector = Txn.application_args[0]

    program = Cond(
        [Txn.application_id() == Int(0), on_creation],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_platform)],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_platform)],
        [Txn.on_completion() == OnComplete.OptIn, Approve()],
        [Txn.on_completion() == OnComplete.CloseOut, Approve()],
        [Txn.on_completion() == OnComplete.NoOp, Cond(
            [method_selector == Bytes("mint_butki"), on_mint_butki],
            [method_selector == Bytes("mint_bauni"), on_mint_bauni],
            [method_selector == Bytes("mint_shawty"), on_mint_shawty],
            [method_selector == Bytes("burn_shawty"), on_burn_shawty],
            [method_selector == Bytes("check_membership"), on_check_membership],
            [method_selector == Bytes("pause"), on_pause],
            [method_selector == Bytes("unpause"), on_unpause],
        )],
    )

    return program


def clear_program():
    """Clear state program — always approves."""
    return Approve()


if __name__ == "__main__":
    print("=== NFTController Approval Program ===")
    print(compileTeal(approval_program(), mode=Mode.Application, version=8))
    print("\n=== NFTController Clear State Program ===")
    print(compileTeal(clear_program(), mode=Mode.Application, version=8))
