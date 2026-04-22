# Example 04 — Real Case: DEFER under Constraint Conflict

## Overview

This is a real execution case where Kernel Core v0.2 was applied to a coding evaluation task.

This is not a theoretical example.

It demonstrates how the system behaves when a valid judgment cannot be structurally completed.

---

## Task

Sliding Window Rate Limiter
Condition: non-monotonic timestamps

---

## Structural conflict

The task revealed a requirement conflict between:

* exact historical replay
* bounded memory (garbage collection)
* out-of-order timestamps

These constraints cannot be satisfied simultaneously without introducing trade-offs that require external authority.

---

## System behavior

The system did not attempt to resolve the conflict.

Instead, it produced a structured decision state:

```yaml
terminal_state: DEFER
trace_complete: false
missing_gates:
  - jro_select
  - audit
```

---

## What this means

The decision process reached a point where it could not proceed without violating structural constraints.

Specifically:

* no valid repair operation could be selected (`jro_select` missing)
* no audit could be completed (`audit` missing)
* no authority was defined to resolve the conflict

---

## Why it stopped

Kernel Core enforces traceability as a hard invariant.

An incomplete decision path cannot be treated as complete.

Therefore:

> The system did not fail.
> It refused to produce a structurally invalid judgment.

---

## Key principle

No named authority → no final semantic commitment

---

## Interpretation

This case shows that:

* ambiguity was not collapsed
* uncertainty was not converted into false certainty
* responsibility was not implicitly assigned
* traceability remained intact

---

## Important distinction

This is not an error condition.

It is a correct outcome under structural constraints.

A system that always produces an answer may hide invalid assumptions.

This system preserves the boundary between:

* what can be derived from evidence
* what requires external decision authority

---

## Operational continuation

To resolve this state, an external authority must be introduced:

```yaml
defer_resolution:
  monitor_role: system architect
  resolution_trigger:
    - named approver assigned
    - approval scope confirmed
    - constraint trade-off explicitly accepted
  next_gate_on_trigger: jro_select
```

---

## Insight

This example demonstrates a key property of Kernel Core:

> incomplete judgment remains explicitly incomplete

The system does not optimize for completion.

It preserves structural integrity.
