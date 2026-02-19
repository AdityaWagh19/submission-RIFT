"""
Unit tests for Butki loyalty service.

Tests tip recording, badge earning logic, and idempotency.
"""
import pytest
from datetime import datetime

from services import butki_service
from db_models import FanLoyalty, LoyaltyTipEvent


@pytest.mark.asyncio
async def test_record_tip_below_threshold(db_session, sample_creator_wallet, sample_fan_wallet):
    """Tip below 0.5 ALGO should not increment loyalty."""
    result = await butki_service.record_tip(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        tx_id="tx_below_threshold",
        amount_micro=400_000,  # 0.4 ALGO
    )

    assert result["tip_count"] == 0
    assert result["earned_badge"] is False
    assert result["badges_total"] == 0


@pytest.mark.asyncio
async def test_record_tip_qualifying(db_session, sample_creator_wallet, sample_fan_wallet):
    """Qualifying tip (>= 0.5 ALGO) should increment tip_count."""
    result = await butki_service.record_tip(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        tx_id="tx_qualifying_1",
        amount_micro=500_000,  # 0.5 ALGO
    )

    assert result["tip_count"] == 1
    assert result["earned_badge"] is False  # Not 5th tip yet
    assert result["badges_total"] == 0


@pytest.mark.asyncio
async def test_record_tip_earns_badge_on_5th(db_session, sample_creator_wallet, sample_fan_wallet):
    """Every 5th tip should earn a Butki badge."""
    # Record 4 tips first
    for i in range(4):
        await butki_service.record_tip(
            db_session,
            fan_wallet=sample_fan_wallet,
            creator_wallet=sample_creator_wallet,
            tx_id=f"tx_{i}",
            amount_micro=500_000,
        )
        await db_session.commit()

    # 5th tip should earn badge
    result = await butki_service.record_tip(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        tx_id="tx_5th",
        amount_micro=500_000,
    )

    assert result["tip_count"] == 5
    assert result["earned_badge"] is True
    assert result["badges_total"] == 1


@pytest.mark.asyncio
async def test_record_tip_idempotency(db_session, sample_creator_wallet, sample_fan_wallet):
    """Same tx_id should only be processed once."""
    tx_id = "tx_duplicate"

    # First call
    result1 = await butki_service.record_tip(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        tx_id=tx_id,
        amount_micro=500_000,
    )
    await db_session.commit()

    tip_count_after_first = result1["tip_count"]

    # Second call with same tx_id should return same count (idempotent)
    result2 = await butki_service.record_tip(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        tx_id=tx_id,
        amount_micro=500_000,
    )

    assert result2["tip_count"] == tip_count_after_first
    assert result2["earned_badge"] is False  # Should not earn badge again


@pytest.mark.asyncio
async def test_get_leaderboard(db_session, sample_creator_wallet, sample_fan_wallet):
    """Leaderboard should rank by badges earned, then total tipped."""
    # Create multiple fans with different loyalty levels
    fan2 = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

    # Fan 1: 10 tips, 2 badges
    for i in range(10):
        await butki_service.record_tip(
            db_session,
            fan_wallet=sample_fan_wallet,
            creator_wallet=sample_creator_wallet,
            tx_id=f"fan1_tx_{i}",
            amount_micro=500_000,
        )
        await db_session.commit()

    # Fan 2: 3 tips, 0 badges
    for i in range(3):
        await butki_service.record_tip(
            db_session,
            fan_wallet=fan2,
            creator_wallet=sample_creator_wallet,
            tx_id=f"fan2_tx_{i}",
            amount_micro=500_000,
        )
        await db_session.commit()

    leaderboard = await butki_service.get_leaderboard(
        db_session,
        creator_wallet=sample_creator_wallet,
        limit=10,
    )

    assert len(leaderboard) == 2
    # Fan 1 should be first (more badges)
    assert leaderboard[0].fan_wallet == sample_fan_wallet
    assert leaderboard[0].butki_badges_earned == 2
    assert leaderboard[1].fan_wallet == fan2
    assert leaderboard[1].butki_badges_earned == 0
