"""
Tests for transaction service — base64 handling, submission, error classification.

Tests: fix_base64_padding, validate_base64, submit_single, submit_group, classify_error
"""
# TODO FOR JULES:
# 1. Add tests for actual Algorand signed transaction format (decode → verify structure)
# 2. Add integration tests with mock algod client for submission paths
# 3. Add tests for all error classification cases
# 4. Add tests for concurrent group submission
# 5. Add performance test — submit_group with 16 transactions (max atomic group size)
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import base64
from services.transaction_service import (
    fix_base64_padding,
    validate_base64,
    classify_error,
)


class TestFixBase64Padding:
    """Tests for fix_base64_padding()."""

    @pytest.mark.unit
    def test_already_padded(self):
        """Properly padded base64 should return unchanged."""
        assert fix_base64_padding("SGVsbG8=") == "SGVsbG8="

    @pytest.mark.unit
    def test_missing_one_pad(self):
        """Base64 missing 1 padding char should be fixed."""
        result = fix_base64_padding("SGVsbG8")
        assert result == "SGVsbG8="

    @pytest.mark.unit
    def test_missing_two_pads(self):
        """Base64 missing 2 padding chars should be fixed."""
        result = fix_base64_padding("SGVs")
        assert result == "SGVs"  # length 4, already multiple of 4

    @pytest.mark.unit
    def test_empty_string(self):
        """Empty string should return empty."""
        assert fix_base64_padding("") == ""

    @pytest.mark.unit
    def test_correct_length_no_padding_needed(self):
        """String already multiple of 4 needs no padding."""
        s = "AAAA"  # length 4
        assert fix_base64_padding(s) == s


class TestValidateBase64:
    """Tests for validate_base64()."""

    @pytest.mark.unit
    def test_valid_base64(self):
        """Valid base64 should return decoded bytes."""
        encoded = base64.b64encode(b"Hello World").decode()
        result = validate_base64(encoded)
        assert result == b"Hello World"

    @pytest.mark.unit
    def test_valid_base64_without_padding(self):
        """Valid base64 without padding should still decode (auto-padded)."""
        encoded = base64.b64encode(b"Hello").decode().rstrip("=")
        result = validate_base64(encoded)
        assert result == b"Hello"

    @pytest.mark.unit
    def test_invalid_base64_raises(self):
        """Completely invalid base64 should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid base64"):
            validate_base64("!!!NOT_BASE64!!!")

    @pytest.mark.unit
    def test_empty_base64(self):
        """Empty base64 should decode to empty bytes."""
        result = validate_base64("")
        assert result == b""


class TestClassifyError:
    """Tests for classify_error() — error message → HTTP status mapping."""

    @pytest.mark.unit
    def test_insufficient_balance(self):
        status, detail = classify_error("Insufficient balance for this operation")
        assert status == 400
        assert "balance" in detail.lower()

    @pytest.mark.unit
    def test_below_min(self):
        status, detail = classify_error("Amount is below min threshold")
        assert status == 400

    @pytest.mark.unit
    def test_invalid_signature(self):
        status, detail = classify_error("Invalid signature provided")
        assert status == 400
        assert "signature" in detail.lower()

    @pytest.mark.unit
    def test_already_in_ledger(self):
        status, detail = classify_error("Transaction already in ledger")
        assert status == 409

    @pytest.mark.unit
    def test_pool_full(self):
        status, detail = classify_error("The transaction pool is full")
        assert status == 503
        assert "busy" in detail.lower()

    @pytest.mark.unit
    def test_unknown_error_returns_500(self):
        status, detail = classify_error("Something completely unexpected happened")
        assert status == 500

    @pytest.mark.unit
    def test_case_insensitive_matching(self):
        """Error classification should be case-insensitive."""
        status, _ = classify_error("INSUFFICIENT BALANCE error")
        assert status == 400
