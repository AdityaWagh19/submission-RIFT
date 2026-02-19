"""
SQLAlchemy ORM models for the Creator Sticker Platform.

Tables:
    users             — wallets (creator or fan)
    contracts         — per-creator TipProxy deployments (V4)
    sticker_templates — sticker designs with IPFS hashes
    nfts              — minted NFT instances
    transactions      — tip events detected from TipProxy logs
    fan_loyalty       — per-fan-per-creator Butki loyalty tracking
    memberships       — Bauni time-bound membership passes
    shawty_tokens     — Shawty transferable utility NFTs
    redemptions       — Shawty burn/lock redemption history
    auth_challenges   — wallet login nonces for signature verification
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean, DateTime, Text, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    """Wallet addresses for creators and fans."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_address = Column(String(58), unique=True, nullable=False, index=True)
    role = Column(String(20), nullable=False, default="fan")  # "creator" | "fan"
    username = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contracts = relationship("Contract", back_populates="creator", lazy="select")


class Contract(Base):
    """Per-creator TipProxy smart contract deployments (V4)."""
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_wallet = Column(
        String(58),
        ForeignKey("users.wallet_address"),
        nullable=False,
        index=True,
    )
    app_id = Column(Integer, unique=True, nullable=False, index=True)
    app_address = Column(String(58), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True)
    deployed_at = Column(DateTime, default=datetime.utcnow)
    upgraded_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("User", back_populates="contracts")
    transactions = relationship("Transaction", back_populates="contract", lazy="select")


class StickerTemplate(Base):
    """Sticker designs configured by creators."""
    __tablename__ = "sticker_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_wallet = Column(String(58), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    ipfs_hash = Column(String(100), nullable=True)
    image_url = Column(Text, nullable=True)
    metadata_url = Column(Text, nullable=True)
    sticker_type = Column(String(20), nullable=False, default="soulbound")  # "soulbound" | "golden"
    category = Column(String(50), nullable=False, default="tip")  # "tip" | "membership_bronze" | etc.
    tip_threshold = Column(Float, nullable=False, default=1.0)  # min ALGO to earn this sticker
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    nfts = relationship("NFT", back_populates="template", lazy="select")


class NFT(Base):
    """Minted NFT instances — one row per ASA created."""
    __tablename__ = "nfts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, unique=True, nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("sticker_templates.id"), nullable=False, index=True)
    owner_wallet = Column(String(58), nullable=False, index=True)
    sticker_type = Column(String(20), nullable=False)  # "soulbound" | "golden"
    nft_class = Column(String(20), nullable=True)  # "butki" | "bauni" | "shawty" | None (legacy)
    tx_id = Column(String(64), nullable=True)  # Algorand tx ID of the transfer to fan
    delivery_status = Column(
        String(20), nullable=False, default="delivered"
    )  # "delivered" | "pending_optin" | "failed"
    expires_at = Column(DateTime, nullable=True)  # membership expiry, null for non-membership
    is_burned = Column(Boolean, nullable=False, default=False)  # Shawty burn state
    is_locked = Column(Boolean, nullable=False, default=False)  # Shawty lock for discount
    minted_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    template = relationship("StickerTemplate", back_populates="nfts")

    # Phase 6: Composite indexes for common query patterns
    __table_args__ = (
        # For fan NFT inventory: filter by owner_wallet and sticker_type
        Index("ix_nfts_owner_type", "owner_wallet", "sticker_type"),
        # For creator NFT counts: join with StickerTemplate on template_id and creator_wallet
        Index("ix_nfts_template_minted", "template_id", "minted_at"),
    )


class Transaction(Base):
    """Tip events detected from TipProxy on-chain logs."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tx_id = Column(String(64), unique=True, nullable=False, index=True)  # Algorand tx ID (dedup key)
    fan_wallet = Column(String(58), nullable=False, index=True)
    creator_wallet = Column(String(58), nullable=False, index=True)
    app_id = Column(Integer, ForeignKey("contracts.app_id"), nullable=False)  # V4: TipProxy that processed it
    amount_micro = Column(BigInteger, nullable=False)  # microAlgos (1 ALGO = 1_000_000)
    memo = Column(Text, nullable=True)
    processed = Column(Boolean, nullable=False, default=False)  # has minting pipeline run?
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    contract = relationship("Contract", back_populates="transactions")

    # Phase 6: Composite indexes for common query patterns
    __table_args__ = (
        # For leaderboard queries: group by creator_wallet, order by amount
        Index("ix_transactions_creator_amount", "creator_wallet", "amount_micro"),
        # For fan stats: filter by fan_wallet, order by detected_at
        Index("ix_transactions_fan_detected", "fan_wallet", "detected_at"),
        # For processed status queries (listener retry task)
        Index("ix_transactions_processed_detected", "processed", "detected_at"),
    )


class SubmittedTransaction(Base):
    """
    Idempotency table for client-submitted transactions (/submit, /submit-group).

    Phase 3 requirement: store idempotency key -> tx_id mapping with a short TTL
    so clients can safely retry without accidental duplicate submissions.
    """

    __tablename__ = "submitted_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)
    tx_id = Column(String(64), nullable=False, index=True)
    request_hash = Column(String(64), nullable=True)  # sha256 hex of request payload
    kind = Column(String(20), nullable=False, default="single")  # "single" | "group"
    status = Column(String(20), nullable=False, default="submitted")  # submitted | failed
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)


# ════════════════════════════════════════════════════════════════════
# BUTKI — Loyalty / Tipping Token Tracking
# ════════════════════════════════════════════════════════════════════

class FanLoyalty(Base):
    """
    Tracks per-fan-per-creator loyalty for Butki badges.

    Each row = one fan's relationship with one creator.
    tip_count increments on every qualifying tip (>= 0.5 ALGO).
    Every 5th tip earns 1 Butki badge (butki_badges_earned counter).
    """
    __tablename__ = "fan_loyalty"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fan_wallet = Column(String(58), nullable=False, index=True)
    creator_wallet = Column(String(58), nullable=False, index=True)
    tip_count = Column(Integer, nullable=False, default=0)
    total_tipped_micro = Column(BigInteger, nullable=False, default=0)  # running sum in microAlgos

    # Butki badge count — incremented every 5th tip
    butki_badges_earned = Column(Integer, nullable=False, default=0)
    last_badge_asset_id = Column(Integer, nullable=True)  # ASA ID of most recent badge

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("fan_wallet", "creator_wallet", name="uq_fan_creator_loyalty"),
        # Phase 6: Composite index for Butki leaderboard queries
        # Order by butki_badges_earned DESC, total_tipped_micro DESC
        Index("ix_fan_loyalty_creator_badges_tipped", "creator_wallet", "butki_badges_earned", "total_tipped_micro"),
    )


class LoyaltyTipEvent(Base):
    """
    Idempotency table for Butki loyalty increments.

    Each qualifying tip transaction should only increment loyalty once.
    This table prevents duplicate increments during listener retries.
    """

    __tablename__ = "loyalty_tip_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tx_id = Column(String(64), unique=True, nullable=False, index=True)
    fan_wallet = Column(String(58), nullable=False, index=True)
    creator_wallet = Column(String(58), nullable=False, index=True)
    amount_micro = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════
# BAUNI — Membership NFT (Time-Bound)
# ════════════════════════════════════════════════════════════════════

class Membership(Base):
    """
    Tracks Bauni membership passes per fan per creator.

    Cost: 5 ALGO, validity: 30 days.
    Expired memberships auto-revoke access.
    Renewal before expiry extends by +30 days.
    """
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fan_wallet = Column(String(58), nullable=False, index=True)
    creator_wallet = Column(String(58), nullable=False, index=True)
    asset_id = Column(Integer, nullable=False, index=True)  # Bauni ASA on Algorand
    purchased_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    purchase_tx_id = Column(String(64), nullable=True)  # the tip TX that triggered this
    amount_paid_micro = Column(BigInteger, nullable=False, default=5_000_000)  # 5 ALGO in microAlgos

    __table_args__ = (
        # One active membership per fan/creator pair
        UniqueConstraint(
            "fan_wallet",
            "creator_wallet",
            "is_active",
            name="uq_membership_fan_creator_active",
        ),
        # Prevent duplicate on-chain Bauni tokens from being tracked twice
        UniqueConstraint("asset_id", name="uq_membership_asset_id"),
        # Phase 6: Composite index for membership verification queries
        # Filter by fan_wallet + creator_wallet + is_active + expires_at
        Index("ix_memberships_fan_creator_active_expires", "fan_wallet", "creator_wallet", "is_active", "expires_at"),
    )


# ════════════════════════════════════════════════════════════════════
# SHAWTY — Transactional Utility NFT
# ════════════════════════════════════════════════════════════════════

class ShawtyToken(Base):
    """
    Tracks Shawty transferable utility NFTs.

    Cost: 2 ALGO, no expiration.
    Can be burned for merch or locked for discount.
    Fully transferable between wallets.
    """
    __tablename__ = "shawty_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, unique=True, nullable=False, index=True)
    owner_wallet = Column(String(58), nullable=False, index=True)
    creator_wallet = Column(String(58), nullable=False, index=True)  # which creator's store
    purchase_tx_id = Column(String(64), nullable=True)
    amount_paid_micro = Column(BigInteger, nullable=False, default=2_000_000)  # 2 ALGO
    is_burned = Column(Boolean, nullable=False, default=False)
    is_locked = Column(Boolean, nullable=False, default=False)  # locked for discount
    burned_at = Column(DateTime, nullable=True)
    locked_at = Column(DateTime, nullable=True)
    purchased_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        # Ensure each purchase transaction only registers a single Shawty token
        UniqueConstraint("purchase_tx_id", name="uq_shawty_purchase_tx_id"),
    )


class Redemption(Base):
    """
    Records Shawty redemption events (burn for merch, lock for discount).
    Prevents double-spending.
    """
    __tablename__ = "redemptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shawty_asset_id = Column(Integer, ForeignKey("shawty_tokens.asset_id"), nullable=False, index=True)
    fan_wallet = Column(String(58), nullable=False, index=True)
    redemption_type = Column(String(20), nullable=False)  # "burn_merch" | "lock_discount"
    description = Column(Text, nullable=True)  # e.g., "T-shirt XL" or "10% off next tip"
    redeemed_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════
# Merch & Discounts
# ════════════════════════════════════════════════════════════════════

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_wallet = Column(String(58), ForeignKey("users.wallet_address"), nullable=False, index=True)
    slug = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    image_ipfs_hash = Column(String(100), nullable=True)
    price_algo = Column(Float, nullable=False, default=1.0)
    currency = Column(String(10), nullable=False, default="ALGO")
    max_per_order = Column(Integer, nullable=False, default=5)
    stock_quantity = Column(Integer, nullable=True)  # null => unlimited
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("creator_wallet", "slug", name="uq_product_creator_slug"),
    )


class DiscountRule(Base):
    __tablename__ = "discount_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_wallet = Column(String(58), ForeignKey("users.wallet_address"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)  # null => applies to all products
    discount_type = Column(String(20), nullable=False, default="PERCENT")  # PERCENT | FIXED_ALGO
    value = Column(Float, nullable=False, default=10.0)  # percent or ALGO
    min_shawty_tokens = Column(Integer, nullable=False, default=0)
    requires_bauni = Column(Boolean, nullable=False, default=False)
    max_uses_per_wallet = Column(Integer, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fan_wallet = Column(String(58), nullable=False, index=True)
    creator_wallet = Column(String(58), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="PENDING_PAYMENT", index=True)  # PENDING_PAYMENT | PAID | CANCELLED
    subtotal_algo = Column(Float, nullable=False, default=0.0)
    discount_algo = Column(Float, nullable=False, default=0.0)
    total_algo = Column(Float, nullable=False, default=0.0)
    shawty_asset_ids_used = Column(Text, nullable=True)  # JSON list of asset IDs
    tx_id = Column(String(64), nullable=True, index=True)  # payment tx id detected by listener
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    paid_at = Column(DateTime, nullable=True)

    # Phase 6: Composite indexes for order queries
    __table_args__ = (
        # For fan order history: filter by fan_wallet, order by created_at DESC
        Index("ix_orders_fan_created", "fan_wallet", "created_at"),
        # For order settlement: filter by status and creator_wallet
        Index("ix_orders_status_creator", "status", "creator_wallet"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_algo = Column(Float, nullable=False, default=0.0)
    discount_algo = Column(Float, nullable=False, default=0.0)


# ════════════════════════════════════════════════════════════════════
# Auth Challenges (Signature-based Wallet Login)
# ════════════════════════════════════════════════════════════════════

class AuthChallenge(Base):
    """
    Short-lived nonce used for wallet signature-based authentication.

    Flow:
      1) Client requests challenge for a wallet.
      2) Client signs nonce bytes with wallet (Pera).
      3) Backend verifies signature and issues JWT access token.
    """

    __tablename__ = "auth_challenges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_address = Column(String(58), nullable=False, index=True)
    nonce = Column(String(128), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("wallet_address", "nonce", name="uq_auth_challenge_wallet_nonce"),
    )


# ════════════════════════════════════════════════════════════════════
# Transak & Listener State (unchanged)
# ════════════════════════════════════════════════════════════════════

class TransakOrder(Base):
    """
    Tracks fiat-to-crypto on-ramp orders via Transak.

    Lifecycle:
        1. Frontend opens Transak widget -> order created (status=PENDING)
        2. Fan pays via UPI -> Transak webhook updates status
        3. ALGO arrives at platform wallet -> backend routes tip
        4. Listener detects on-chain tip -> mints NFT
    """
    __tablename__ = "transak_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(100), unique=True, nullable=False, index=True)  # Transak order ID
    partner_order_id = Column(String(200), unique=True, nullable=False, index=True)  # Our internal ID

    # Fan & Creator
    fan_wallet = Column(String(58), nullable=False, index=True)
    creator_wallet = Column(String(58), nullable=False, index=True)

    # Fiat side
    fiat_currency = Column(String(10), nullable=False, default="INR")
    fiat_amount = Column(Float, nullable=False)  # e.g., 100.0 (INR)

    # Crypto side (filled after conversion)
    crypto_amount = Column(Float, nullable=True)   # ALGO received
    network_fee = Column(Float, nullable=True)      # Transak network fee in ALGO
    transak_fee = Column(Float, nullable=True)      # Transak processing fee in fiat

    # Platform
    platform_fee_algo = Column(Float, nullable=True)  # Our cut in ALGO
    tip_amount_algo = Column(Float, nullable=True)    # ALGO actually sent to creator

    # Status tracking
    status = Column(String(30), nullable=False, default="PENDING")

    # Linked Algorand transaction (after tip is sent)
    tip_tx_id = Column(String(64), nullable=True)    # On-chain tip tx ID

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)   # When Transak conversion finished
    tip_sent_at = Column(DateTime, nullable=True)     # When we routed the tip on-chain


class ListenerState(Base):
    """
    Persisted state for the transaction listener.

    Stores the last processed Algorand round so the listener
    can resume from where it left off after a server restart,
    instead of re-scanning from round 0.
    """
    __tablename__ = "listener_state"

    id = Column(Integer, primary_key=True, default=1)
    last_processed_round = Column(BigInteger, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
