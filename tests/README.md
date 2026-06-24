# Tests

This directory contains the test suite for Kernel Core v0.2.

The tests verify that Kernel Core preserves structural integrity before emitting a JudgmentEvent.

The purpose of the test suite is not to evaluate answer quality.

The purpose is to ensure that Kernel invariants are enforced.

## What the tests check

- adapter input validation
- traceability enforcement
- uncertainty preservation
- single primary cause enforcement
- red flag detection
- execution boundary preservation

## Key principle

If a JudgmentEvent cannot be structurally justified, it must not be emitted.

## Test file

- `test_suite_v02.py`

## Scope

The test suite validates Kernel behavior only.

It does not test:

- downstream UCOS decisions
- governance policy
- repair operations
- output approval or rejection

Those belong outside Kernel Core.
