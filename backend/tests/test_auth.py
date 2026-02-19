"""
Tests for wallet authentication middleware.

Tests: require_wallet_auth — header validation, wallet matching.
"""
# TODO FOR JULES:
# 1. Add integration tests with the actual FastAPI app (test that protected endpoints reject unauthenticated requests)
# 2. Add tests for all protected routes in creator.py (deploy, upgrade, pause, unpause, delete_template)
# 3. Add tests verifying auth bypass doesn't work (e.g., setting header after route matching)
# 4. When Ed25519 signature auth is implemented, add tests for:
#    a. Valid signature verification
#    b. Expired nonce rejection
#    c. Signature replay attack prevention
#    d. JWT token generation and validation
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock


class TestRequireWalletAuth:
    """Tests for the require_wallet_auth middleware."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_valid_header_match(self):
        """Matching header and path wallet should return the wallet."""
        from middleware.auth import require_wallet_auth
        result = await require_wallet_auth(
            wallet="TESTWALLET123",
            x_wallet_address="TESTWALLET123",
        )
        assert result == "TESTWALLET123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_header_raises_401(self):
        """Missing X-Wallet-Address header should raise 401."""
        from middleware.auth import require_wallet_auth
        with pytest.raises(HTTPException) as exc_info:
            await require_wallet_auth(
                wallet="TESTWALLET123",
                x_wallet_address=None,
            )
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mismatched_header_raises_403(self):
        """Wallet mismatch between header and URL path should raise 403."""
        from middleware.auth import require_wallet_auth
        with pytest.raises(HTTPException) as exc_info:
            await require_wallet_auth(
                wallet="WALLET_A_ADDRESS",
                x_wallet_address="WALLET_B_ADDRESS",
            )
        assert exc_info.value.status_code == 403
        assert "mismatch" in exc_info.value.detail.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_header_raises_401(self):
        """Empty string header should raise 401 (treated as missing)."""
        from middleware.auth import require_wallet_auth
        with pytest.raises(HTTPException) as exc_info:
            await require_wallet_auth(
                wallet="TESTWALLET123",
                x_wallet_address="",
            )
        # Empty string is falsy, should trigger 401
        assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_case_sensitive_match(self):
        """Wallet comparison should be case-sensitive."""
        from middleware.auth import require_wallet_auth
        with pytest.raises(HTTPException) as exc_info:
            await require_wallet_auth(
                wallet="TESTWALLET",
                x_wallet_address="testwallet",
            )
        assert exc_info.value.status_code == 403
