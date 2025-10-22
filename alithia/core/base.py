from __future__ import annotations

from pydantic import BaseModel


class ToolInput(BaseModel):
    """Base class for tool input models."""


class ToolOutput(BaseModel):
    """Base class for tool output models."""
