"""Standard API response models for consistent responses."""
from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    error_code: Optional[str] = None

    @classmethod
    def success_response(cls, data: T, message: Optional[str] = None) -> "APIResponse[T]":
        """Create a success response."""
        return cls(success=True, data=data, message=message)

    @classmethod
    def error_response(
        cls,
        message: str,
        error_code: Optional[str] = None,
        data: Optional[T] = None
    ) -> "APIResponse[T]":
        """Create an error response."""
        return cls(success=False, message=message, error_code=error_code, data=data)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
            has_previous=page > 1,
        )
