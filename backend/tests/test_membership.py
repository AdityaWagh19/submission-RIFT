"""
Tests for membership service — tier logic.

Tests: is_membership_memo, get_tier, calculate_expiry, get_tier_name
"""
# TODO FOR JULES:
# 1. Add tests for membership upgrade paths (e.g., Bronze → Silver while Bronze is active)
# 2. Add tests for expiry date calculations across timezones
# 3. Add tests for concurrent membership purchases
# 4. Add integration test with NFT minting (membership purchase → correct NFT minted)
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
from services.membership_service import (
    is_membership_memo,
    get_tier,
    calculate_expiry,
    get_tier_name,
    MEMBERSHIP_TIERS,
)


class TestIsMembershipMemo:
    """Tests for is_membership_memo()."""

    @pytest.mark.unit
    def test_bronze_memo(self):
        assert is_membership_memo("MEMBERSHIP:BRONZE") is True

    @pytest.mark.unit
    def test_silver_memo(self):
        assert is_membership_memo("MEMBERSHIP:SILVER") is True

    @pytest.mark.unit
    def test_gold_memo(self):
        assert is_membership_memo("MEMBERSHIP:GOLD") is True

    @pytest.mark.unit
    def test_case_insensitive(self):
        """Memo matching should be case-insensitive."""
        assert is_membership_memo("membership:bronze") is True
        assert is_membership_memo("Membership:Gold") is True

    @pytest.mark.unit
    def test_with_extra_text(self):
        """Memo with extra text after tier should still match (startswith)."""
        assert is_membership_memo("MEMBERSHIP:BRONZE extra text here") is True

    @pytest.mark.unit
    def test_with_whitespace(self):
        """Leading/trailing whitespace should be handled."""
        assert is_membership_memo("  MEMBERSHIP:BRONZE  ") is True

    @pytest.mark.unit
    def test_regular_memo_returns_false(self):
        assert is_membership_memo("Thanks for the great content!") is False

    @pytest.mark.unit
    def test_empty_memo_returns_false(self):
        assert is_membership_memo("") is False

    @pytest.mark.unit
    def test_none_memo_returns_false(self):
        assert is_membership_memo(None) is False

    @pytest.mark.unit
    def test_partial_keyword_returns_false(self):
        assert is_membership_memo("MEMBERSHIP:") is False
        assert is_membership_memo("MEMBERSHIP") is False


class TestGetTier:
    """Tests for get_tier()."""

    @pytest.mark.unit
    def test_bronze_tier(self):
        tier = get_tier("MEMBERSHIP:BRONZE")
        assert tier is not None
        assert tier["category"] == "membership_bronze"
        assert tier["min_algo"] == 5.0
        assert tier["expiry_days"] == 30

    @pytest.mark.unit
    def test_silver_tier(self):
        tier = get_tier("MEMBERSHIP:SILVER")
        assert tier is not None
        assert tier["category"] == "membership_silver"
        assert tier["min_algo"] == 12.0
        assert tier["expiry_days"] == 90

    @pytest.mark.unit
    def test_gold_tier(self):
        tier = get_tier("MEMBERSHIP:GOLD")
        assert tier is not None
        assert tier["category"] == "membership_gold"
        assert tier["min_algo"] == 40.0
        assert tier["expiry_days"] == 365

    @pytest.mark.unit
    def test_invalid_memo_returns_none(self):
        assert get_tier("regular tip") is None

    @pytest.mark.unit
    def test_empty_returns_none(self):
        assert get_tier("") is None

    @pytest.mark.unit
    def test_none_returns_none(self):
        assert get_tier(None) is None


class TestCalculateExpiry:
    """Tests for calculate_expiry()."""

    @pytest.mark.unit
    def test_bronze_expiry_30_days(self):
        tier = MEMBERSHIP_TIERS["MEMBERSHIP:BRONZE"]
        expiry = calculate_expiry(tier)
        expected = datetime.utcnow() + timedelta(days=30)
        # Allow 1 second tolerance
        assert abs((expiry - expected).total_seconds()) < 1.0

    @pytest.mark.unit
    def test_gold_expiry_365_days(self):
        tier = MEMBERSHIP_TIERS["MEMBERSHIP:GOLD"]
        expiry = calculate_expiry(tier)
        expected = datetime.utcnow() + timedelta(days=365)
        assert abs((expiry - expected).total_seconds()) < 1.0

    @pytest.mark.unit
    def test_expiry_is_in_future(self):
        for key, tier in MEMBERSHIP_TIERS.items():
            expiry = calculate_expiry(tier)
            assert expiry > datetime.utcnow()


class TestGetTierName:
    """Tests for get_tier_name()."""

    @pytest.mark.unit
    def test_bronze_name(self):
        assert get_tier_name("MEMBERSHIP:BRONZE") == "Bronze"

    @pytest.mark.unit
    def test_silver_name(self):
        assert get_tier_name("MEMBERSHIP:SILVER") == "Silver"

    @pytest.mark.unit
    def test_gold_name(self):
        assert get_tier_name("MEMBERSHIP:GOLD") == "Gold"

    @pytest.mark.unit
    def test_invalid_returns_none(self):
        assert get_tier_name("regular tip") is None

    @pytest.mark.unit
    def test_none_returns_none(self):
        assert get_tier_name(None) is None
