"""Domain models for the procurement pre-payment exception review agent.

This module defines the typed schema shared by the rule engine (src/engine.py),
the LLM narration layer (src/llm.py), and the Streamlit dashboard (app.py).
"""
from dataclasses import dataclass, field
from enum import Enum


class ExceptionType(str, Enum):
    """The six pre-payment exception conditions this agent detects."""

    BUDGET_VARIANCE = "budget_variance"
    DUPLICATE_INVOICE = "duplicate_invoice"
    MISSING_DOCUMENTATION = "missing_documentation"
    INACTIVE_SUPPLIER = "inactive_supplier"
    POLICY_THRESHOLD = "policy_threshold"
    UPCOMING_RENEWAL = "upcoming_renewal"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Exposure bands used to derive severity from financial_exposure. These are
# simple, transparent thresholds (not a scoring model) so the rationale is
# always inspectable.
_CRITICAL_THRESHOLD = 50_000
_HIGH_THRESHOLD = 20_000
_MEDIUM_THRESHOLD = 5_000


def severity_from_exposure(financial_exposure: float) -> str:
    """Deterministically derive a severity band from a dollar exposure amount."""
    if financial_exposure >= _CRITICAL_THRESHOLD:
        return Severity.CRITICAL.value
    if financial_exposure >= _HIGH_THRESHOLD:
        return Severity.HIGH.value
    if financial_exposure >= _MEDIUM_THRESHOLD:
        return Severity.MEDIUM.value
    return Severity.LOW.value


@dataclass
class Exception:  # noqa: A001 - name mandated by spec; callers should import with an alias.
    """A single detected pre-payment exception.

    Note: this shadows the Python builtin ``Exception`` within this module's
    namespace. Every other module in this repo imports it as
    ``from src.models import Exception as ExceptionRecord`` specifically to
    avoid colliding with the builtin when raising real errors elsewhere.
    """

    po_id: str
    exception_type: str
    description: str
    financial_exposure: float
    recommended_action: str
    department: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    severity: str = field(init=False, default="")

    def __post_init__(self) -> None:
        self.severity = severity_from_exposure(self.financial_exposure)

    @property
    def unique_id(self) -> str:
        """Stable key for UI selection/state since one PO can carry several exception types."""
        return f"{self.po_id}::{self.exception_type}"
