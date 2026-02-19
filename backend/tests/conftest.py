"""
Shared test fixtures for the Creator Sticker Platform test suite.

Provides:
    - Async SQLite test database (in-memory)
    - FastAPI test client with all routes
    - Mock wallets (valid Algorand addresses)
    - Mock Algorand client
    - Authentication helpers
    - Factory fixtures for creating test data
"""
import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Override settings BEFORE importing app ──────────────────────────
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SIMULATION_MODE"] = "true"
os.environ["DEMO_MODE"] = "true"
os.environ["ENVIRONMENT"] = "development"
os.environ["PLATFORM_WALLET"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
os.environ["PLATFORM_MNEMONIC"] = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
os.environ["PINATA_API_KEY"] = "test_pinata_key"
os.environ["PINATA_SECRET"] = "test_pinata_secret"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["GOLDEN_THRESHOLD"] = "0.10"
os.environ["GOLDEN_TRIGGER_INTERVAL"] = "10"


# ── Valid Algorand test addresses (real format, TestNet) ────────────
# These are well-known Algorand addresses used for testing
VALID_WALLET_1 = "GD64YIY3TWGDMCNPP553DZPPR6LDUSFQOIJVFDPPNRL3NMKBER23VHQCTI"
VALID_WALLET_2 = "EQC53QLKJKHH73WFOQRAAP6XKY3Z5TMCPXYCUHDOMHAKR3PH2HJFQGMKBY"
INVALID_WALLET_SHORT = "AAAA"
INVALID_WALLET_BAD_CHECKSUM = "A" * 58


# ── Database Fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    from database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Create a fresh database session for each test."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_client(db_engine):
    """
    Create an async test client with the real FastAPI app.
    Overrides the database dependency to use the test database.
    """
    from database import Base, get_db

    # Override the DB dependency
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    from main import app
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ── Auth Helper ────────────────────────────────────────────────────

def auth_headers(wallet: str) -> dict:
    """Generate authentication headers for a given wallet."""
    return {"X-Wallet-Address": wallet}


# ── Factory Fixtures ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def create_user(db_session):
    """Factory fixture to create a User in the test DB."""
    from db_models import User

    async def _create(wallet: str = VALID_WALLET_1, role: str = "creator", username: str = "TestCreator"):
        user = User(wallet_address=wallet, role=role, username=username)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create


@pytest_asyncio.fixture
async def create_contract(db_session, create_user):
    """Factory fixture to create a Contract in the test DB."""
    from db_models import Contract

    async def _create(wallet: str = VALID_WALLET_1, app_id: int = 12345, app_address: str = "APPADDRESS"):
        # Ensure user exists
        await create_user(wallet=wallet)
        contract = Contract(
            creator_wallet=wallet,
            app_id=app_id,
            app_address=app_address,
            version=1,
            active=True,
        )
        db_session.add(contract)
        await db_session.commit()
        await db_session.refresh(contract)
        return contract

    return _create


@pytest_asyncio.fixture
async def create_template(db_session):
    """Factory fixture to create a StickerTemplate in the test DB."""
    from db_models import StickerTemplate

    async def _create(
        creator_wallet: str = VALID_WALLET_1,
        name: str = "Test Sticker",
        sticker_type: str = "soulbound",
        tip_threshold: float = 1.0,
        ipfs_hash: str = "QmTestHash123",
        metadata_url: str = "https://gateway.pinata.cloud/ipfs/QmTestMeta123",
    ):
        template = StickerTemplate(
            creator_wallet=creator_wallet,
            name=name,
            sticker_type=sticker_type,
            tip_threshold=tip_threshold,
            ipfs_hash=ipfs_hash,
            image_url=f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}",
            metadata_url=metadata_url,
            category="tip",
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        return template

    return _create


@pytest_asyncio.fixture
async def create_nft(db_session, create_template):
    """Factory fixture to create an NFT in the test DB."""
    from db_models import NFT

    async def _create(
        asset_id: int = 99999,
        owner_wallet: str = VALID_WALLET_2,
        sticker_type: str = "soulbound",
        template_id: int = None,
    ):
        if template_id is None:
            template = await create_template()
            template_id = template.id

        nft = NFT(
            asset_id=asset_id,
            template_id=template_id,
            owner_wallet=owner_wallet,
            sticker_type=sticker_type,
            delivery_status="delivered",
        )
        db_session.add(nft)
        await db_session.commit()
        await db_session.refresh(nft)
        return nft

    return _create


@pytest_asyncio.fixture
async def create_transaction(db_session, create_contract):
    """Factory fixture to create a Transaction in the test DB."""
    from db_models import Transaction

    async def _create(
        tx_id: str = "TESTTXID123",
        fan_wallet: str = VALID_WALLET_2,
        creator_wallet: str = VALID_WALLET_1,
        app_id: int = 12345,
        amount_micro: int = 1_000_000,
        processed: bool = True,
    ):
        txn = Transaction(
            tx_id=tx_id,
            fan_wallet=fan_wallet,
            creator_wallet=creator_wallet,
            app_id=app_id,
            amount_micro=amount_micro,
            processed=processed,
        )
        db_session.add(txn)
        await db_session.commit()
        await db_session.refresh(txn)
        return txn

    return _create


# ── Mock Algorand Client ──────────────────────────────────────────

@pytest.fixture
def mock_algod():
    """Mock the Algorand algod client."""
    mock = MagicMock()
    mock.suggested_params.return_value = MagicMock(
        fee=1000,
        first=1000,
        last=2000,
        gh="SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
        gen="testnet-v1.0",
        flat_fee=True,
        min_fee=1000,
    )
    mock.status.return_value = {"last-round": 1000}
    mock.send_raw_transaction.return_value = "MOCKTXID123456"
    return mock
