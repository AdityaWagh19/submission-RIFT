"""
Tests for Algorand address validation utility.

Tests: validate_algorand_address, validated_wallet, validated_wallet_query
"""
# TODO FOR JULES:
# 1. Add property-based tests using Hypothesis (generate random 58-char strings)
# 2. Add tests for address encoding edge cases (all zeros, all ones)
# 3. Add TestNet vs MainNet address format validation
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi import HTTPException
from utils.validators import validate_algorand_address
from conftest import VALID_WALLET_1, VALID_WALLET_2, INVALID_WALLET_SHORT, INVALID_WALLET_BAD_CHECKSUM


class TestValidateAlgorandAddress:
    """Test suite for Algorand address validation."""

    @pytest.mark.unit
    def test_valid_address_passes(self):
        """A correctly formatted Algorand address returns unchanged."""
        result = validate_algorand_address(VALID_WALLET_1)
        assert result == VALID_WALLET_1

    @pytest.mark.unit
    def test_second_valid_address_passes(self):
        """Another valid address also passes."""
        result = validate_algorand_address(VALID_WALLET_2)
        assert result == VALID_WALLET_2

    @pytest.mark.unit
    def test_empty_address_raises_400(self):
        """Empty string raises HTTP 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_algorand_address("")
        assert exc_info.value.status_code == 400
        assert "required" in exc_info.value.detail.lower()

    @pytest.mark.unit
    def test_none_address_raises_400(self):
        """None raises HTTP 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_algorand_address(None)
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_short_address_raises_400(self):
        """Address shorter than 58 chars raises HTTP 400 with length detail."""
        with pytest.raises(HTTPException) as exc_info:
            validate_algorand_address(INVALID_WALLET_SHORT)
        assert exc_info.value.status_code == 400
        assert "58 characters" in exc_info.value.detail

    @pytest.mark.unit
    def test_long_address_raises_400(self):
        """Address longer than 58 chars raises HTTP 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_algorand_address("A" * 59)
        assert exc_info.value.status_code == 400
        assert "58 characters" in exc_info.value.detail

    @pytest.mark.unit
    def test_bad_checksum_raises_400(self):
        """58-char address with bad checksum raises HTTP 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_algorand_address(INVALID_WALLET_BAD_CHECKSUM)
        assert exc_info.value.status_code == 400
        assert "checksum" in exc_info.value.detail.lower()

    @pytest.mark.unit
    def test_address_with_spaces_raises_400(self):
        """Address with spaces is invalid (length check catches it)."""
        with pytest.raises(HTTPException) as exc_info:
            validate_algorand_address("  " + VALID_WALLET_1[:56])
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_address_with_lowercase_raises_400(self):
        """Algorand addresses are base32 uppercase — lowercase should fail checksum."""
        lower = VALID_WALLET_1.lower()
        with pytest.raises(HTTPException) as exc_info:
            validate_algorand_address(lower)
        assert exc_info.value.status_code == 400
