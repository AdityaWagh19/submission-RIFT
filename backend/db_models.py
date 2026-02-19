"""
SQLAlchemy ORM models for the Creator Sticker Platform.

Tables:
    users             — wallets (creator or fan)
    contracts         — per-creator TipProxy deployments (V4)
    sticker_templates — sticker designs with IPFS hashes
    nfts              — minted NFT instances
    transactions      — tip events detected from TipProxy logs
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean, DateTime, Text, ForeignKey
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
    template_id = Column(Integer, ForeignKey("sticker_templates.id"), nullable=False)
    owner_wallet = Column(String(58), nullable=False, index=True)
    sticker_type = Column(String(20), nullable=False)  # "soulbound" | "golden"
    tx_id = Column(String(64), nullable=True)  # Algorand tx ID of the transfer to fan
    delivery_status = Column(
        String(20), nullable=False, default="delivered"
    )  # "delivered" | "pending_optin" | "failed"
    expires_at = Column(DateTime, nullable=True)  # membership expiry, null for non-membership
    minted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    template = relationship("StickerTemplate", back_populates="nfts")


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
    detected_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contract = relationship("Contract", back_populates="transactions")


class TransakOrder(Base):
    """
    Tracks fiat-to-crypto on-ramp orders via Transak.

    Lifecycle:
        1. Frontend opens Transak widget → order created (status=PENDING)
        2. Fan pays via UPI → Transak webhook updates status
        3. ALGO arrives at platform wallet → backend routes tip
        4. Listener detects on-chain tip → mints NFT
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
    fiat_amount = Column(Float, nullable=False)  # e.g., 100.0 (₹)

    # Crypto side (filled after conversion)
    crypto_amount = Column(Float, nullable=True)   # ALGO received
    network_fee = Column(Float, nullable=True)      # Transak network fee in ALGO
    transak_fee = Column(Float, nullable=True)      # Transak processing fee in fiat

    # Platform
    platform_fee_algo = Column(Float, nullable=True)  # Our cut in ALGO
    tip_amount_algo = Column(Float, nullable=True)    # ALGO actually sent to creator

    # Status tracking
    status = Column(String(30), nullable=False, default="PENDING")
    #   PENDING → PROCESSING → COMPLETED → TIP_SENT → NFT_MINTED
    #   or → FAILED / EXPIRED / REFUNDED

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
