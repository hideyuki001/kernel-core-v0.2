# Integration with UCOS

Kernel Core v0.2 is designed to work as a structural validation layer before UCOS.

It does not generate answers.  
It does not decide meaning.  
It does not replace UCOS.

Its role is narrower and stricter:

> Kernel Core determines whether a judgment trace is structurally admissible before semantic governance is applied.

---

## Recommended Architecture

```text
Input
  ↓
Kernel Core v0.2
  - structural validation
  - trace completeness check
  - red flag detection
  - invalid judgment prevention
  ↓
JudgmentEvent
  ↓
UCOS
  - OBS / INT / UNC / DTR decomposition
  - semantic governance
  - uncertainty handling
  - decision responsibility
  ↓
Output System
```

---

## Boundary Principle

```text
Kernel Core enforces structure.
UCOS governs meaning.
```

This boundary is essential.

Kernel Core should not make final semantic decisions.

UCOS should not be forced to repair structurally invalid traces that should have been blocked earlier.

---

## Responsibility Split

| Layer | Responsibility | Non-Responsibility |
|---|---|---|
| Kernel Core | Validate structural admissibility | Decide final meaning |
| Kernel Core | Detect incomplete traceability and invalid structural chains | Produce UCOS DTR `missing_gates` directly |
| Kernel Core | Preserve uncertainty instead of collapsing it | Resolve ambiguity by assumption |
| UCOS v1.8.1 | Interpret observations, intent, uncertainty, and decision responsibility | Ignore structural invalidity |
| UCOS v1.8.1 | Record `missing_gates` when a DTR trace is incomplete | Treat incomplete trace as resolved |
| UCOS v1.8.1 | Determine terminal governance such as `ALLOW`, `ALLOW_WITH_CAVEAT`, `DEFER`, or `STOP` | Invent missing authority |

---

## What Kernel Core Sends to UCOS

Kernel Core should pass a structurally validated `JudgmentEvent` to UCOS.

If structural validation fails, Kernel Core should expose the failure as a blocked structural status, not as a final decision.

Example downstream integration payload:

```yaml
kernel_result:
  input_type: evaluation_case
  structural_validity: false
  traceability_complete: false
  primary_issue: incomplete_traceability
  red_flags:
    - forced_resolution
    - unsupported_finalization
  blocked_reason:
    - missing evidence-to-claim link
    - final decision attempted before structural validation
  kernel_status: structurally_blocked
```

This payload does not tell UCOS what the final answer is.

It tells UCOS that the judgment cannot safely proceed as if it were structurally complete.

If UCOS creates a DTR record from this state, UCOS v1.8.1 should represent the absent decision gates using `missing_gates`.

---

## UCOS Processing After Kernel Core

After receiving a `JudgmentEvent` or downstream integration payload, UCOS may apply its governance layers:

```text
OBS → What is directly observed?
INT → What interpretation is being attempted?
UNC → What uncertainty remains?
DTR → What decision responsibility is required?
```

UCOS can then determine whether the case should:

- `ALLOW`
- `ALLOW_WITH_CAVEAT`
- `DEFER`
- `STOP`
- generate a Handoff Packet
- preserve unresolved uncertainty

---

## Example: DEFER Case

A real evaluation case may reach the following state:

```yaml
terminal_state: DEFER
trace_complete: false
```

This is not necessarily a system failure.

It may indicate that the structure is complete enough to reveal the problem, but incomplete for final judgment.

In this case:

```text
Kernel Core identifies the incomplete trace.
UCOS interprets the decision responsibility.
The output system avoids unsupported finalization.
```

The important point is that uncertainty remains visible.

It is not collapsed into a fluent but unjustified answer.

---

## Invalid Integration Pattern

The following pattern should be avoided:

```text
Input
  ↓
UCOS
  ↓
Output
  ↓
Kernel Core checks afterward
```

This is weaker because invalid judgments may already have been generated before structural validation occurs.

Kernel Core should operate before final semantic commitment.

---

## Valid Integration Pattern

The preferred pattern is:

```text
Input
  ↓
Kernel Core
  ↓
JudgmentEvent
  ↓
UCOS
  ↓
Final Decision / Deferral / Escalation
```

This keeps the system from producing answers that are fluent but structurally unsupported.

---

## Practical Rule

If Kernel Core returns:

```yaml
structural_validity: false
```

then UCOS must not silently convert the case into a final answer.

The missing structure must remain visible in the judgment path.

A downstream system may still continue, but only if it explicitly handles the missing structure.

---

## Non-Goals

Kernel Core does not:

- replace UCOS
- decide final correctness
- apply full task policy
- infer missing evidence
- invent missing authority
- complete incomplete traces
- generate final user-facing answers
- directly produce UCOS DTR `missing_gates`

UCOS does not:

- ignore Kernel Core violations
- treat missing evidence as resolved
- collapse uncertainty without justification
- finalize judgments without decision responsibility
- invent missing authority

---

## Summary

Kernel Core v0.2 and UCOS are complementary.

```text
Kernel Core = structural admissibility
UCOS        = semantic governance
```

Kernel Core asks:

> Is this judgment structurally allowed to proceed?

UCOS asks:

> Given the structure, uncertainty, and responsibility, what should be done?

Together, they prevent a common failure mode in AI systems:

> producing a confident answer before the judgment is structurally justified.
