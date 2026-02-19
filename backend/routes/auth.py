"""
Auth endpoints — wallet signature challenge/verify.

Flow:
  1) POST /auth/challenge  -> {nonce, expires_at, message_to_sign}
  2) Client signs the nonce bytes with Pera Wallet
  3) POST /auth/verify     -> verifies signature, returns JWT access token
"""

import logging
import base64
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from db_models import AuthChallenge, User
from middleware.rate_limit import rate_limit
from middleware.auth import issue_access_token
from utils.validators import validate_algorand_address

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _now_utc() -> datetime:
    # Keep timestamps consistent with existing DB models (naive UTC via datetime.utcnow)
    return datetime.utcnow()


class ChallengeRequest(BaseModel):
    wallet_address: str = Field(..., alias="walletAddress", min_length=58, max_length=58)


class ChallengeResponse(BaseModel):
    wallet_address: str = Field(..., alias="walletAddress")
    nonce: str
    expires_at: str = Field(..., alias="expiresAt")
    message: str


class VerifyRequest(BaseModel):
    wallet_address: str = Field(..., alias="walletAddress", min_length=58, max_length=58)
    nonce: str = Field(..., min_length=16, max_length=128)
    signature: str = Field(
        ...,
        description="Base64 signature over the nonce bytes (utf-8).",
        min_length=16,
    )


class VerifyResponse(BaseModel):
    wallet_address: str = Field(..., alias="walletAddress")
    role: str
    access_token: str = Field(..., alias="accessToken")
    token_type: str = Field("Bearer", alias="tokenType")
    expires_in_seconds: int = Field(..., alias="expiresInSeconds")


@router.post("/challenge", response_model=ChallengeResponse)
async def create_challenge(
    request: ChallengeRequest,
    req: Request = None,
    db: AsyncSession = Depends(get_db),
    _rate=Depends(rate_limit(max_requests=20, window_seconds=60)),
):
    validate_algorand_address(request.wallet_address)

    nonce = secrets.token_urlsafe(32)[:64]
    now = _now_utc()
    expires_at = now + timedelta(minutes=settings.auth_challenge_ttl_minutes)

    # Best-effort cleanup: mark old unused challenges expired by leaving them as-is;
    # verification always selects a specific nonce and checks expires_at.
    db.add(
        AuthChallenge(
            wallet_address=request.wallet_address,
            nonce=nonce,
            expires_at=expires_at,
        )
    )
    await db.commit()

    message = (
        "FanForge authentication\n"
        f"Wallet: {request.wallet_address}\n"
        f"Nonce: {nonce}\n"
        f"ExpiresAt: {expires_at.isoformat()}\n"
    )

    return ChallengeResponse(
        walletAddress=request.wallet_address,
        nonce=nonce,
        expiresAt=expires_at.isoformat(),
        message=message,
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_challenge(
    request: VerifyRequest,
    req: Request = None,
    db: AsyncSession = Depends(get_db),
    _rate=Depends(rate_limit(max_requests=30, window_seconds=60)),
):
    validate_algorand_address(request.wallet_address)

    q = await db.execute(
        select(AuthChallenge)
        .where(
            AuthChallenge.wallet_address == request.wallet_address,
            AuthChallenge.nonce == request.nonce,
            AuthChallenge.used_at.is_(None),
        )
        .order_by(desc(AuthChallenge.created_at))
        .limit(1)
    )
    challenge = q.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=400, detail="Invalid or already-used nonce.")

    now = _now_utc()
    if challenge.expires_at <= now:
        raise HTTPException(status_code=400, detail="Nonce expired. Request a new challenge.")

    # Verify Ed25519 signature against Algorand address
    ok = False

    # In demo/development mode, skip signature verification
    # Pera Wallet signData format varies between SDK versions
    if settings.simulation_mode:
        logger.info(f"DEMO/SIMULATION MODE: Skipping signature verification for {request.wallet_address}")
        ok = True
    else:
        try:
            sig_bytes = base64.b64decode(request.signature)
        except Exception:
            raise HTTPException(status_code=400, detail="Signature must be base64 encoded.")

        try:
            from algosdk import util as algo_util

            # verify_bytes prepends b"MX" internally — matches Pera signData behavior
            ok = algo_util.verify_bytes(
                message=request.nonce.encode("utf-8"),
                signature=sig_bytes,
                address=request.wallet_address,
            )
            logger.info(f"verify_bytes (with MX prefix) result: {ok}")
        except Exception as e:
            logger.warning(f"verify_bytes (MX) failed: {e}")

        if not ok:
            # Fallback: try raw Ed25519 verification without MX prefix
            try:
                from nacl.signing import VerifyKey
                from algosdk import encoding

                vk = VerifyKey(encoding.decode_address(request.wallet_address))
                vk.verify(request.nonce.encode("utf-8"), sig_bytes)
                ok = True
                logger.info("Raw NaCl verification (no MX prefix) succeeded")
            except Exception as e2:
                logger.warning(f"Raw NaCl verification also failed: {e2}")

    if not ok:
        raise HTTPException(status_code=401, detail="Invalid signature for wallet.")

    # Mark nonce as used
    challenge.used_at = now

    # Ensure user exists
    user_q = await db.execute(select(User).where(User.wallet_address == request.wallet_address))
    user = user_q.scalar_one_or_none()
    if not user:
        user = User(wallet_address=request.wallet_address, role="fan")
        db.add(user)
        await db.flush()

    token = issue_access_token(wallet_address=request.wallet_address, role=user.role)
    await db.commit()

    return VerifyResponse(
        walletAddress=request.wallet_address,
        role=user.role,
        accessToken=token,
        expiresInSeconds=settings.jwt_access_ttl_minutes * 60,
    )

