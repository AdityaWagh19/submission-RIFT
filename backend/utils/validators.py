"""
Input validation utilities for the Creator Sticker Platform.

Provides reusable validators for Algorand addresses and other inputs.
Security fix H1: All wallet parameters are now validated for correct format.
"""
from fastapi import HTTPException, Path, Query
from algosdk import encoding


def validate_algorand_address(address: str) -> str:
    """
    Validate an Algorand address format and checksum.

    Args:
        address: Algorand wallet address string

    Returns:
        The validated address (unchanged)

    Raises:
        HTTPException(400) if the address is invalid
    """
    if not address:
        raise HTTPException(status_code=400, detail="Wallet address is required")

    if len(address) != 58:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Algorand address: expected 58 characters, got {len(address)}"
        )

    if not encoding.is_valid_address(address):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Algorand address checksum: {address[:12]}..."
        )

    return address


def validated_wallet(wallet: str = Path(..., description="Algorand wallet address")) -> str:
    """FastAPI dependency for validating wallet path parameters."""
    return validate_algorand_address(wallet)


def validated_wallet_query(wallet: str = Query(..., description="Algorand wallet address")) -> str:
    """FastAPI dependency for validating wallet query parameters."""
    return validate_algorand_address(wallet)
