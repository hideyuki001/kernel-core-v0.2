# Judgment Event Schema

Status: Specification

---

# Purpose

The JudgmentEvent is the canonical output structure emitted by Kernel Core.

Kernel does not generate decisions.

Kernel generates a structured judgment record that preserves:

- observations
- evidence
- interpretations
- uncertainty
- cause assignments
- traceability

A JudgmentEvent is intended to be consumed by downstream systems such as:

- UCOS
- Governance Layers
- Audit Systems
- Repair Systems
- Analytics Pipelines

---

# Design Principles

A JudgmentEvent must satisfy the following properties:

1. Evidence-linked
2. Traceable
3. Uncertainty-preserving
4. Deterministic
5. Single-primary-cause

If any property cannot be satisfied, the event must not be emitted.

---

# High-Level Structure

```text
Observation
    ↓
Evidence
    ↓
Interpretation
    ↓
Uncertainty
    ↓
Cause Assignment
    ↓
Stability Signals
    ↓
Traceability
    ↓
Validation
```

---

# Event Structure

## Observation

Represents what was directly observed.

Contains:

- raw_unit
- normalized_unit
- summary

Observation must not contain interpretation.

---

## Evidence

Represents supporting evidence.

Evidence may be:

- textual
- audible
- visible
- temporal
- multimodal

Evidence must remain linked to source locations.

---

## Interpretation

Represents the selected interpretation.

Contains:

- selected interpretation
- alternatives
- selection basis
- interpretation constraints

Interpretation must remain evidence-bound.

---

## Uncertainty

Represents unresolved elements.

Contains:

- confidence score
- uncertainty flags
- unresolved elements
- revisit indicators
- structural uncertainty type

Uncertainty must not be removed for fluency.

---

## Cause Assignment

Represents why a judgment issue occurred.

Contains:

- exactly one primary cause
- optional secondary factors
- optional root context

Multiple primary causes are not allowed.

---

## Stability Signals

Represents structural state indicators.

Examples:

- hesitation_present
- conflict_detected
- ambiguity_density
- reconstruction_risk

Signals describe state only.

Signals do not trigger actions.

---

## Red Flags

Represents structural violations detected by Kernel.

Examples:

- unsupported inference
- forced resolution
- uncertainty collapse

Red flags do not make decisions.

---

## Traceability

Represents linkage integrity.

Required links:

```text
Evidence
    ↓
Interpretation
    ↓
Cause Assignment
```

Broken traceability prevents event emission.

---

## Validation Block

Represents structural validation status.

Includes:

- schema validity
- evidence presence
- uncertainty requirements
- primary cause validation
- boundary compliance

---

# Example (Language-Agnostic)

Observation:
    unclear audio segment

Evidence:
    low-confidence audio signal

Interpretation:
    unintelligible

Uncertainty:
    partial audibility

Primary Cause:
    partial_audibility

Result:
    JudgmentEvent emitted

---

# What JudgmentEvent Is Not

JudgmentEvent is not:

- a policy decision
- a repair instruction
- a governance action
- a STOP / DEFER / ALLOW result

Those belong to downstream systems.

---

# Kernel Responsibility

Kernel ends after JudgmentEvent emission.

After emission:

```text
Kernel
    ↓
JudgmentEvent
    ↓
Downstream System
```

Kernel does not continue processing beyond this point.

---

# Relationship to Other Specifications

```text
kernel_charter
        ↓
kernel_principles
        ↓
execution_boundary
        ↓
judgment_event_schema
        ↓
adapter_contract
        ↓
red_flag_library
```

This document defines the output object emitted by Kernel Core.

The upstream specifications define:

- why the Kernel exists
- what principles it enforces
- where its authority ends

This specification defines:

- what the Kernel emits

Downstream systems may consume JudgmentEvents, but they must not alter the structural guarantees established by Kernel Core.
```
