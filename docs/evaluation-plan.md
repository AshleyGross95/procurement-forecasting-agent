# Evaluation Plan

## What "correct" means for this agent

This agent has no model in the loop for detection -- every exception and
every dollar figure is produced by deterministic, rule-based pandas logic in
`src/engine.py`. "Correct" therefore means:

1. **Detection recall on seeded cases** -- every deliberately seeded
   exception condition in `data/synthetic/` is caught by its corresponding
   rule. This is checked directly, by PO ID, in `tests/test_engine.py` (the
   original seeded cases) and `tests/test_engine_scale.py` (the additional
   cases seeded into the expanded 48-PO dataset).
2. **No false positives on clean data** -- a hand-built PO/supplier/budget/
   invoice combination with none of the six seeded problems produces zero
   exceptions. `tests/test_engine.py::test_clean_data_produces_zero_exceptions`.
3. **Exact rule count** -- exactly six rule functions exist
   (`tests/test_engine_scale.py::test_exactly_six_rule_functions_exist`),
   matching the six values of `ExceptionType` in `src/models.py`.
4. **Correct prioritization** -- the full detected list is always sorted by
   `financial_exposure` descending, at both the original and expanded
   dataset scale (`test_prioritize_sorts_descending`,
   `test_prioritize_sorts_descending_at_scale`).
5. **Referential integrity of the seeded data itself** -- every PO's
   `supplier_id` and `budget_line`, and every invoice's `po_id`, resolves to
   a real row, and primary keys are unique (`tests/test_data_integrity.py`).
6. **Correct human-review state transitions** -- the four-state workflow
   (pending / approved / held / escalated) only ever moves through the three
   documented actions, rejects anything else, and "Reset State" always
   returns every exception to pending (`tests/test_review.py`).
7. **Correct forecast aggregation** -- the illustrative monthly
   cumulative-exposure chart and the exception-count-by-type table sum back
   exactly to the rule engine's own totals, both on hand-built fixtures with
   known arithmetic and on the real seeded dataset (`tests/test_forecast.py`).

## What is explicitly out of scope for evaluation

- LLM narration text quality (`src/llm.py`, LIVE mode only) -- it never
  changes detection or dollar amounts, so it is not evaluated for
  correctness, only exercised for the fallback-to-template path on failure.
- Any claim about real-world detection accuracy against real procurement
  data -- there is no real data in this repository to evaluate against.

## Running the suite

```bash
pytest -v
```

At release time this repo's exact verified count was **53 tests, 53
passed**, spanning:

- `tests/test_engine.py` (9) -- original seeded-case detection + clean-data
  zero-exceptions baseline, unmodified from the prior audit pass.
- `tests/test_engine_scale.py` (14) -- exact rule-function count, additional
  seeded cases in the expanded 48-PO dataset for all six rule types,
  prioritization and total-count consistency at the larger scale.
- `tests/test_data_integrity.py` (12) -- row counts, uniqueness, referential
  integrity, and a guard that the original seeded PO rows are unchanged.
- `tests/test_review.py` (10) -- the pending/approved/held/escalated state
  machine, including rejecting invalid actions and the reset-to-pending
  behavior.
- `tests/test_forecast.py` (8) -- monthly cumulative-exposure and
  count-by-type aggregation correctness, on both fixtures and real data.

The exact count is restated in `README.md` section 12 and displayed live in
the app's 3-metric panel (`app.py::NUM_VERIFIED_TESTS`) -- re-run `pytest -v`
and update both places together if tests are ever added or removed.
