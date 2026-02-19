"""
Standard API response models and helpers for consistent response formatting.

All endpoints should use these helpers to ensure consistent response envelopes:
- Success: { "success": true, "data": <payload>, "meta": {...} }
- Error: { "success": false, "error": { "code": "...", "message": "...", "details": {...} } }
"""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Standard error detail structure."""
    code: str = Field(..., description="Error code (e.g., 'not_found', 'validation_error')")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error context")


class StandardErrorResponse(BaseModel):
    """Standard error response envelope."""
    success: bool = Field(False, description="Always false for errors")
    error: ErrorDetail = Field(..., description="Error details")


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    limit: int = Field(..., description="Number of items per page")
    offset: int | None = Field(default=None, description="Offset (for offset-based pagination)")
    skip: int | None = Field(default=None, description="Skip count (alias for offset)")
    total: int = Field(..., description="Total number of items")
    has_more: bool = Field(..., alias="hasMore", description="Whether more items exist")


class StandardSuccessResponse(BaseModel, Generic[T]):
    """Standard success response envelope."""
    success: bool = Field(True, description="Always true for success")
    data: T = Field(..., description="Response payload")
    meta: dict[str, Any] | None = Field(default=None, description="Optional metadata (pagination, etc.)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response with standardized structure."""
    success: bool = Field(True, description="Always true for success")
    data: list[T] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


def success_response(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: The response payload
        meta: Optional metadata (pagination, timestamps, etc.)

    Returns:
        dict: { "success": true, "data": <data>, "meta": <meta> }
    """
    response = {"success": True, "data": data}
    if meta:
        response["meta"] = meta
    return response


def paginated_response(
    items: list[Any],
    limit: int,
    offset: int | None = None,
    skip: int | None = None,
    total: int | None = None,
) -> dict[str, Any]:
    """
    Create a standardized paginated response.

    Args:
        items: List of items for this page
        limit: Number of items per page
        offset: Offset value (if using offset-based pagination)
        skip: Skip count (alias for offset)
        total: Total number of items (if None, uses len(items))

    Returns:
        dict: { "success": true, "data": <items>, "meta": { "limit", "offset", "total", "hasMore" } }
    """
    if total is None:
        total = len(items)

    # Use offset if provided, otherwise skip, otherwise 0
    pagination_offset = offset if offset is not None else (skip if skip is not None else 0)

    meta = {
        "limit": limit,
        "offset": pagination_offset,
        "skip": pagination_offset,  # Include both for compatibility
        "total": total,
        "hasMore": (pagination_offset + limit) < total,
    }

    return success_response(data=items, meta=meta)
