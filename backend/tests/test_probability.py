"""
Tests for probability service — golden sticker chance engine.

Tests: should_mint_golden, get_golden_probability
"""
# TODO FOR JULES:
# 1. Add statistical tests — run 10000 iterations and verify golden rate is within expected range
# 2. Add tests for probability cap at 80% (even with maximum whale bonus)
# 3. Add fuzz tests for extreme tip amounts (0, negative, MAX_UINT64)
# 4. Add tests for RNG seeding (reproducibility for deterministic test runs)
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
from services.probability_service import should_mint_golden, get_golden_probability


class TestShouldMintGolden:
    """Tests for should_mint_golden() logic."""

    @pytest.mark.unit
    def test_guaranteed_trigger_at_interval(self):
        """Tip count at trigger interval should always return True."""
        # Default interval is 10
        result = should_mint_golden(tip_count=10, amount_algo=1.0)
        assert result is True

    @pytest.mark.unit
    def test_guaranteed_trigger_at_multiples(self):
        """Tip count at 20, 30, etc. should also trigger."""
        assert should_mint_golden(tip_count=20, amount_algo=1.0) is True
        assert should_mint_golden(tip_count=30, amount_algo=1.0) is True
        assert should_mint_golden(tip_count=100, amount_algo=1.0) is True

    @pytest.mark.unit
    def test_zero_tip_count_no_guaranteed(self):
        """tip_count=0 should NOT trigger guaranteed (0 % N == 0 but count > 0 check protects)."""
        # With override_probability=0 to disable random path
        result = should_mint_golden(tip_count=0, amount_algo=1.0, override_probability=0.0)
        assert result is False

    @pytest.mark.unit
    def test_override_probability_zero_no_random(self):
        """With probability=0 and non-trigger count, should always return False."""
        result = should_mint_golden(tip_count=1, amount_algo=1.0, override_probability=0.0)
        assert result is False

    @pytest.mark.unit
    def test_override_probability_one_always_golden(self):
        """With probability=1.0, should always return True (random check)."""
        result = should_mint_golden(tip_count=1, amount_algo=1.0, override_probability=1.0)
        assert result is True

    @pytest.mark.unit
    def test_whale_bonus_5_algo(self):
        """5+ ALGO tip should get +5% bonus."""
        # Set base to 0 so only bonus applies — won't always trigger but bonus is applied
        # Use probability 0 + whale bonus of 0.05 → 5% chance
        prob_info = get_golden_probability(amount_algo=5.0)
        assert prob_info["bonus"] == 0.05

    @pytest.mark.unit
    def test_whale_bonus_10_algo(self):
        """10+ ALGO tip should get +10% bonus."""
        prob_info = get_golden_probability(amount_algo=10.0)
        assert prob_info["bonus"] == 0.10

    @pytest.mark.unit
    def test_whale_bonus_50_algo(self):
        """50+ ALGO tip should get +20% bonus."""
        prob_info = get_golden_probability(amount_algo=50.0)
        assert prob_info["bonus"] == 0.20

    @pytest.mark.unit
    def test_no_whale_bonus_below_5(self):
        """Tips below 5 ALGO get no bonus."""
        prob_info = get_golden_probability(amount_algo=4.99)
        assert prob_info["bonus"] == 0.0

    @pytest.mark.unit
    def test_probability_cap_at_80_percent(self):
        """Total probability should never exceed 80%."""
        prob_info = get_golden_probability(amount_algo=1000.0)
        assert prob_info["totalProbability"] <= 0.80


class TestGetGoldenProbability:
    """Tests for get_golden_probability() display calculator."""

    @pytest.mark.unit
    def test_returns_all_expected_keys(self):
        """Response should contain all required keys."""
        result = get_golden_probability(amount_algo=1.0)
        assert "baseProbability" in result
        assert "bonus" in result
        assert "totalProbability" in result
        assert "triggerInterval" in result
        assert "description" in result

    @pytest.mark.unit
    def test_description_contains_percentage(self):
        """Description should include the percentage."""
        result = get_golden_probability(amount_algo=1.0)
        assert "%" in result["description"]

    @pytest.mark.unit
    def test_description_includes_whale_bonus(self):
        """For whale tips, description should mention the bonus."""
        result = get_golden_probability(amount_algo=50.0)
        assert "whale bonus" in result["description"].lower()

    @pytest.mark.unit
    def test_base_probability_matches_settings(self):
        """Base probability should match GOLDEN_THRESHOLD from settings."""
        result = get_golden_probability(amount_algo=0.0)
        assert result["baseProbability"] == 0.10  # From test env var

    @pytest.mark.unit
    def test_total_equals_base_plus_bonus(self):
        """Total probability should equal base + bonus (capped at 0.80)."""
        result = get_golden_probability(amount_algo=10.0)
        expected = min(result["baseProbability"] + result["bonus"], 0.80)
        assert result["totalProbability"] == expected
