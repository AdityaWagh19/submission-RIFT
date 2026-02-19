"""
Shared FastAPI dependencies.

Phase 1 (plan.md): centralize common dependencies here so routers can import
from a single place (DB session, auth guards, Bauni gating, pagination).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, TypedDict

from fastapi import Depends, Header, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db_models import User
from domain.errors import PermissionDeniedError
from services import bauni_service
from middleware.auth import require_wallet_auth, require_authenticated_wallet


class Pagination(TypedDict):
    limit: int
    offset: int


def pagination_params(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=100_000),
) -> Pagination:
    return {"limit": limit, "offset": offset}


async def require_creator(
    wallet: str = Depends(require_wallet_auth),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    Require that the authenticated wallet is a creator.

    - Authenticates wallet against path `{wallet}` using JWT (preferred) or legacy header.
    - Ensures a User row exists and role == 'creator'.
    """
    q = await db.execute(select(User).where(User.wallet_address == wallet))
    user = q.scalar_one_or_none()
    if not user:
        raise PermissionDeniedError("Creator account not found for wallet.")
    if user.role != "creator":
        raise PermissionDeniedError("Creator role required for this endpoint.")
    return wallet


async def require_fan(
    auth_wallet: str = Depends(require_authenticated_wallet),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    Require that the authenticated wallet is a fan.

    Ensures a User row exists and role == 'fan'.
    """
    q = await db.execute(select(User).where(User.wallet_address == auth_wallet))
    user = q.scalar_one_or_none()
    if not user:
        # Create-on-demand so new wallets can use fan endpoints after auth.
        user = User(wallet_address=auth_wallet, role="fan")
        db.add(user)
        await db.flush()
        return auth_wallet
    if user.role != "fan":
        raise PermissionDeniedError("Fan role required for this endpoint.")
    return auth_wallet


async def require_bauni_membership(
    fan_wallet: str,
    creator_wallet: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Content gating dependency (moved from routes/bauni.py to avoid route↔route imports).
    """
    result = await bauni_service.verify_membership(db, fan_wallet, creator_wallet)
    if not result["is_valid"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "membership_required",
                "message": (
                    f"Active Bauni membership required. "
                    f"Purchase for {bauni_service.BAUNI_COST_ALGO} ALGO "
                    f"with memo 'MEMBERSHIP:BAUNI'"
                ),
                "cost_algo": bauni_service.BAUNI_COST_ALGO,
            },
        )
    return result

