"""
Custom exception classes for Algorand operations.
"""


class AlgorandNodeError(Exception):
    """Raised when there's an issue connecting to the Algorand node."""
    pass


class TransactionValidationError(Exception):
    """Raised when transaction validation fails."""
    pass


class InsufficientBalanceError(Exception):
    """Raised when account has insufficient balance for transaction."""
    pass
