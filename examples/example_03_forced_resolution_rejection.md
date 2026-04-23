# Example 03 — Forced Resolution Rejection

## Purpose

This example demonstrates how **Kernel Core v0.2** rejects a judgment when uncertainty is resolved **without sufficient evidence**.

The goal is not to produce a definitive answer.
The goal is to prevent **premature certainty**.

---

## Scenario

A system receives input where the correct interpretation depends on incomplete information.

A downstream component attempts to produce a definitive answer by **filling gaps with assumptions**.

This creates a structural violation.

Kernel Core rejects this judgment before it can be treated as valid.

---

## Input

```json id="n2l3qv"
{
  "input_id": "EX-003",
  "domain": "translation_qa",
  "source_text": "The system failed due to an error.",
  "available_evidence": [
    "A failure occurred",
    "An error is mentioned",
    "No specific type or cause of error is given"
  ]
}
```

---

## Invalid Attempted Judgment

The following interpretation introduces a specific cause without evidence:

```json id="8v2p0d"
{
  "proposed_interpretation": "The system failed due to a network error.",
  "confidence": "high",
  "traceability": [
    {
      "claim": "the error was network-related",
      "linked_evidence": null
    }
  ]
}
```

---

## Why This Must Be Rejected

This judgment introduces a specific conclusion that is not supported by evidence:

> "network error"

However, the input evidence does not specify:

* the type of error
* the source of failure
* any technical cause

This is a case of **forced resolution**.

It replaces uncertainty with an unsupported conclusion.

Kernel Core does not allow missing information to be filled by assumption.

---

## Kernel Result

The Kernel rejects the judgment due to invariant violation:

```json id="f1m9kx"
{
  "status": "rejected",
  "reason": "forced_resolution",
  "violated_invariants": [
    "No unsupported inference",
    "Uncertainty must remain explicit"
  ],
  "primary_cause": "forced_resolution",
  "downstream_action": "blocked_before_interpretation"
}
```

---

## Structural Explanation

Kernel Core rejects this judgment because:

* A specific conclusion was introduced without evidence
* The original uncertainty was not preserved
* The interpretation exceeds the available information

This is not a precision issue.
It is a structural violation of evidence-bounded judgment.

---

## What Would Be Acceptable Instead

A structurally valid interpretation preserves uncertainty:

```json id="3c8xrp"
{
  "proposed_interpretation": "The system failed due to an unspecified error.",
  "confidence": "bounded",
  "traceability": [
    {
      "claim": "a failure occurred",
      "linked_evidence": "A failure occurred"
    },
    {
      "claim": "an error is mentioned",
      "linked_evidence": "An error is mentioned"
    }
  ]
}
```

This version:

* does not assume a specific cause
* remains within available evidence
* preserves uncertainty

---

## Key Takeaway

Kernel Core v0.2 enforces a single rule:

> If information is missing, it must not be invented.

Absence of evidence is not a license to conclude.
It is a constraint that must be preserved.

---

## Related Invariants

* No unsupported inference
* Uncertainty must remain explicit
* Traceability must be verifiable

---

## Position in the stack

```text id="9r2kdl"
Input
  ↓
Kernel Core v0.2
  - detects missing evidence
  - prevents forced conclusions
  ↓
JudgmentEvent: rejected
  ↓
Downstream system does not proceed
```
