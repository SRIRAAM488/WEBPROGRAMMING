"""Small shared response schemas."""

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Simple success message returned by DELETE-style endpoints."""

    message: str
    success: bool = True
    detail: str | None = Field(
        None, description="Optional extra information for the UI."
    )


class ErrorResponse(BaseModel):
    """Consistent error body used across the API."""

    success: bool = False
    error: str = Field(..., description="A short, human readable reason.")
    detail: str | None = Field(None, description="Field-level detail when available.")