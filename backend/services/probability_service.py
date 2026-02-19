"""
Probability Service — Golden Sticker chance engine.

Determines whether a fan's tip triggers a golden (tradable) sticker
instead of the usual soulbound sticker. Uses a configurable probability
threshold plus a guaranteed trigger after N tips.

Configuration (from .env):
    GOLDEN_THRESHOLD       — Base probability (default 0.10 = 10%)
    GOLDEN_TRIGGER_INTERVAL — Guaranteed golden every N tips (default 10)
"""
import logging
import random
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

# Seed the RNG for reproducibility in tests (can be overridden)
_rng = random.Random()


def should_mint_golden(
    tip_count: int,
    amount_algo: float = 0.0,
    override_probability: Optional[float] = None,
) -> bool:
    """
    Decide whether a tip should yield a golden sticker.

    Two paths to golden:
    1. Random chance — each tip has GOLDEN_THRESHOLD probability
    2. Guaranteed — every GOLDEN_TRIGGER_INTERVAL tips

    Higher tip amounts get a bonus to their probability:
    - 5+ ALGO: +5% bonus
    - 10+ ALGO: +10% bonus
    - 50+ ALGO: +20% bonus

    Args:
        tip_count: The creator's total tip count at this moment
        amount_algo: Tip amount in ALGO (for probability bonus)
        override_probability: Override the base probability (for testing)

    Returns:
        True if this tip should trigger a golden sticker mint
    """
    base_probability = override_probability if override_probability is not None else settings.golden_threshold
    trigger_interval = settings.golden_trigger_interval

    # Path 1: Guaranteed trigger every N tips
    if trigger_interval > 0 and tip_count > 0 and tip_count % trigger_interval == 0:
        logger.info(
            f"  🌟 Golden sticker GUARANTEED — tip #{tip_count} "
            f"(every {trigger_interval} tips)"
        )
        return True

    # Path 2: Random chance with tip-amount bonus
    probability = base_probability

    # Whale bonus — bigger tips get higher golden chance
    if amount_algo >= 50.0:
        probability += 0.20
    elif amount_algo >= 10.0:
        probability += 0.10
    elif amount_algo >= 5.0:
        probability += 0.05

    # Cap at 80% — guaranteed triggers handle the rest
    probability = min(probability, 0.80)

    roll = _rng.random()
    is_golden = roll < probability

    if is_golden:
        logger.info(
            f"  🌟 Golden sticker WON — roll={roll:.4f} < threshold={probability:.4f} "
            f"(tip #{tip_count}, {amount_algo:.2f} ALGO)"
        )
    else:
        logger.debug(
            f"  Regular sticker — roll={roll:.4f} >= threshold={probability:.4f} "
            f"(tip #{tip_count}, {amount_algo:.2f} ALGO)"
        )

    return is_golden


def get_golden_probability(
    amount_algo: float = 0.0,
) -> dict:
    """
    Calculate the current golden sticker probability for display.

    Useful for showing fans their current odds on the frontend.

    Args:
        amount_algo: Planned tip amount in ALGO

    Returns:
        dict with base_probability, bonus, total, trigger_interval
    """
    base = settings.golden_threshold
    bonus = 0.0

    if amount_algo >= 50.0:
        bonus = 0.20
    elif amount_algo >= 10.0:
        bonus = 0.10
    elif amount_algo >= 5.0:
        bonus = 0.05

    total = min(base + bonus, 0.80)

    return {
        "baseProbability": base,
        "bonus": bonus,
        "totalProbability": total,
        "triggerInterval": settings.golden_trigger_interval,
        "description": (
            f"{total:.0%} chance of golden sticker"
            + (f" (+{bonus:.0%} whale bonus)" if bonus > 0 else "")
            + f". Guaranteed every {settings.golden_trigger_interval} tips."
        ),
    }
