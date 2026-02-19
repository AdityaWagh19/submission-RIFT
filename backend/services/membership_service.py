"""
Membership Service — tiered membership sticker logic.

Fans can send tips with special MEMBERSHIP: prefixed memos to
purchase membership stickers. Each tier has:
  - Min ALGO threshold
  - Expiry duration (in days)
  - Category matching a sticker template
"""
from datetime import datetime, timedelta
from typing import Optional

MEMBERSHIP_TIERS = {
    "MEMBERSHIP:BRONZE": {
        "category": "membership_bronze",
        "min_algo": 5.0,
        "expiry_days": 30,
    },
    "MEMBERSHIP:SILVER": {
        "category": "membership_silver",
        "min_algo": 12.0,
        "expiry_days": 90,
    },
    "MEMBERSHIP:GOLD": {
        "category": "membership_gold",
        "min_algo": 40.0,
        "expiry_days": 365,
    },
}


def is_membership_memo(memo: str) -> bool:
    """Check if a tip memo indicates a membership purchase."""
    if not memo:
        return False
    return any(memo.strip().upper().startswith(k) for k in MEMBERSHIP_TIERS)


def get_tier(memo: str) -> Optional[dict]:
    """
    Look up membership tier from memo text.

    Returns tier dict {category, min_algo, expiry_days} or None.
    """
    if not memo:
        return None
    memo_upper = memo.strip().upper()
    for key, tier in MEMBERSHIP_TIERS.items():
        if memo_upper.startswith(key):
            return tier
    return None


def calculate_expiry(tier: dict) -> datetime:
    """Calculate expiry datetime from a tier definition."""
    return datetime.utcnow() + timedelta(days=tier["expiry_days"])


def get_tier_name(memo: str) -> Optional[str]:
    """Extract human-readable tier name from memo."""
    if not memo:
        return None
    memo_upper = memo.strip().upper()
    for key in MEMBERSHIP_TIERS:
        if memo_upper.startswith(key):
            return key.split(":")[1].title()  # "BRONZE" -> "Bronze"
    return None
