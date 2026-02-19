"""
TipProxy Smart Contract — Per-Creator Tip Jar for Algorand.

Each creator gets their own TipProxy deployed on registration.
Fans tip by sending atomic groups (PaymentTxn + AppCallTxn).
The contract validates, forwards ALGO to the creator via inner transaction,
and emits a binary log for the backend listener.

Methods:
    tip(memo)           — Fan tips the creator (requires atomic group with payment)
    update_min_tip(amt) — Creator updates minimum tip amount
    pause()             — Creator or platform pauses the contract
    unpause()           — Creator or platform unpauses the contract

Global State:
    creator_address   (bytes)  — creator wallet who receives tips
    platform_address  (bytes)  — platform wallet (co-admin)
    min_tip_amount    (uint)   — minimum microAlgo tip (default 1_000_000 = 1 ALGO)
    total_tips        (uint)   — counter of tip() calls
    total_amount      (uint)   — running sum of microAlgos tipped
    contract_version  (uint)   — version number for upgrade tracking
    paused            (uint)   — 0 = active, 1 = paused
"""

from pyteal import *

# ── Contract Metadata (read by compiler) ──────────────────────────
CONTRACT_NAME = "TipProxy"
CONTRACT_DESCRIPTION = (
    "Per-creator tip proxy — validates payments, forwards ALGO via inner "
    "transaction, emits structured logs for backend listener."
)
CONTRACT_VERSION = "1.0.0"
GLOBAL_UINTS = 5   # min_tip_amount, total_tips, total_amount, contract_version, paused
GLOBAL_BYTES = 2   # creator_address, platform_address
LOCAL_UINTS = 0
LOCAL_BYTES = 0
CONTRACT_METHODS = ["tip", "update_min_tip", "pause", "unpause"]


def approval_program():
    """Main approval program for the TipProxy contract."""

    # ========== Global State Keys ==========
    creator_key = Bytes("creator_address")
    platform_key = Bytes("platform_address")
    min_tip_key = Bytes("min_tip_amount")
    total_tips_key = Bytes("total_tips")
    total_amount_key = Bytes("total_amount")
    version_key = Bytes("contract_version")
    paused_key = Bytes("paused")

    # ========== Helpers ==========
    is_creator = Txn.sender() == App.globalGet(creator_key)
    is_platform = Txn.sender() == App.globalGet(platform_key)
    is_admin = Or(is_creator, is_platform)
    is_paused = App.globalGet(paused_key) == Int(1)

    # ========== On Creation ==========
    # App args at creation:
    #   arg[0] = creator_address (32 bytes)
    #   arg[1] = platform_address (32 bytes)
    #   arg[2] = min_tip_amount (uint64, 8 bytes)
    #   arg[3] = contract_version (uint64, 8 bytes)
    on_creation = Seq([
        Assert(Txn.application_args.length() == Int(4)),
        App.globalPut(creator_key, Txn.application_args[0]),
        App.globalPut(platform_key, Txn.application_args[1]),
        App.globalPut(min_tip_key, Btoi(Txn.application_args[2])),
        App.globalPut(version_key, Btoi(Txn.application_args[3])),
        App.globalPut(total_tips_key, Int(0)),
        App.globalPut(total_amount_key, Int(0)),
        App.globalPut(paused_key, Int(0)),
        Approve()
    ])

    # ========== tip(memo) Method ==========
    # Atomic group: [PaymentTxn → contract, AppCallTxn with tip(memo)]
    # The payment must be the transaction BEFORE this app call in the group.
    payment_txn_index = Txn.group_index() - Int(1)
    payment_amount = Gtxn[payment_txn_index].amount()
    tip_memo = If(
        Txn.application_args.length() >= Int(2),
        Txn.application_args[1],
        Bytes("")
    )

    on_tip = Seq([
        # Contract must not be paused
        Assert(Not(is_paused)),

        # Must be in an atomic group of exactly 2
        Assert(Global.group_size() == Int(2)),

        # Previous txn must be a payment
        Assert(Gtxn[payment_txn_index].type_enum() == TxnType.Payment),

        # Payment must go to this contract's escrow address
        Assert(Gtxn[payment_txn_index].receiver() == Global.current_application_address()),

        # Payment sender must match app caller (fan)
        Assert(Gtxn[payment_txn_index].sender() == Txn.sender()),

        # Payment must meet minimum tip amount
        Assert(payment_amount >= App.globalGet(min_tip_key)),

        # Forward ALGO to creator via inner transaction
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: App.globalGet(creator_key),
            TxnField.amount: payment_amount,
            TxnField.fee: Int(0),  # fee pooling from outer txn
        }),
        InnerTxnBuilder.Submit(),

        # Emit structured log: [32B fan_address][8B uint64 amount][NB memo]
        Log(Concat(
            Txn.sender(),       # 32 bytes — fan address
            Itob(payment_amount),  # 8 bytes — amount in microAlgo
            tip_memo            # N bytes — UTF-8 memo
        )),

        # Update counters
        App.globalPut(
            total_tips_key,
            App.globalGet(total_tips_key) + Int(1)
        ),
        App.globalPut(
            total_amount_key,
            App.globalGet(total_amount_key) + payment_amount
        ),

        Approve()
    ])

    # ========== update_min_tip(amount) Method ==========
    # arg[1] = new min_tip_amount (uint64, 8 bytes)
    on_update_min_tip = Seq([
        Assert(is_creator),
        Assert(Txn.application_args.length() == Int(2)),
        App.globalPut(min_tip_key, Btoi(Txn.application_args[1])),
        Approve()
    ])

    # ========== pause() Method ==========
    on_pause = Seq([
        Assert(is_admin),
        App.globalPut(paused_key, Int(1)),
        Approve()
    ])

    # ========== unpause() Method ==========
    on_unpause = Seq([
        Assert(is_admin),
        App.globalPut(paused_key, Int(0)),
        Approve()
    ])

    # ========== Router ==========
    method_selector = Txn.application_args[0]

    program = Cond(
        # App creation
        [Txn.application_id() == Int(0), on_creation],
        # Delete — only admin can delete
        [Txn.on_completion() == OnComplete.DeleteApplication,
         Return(is_admin)],
        # Update — only admin can update
        [Txn.on_completion() == OnComplete.UpdateApplication,
         Return(is_admin)],
        # Opt-in
        [Txn.on_completion() == OnComplete.OptIn, Approve()],
        # Close-out
        [Txn.on_completion() == OnComplete.CloseOut, Approve()],
        # NoOp — route by method selector
        [Txn.on_completion() == OnComplete.NoOp, Cond(
            [method_selector == Bytes("tip"), on_tip],
            [method_selector == Bytes("update_min_tip"), on_update_min_tip],
            [method_selector == Bytes("pause"), on_pause],
            [method_selector == Bytes("unpause"), on_unpause],
        )]
    )

    return program


def clear_program():
    """Clear state program — always approves."""
    return Approve()


if __name__ == "__main__":
    # Compile and print TEAL for inspection
    print("=== TipProxy Approval Program ===")
    print(compileTeal(approval_program(), mode=Mode.Application, version=8))
    print("\n=== TipProxy Clear State Program ===")
    print(compileTeal(clear_program(), mode=Mode.Application, version=8))
