"""Narration layer for detected procurement exceptions.

This module NEVER decides what is an exception or how large the financial
exposure is — that is 100% the job of src/engine.py's rule functions. All
this module does is turn an already-detected Exception record into a
readable explanation for a human reviewer.

- Mock mode (default, MOCK_MODE=true or no ANTHROPIC_API_KEY): a deterministic
  template built directly from the structured Exception fields. No network
  call, no randomness, fully functional out of the box.
- Live mode (MOCK_MODE=false and ANTHROPIC_API_KEY set): calls Claude
  (model claude-sonnet-5) to write a more natural explanation from the same
  structured fields. The structured data passed in is unchanged either way.
"""
from __future__ import annotations

import os

from src.models import Exception as ExceptionRecord


def _is_mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "true").strip().lower() != "false"


def _mock_explanation(exception: ExceptionRecord) -> str:
    type_label = exception.exception_type.replace("_", " ")
    return (
        f"[{exception.severity.upper()} SEVERITY] PO {exception.po_id} was flagged as a "
        f"'{type_label}' exception with an estimated financial exposure of "
        f"${exception.financial_exposure:,.2f}.\n\n"
        f"{exception.description}\n\n"
        f"Recommended action: {exception.recommended_action}"
    )


def _live_explanation(exception: ExceptionRecord) -> str:
    try:
        import anthropic

        client = anthropic.Anthropic()
        prompt = (
            "You are assisting an accounts payable reviewer. Given this structured, "
            "already-detected procurement exception, write a short (2-4 sentence) plain-English "
            "explanation a busy reviewer can scan in a few seconds. Do not invent numbers or facts "
            "beyond what is given, and do not change the recommended action.\n\n"
            f"exception_type: {exception.exception_type}\n"
            f"po_id: {exception.po_id}\n"
            f"department: {exception.department}\n"
            f"supplier: {exception.supplier_name or exception.supplier_id}\n"
            f"financial_exposure: ${exception.financial_exposure:,.2f}\n"
            f"severity: {exception.severity}\n"
            f"rule_description: {exception.description}\n"
            f"recommended_action: {exception.recommended_action}\n"
        )
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()
        return text or _mock_explanation(exception)
    except Exception as exc:  # broad on purpose: any live-mode failure falls back to the mock path
        return _mock_explanation(exception) + f"\n\n(Live explanation unavailable, fell back to template: {exc})"


def generate_explanation(exception: ExceptionRecord) -> str:
    """Return a human-readable explanation for a detected exception.

    Uses the deterministic mock template unless MOCK_MODE=false and an
    ANTHROPIC_API_KEY is configured, in which case it calls Claude to narrate
    the same structured fields.
    """
    if _is_mock_mode() or not os.getenv("ANTHROPIC_API_KEY"):
        return _mock_explanation(exception)
    return _live_explanation(exception)
