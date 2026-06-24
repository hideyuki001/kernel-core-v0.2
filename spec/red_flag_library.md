# Red Flag Library v0.2

Status: Specification

---

## Purpose

The Red Flag Library defines structural failure patterns detected by Kernel Core.

Red Flags are not final decisions.

They are structural warning signals indicating that a judgment may have violated evidence, uncertainty, traceability, or boundary constraints.

---

## Core Rule

Red Flags detect risk.

Red Flags do not decide action.

A Red Flag may inform downstream systems, but it must not directly produce:

* STOP
* DEFER
* ALLOW
* APPROVE
* REJECT

Those belong to downstream governance layers.

---

## Red Flag Archetypes

Each Red Flag may be classified using one primary archetype.

### Outcome-Property

The failure can be detected from the final output or observable result.

Example:

* fabricated content
* unsupported completion
* format-breaking output

### Process

The failure occurs in the reasoning or judgment path.

Example:

* uncertainty collapsed too early
* evidence ignored
* interpretation selected without traceability

### Intervention

The failure appears when the input, context, or evaluation condition changes.

Example:

* misleading context causes overcommitment
* domain knowledge contaminates observation
* weak evidence becomes overconfident after prompt pressure

---

## RF-001 — Unsupported Inference

Type: Process

Description:

A judgment introduces information that is not supported by observable evidence.

Violation:

* Evidence First
* No Hidden Inference

Trigger Conditions:

* interpretation exceeds evidence
* missing content is reconstructed
* external knowledge is used as if observed

Example:

```text
Input:
unclear utterance

Invalid interpretation:
the speaker said a specific named entity
```

Expected Handling:

Preserve uncertainty.

---

## RF-002 — Forced Resolution

Type: Process

Description:

Ambiguity is collapsed into a single interpretation without sufficient evidence.

Violation:

* Uncertainty Preservation
* Weaker Interpretation Preferred

Trigger Conditions:

* multiple interpretations exist
* no evidence strongly selects one
* output commits to one interpretation anyway

Expected Handling:

Preserve alternatives or emit unresolved state.

---

## RF-003 — Uncertainty Collapse

Type: Process

Description:

Uncertainty exists in the input but disappears from the judgment record.

Violation:

* Uncertainty Preservation
* Traceability Required

Trigger Conditions:

* low-confidence evidence
* no uncertainty flag emitted
* unresolved elements omitted

Expected Handling:

Emit uncertainty explicitly.

---

## RF-004 — Over-Strong Interpretation

Type: Process

Description:

The selected interpretation is stronger than the evidence allows.

Violation:

* Structural Integrity Over Fluency
* Weaker Interpretation Preferred

Trigger Conditions:

* weak signal
* confident output
* no conservative alternative retained

Expected Handling:

Prefer a weaker, evidence-bound interpretation.

---

## RF-005 — Attribution Overreach

Type: Process

Description:

Agency, intent, speaker identity, or responsibility is assigned without evidence.

Violation:

* Evidence First
* Traceability Required

Trigger Conditions:

* speaker identity fixed without evidence
* intent inferred
* responsibility assigned from context only

Expected Handling:

Retain attribution uncertainty.

---

## RF-006 — Scope Expansion

Type: Intervention

Description:

The judgment extends beyond the observable scope of the input.

Violation:

* Boundary Preservation
* No Hidden Inference

Trigger Conditions:

* cross-segment reasoning without explicit support
* external context treated as evidence
* task boundary exceeded

Expected Handling:

Limit judgment to observable scope.

---

## RF-007 — Guessed Completion

Type: Outcome-Property

Description:

Missing or unclear content is completed into a fluent output.

Violation:

* No Hidden Inference
* Uncertainty Preservation

Trigger Conditions:

* unclear content becomes fluent text
* no evidence supports reconstruction
* uncertainty markers removed

Expected Handling:

Use unresolved, unclear, or unintelligible representation.

---

## RF-008 — Primary Cause Duplication

Type: Process

Description:

A single judgment event contains more than one primary cause.

Violation:

* One Event, One Primary Cause

Trigger Conditions:

* multiple primary causes assigned
* primary cause duplicated as secondary factor

Expected Handling:

Select exactly one primary cause.

---

## RF-009 — Causal Inflation

Type: Process

Description:

Too many causal explanations are attached to one event, reducing analytical clarity.

Violation:

* Causal Integrity
* Traceability Required

Trigger Conditions:

* excessive secondary factors
* unclear causal hierarchy
* weakly related causes attached

Expected Handling:

Preserve one primary cause and only necessary secondary factors.

---

## RF-010 — Evidence Gap Masking

Type: Outcome-Property

Description:

A judgment appears complete even though evidence is missing.

Violation:

* Evidence First
* Traceability Required

Trigger Conditions:

* observation exists
* evidence list is empty or insufficient
* interpretation still appears complete

Expected Handling:

Block event emission or mark evidence gap.

---

## RF-011 — Interpretation-Observation Swap

Type: Process

Description:

Interpretation is encoded as observation.

Violation:

* Observation / Interpretation Separation

Trigger Conditions:

* observation summary contains conclusions
* raw evidence is replaced by explanation
* causal reading appears before evidence registration

Expected Handling:

Separate observation from interpretation.

---

## RF-012 — Hidden Context Injection

Type: Intervention

Description:

Unprovided background context is injected into the judgment.

Violation:

* No Hidden Inference
* Boundary Preservation

Trigger Conditions:

* external assumptions fill evidence gaps
* domain knowledge overrides weak evidence
* contextual plausibility replaces observation

Expected Handling:

Treat unprovided context as unavailable.

---

## Monitorability Notes

Red Flags are monitorability signals.

They help downstream systems identify whether a judgment process remained observable, traceable, and structurally valid.

A Red Flag should answer:

* What failed?
* Where did it fail?
* Which principle was violated?
* What evidence supports the flag?

---

## Relationship to Kernel Core

Kernel Core detects Red Flags.

Kernel Core does not act on them.

After Red Flags are emitted inside a JudgmentEvent, downstream systems may decide whether to:

* defer
* escalate
* request more evidence
* trigger human review
* initiate repair

---

## Summary

Red Flags are structural warning markers.

They preserve monitorability by making judgment failure modes visible.

A Red Flag does not mean the output is wrong.

It means the judgment requires inspection.

