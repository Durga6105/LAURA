"""
LAURA - Rule Models

Defines the internal representation of Rule Book rules.
"""

from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Supported risk levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Rule(BaseModel):
    """Normalized Rule Book rule."""

    rule_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    rule_name: str = Field(min_length=1)

    description: str = Field(min_length=1)
    validation_criteria: str = Field(min_length=1)

    severity: RiskLevel = RiskLevel.MEDIUM
    mandatory: bool = True

    correction_instruction: str = Field(min_length=1)

    source: str | None = None