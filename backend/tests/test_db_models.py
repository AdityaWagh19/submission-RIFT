"""
Tests for ORM database models.

Tests: Model creation, relationships, column constraints, defaults.
"""
# TODO FOR JULES:
# 1. Add tests for all model relationships (User → Contract, User → NFT, etc.)
# 2. Add tests for unique constraints (e.g., duplicate wallet registration)
# 3. Add tests for database migrations (Alembic up/down)
# 4. Add tests for cascade delete behavior
# 5. Add tests for Transaction model with all field combinations
# 6. Add tests for ListenerState model (checkpoint persistence)
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy import select


class TestUserModel:
    """Tests for the User ORM model."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        from db_models import User
        user = User(wallet_address="TEST_WALLET_001", role="creator", username="TestArtist")
        db_session.add(user)
        await db_session.commit()

        result = await db_session.execute(select(User).where(User.wallet_address == "TEST_WALLET_001"))
        fetched = result.scalar_one()
        assert fetched.username == "TestArtist"
        assert fetched.role == "creator"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_default_created_at(self, db_session):
        from db_models import User
        user = User(wallet_address="TEST_WALLET_002", role="fan")
        db_session.add(user)
        await db_session.commit()

        result = await db_session.execute(select(User).where(User.wallet_address == "TEST_WALLET_002"))
        fetched = result.scalar_one()
        assert fetched.created_at is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_without_username(self, db_session):
        from db_models import User
        user = User(wallet_address="TEST_WALLET_003", role="fan")
        db_session.add(user)
        await db_session.commit()

        result = await db_session.execute(select(User).where(User.wallet_address == "TEST_WALLET_003"))
        fetched = result.scalar_one()
        assert fetched.username is None


class TestContractModel:
    """Tests for the Contract ORM model."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_contract(self, db_session):
        from db_models import Contract
        contract = Contract(
            creator_wallet="CREATOR_WALLET_001",
            app_id=12345,
            app_address="APP_ADDR_001",
            version=1,
            active=True,
        )
        db_session.add(contract)
        await db_session.commit()

        result = await db_session.execute(select(Contract).where(Contract.app_id == 12345))
        fetched = result.scalar_one()
        assert fetched.creator_wallet == "CREATOR_WALLET_001"
        assert fetched.active is True
        assert fetched.version == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_contract_default_active(self, db_session):
        from db_models import Contract
        contract = Contract(
            creator_wallet="CREATOR_WALLET_002",
            app_id=99999,
            app_address="APP_ADDR_002",
            version=1,
        )
        db_session.add(contract)
        await db_session.commit()

        result = await db_session.execute(select(Contract).where(Contract.app_id == 99999))
        fetched = result.scalar_one()
        assert fetched.active is True  # Default should be True


class TestStickerTemplateModel:
    """Tests for the StickerTemplate ORM model."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_template(self, db_session):
        from db_models import StickerTemplate
        template = StickerTemplate(
            creator_wallet="CREATOR_001",
            name="Cool Sticker",
            sticker_type="soulbound",
            tip_threshold=1.0,
            category="tip",
            ipfs_hash="QmTestHash",
        )
        db_session.add(template)
        await db_session.commit()

        result = await db_session.execute(
            select(StickerTemplate).where(StickerTemplate.name == "Cool Sticker")
        )
        fetched = result.scalar_one()
        assert fetched.sticker_type == "soulbound"
        assert fetched.tip_threshold == 1.0


class TestNFTModel:
    """Tests for the NFT ORM model."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_nft(self, db_session):
        from db_models import NFT, StickerTemplate

        # Create template first
        template = StickerTemplate(
            creator_wallet="CREATOR_001",
            name="NFT Template",
            sticker_type="soulbound",
            tip_threshold=1.0,
            category="tip",
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        nft = NFT(
            asset_id=88888,
            template_id=template.id,
            owner_wallet="FAN_WALLET_001",
            sticker_type="soulbound",
            delivery_status="delivered",
        )
        db_session.add(nft)
        await db_session.commit()

        result = await db_session.execute(select(NFT).where(NFT.asset_id == 88888))
        fetched = result.scalar_one()
        assert fetched.owner_wallet == "FAN_WALLET_001"
        assert fetched.sticker_type == "soulbound"
        assert fetched.delivery_status == "delivered"


class TestTransactionModel:
    """Tests for the Transaction ORM model."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_transaction(self, db_session):
        from db_models import Transaction
        txn = Transaction(
            tx_id="TXID_001",
            fan_wallet="FAN_001",
            creator_wallet="CREATOR_001",
            app_id=12345,
            amount_micro=1_000_000,
            processed=False,
        )
        db_session.add(txn)
        await db_session.commit()

        result = await db_session.execute(select(Transaction).where(Transaction.tx_id == "TXID_001"))
        fetched = result.scalar_one()
        assert fetched.amount_micro == 1_000_000
        assert fetched.processed is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_transaction_default_processed_false(self, db_session):
        from db_models import Transaction
        txn = Transaction(
            tx_id="TXID_002",
            fan_wallet="FAN_001",
            creator_wallet="CREATOR_001",
            app_id=12345,
            amount_micro=500_000,
        )
        db_session.add(txn)
        await db_session.commit()

        result = await db_session.execute(select(Transaction).where(Transaction.tx_id == "TXID_002"))
        fetched = result.scalar_one()
        assert fetched.processed is False


class TestTransakOrderModel:
    """Tests for the TransakOrder ORM model."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_order(self, db_session):
        from db_models import TransakOrder
        order = TransakOrder(
            order_id="ORDER_001",
            fan_wallet="FAN_001",
            fiat_amount=10.0,
            fiat_currency="USD",
            crypto_amount=50.0,
            status="pending",
        )
        db_session.add(order)
        await db_session.commit()

        result = await db_session.execute(select(TransakOrder).where(TransakOrder.order_id == "ORDER_001"))
        fetched = result.scalar_one()
        assert fetched.fiat_amount == 10.0
        assert fetched.status == "pending"
