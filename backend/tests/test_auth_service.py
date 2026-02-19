"""
Unit tests for authentication service.

Tests challenge generation, signature verification, and JWT issuance.
"""
import pytest
from fastapi import status

from db_models import AuthChallenge
from middleware.auth import decode_access_token, issue_access_token


@pytest.mark.asyncio
async def test_create_challenge_via_http(test_client, db_session, sample_fan_wallet):
    """Challenge creation via HTTP should generate nonce and store in DB."""
    response = test_client.post(
        "/auth/challenge",
        json={"walletAddress": sample_fan_wallet},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["walletAddress"] == sample_fan_wallet
    assert data["nonce"] is not None
    assert len(data["nonce"]) > 0
    assert data["expiresAt"] is not None
    assert "FanForge authentication" in data["message"]

    # Verify stored in DB
    from sqlalchemy import select
    result = await db_session.execute(
        select(AuthChallenge).where(AuthChallenge.wallet_address == sample_fan_wallet)
    )
    challenge = result.scalar_one_or_none()
    assert challenge is not None
    assert challenge.nonce == data["nonce"]


@pytest.mark.asyncio
async def test_verify_challenge_invalid_signature_via_http(test_client, db_session, sample_fan_wallet):
    """Invalid signature via HTTP should return 400/401."""
    # Create challenge first
    challenge_response = test_client.post(
        "/auth/challenge",
        json={"walletAddress": sample_fan_wallet},
    )
    assert challenge_response.status_code == status.HTTP_200_OK
    challenge_data = challenge_response.json()

    # Verify with invalid signature
    verify_response = test_client.post(
        "/auth/verify",
        json={
            "walletAddress": sample_fan_wallet,
            "nonce": challenge_data["nonce"],
            "signature": "invalid_signature_base64",
        },
    )

    assert verify_response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED]


@pytest.mark.asyncio
async def test_issue_access_token(sample_fan_wallet):
    """JWT token should contain wallet and role."""
    token = issue_access_token(wallet_address=sample_fan_wallet, role="fan")

    assert token is not None
    assert len(token) > 0

    # Decode and verify payload
    payload = decode_access_token(token)
    assert payload["sub"] == sample_fan_wallet
    assert payload["role"] == "fan"
    assert "exp" in payload
    assert "iat" in payload
