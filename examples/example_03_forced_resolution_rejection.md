# Example 03 — Forced Resolution Rejection

## Purpose

This example shows how **Kernel Core v0.2** rejects a judgment when uncertainty is resolved **without sufficient evidence**.

The goal is not to produce a definitive answer.  
The goal is to prevent **premature certainty**.

---

## Scenario

A system receives an input where the correct interpretation depends on missing or incomplete information.

A downstream component attempts to produce a definitive answer by **guessing or filling gaps**.

This creates a structural violation.

Kernel Core must reject this.

---

## Input

```json
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

## Invalid Attempted Judgment

The following interpretation introduces a specific cause without evidence:
```json
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

## Why This Must Be Rejected

This introduces a specific conclusion without evidence.

The judgment resolves uncertainty by selecting a cause:

"network error"

However, the input evidence does not specify:

the type of error
the source of failure
any technical cause

This is therefore a case of forced resolution.

It replaces uncertainty with an unsupported conclusion.

Kernel Core does not allow missing information to be filled by assumption.

## Kernel Result

The Kernel rejects the judgment due to invariant violation:

```json
{
  "status": "rejected",
  "reason": "forced_resolution",
  "violated_invariants": [
    "No unsupported inference",
    "Uncertainty must remain explicit"
  ],
  "primary_cause": "evidence_gap",
  "downstream_action": "blocked_before_interpretation"
}
```

## Structural Explanation

Kernel Core rejects this judgment because:

A specific conclusion was introduced without evidence
The original uncertainty was not preserved
The interpretation exceeds the available information

This is not a precision issue.
This is a structural violation of evidence-bounded judgment.

## What Would Be Acceptable Instead

A structurally valid interpretation preserves uncertainty:

```json
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

This version does not assume a specific cause.

It remains within the evidence boundary.

## Key Takeaway

Kernel Core v0.2 does not allow uncertainty to be replaced by assumption.

It enforces a single rule:

If information is missing, it must not be invented.

In other words, absence of evidence is not a license to conclude —
it is a constraint that must be preserved.

It enforces what is allowed to be concluded — not what seems most plausible.

## Related Invariants
```
No unsupported inference
Uncertainty must remain explicit
Traceability must be verifiable
Position in the stack
Input
  ↓
Kernel Core v0.2
  - detects missing evidence
  - rejects forced conclusions
  ↓
JudgmentEvent: rejected
  ↓
Downstream system does not proceed
```
