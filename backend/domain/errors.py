"""
Custom domain exceptions for consistent error handling.

These exceptions are mapped to HTTP status codes by the global exception handler
in main.py.
"""
from fastapi import HTTPException, status


class DomainError(HTTPException):
    """Base class for all domain-specific errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: dict | None = None):
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    """Resource not found (404)."""
    def __init__(self, resource_type: str, identifier: str, details: dict | None = None):
        message = f"{resource_type} not found: {identifier}"
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, details=details)


class ValidationError(DomainError):
    """Validation error (400)."""
    def __init__(self, message: str, field: str | None = None, details: dict | None = None):
        if field:
            message = f"Validation error on {field}: {message}"
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


class PermissionDeniedError(DomainError):
    """Permission denied (403)."""
    def __init__(self, message: str = "Permission denied", details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, details=details)


class UnauthorizedError(DomainError):
    """Unauthorized access (401)."""
    def __init__(self, message: str = "Unauthorized", details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ConflictError(DomainError):
    """Resource conflict (409)."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, details=details)


class RateLimitError(DomainError):
    """Rate limit exceeded (429)."""
    def __init__(self, message: str = "Rate limit exceeded", details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_429_TOO_MANY_REQUESTS, details=details)


class BlockchainError(DomainError):
    """Blockchain/on-chain operation error (502)."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_502_BAD_GATEWAY, details=details)
