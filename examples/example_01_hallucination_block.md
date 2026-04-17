# Example 01 — Hallucination Block

## Purpose

This example shows how **Kernel Core v0.2** blocks a judgment when the output introduces content that is **not supported by the input evidence**.

The goal is not to improve the answer.  
The goal is to make a structurally invalid judgment **impossible to pass**.

---

## Scenario

A system receives an input where the evidence is incomplete or ambiguous.

A downstream component attempts to produce a confident interpretation that includes details **not present in the source**.

Kernel Core must reject this.

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

## Invalid Attempted Judgment
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

## Why This Must Be Rejected

The judgment introduces a causal explanation:

"because of overheating"

But the input evidence never mentions:

overheating
temperature
thermal condition
any explicit cause

This is therefore an unsupported inference.

Even if the interpretation sounds plausible, Kernel Core does not allow plausibility to replace evidence.

## Kernel Result
```json
{
  "status": "rejected",
  "reason": "unsupported_inference",
  "violated_invariants": [
    "No unsupported inference",
    "Traceability must be verifiable"
  ],
  "primary_cause": "hallucination_risk",
  "downstream_action": "blocked_before_interpretation"
}
```
```json
## Structural Explanation

Kernel Core rejects this judgment because:

A new fact was introduced without evidence
The claim cannot be traced back to the input
Certainty was increased beyond what the source allows

This is not a style error.
This is a structural validity failure.
```

## What Would Be Acceptable Instead

A structurally valid interpretation would preserve uncertainty:
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

This version does not invent a cause.

It remains within the evidence boundary.
```

## Key Takeaway

Kernel Core v0.2 does not ask whether an answer is useful, fluent, or likely.

It asks:

Is this judgment structurally licensed by the evidence?

If not, it does not pass.
```json
Related Invariants
No unsupported inference
Uncertainty must remain explicit
Traceability must be verifiable
Position in the stack
Input
  ↓
Kernel Core v0.2
  - detects unsupported inference
  - rejects hallucinated cause
  ↓
JudgmentEvent: rejected
  ↓
Downstream system does not proceed
```
