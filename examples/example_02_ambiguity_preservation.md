# Example 02 — Ambiguity Preservation

## Purpose

This example shows how **Kernel Core v0.2** enforces the preservation of ambiguity when the input evidence does not support a single, definitive interpretation.

The goal is not to resolve uncertainty.  
The goal is to ensure that uncertainty is **explicitly maintained**.

---

## Scenario

A system receives an input where multiple interpretations are possible.

A downstream component attempts to select a single interpretation without sufficient evidence.

This creates a structural violation.

Kernel Core must reject this.

---

## Input

```json
{
  "input_id": "EX-002",
  "domain": "translation_qa",
  "source_text": "He saw her duck.",
  "available_evidence": [
    "The sentence is syntactically ambiguous",
    "'duck' can be a noun or a verb",
    "No disambiguating context is provided"
  ]
}

---

## Invalid Attempted Judgment

The following interpretation collapses ambiguity without evidence:

```json
{
  "proposed_interpretation": "He saw the duck that belonged to her.",
  "confidence": "high",
  "traceability": [
    {
      "claim": "'duck' refers to a noun (an animal)",
      "linked_evidence": null
    }
  ]
}
```

## Why This Must Be Rejected

The judgment selects a single interpretation where multiple interpretations are equally plausible.

However, the input evidence indicates:

- the sentence is ambiguous  
- "duck" can function as both a noun and a verb  
- no context is provided to resolve the ambiguity  

This is therefore a case of **forced resolution**.

It collapses uncertainty without sufficient evidence.

Kernel Core does not allow ambiguity to be resolved unless it is **evidence-supported**.

## Kernel Result

The Kernel rejects the judgment due to invariant violation:

```json
{
  "status": "rejected",
  "reason": "forced_resolution",
  "violated_invariants": [
    "Uncertainty must remain explicit",
    "No unsupported inference"
  ],
  "primary_cause": "uncertainty_collapse",
  "downstream_action": "blocked_before_interpretation"
}
```

## Structural Explanation

Kernel Core rejects this judgment because:

- Multiple valid interpretations exist  
- No evidence justifies selecting one interpretation over others  
- Uncertainty was removed without justification  

This is not a disambiguation error.  
This is a structural violation of uncertainty preservation.

## What Would Be Acceptable Instead

A structurally valid interpretation preserves ambiguity:

```json
{
  "proposed_interpretation": "The sentence is ambiguous: 'duck' may refer to an animal or an action.",
  "confidence": "bounded",
  "traceability": [
    {
      "claim": "sentence is ambiguous",
      "linked_evidence": "The sentence is syntactically ambiguous"
    },
    {
      "claim": "'duck' can be a noun or a verb",
      "linked_evidence": "'duck' can be a noun or a verb"
    }
  ]
}

This version does not force a single interpretation.

It preserves the structure of uncertainty.

## Key Takeaway

Kernel Core v0.2 does not resolve ambiguity by default.

It enforces a single rule:

> If uncertainty cannot be resolved by evidence, it must remain explicit.

In other words, ambiguity is not a problem to fix —  
it is a condition to preserve.

## Related Invariants

- Uncertainty must remain explicit  
- No unsupported inference  
- Traceability must be verifiable

## Position in the stack

```text
Input
  ↓
Kernel Core v0.2
  - detects ambiguity
  - prevents forced resolution
  ↓
JudgmentEvent: rejected (if collapsed)
  ↓
Downstream system does not proceed
```

