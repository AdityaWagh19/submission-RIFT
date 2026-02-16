"""
Payment Proxy Smart Contract for Algorand TestNet.

This contract acts as a proxy for ALGO payments:
- Users send ALGO to the contract + an app call in an atomic group
- The contract verifies the payment and forwards it to the intended receiver via inner transaction
- Tracks total number of transfers processed

Flow:
  Atomic Group:
    Txn 0: Payment from user -> contract address (amount to transfer)
    Txn 1: App Call with args ["transfer", receiver_address]
  
  Contract verifies the grouped payment and executes an inner transaction
  from the contract to the receiver.
"""

from pyteal import *

# ── Contract Metadata (read by compiler) ──────────────────────────
CONTRACT_NAME = "Payment Proxy"
CONTRACT_DESCRIPTION = "Proxy contract for forwarding ALGO payments via inner transactions"
CONTRACT_VERSION = "1.0.0"
GLOBAL_UINTS = 2   # total_transfers, total_amount
GLOBAL_BYTES = 1   # creator
LOCAL_UINTS = 0
LOCAL_BYTES = 0
CONTRACT_METHODS = ["transfer", "stats"]


def approval_program():
    """Main approval program for the Payment Proxy contract."""
    
    # ========== Global State Keys ==========
    creator_key = Bytes("creator")
    total_transfers_key = Bytes("total_transfers")
    total_amount_key = Bytes("total_amount")
    
    # ========== On Creation ==========
    on_creation = Seq([
        App.globalPut(creator_key, Txn.sender()),
        App.globalPut(total_transfers_key, Int(0)),
        App.globalPut(total_amount_key, Int(0)),
        Approve()
    ])
    
    # ========== Transfer Method ==========
    # Expects an atomic group of 2 transactions:
    #   Txn 0: Payment to the contract
    #   Txn 1: This app call with args ["transfer", receiver_address]
    
    payment_txn_index = Txn.group_index() - Int(1)
    payment_amount = Gtxn[payment_txn_index].amount()
    receiver_addr = Txn.application_args[1]
    
    on_transfer = Seq([
        # Verify this is part of a group of exactly 2
        Assert(Global.group_size() == Int(2)),
        
        # Verify the previous transaction is a payment
        Assert(Gtxn[payment_txn_index].type_enum() == TxnType.Payment),
        
        # Verify payment is sent to this contract's address
        Assert(Gtxn[payment_txn_index].receiver() == Global.current_application_address()),
        
        # Verify payment sender is the same as app caller
        Assert(Gtxn[payment_txn_index].sender() == Txn.sender()),
        
        # Verify we have the receiver argument
        Assert(Txn.application_args.length() == Int(2)),
        
        # Verify payment amount is greater than 0
        Assert(payment_amount > Int(0)),
        
        # Execute inner transaction: contract -> receiver
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: receiver_addr,
            TxnField.amount: payment_amount,
            TxnField.fee: Int(0),  # Use fee pooling from outer txn
        }),
        InnerTxnBuilder.Submit(),
        
        # Update global state counters
        App.globalPut(
            total_transfers_key,
            App.globalGet(total_transfers_key) + Int(1)
        ),
        App.globalPut(
            total_amount_key,
            App.globalGet(total_amount_key) + payment_amount
        ),
        
        Approve()
    ])
    
    # ========== Get Stats Method ==========
    # Returns contract statistics via logs
    on_stats = Seq([
        Log(Concat(
            Bytes("transfers:"),
            Itob(App.globalGet(total_transfers_key))
        )),
        Log(Concat(
            Bytes("amount:"),
            Itob(App.globalGet(total_amount_key))
        )),
        Approve()
    ])
    
    # ========== Router ==========
    method_selector = Txn.application_args[0]
    
    program = Cond(
        # App creation
        [Txn.application_id() == Int(0), on_creation],
        # Delete - only creator can delete
        [Txn.on_completion() == OnComplete.DeleteApplication,
         Return(Txn.sender() == App.globalGet(creator_key))],
        # Update - only creator can update
        [Txn.on_completion() == OnComplete.UpdateApplication,
         Return(Txn.sender() == App.globalGet(creator_key))],
        # Opt-in
        [Txn.on_completion() == OnComplete.OptIn, Approve()],
        # Close-out
        [Txn.on_completion() == OnComplete.CloseOut, Approve()],
        # NoOp - route by method
        [Txn.on_completion() == OnComplete.NoOp, Cond(
            [method_selector == Bytes("transfer"), on_transfer],
            [method_selector == Bytes("stats"), on_stats],
        )]
    )
    
    return program


def clear_program():
    """Clear state program — always approves."""
    return Approve()


if __name__ == "__main__":
    # Compile and print TEAL for inspection
    print("=== Approval Program ===")
    print(compileTeal(approval_program(), mode=Mode.Application, version=8))
    print("\n=== Clear State Program ===")
    print(compileTeal(clear_program(), mode=Mode.Application, version=8))
