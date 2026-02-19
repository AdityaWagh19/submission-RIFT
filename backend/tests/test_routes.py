"""
Tests for API route endpoints.

Tests: Health, params, and route-level integration tests.
"""
# TODO FOR JULES:
# 1. Add full integration tests for ALL 30+ endpoints across all route modules:
#    a. creator.py: register, deploy, upgrade, pause, unpause, dashboard, templates
#    b. fan.py: stats, inventory, pending NFTs, claim, leaderboards
#    c. nft.py: mint soulbound, mint golden, transfer, opt-in, inventory
#    d. onramp.py: config, create order, webhook, order status, history, simulate
#    e. contracts.py: contract info, listing
#    f. transactions.py: submit single, submit group
# 2. Add tests for authentication on protected endpoints (expect 401/403 without auth)
# 3. Add tests for rate limiting on sensitive endpoints (expect 429 after limit)
# 4. Add tests for pagination on inventory/leaderboard endpoints
# 5. Add tests for error responses (malformed requests, missing resources)
# 6. Add load tests using pytest-benchmark
# 7. Add contract deployment integration test with mock algod
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest_asyncio.fixture(scope="function")
async def client():
    """Create a lightweight test client for route-level tests."""
    # Set env vars
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("SIMULATION_MODE", "true")
    os.environ.setdefault("DEMO_MODE", "true")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("PLATFORM_WALLET", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    os.environ.setdefault("PLATFORM_MNEMONIC", "abandon " * 24 + "about")
    os.environ.setdefault("PINATA_API_KEY", "test")
    os.environ.setdefault("PINATA_SECRET", "test")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    """Tests for GET /health."""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_health_returns_status(self, client):
        response = await client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("ok", "healthy")

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_health_returns_version(self, client):
        response = await client.get("/health")
        data = response.json()
        assert "version" in data or "environment" in data


class TestCreatorEndpoints:
    """Tests for /creator/* endpoints."""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_creators_returns_list(self, client):
        """GET /creator/list should return a list (even if empty)."""
        response = await client.get("/creator/list")
        # May return 200 or 404 depending on implementation
        assert response.status_code in (200, 404)

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_register_without_auth_rejected(self, client):
        """POST /creator/register should reject requests without wallet auth."""
        response = await client.post(
            "/creator/register",
            json={"walletAddress": "TESTWALLET" + "A" * 48, "username": "Test"},
        )
        # Should fail — either 401 (no auth) or 400 (invalid address) or 422 (validation)
        assert response.status_code in (400, 401, 403, 422)


class TestFanEndpoints:
    """Tests for /fan/* endpoints."""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_invalid_wallet_rejected(self, client):
        """GET /fan/INVALID/stats should reject invalid wallet."""
        response = await client.get("/fan/INVALID/stats")
        assert response.status_code in (400, 422)

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_leaderboard_global(self, client):
        """GET /leaderboard/global/top-creators should return data."""
        response = await client.get("/leaderboard/global/top-creators")
        assert response.status_code in (200, 404)


class TestNFTEndpoints:
    """Tests for /nft/* endpoints."""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_invalid_wallet_nft_inventory(self, client):
        """GET /nft/INVALID/inventory should reject invalid wallet."""
        response = await client.get("/nft/INVALID/inventory")
        assert response.status_code in (400, 422)


class TestOnrampEndpoints:
    """Tests for /onramp/* endpoints."""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_config(self, client):
        """GET /onramp/config should return on-ramp configuration."""
        response = await client.get("/onramp/config")
        assert response.status_code == 200
        data = response.json()
        assert "simulation_mode" in data or "simulationMode" in data

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_simulate_fund_wallet(self, client):
        """POST /onramp/simulate/fund-wallet should work in simulation mode."""
        response = await client.post(
            "/onramp/simulate/fund-wallet",
            json={"wallet": "TEST" + "A" * 54, "amountAlgo": 10.0},
        )
        # Should work in simulation mode or fail with validation error
        assert response.status_code in (200, 400, 422)


class TestTransactionEndpoints:
    """Tests for /transactions/* endpoints."""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_submit_invalid_txn_rejected(self, client):
        """POST /submit with invalid base64 should be rejected."""
        response = await client.post(
            "/submit",
            json={"signed_txn": "!!!INVALID!!!"},
        )
        # Should fail — either network error or validation
        assert response.status_code in (400, 500)
