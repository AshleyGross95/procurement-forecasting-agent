"""Pure state-transition helpers for the human review workflow.

Kept separate from Streamlit so the workflow logic is unit-testable without a
running Streamlit session. app.py stores reviewer decisions in
``st.session_state["review_status"]`` (a plain ``dict`` mapping an
exception's ``unique_id`` to a status string) and calls these functions to
read and mutate it. Nothing here talks to any real approval, ticketing, or
payment system -- see docs/limitations.md.

There are exactly four possible states for any exception:
- ``pending``   -- the implicit starting state before any reviewer action.
- ``approved``  -- reviewer explicitly approved the exception.
- ``held``      -- reviewer explicitly put the exception on hold.
- ``escalated`` -- reviewer explicitly escalated the exception.

Only the last three are real "actions" a reviewer takes; pending is never
written to the dict, it is simply the default returned by ``get_status`` for
any unique_id with no recorded decision.
"""
from __future__ import annotations

from typing import Dict

PENDING = "pending"
APPROVED = "approved"
HELD = "held"
ESCALATED = "escalated"

#: The three explicit reviewer actions available in the UI. PENDING is
#: deliberately excluded -- it is never something a reviewer "chooses", it is
#: the absence of a decision.
VALID_ACTIONS = (APPROVED, HELD, ESCALATED)

#: All possible values ``get_status`` can return, including the implicit one.
ALL_STATUSES = (PENDING,) + VALID_ACTIONS


def get_status(review_status: Dict[str, str], unique_id: str) -> str:
    """Return the current review status for one exception, defaulting to pending."""
    return review_status.get(unique_id, PENDING)


def apply_action(review_status: Dict[str, str], unique_id: str, action: str) -> Dict[str, str]:
    """Record a reviewer action for one exception. Mutates and returns review_status.

    Raises ``ValueError`` for anything other than the three valid actions,
    so the workflow can never drift beyond the four documented states.
    """
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unknown review action {action!r}; must be one of {VALID_ACTIONS}")
    review_status[unique_id] = action
    return review_status


def reset_all(review_status: Dict[str, str]) -> Dict[str, str]:
    """Clear every recorded review decision, returning every exception to pending."""
    review_status.clear()
    return review_status


def summarize(review_status: Dict[str, str], all_unique_ids) -> Dict[str, int]:
    """Count how many of ``all_unique_ids`` currently sit in each of the four states.

    Useful for a reviewer-facing summary (e.g. "3 pending, 1 held") without
    exposing the raw session-state dict.
    """
    counts = {status: 0 for status in ALL_STATUSES}
    for uid in all_unique_ids:
        counts[get_status(review_status, uid)] += 1
    return counts
