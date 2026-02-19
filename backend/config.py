"""
Configuration management for the Creator Sticker Platform (V4).

Loads settings from .env via pydantic-settings.

Security notes:
    - H4: platform_private_key is derived once and cached
    - M2: validate_production_settings() enforces strict CORS in production
    - I3: SIMULATION_MODE and DEMO_MODE documented in .env.example
"""
import logging
from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Algorand TestNet ────────────────────────────────────────────
    algorand_algod_address: str = "https://testnet-api.algonode.cloud"
    algorand_algod_token: str = ""
    algorand_indexer_url: str = "https://testnet-idx.algonode.cloud"

    # ── Platform Wallet (deploys contracts + mints NFTs) ────────────
    platform_wallet: str = ""
    platform_mnemonic: str = ""

    # ── Fan Wallet (testing/demo only) ───────────────────────────
    fan_wallet: str = ""
    fan_mnemonic: str = ""

    # ── Pinata IPFS ─────────────────────────────────────────────────
    pinata_api_key: str = ""
    pinata_secret: str = ""
    pinata_gateway: str = "https://gateway.pinata.cloud/ipfs"

    # ── Database ────────────────────────────────────────────────────
    database_url: str = "sqlite:///./data/sticker_platform.db"

    # ── Golden Sticker Probability ──────────────────────────────────
    golden_threshold: float = 0.10       # 10% chance
    golden_trigger_interval: int = 10    # every N tips

    # ── Listener ────────────────────────────────────────────────────
    listener_poll_seconds: int = 10

    # ── Contract ────────────────────────────────────────────────────
    tip_proxy_contract_path: str = "contracts/tip_proxy/compiled"
    contract_fund_amount: int = 100_000  # 0.1 ALGO in microAlgos

    # ── Application ─────────────────────────────────────────────────
    environment: str = "development"
    simulation_mode: bool = True  # Hackathon demo: simulate fiat on-ramp, real blockchain

    # ── Auth (JWT) ──────────────────────────────────────────────────
    jwt_secret: str = ""
    jwt_issuer: str = "fanforge-api"
    jwt_access_ttl_minutes: int = 15
    auth_challenge_ttl_minutes: int = 5

    # ── Demo Mode ───────────────────────────────────────────────────
    # When True, fan mnemonics from demo_accounts.json are used
    # to auto opt-in + transfer NFTs in the listener pipeline.
    # In production, the frontend handles opt-in via Pera Wallet.
    demo_mode: bool = True
    demo_accounts_file: str = "scripts/demo_accounts.json"

    # ── Transak On-Ramp ────────────────────────────────────────────
    transak_api_key: str = ""
    transak_secret: str = ""
    transak_environment: str = "STAGING"      # STAGING or PRODUCTION
    platform_fee_percent: float = 2.0         # % deducted from tips

    # ── CORS ────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # allow unknown .env keys without crashing
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @cached_property
    def platform_private_key(self) -> str:
        """
        Derive platform wallet private key from mnemonic (computed once, cached).

        Security fix H4: avoids re-deriving the key on every request.
        The key is held in memory for the process lifetime.
        """
        if not self.platform_mnemonic:
            raise ValueError("PLATFORM_MNEMONIC not set in .env")
        from algosdk import mnemonic
        return mnemonic.to_private_key(self.platform_mnemonic)

    def validate_production_settings(self):
        """
        Validate settings for production safety.

        Security fix M2: Enforces strict CORS and disables simulation in production.
        Called during app startup.
        """
        if self.environment == "production":
            # M2: Block wildcard CORS in production
            if "*" in self.cors_origins:
                raise ValueError(
                    "CORS_ORIGINS must not contain '*' in production. "
                    "Set explicit allowed origins."
                )
            # H3: Block simulation mode in production
            if self.simulation_mode:
                raise ValueError(
                    "SIMULATION_MODE must be false in production. "
                    "Simulation endpoints allow free wallet funding."
                )
            # M5: Block demo mode in production
            if self.demo_mode:
                raise ValueError(
                    "DEMO_MODE must be false in production. "
                    "Demo mode uses stored private keys for auto opt-in."
                )
            # Auth: require JWT secret in production
            if not self.jwt_secret:
                raise ValueError(
                    "JWT_SECRET must be set in production. "
                    "It is used to sign access tokens for wallet authentication."
                )
            logger.info("✅ Production settings validated")
        else:
            # Warn about insecure settings in non-production
            warnings = []
            if self.simulation_mode:
                warnings.append("SIMULATION_MODE=true (wallet funding enabled)")
            if self.demo_mode:
                warnings.append("DEMO_MODE=true (fan auto opt-in enabled)")
            if "*" in self.cors_origins:
                warnings.append("CORS_ORIGINS contains '*' (open access)")
            for w in warnings:
                logger.warning(f"⚠️  {w}")


# Global settings instance
settings = Settings()
