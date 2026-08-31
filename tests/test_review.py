"""Tests for the human review state machine in src/review.py.

Covers the four possible states (pending, approved, held, escalated) and the
three explicit reviewer actions (approve, hold, escalate), plus the
"Reset State" control, independent of Streamlit.
"""
from __future__ import annotations

import pytest

from src import review


def test_default_status_is_pending_when_unset():
    status_map: dict = {}
    assert review.get_status(status_map, "PO-1::budget_variance") == review.PENDING


def test_apply_action_approve_sets_status():
    status_map: dict = {}
    review.apply_action(status_map, "PO-1::budget_variance", review.APPROVED)
    assert review.get_status(status_map, "PO-1::budget_variance") == "approved"


def test_apply_action_hold_sets_status():
    status_map: dict = {}
    review.apply_action(status_map, "PO-2::policy_threshold", review.HELD)
    assert review.get_status(status_map, "PO-2::policy_threshold") == "held"


def test_apply_action_escalate_sets_status():
    status_map: dict = {}
    review.apply_action(status_map, "PO-3::duplicate_invoice", review.ESCALATED)
    assert review.get_status(status_map, "PO-3::duplicate_invoice") == "escalated"


def test_apply_action_can_change_status_across_actions():
    status_map: dict = {}
    uid = "PO-4::inactive_supplier"
    review.apply_action(status_map, uid, review.APPROVED)
    assert review.get_status(status_map, uid) == "approved"
    review.apply_action(status_map, uid, review.ESCALATED)
    assert review.get_status(status_map, uid) == "escalated"
    review.apply_action(status_map, uid, review.HELD)
    assert review.get_status(status_map, uid) == "held"


def test_apply_action_rejects_pending_as_an_action():
    status_map: dict = {}
    with pytest.raises(ValueError):
        review.apply_action(status_map, "PO-5::missing_documentation", review.PENDING)


def test_apply_action_rejects_unknown_action():
    status_map: dict = {}
    with pytest.raises(ValueError):
        review.apply_action(status_map, "PO-6::upcoming_renewal", "reject")


def test_reset_all_clears_every_decision_back_to_pending():
    status_map = {
        "PO-1::a": review.APPROVED,
        "PO-2::b": review.HELD,
        "PO-3::c": review.ESCALATED,
    }
    review.reset_all(status_map)
    assert status_map == {}
    assert review.get_status(status_map, "PO-1::a") == review.PENDING
    assert review.get_status(status_map, "PO-2::b") == review.PENDING
    assert review.get_status(status_map, "PO-3::c") == review.PENDING


def test_summarize_counts_all_four_states():
    status_map = {
        "PO-1::a": review.APPROVED,
        "PO-2::b": review.HELD,
        "PO-3::c": review.ESCALATED,
        "PO-4::d": review.APPROVED,
    }
    all_ids = ["PO-1::a", "PO-2::b", "PO-3::c", "PO-4::d", "PO-5::e"]  # PO-5 never touched
    counts = review.summarize(status_map, all_ids)
    assert counts == {"pending": 1, "approved": 2, "held": 1, "escalated": 1}


def test_only_three_explicit_actions_are_valid():
    assert set(review.VALID_ACTIONS) == {"approved", "held", "escalated"}
    assert review.PENDING not in review.VALID_ACTIONS
    assert set(review.ALL_STATUSES) == {"pending", "approved", "held", "escalated"}
