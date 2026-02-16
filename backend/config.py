"""
Configuration management for Algorand WalletConnect backend.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Algorand TestNet configuration
    algorand_algod_address: str = "https://testnet-api.algonode.cloud"
    algorand_algod_token: str = ""
    
    # Application environment
    environment: str = "development"
    
    # CORS configuration
    cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080,http://localhost:3000,http://127.0.0.1:3000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
