"""
Pytest configuration and shared fixtures for FanForge tests.

Phase 8: Provides FastAPI test client, in-memory SQLite DB, and mocks
for Algorand/Pinata services.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db
from config import settings

# ── Test Configuration ───────────────────────────────────────────────
# Set test-only values for settings that would normally come from .env
if not settings.jwt_secret:
    settings.jwt_secret = "test-jwt-secret-for-pytest-only"


# ── Database Fixtures ────────────────────────────────────────────────


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create an in-memory SQLite database session for each test.

    Uses StaticPool to allow in-memory SQLite with async SQLAlchemy.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture(scope="function")
def test_client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """
    FastAPI test client with in-memory database.

    Overrides get_db dependency to use test DB session.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# ── Mock Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def mock_algod_client():
    """Mock Algorand algod client for unit tests."""
    mock_client = MagicMock()
    mock_client.status.return_value = {"last-round": 1000}
    mock_client.suggested_params.return_value = MagicMock(fee=1000, flat_fee=True)
    mock_client.compile.return_value = {"result": "base64_compiled_teal"}
    mock_client.send_transaction.return_value = "test_tx_id_123"
    mock_client.send_raw_transaction.return_value = "test_tx_id_123"
    mock_client.application_info.return_value = {
        "params": {
            "global-state": [
                {"key": "dG90YWxfdGlwcw==", "value": {"uint": 100}},
                {"key": "dG90YWxfYW1vdW50", "value": {"uint": 5_000_000}},
            ]
        }
    }
    mock_client.account_info.return_value = {"assets": []}
    mock_client.asset_info.return_value = {
        "params": {"default-frozen": False, "total": 1}
    }

    from algorand_client import algorand_client as ac
    original_client = ac._client
    ac._client = mock_client
    yield mock_client
    ac._client = original_client


@pytest.fixture
def mock_indexer():
    """Mock Algorand Indexer for listener tests."""
    mock_responses = {
        "transactions": [],
        "next-token": None,
    }

    async def mock_get(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_responses
        mock_response.raise_for_status = MagicMock()
        return mock_response

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        yield mock_responses


@pytest.fixture
def mock_ipfs():
    """Mock Pinata IPFS service."""
    mock_upload = AsyncMock(return_value={"IpfsHash": "QmTest123"})
    mock_fetch = AsyncMock(return_value={"name": "test", "image": "ipfs://QmTest123"})

    with patch("services.ipfs_service.upload_to_ipfs", mock_upload), \
         patch("services.ipfs_service.fetch_from_ipfs", mock_fetch):
        yield {"upload": mock_upload, "fetch": mock_fetch}


# ── Test Data Fixtures ────────────────────────────────────────────────


@pytest.fixture
def sample_creator_wallet() -> str:
    """Sample creator wallet address for tests (valid Algorand address)."""
    return "CFZRI425PCKOE7PN3ICOQLFHXQMB2FLM45BYLEHXVLFHIQCU2NDCFKIHM4"


@pytest.fixture
def sample_fan_wallet() -> str:
    """Sample fan wallet address for tests (valid Algorand address)."""
    return "K2N7KBBVYX5XOZHOPM2PVRKL6DOJXLTYNKV53372QJG4YD3UH57LBHGNCE"


@pytest.fixture
async def sample_user(db_session: AsyncSession, sample_creator_wallet: str):
    """Create a sample creator user in test DB."""
    from db_models import User

    user = User(wallet_address=sample_creator_wallet, role="creator")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_contract(db_session: AsyncSession, sample_creator_wallet: str):
    """Create a sample TipProxy contract in test DB."""
    from db_models import Contract

    contract = Contract(
        creator_wallet=sample_creator_wallet,
        app_id=12345,
        app_address="APP" + "0" * 55,
        version=1,
        active=True,
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    return contract


@pytest.fixture
async def sample_template(db_session: AsyncSession, sample_creator_wallet: str):
    """Create a sample sticker template in test DB."""
    from db_models import StickerTemplate

    template = StickerTemplate(
        creator_wallet=sample_creator_wallet,
        name="Test Badge",
        category="butki_badge",
        sticker_type="soulbound",
        metadata_url="ipfs://QmTest123",
        tip_threshold=0.5,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


# ── Async Event Loop ───────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
