"""
Wallet authentication helpers.

Legacy prototype approach:
  - State-changing endpoints require an X-Wallet-Address header
  - Header must match the wallet in the URL path/body

Production-ready approach (implemented here):
  - Issue short-lived JWT access tokens after verifying an Ed25519 signature
    over a server-provided nonce (see routes/auth.py).

Backward compatibility:
  - For now, endpoints may accept either:
      - Authorization: Bearer <jwt>
      - X-Wallet-Address: <wallet> (legacy; not cryptographically secure)
"""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Header, Path
from typing import Optional

import jwt

from config import settings

logger = logging.getLogger(__name__)

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def decode_access_token(token: str) -> dict:
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=500,
            detail="Server auth misconfigured (JWT secret missing).",
        )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid access token.")


def issue_access_token(*, wallet_address: str, role: str) -> str:
    now = _now_utc()
    exp = now.replace(microsecond=0) + timedelta(minutes=settings.jwt_access_ttl_minutes)
    payload = {
        "iss": settings.jwt_issuer,
        "sub": wallet_address,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=500,
            detail="Server auth misconfigured (JWT secret missing).",
        )
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def get_authenticated_wallet(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
) -> Optional[str]:
    """
    Best-effort authentication:
      - Prefer Authorization Bearer JWT
      - Fall back to legacy X-Wallet-Address header (NOT secure)
    """
    token = _parse_bearer_token(authorization)
    if token:
        payload = decode_access_token(token)
        return payload.get("sub")
    return x_wallet_address


async def require_authenticated_wallet(
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    auth_wallet = await get_authenticated_wallet(
        authorization=authorization,
        x_wallet_address=x_wallet_address,
    )
    if not auth_wallet:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Authorization: Bearer <token> (preferred) or X-Wallet-Address (legacy).",
        )
    return auth_wallet


async def require_wallet_auth(
    wallet: str = Path(..., description="Algorand wallet address"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_wallet_address: Optional[str] = Header(
        None,
        alias="X-Wallet-Address",
        description="Legacy caller wallet header (deprecated).",
    ),
) -> str:
    """
    Dependency for routes that act on a `{wallet}` path parameter.

    - If JWT is provided, it must match the path wallet.
    - Otherwise falls back to legacy X-Wallet-Address header match.
    """
    token = _parse_bearer_token(authorization)
    if token:
        payload = decode_access_token(token)
        auth_wallet = payload.get("sub")
        if auth_wallet != wallet:
            raise HTTPException(status_code=403, detail="Wallet mismatch for access token.")
        return wallet

    # Legacy fallback (kept for backward compatibility)
    if not x_wallet_address:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Authorization: Bearer <token> (preferred) or X-Wallet-Address (legacy).",
        )
    if x_wallet_address != wallet:
        logger.warning(
            f"Auth mismatch: path wallet={wallet[:8]}... vs header wallet={x_wallet_address[:8]}..."
        )
        raise HTTPException(
            status_code=403,
            detail="Wallet mismatch: X-Wallet-Address header does not match the wallet in the URL.",
        )
    return wallet
