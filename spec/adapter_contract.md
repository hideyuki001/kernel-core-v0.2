# Adapter Contract v0.2

## Purpose

This document defines the responsibilities and boundaries of Adapters
that interface between external data sources and Kernel Core.

Adapters exist to normalize incoming data into a format that can be
processed by Kernel Core.

Adapters MUST NOT perform judgment, interpretation, approval,
rejection, risk scoring, or governance decisions.

Their responsibility is transformation only.

---

# Core Principle

Adapter = Translation Layer

NOT

Adapter = Decision Layer

Adapters convert source-specific representations into a canonical
observation structure.

---

# Allowed Responsibilities

Adapters MAY:

- Parse source data
- Normalize formats
- Convert timestamps
- Convert metadata
- Preserve source uncertainty markers
- Preserve source provenance
- Map source fields into canonical schema fields

Example:

Input:

Speaker A:
"uh ... maybe"

Output:

Observation:
speaker=A
text="uh ... maybe"

No interpretation is added.

---

# Forbidden Responsibilities

Adapters MUST NOT:

- Guess missing information
- Resolve ambiguity
- Infer intent
- Assign blame
- Assign risk levels
- Generate recommendations
- Produce final decisions

Example:

Input:
"probably"

Forbidden Output:

certainty=high

Reason:

certainty was not present in source data.

---

# Evidence Preservation

Adapters MUST preserve all observable evidence.

Observable evidence includes:

- Raw text
- Raw transcription
- Audio markers
- Timing information
- Metadata
- Source confidence values

Adapters MUST NOT discard evidence solely because it appears noisy,
irrelevant, or incomplete.

---

# Uncertainty Preservation

If uncertainty exists in source data,
it MUST remain visible after transformation.

Examples:

"[inaudible]"

"[unclear]"

"???"

low_confidence=true

These markers MUST survive adapter processing.

---

# Canonical Observation Format

Adapters SHOULD emit observations using a consistent structure.

Example:

Observation:

- source_id
- timestamp
- content
- metadata
- uncertainty_markers

This structure is intentionally minimal.

Domain-specific extensions MAY be added separately.

---

# Traceability Requirement

Every observation produced by an Adapter MUST be traceable
to an original source.

The following MUST be recoverable:

- source identifier
- source location
- original evidence

Traceability loss is considered a contract violation.

---

# Adapter Output Boundary

Adapters MAY emit:

Observation

Adapters MUST NOT emit:

Interpretation

Judgment

Decision

Governance Action

These belong to downstream systems.

---

# Failure Handling

If an Adapter cannot safely transform data:

DO NOT GUESS.

Instead emit:

adapter_failure=true

and preserve available evidence.

Failure is preferable to silent distortion.

---

# Compliance Test

A compliant Adapter should satisfy the following question:

"Can a reviewer reconstruct the original source
from the adapter output?"

If the answer is NO,

the Adapter violates this contract.

---

# Summary

Adapters normalize.

Kernel observes.

UCOS evaluates.

Governance decides.

The Adapter is responsible only for preserving reality
while translating it into a machine-processable form.
