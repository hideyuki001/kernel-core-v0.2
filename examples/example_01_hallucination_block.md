# Example 01 — Hallucination Block

## Purpose

This example demonstrates how **Kernel Core v0.2** prevents a judgment from being accepted when it introduces content **not supported by evidence**.

The goal is not to improve the answer.
The goal is to make structurally invalid judgment **impossible to pass**.

---

## Scenario

A system receives input with limited or incomplete evidence.

A downstream component attempts to produce a confident interpretation by introducing details **not present in the source**.

This creates a structural violation.

Kernel Core rejects this judgment before it can be treated as valid.

---

## Input

```json
{
  "input_id": "EX-001",
  "domain": "translation_qa",
  "source_text": "The device may fail under certain conditions.",
  "available_evidence": [
    "The sentence states possibility ('may fail')",
    "No specific condition is given",
    "No cause is explicitly stated"
  ]
}
```

---

## Invalid Attempted Judgment

The following interpretation introduces a claim not supported by evidence:

```json
{
  "proposed_interpretation": "The device fails because of overheating.",
  "confidence": "high",
  "traceability": [
    {
      "claim": "device fails because of overheating",
      "linked_evidence": null
    }
  ]
}
```

---

## Why This Must Be Rejected

The judgment introduces a causal claim that is not grounded in the available evidence:

> "because of overheating"

However, the input evidence does not mention:

* overheating
* temperature
* thermal condition
* any explicit cause

This is an **unsupported inference**.

Even if the interpretation appears plausible,
Kernel Core does not allow plausibility to replace evidence.

---

## Kernel Result

The Kernel rejects the judgment due to invariant violation:

```json
{
  "status": "rejected",
  "reason": "unsupported_inference",
  "violated_invariants": [
    "No unsupported inference",
    "Traceability must be verifiable"
  ],
  "primary_cause": "unsupported_inference",
  "downstream_action": "blocked_before_interpretation"
}
```

---

## Structural Explanation

Kernel Core rejects this judgment because:

* A new claim was introduced without evidence
* The claim cannot be traced back to the input
* Certainty was increased beyond what the source allows

This is not a stylistic issue.
It is a structural validity failure.

---

## What Would Be Acceptable Instead

A structurally valid interpretation preserves evidence boundaries:

```json
{
  "proposed_interpretation": "The device may fail under certain unspecified conditions.",
  "confidence": "bounded",
  "traceability": [
    {
      "claim": "device may fail",
      "linked_evidence": "The sentence states possibility ('may fail')"
    },
    {
      "claim": "conditions are unspecified",
      "linked_evidence": "No specific condition is given"
    }
  ]
}
```

This version:

* does not invent a cause
* remains within available evidence
* preserves uncertainty

---

## Key Takeaway

Kernel Core v0.2 enforces a single rule:

> A judgment must be licensed by evidence.

If not, it is rejected.

This is not a correction mechanism.
It is a rejection mechanism.

---

## Related Invariants

* No unsupported inference
* Uncertainty must remain explicit
* Traceability must be verifiable

---

## Position in the stack

```text
Input
  ↓
Kernel Core v0.2
  - detects unsupported inference
  - blocks hallucinated content
  ↓
JudgmentEvent: rejected
  ↓
Downstream system does not proceed
```
