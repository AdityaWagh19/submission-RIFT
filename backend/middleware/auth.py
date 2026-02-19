"""
Wallet-based authentication middleware for the Creator Sticker Platform.

Security fix C1: Lightweight wallet-ownership verification.

Prototype approach:
    - State-changing endpoints require an X-Wallet-Address header
    - The header value must match the wallet in the URL path
    - This prevents casual abuse where someone calls endpoints with
      another user's wallet address

Production approach (future):
    - Replace with Ed25519 signature verification
    - Frontend signs a challenge/nonce with Pera Wallet
    - Backend verifies the signature against the wallet's public key

Usage in routes:
    @router.post("/{wallet}/upgrade-contract")
    async def upgrade(wallet: str = Depends(require_wallet_auth)):
        ...
"""
import logging
from fastapi import HTTPException, Header, Path
from typing import Optional

logger = logging.getLogger(__name__)

# TODO FOR JULES:
# 1. Replace X-Wallet-Address header check with Ed25519 signature verification:
#    a. Add GET /auth/challenge endpoint that returns a random nonce (store server-side with 5-min TTL)
#    b. Frontend signs nonce with Pera Wallet private key → sends signature + wallet address
#    c. Backend verifies Ed25519 signature against wallet's public key using algosdk.encoding
#    d. On success, issue a short-lived JWT token (15-min expiry) for subsequent requests
# 2. Add session management — store JWT in httpOnly cookie or Authorization header
# 3. Add rate limiting on /auth/challenge (prevent nonce flooding)
# 4. Support both TestNet and MainNet address validation
# 5. Add wallet rotation support — allow user to migrate to new wallet
# END TODO


async def require_wallet_auth(
    wallet: str = Path(..., description="Algorand wallet address"),
    x_wallet_address: Optional[str] = Header(
        None,
        description="Caller's wallet address — must match the {wallet} path parameter",
    ),
) -> str:
    """
    Verify that the caller has declared ownership of the wallet.

    For the prototype, this is a simple header check:
    the X-Wallet-Address header must match the {wallet} path param.

    This prevents:
    - Accidentally calling endpoints with the wrong wallet
    - Simple attacks where someone guesses another wallet's address
    - Tools/scripts that don't set the auth header

    It does NOT prevent:
    - A determined attacker who sets the header manually
    - For full security, use Ed25519 signature verification (future)

    Returns:
        The validated wallet address
    """
    if not x_wallet_address:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Set the X-Wallet-Address header "
                   "to your connected wallet address.",
        )

    if x_wallet_address != wallet:
        logger.warning(
            f"Auth mismatch: path wallet={wallet[:8]}... "
            f"vs header wallet={x_wallet_address[:8]}..."
        )
        raise HTTPException(
            status_code=403,
            detail="Wallet mismatch: X-Wallet-Address header does not match "
                   "the wallet in the URL. You can only perform actions on "
                   "your own wallet.",
        )

    return wallet
