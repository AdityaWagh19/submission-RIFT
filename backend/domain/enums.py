"""
Domain enums (minimal set used for clarity in services).
"""

from enum import Enum


class OrderStatus(str, Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

