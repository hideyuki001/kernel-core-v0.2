"""
Judgment Kernel Core v0.2 — Test Suite
Source spec: 09_test_suite.yaml

Validates:
- Core principle compliance
- Boundary enforcement
- Assignment integrity
- Uncertainty handling
- Hallucination prevention
- Schema integrity
- v0.2 additions: derived_from provenance, traceability invariant, structural_type preservation

Pass criteria (from spec):
- all_expected_fields_present
- no_failure_conditions_triggered
- schema_valid == True
- boundary_respected == True

Test categories:
  hallucination_prevention   — RF-001, RF-005, RF-007, RF-012
  uncertainty_handling       — RF-003, revisit_needed, confidence preservation
  assignment_integrity       — one-primary-cause invariant
  core_principle_compliance  — determinism, weaker interpretation preference
  boundary_enforcement       — STOP/DEFER/ALLOW prohibition, adapter_must_not
  schema_integrity           — RF-002, RF-004, RF-006, JSI signals
  boundary_regression        — B-01/B-02 destruction probe regressions
  v02_stability_signals      — derived_from population and content (Task 1)
  v02_traceability           — validate_traceability invariant (Task 2)
  v02_structural_type        — Uncertainty.structural_type preservation (Task 3)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kernel_core import (
    AdapterInput, Modality, TaskType,
    Evidence, EvidenceType, EvidenceStrength,
    Observation, Interpretation, InterpretationConstraints, SelectionBasis,
    Uncertainty, UncertaintyFlag, UncertaintyType, UncertaintyStructuralType,
    CauseAssignment, CauseValidation,
    PrimaryCause, SecondaryFactor, RootContext,
    make_cause_assignment,
    DecisionStub, DecisionStubConstraints, ActionHint,
    emit_judgment_event,
    AdapterInputRejected, KernelConstraintViolation,
    validate_adapter_input,
    build_traceability, validate_traceability, Traceability,
)


# ============================================================
# TEST RUNNER
# Minimal, deterministic. No external test framework dependency.
# ============================================================

_RESULTS: list[dict] = []


def run_test(test_id: str, name: str, category: str, fn) -> None:
    try:
        outcome, failures = fn()
        passed = outcome and not failures
        _RESULTS.append({
            "id": test_id,
            "name": name,
            "category": category,
            "passed": passed,
            "failures": failures,
        })
    except Exception as e:
        _RESULTS.append({
            "id": test_id,
            "name": name,
            "category": category,
            "passed": False,
            "failures": [f"EXCEPTION: {e}"],
        })


# ============================================================
# SHARED FIXTURE HELPERS
# Reduce duplication across tests with similar structure.
# All helpers return concrete objects; no shared mutable state.
# ============================================================

def _make_standard_stub(
    label: str = "intermediate",
    value: str = "test",
    action_hint: ActionHint = ActionHint.KEEP,
    not_final_decision: bool = True,
    no_policy_applied: bool = True,
) -> DecisionStub:
    """Standard intermediate decision stub with configurable constraints."""
    return DecisionStub(
        label=label,
        value=value,
        action_hint=action_hint,
        constraints=DecisionStubConstraints(
            not_final_decision=not_final_decision,
            no_policy_applied=no_policy_applied,
        ),
    )


def _make_single_evidence(
    evidence_id: str,
    ev_type: EvidenceType,
    source_location: str,
    detail: str,
    strength: EvidenceStrength,
) -> Evidence:
    """Construct a single Evidence instance."""
    return Evidence(
        evidence_id=evidence_id,
        type=ev_type,
        source_location=source_location,
        detail=detail,
        strength=strength,
    )


# ============================================================
# TC-001: ASR Unintelligible Audio
# ============================================================

def tc_001():
    adapter = AdapterInput(
        observation_unit="low volume, high noise segment",
        evidence_mapping=[
            _make_single_evidence(
                "E001", EvidenceType.AUDIBLE, "t=0.0-1.5",
                "audio amplitude below threshold", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.AUDIO,
        task_type=TaskType.ASR,
    )
    obs = Observation(
        raw_unit="low volume, high noise segment",
        normalized_unit="[unintelligible segment]",
        summary="audio segment with low amplitude and high noise",
    )
    interp = Interpretation(
        selected="unintelligible",
        alternatives=[],
        selection_basis=SelectionBasis.PARTIAL_RETENTION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.1,
        flags=[
            UncertaintyFlag(type=UncertaintyType.LOW_CONFIDENCE, detail="amplitude below threshold"),
            UncertaintyFlag(type=UncertaintyType.PARTIAL_AUDIBILITY, detail="high noise present"),
        ],
        unresolved_elements=["lexical content"],
        revisit_needed=False,
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="partial_audibility",
        secondary_factors=[],
        root_context=["low_signal_environment"],
    )
    stub = _make_standard_stub(label="intermediate", value="unintelligible", action_hint=ActionHint.FLAG)

    event = emit_judgment_event(adapter, "SEG-001", obs, interp, unc, cause, stub)

    failures = []
    if event.interpretation.selected != "unintelligible":
        failures.append("interpretation.selected != 'unintelligible'")
    unc_types = [f.type for f in event.uncertainty.flags]
    if UncertaintyType.LOW_CONFIDENCE not in unc_types:
        failures.append("uncertainty flag low_confidence missing")
    if UncertaintyType.PARTIAL_AUDIBILITY not in unc_types:
        failures.append("uncertainty flag partial_audibility missing")
    if event.cause_assignment.primary_cause != "partial_audibility":
        failures.append("primary_cause != partial_audibility")
    if event.red_flags:
        failures.append(f"unexpected red_flags: {[rf.flag_id for rf in event.red_flags]}")
    if event.interpretation.selected not in ("unintelligible", "unclear", "uncertain", "insufficient_evidence"):
        failures.append("fluent text produced instead of unknown state")
    return True, failures


# ============================================================
# TC-002: Translation Ambiguity Preservation
# ============================================================

def tc_002():
    adapter = AdapterInput(
        observation_unit="He saw her duck",
        evidence_mapping=[
            _make_single_evidence(
                "E002", EvidenceType.TEXTUAL, "span[0:16]",
                "lexically ambiguous: duck=animal or duck=action", EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="He saw her duck",
        normalized_unit="He saw her duck",
        summary="sentence with lexical ambiguity on word 'duck'",
    )
    interp = Interpretation(
        selected="ambiguous: duck (animal) or duck (action)",
        alternatives=["duck (animal)", "duck (action)"],
        selection_basis=SelectionBasis.WEAKER_INTERPRETATION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.4,
        flags=[UncertaintyFlag(type=UncertaintyType.AMBIGUITY, detail="'duck' is lexically ambiguous")],
        unresolved_elements=["word sense of 'duck'"],
        revisit_needed=False,
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="ambiguity_propagation",
        secondary_factors=[],
        root_context=["ambiguous_source_structure"],
    )
    stub = _make_standard_stub(label="intermediate", value="ambiguous", action_hint=ActionHint.DEFER_CANDIDATE)

    event = emit_judgment_event(adapter, "SEG-002", obs, interp, unc, cause, stub)

    failures = []
    if "duck (animal)" not in event.interpretation.alternatives:
        failures.append("alternative 'duck (animal)' missing")
    if "duck (action)" not in event.interpretation.alternatives:
        failures.append("alternative 'duck (action)' missing")
    unc_types = [f.type for f in event.uncertainty.flags]
    if UncertaintyType.AMBIGUITY not in unc_types:
        failures.append("uncertainty flag ambiguity missing")
    if event.cause_assignment.primary_cause != "ambiguity_propagation":
        failures.append("primary_cause != ambiguity_propagation")
    return True, failures


# ============================================================
# TC-003: Image Partial Visibility
# ============================================================

def tc_003():
    adapter = AdapterInput(
        observation_unit="object partially occluded in frame",
        evidence_mapping=[
            _make_single_evidence(
                "E003", EvidenceType.VISIBLE, "bbox[10,10,80,80]",
                "approximately 40% of object is visible", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.IMAGE,
        task_type=TaskType.IMAGE,
    )
    obs = Observation(
        raw_unit="object partially occluded in frame",
        normalized_unit="partially visible object",
        summary="object with partial occlusion, insufficient visibility for identification",
    )
    interp = Interpretation(
        selected="unknown_object",
        alternatives=[],
        selection_basis=SelectionBasis.PARTIAL_RETENTION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.1,
        flags=[UncertaintyFlag(type=UncertaintyType.PARTIAL_VISIBILITY, detail="object is ~40% visible")],
        unresolved_elements=["object identity"],
        revisit_needed=False,
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="partial_visibility_overreach",
        secondary_factors=[],
        root_context=["partial_visibility_condition"],
    )
    stub = _make_standard_stub(label="intermediate", value="unknown_object", action_hint=ActionHint.FLAG)

    event = emit_judgment_event(adapter, "SEG-003", obs, interp, unc, cause, stub)

    failures = []
    if event.interpretation.selected != "unknown_object":
        failures.append("interpretation.selected != 'unknown_object'")
    unc_types = [f.type for f in event.uncertainty.flags]
    if UncertaintyType.PARTIAL_VISIBILITY not in unc_types:
        failures.append("uncertainty flag partial_visibility missing")
    if event.cause_assignment.primary_cause != "partial_visibility_overreach":
        failures.append("primary_cause != partial_visibility_overreach")
    return True, failures


# ============================================================
# TC-004: Primary Cause Uniqueness
# ============================================================

def tc_004():
    adapter = AdapterInput(
        observation_unit="ambiguity collapsed and certainty increased",
        evidence_mapping=[
            _make_single_evidence(
                "E004", EvidenceType.TEXTUAL, "span[0:40]",
                "source had two readings; output committed to one definite meaning",
                EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="ambiguity collapsed and certainty increased",
        normalized_unit="ambiguity collapsed and certainty increased",
        summary="output committed to single meaning where source was ambiguous",
    )
    interp = Interpretation(
        selected="single committed meaning applied",
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=False,   # forced resolution occurred
        ),
    )
    unc = Uncertainty(
        confidence_score=0.6,
        flags=[UncertaintyFlag(type=UncertaintyType.AMBIGUITY, detail="source had multiple readings")],
        unresolved_elements=[],
        revisit_needed=False,
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="forced_resolution",
        secondary_factors=["certainty_shift"],
        root_context=["ambiguous_source_structure"],
    )
    stub = _make_standard_stub(
        label="intermediate", value="forced_resolution_detected", action_hint=ActionHint.FLAG
    )

    event = emit_judgment_event(adapter, "SEG-004", obs, interp, unc, cause, stub)

    failures = []
    if event.cause_assignment.primary_cause != "forced_resolution":
        failures.append("primary_cause != forced_resolution")
    if "certainty_shift" not in event.cause_assignment.secondary_factors:
        failures.append("secondary_factors missing certainty_shift")
    if not event.cause_assignment.validation.exactly_one_primary:
        failures.append("exactly_one_primary is False")
    return True, failures


# ============================================================
# TC-005: Weaker Interpretation Preference
# ============================================================

def tc_005():
    adapter = AdapterInput(
        observation_unit="two plausible interpretations with one stronger",
        evidence_mapping=[
            _make_single_evidence(
                "E005", EvidenceType.TEXTUAL, "span[0:50]",
                "evidence supports both interpretations; stronger requires additional assumption",
                EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="two plausible interpretations with one stronger",
        normalized_unit="two plausible interpretations with one stronger",
        summary="input segment with two valid readings",
    )
    interp = Interpretation(
        selected="weaker_option",
        alternatives=["stronger_option"],
        selection_basis=SelectionBasis.WEAKER_INTERPRETATION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.45,
        flags=[UncertaintyFlag(type=UncertaintyType.AMBIGUITY, detail="two plausible readings")],
        unresolved_elements=[],
        revisit_needed=False,
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="ambiguity_propagation",
        secondary_factors=[],
        root_context=["ambiguous_source_structure"],
    )
    stub = _make_standard_stub(label="intermediate", value="weaker_option")

    event = emit_judgment_event(adapter, "SEG-005", obs, interp, unc, cause, stub)

    failures = []
    if event.interpretation.selected != "weaker_option":
        failures.append("stronger interpretation selected without evidence")
    if not event.stability_signals.hesitation_present:
        failures.append("hesitation_present not True")
    return True, failures


# ============================================================
# TC-006: Uncertainty Preservation
# ============================================================

def tc_006():
    adapter = AdapterInput(
        observation_unit="low confidence input segment",
        evidence_mapping=[
            _make_single_evidence(
                "E006", EvidenceType.TEXTUAL, "span[0:20]",
                "input signal weak", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.QA,
    )
    obs = Observation(
        raw_unit="low confidence input segment",
        normalized_unit="low confidence input segment",
        summary="input segment with weak evidence signal",
    )
    interp = Interpretation(
        selected="uncertain",
        alternatives=[],
        selection_basis=SelectionBasis.PARTIAL_RETENTION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.2,
        flags=[UncertaintyFlag(type=UncertaintyType.LOW_CONFIDENCE, detail="evidence strength is low")],
        unresolved_elements=["meaning of input segment"],
        revisit_needed=True,
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="unsupported_inference",
        secondary_factors=[],
        root_context=[],
    )
    stub = _make_standard_stub(
        label="intermediate", value="uncertain", action_hint=ActionHint.DEFER_CANDIDATE
    )

    event = emit_judgment_event(adapter, "SEG-006", obs, interp, unc, cause, stub)

    failures = []
    unc_types = [f.type for f in event.uncertainty.flags]
    if UncertaintyType.LOW_CONFIDENCE not in unc_types:
        failures.append("uncertainty flag low_confidence missing")
    if not event.uncertainty.revisit_needed:
        failures.append("revisit_needed not True")
    if event.uncertainty.confidence_score is not None and event.uncertainty.confidence_score > 0.5:
        failures.append("confidence artificially high")
    return True, failures


# ============================================================
# TC-007: Forced Resolution Detection
# ============================================================

def tc_007():
    adapter = AdapterInput(
        observation_unit="ambiguous input resolved to single meaning",
        evidence_mapping=[
            _make_single_evidence(
                "E007", EvidenceType.TEXTUAL, "span[0:40]",
                "source has two readings; only one selected", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="ambiguous input resolved to single meaning",
        normalized_unit="ambiguous input resolved to single meaning",
        summary="ambiguous source committed to single interpretation",
    )
    interp = Interpretation(
        selected="single_meaning",
        alternatives=[],                       # forced: no alternatives retained
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=False,   # forced resolution occurred
        ),
    )
    unc = Uncertainty(
        confidence_score=0.7,
        flags=[],                              # collapsed: no uncertainty flags
        unresolved_elements=[],
        revisit_needed=False,
        uncertainty_preserved=False,
    )
    cause = make_cause_assignment(
        primary_cause="forced_resolution",
        secondary_factors=[],
        root_context=["ambiguous_source_structure"],
    )
    stub = _make_standard_stub(
        label="intermediate", value="forced_resolution_detected", action_hint=ActionHint.FLAG
    )

    event = emit_judgment_event(adapter, "SEG-007", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]
    if "RF-002" not in rf_ids:
        failures.append("RF-002 (forced_resolution) not emitted")
    return True, failures


# ============================================================
# TC-008: Primary Cause Duplication — KernelConstraintViolation
# D-04 aligned: one-primary is a Kernel structural invariant.
# Violation must prevent event construction entirely.
# Spec basis: 02_core_principles.yaml one_event_one_primary_cause,
#             06_assignment_logic.md §2, 01_kernel_charter.md §9.
# Chosen behavior: raise KernelConstraintViolation before event is emitted.
# Rationale: emitting an event with invalid causal structure would produce
#            an unreliable intermediate artifact. The Kernel must stop.
# ============================================================

def tc_008():
    """
    exactly_one_primary=False passed to Kernel.
    Expected: KernelConstraintViolation raised, no event generated.
    This is the canonical behavior for primary-cause invariant violation.
    """
    adapter = AdapterInput(
        observation_unit="two causes assigned as primary",
        evidence_mapping=[
            _make_single_evidence(
                "E008", EvidenceType.TEXTUAL, "span[0:30]",
                "two causes both marked primary", EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="two causes assigned as primary",
        normalized_unit="two causes assigned as primary",
        summary="causal structure with invalid double primary",
    )
    interp = Interpretation(
        selected="ambiguous",
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(evidence_bound=True),
    )
    unc = Uncertainty(confidence_score=None, flags=[], uncertainty_preserved=True)
    cause = make_cause_assignment(
        primary_cause="forced_resolution",
        secondary_factors=[],
        root_context=[],
        exactly_one_primary=False,    # structural violation under test
        no_primary_duplication=True,
    )
    stub = _make_standard_stub(label="intermediate", value="invalid", action_hint=ActionHint.FLAG)

    failures = []
    raised = False
    event_generated = False
    try:
        emit_judgment_event(adapter, "SEG-008", obs, interp, unc, cause, stub)
        event_generated = True
    except KernelConstraintViolation:
        raised = True

    if not raised:
        failures.append("KernelConstraintViolation not raised for exactly_one_primary=False")
    if event_generated:
        failures.append(
            "event was generated despite primary-cause invariant violation — kernel did not stop"
        )
    return True, failures


# ============================================================
# TC-009: No Decision Authority
# ============================================================

def tc_009():
    adapter = AdapterInput(
        observation_unit="ambiguous and risky input segment",
        evidence_mapping=[
            _make_single_evidence(
                "E009", EvidenceType.TEXTUAL, "span[0:30]",
                "input is ambiguous", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.QA,
    )
    obs = Observation(
        raw_unit="ambiguous and risky input segment",
        normalized_unit="ambiguous and risky input segment",
        summary="ambiguous input of uncertain content",
    )
    interp = Interpretation(
        selected="uncertain",
        alternatives=[],
        selection_basis=SelectionBasis.PARTIAL_RETENTION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.2,
        flags=[UncertaintyFlag(type=UncertaintyType.LOW_CONFIDENCE, detail="low evidence strength")],
        revisit_needed=True,
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="ambiguity_propagation",
        secondary_factors=[],
        root_context=[],
    )
    stub = _make_standard_stub(
        label="intermediate", value="uncertain", action_hint=ActionHint.DEFER_CANDIDATE
    )

    event = emit_judgment_event(adapter, "SEG-009", obs, interp, unc, cause, stub)

    failures = []
    if event.decision_stub.label != "intermediate":
        failures.append("decision_stub.label != 'intermediate'")
    if not event.decision_stub.constraints.not_final_decision:
        failures.append("not_final_decision is False")
    forbidden = {"STOP", "DEFER", "ALLOW"}
    if event.decision_stub.value.upper() in forbidden:
        failures.append(f"forbidden decision value present: {event.decision_stub.value}")
    return True, failures


# ============================================================
# TC-010: No Context Injection
# ============================================================

def tc_010():
    adapter = AdapterInput(
        observation_unit="missing context segment",
        evidence_mapping=[
            _make_single_evidence(
                "E010", EvidenceType.TEXTUAL, "span[0:20]",
                "context is absent from input", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.QA,
        optional_context=None,   # no context provided
    )
    obs = Observation(
        raw_unit="missing context segment",
        normalized_unit="missing context segment",
        summary="segment with absent context",
    )
    interp = Interpretation(
        selected="uncertain",
        alternatives=[],
        selection_basis=SelectionBasis.PARTIAL_RETENTION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.1,
        flags=[UncertaintyFlag(type=UncertaintyType.UNRESOLVED, detail="context absent")],
        unresolved_elements=["context"],
        revisit_needed=True,
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="instruction_misalignment",
        secondary_factors=[],
        root_context=["under_specified_task_context"],
    )
    stub = _make_standard_stub(
        label="intermediate", value="uncertain", action_hint=ActionHint.DEFER_CANDIDATE
    )

    event = emit_judgment_event(adapter, "SEG-010", obs, interp, unc, cause, stub)

    failures = []
    if event.interpretation.selected != "uncertain":
        failures.append("interpretation.selected != 'uncertain'")
    if adapter.optional_context is not None:
        failures.append("external context was injected")
    return True, failures


# ============================================================
# TC-011: Hesitation Signal Detection
# ============================================================

def tc_011():
    adapter = AdapterInput(
        observation_unit="multiple plausible interpretations present",
        evidence_mapping=[
            _make_single_evidence(
                "E011", EvidenceType.TEXTUAL, "span[0:40]",
                "two valid interpretations, roughly equal evidence", EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="multiple plausible interpretations present",
        normalized_unit="multiple plausible interpretations present",
        summary="segment with multiple valid readings",
    )
    interp = Interpretation(
        selected="interpretation_A",
        alternatives=["interpretation_B"],
        selection_basis=SelectionBasis.WEAKER_INTERPRETATION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.45,
        flags=[UncertaintyFlag(type=UncertaintyType.AMBIGUITY, detail="two valid readings")],
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="ambiguity_propagation",
        secondary_factors=[],
        root_context=[],
    )
    stub = _make_standard_stub(
        label="intermediate", value="ambiguous", action_hint=ActionHint.DEFER_CANDIDATE
    )

    event = emit_judgment_event(adapter, "SEG-011", obs, interp, unc, cause, stub)

    failures = []
    if not event.stability_signals.hesitation_present:
        failures.append("hesitation_present not True")
    return True, failures


# ============================================================
# TC-012: Conflict Signal Detection
# ============================================================

def tc_012():
    adapter = AdapterInput(
        observation_unit="evidence contradicts interpretation",
        evidence_mapping=[
            _make_single_evidence(
                "E012", EvidenceType.TEXTUAL, "span[0:40]",
                "evidence supports reading A", EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.QA,
    )
    obs = Observation(
        raw_unit="evidence contradicts interpretation",
        normalized_unit="evidence contradicts interpretation",
        summary="conflict between evidence and selected interpretation",
    )
    interp = Interpretation(
        selected="reading_B",                  # does not match evidence
        alternatives=["reading_A"],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=False,              # conflict: not evidence-bound
            weaker_interpretation_applied=False,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.3,
        flags=[UncertaintyFlag(
            type=UncertaintyType.AMBIGUITY, detail="evidence-interpretation mismatch"
        )],
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="unsupported_inference",
        secondary_factors=[],
        root_context=[],
    )
    stub = _make_standard_stub(label="intermediate", value="conflict", action_hint=ActionHint.FLAG)

    event = emit_judgment_event(adapter, "SEG-012", obs, interp, unc, cause, stub)

    failures = []
    if not event.stability_signals.conflict_detected:
        failures.append("conflict_detected not True")
    return True, failures


# ============================================================
# TC-013: Hallucination Failure — RF-001 specific
# D-04 aligned: spec expects RF-001 (unsupported_inference) specifically.
# Fixture: evidence present but interpretation.selected is fluent text that
# no evidence detail supports. RF-001 triggers on evidence present but
# interpretation content not derivable from it (evidence[].detail does not
# contain information sufficient to produce the selected output).
# ============================================================

def tc_013():
    """
    Evidence is present but weak (LOW strength, unintelligible detail).
    interpretation.selected is a specific fluent claim the evidence cannot support.
    Expected: RF-001 (unsupported_inference) emitted — not RF-003.

    RF-001 vs RF-003 distinction:
      RF-001 = interpretation asserts content beyond what evidence contains
      RF-003 = uncertainty signals are missing for weak evidence
    This fixture specifically tests RF-001 by ensuring the interpretation
    makes a claim that exceeds the observable evidence content.
    """
    adapter = AdapterInput(
        observation_unit="[inaudible: 1.2s]",
        evidence_mapping=[
            _make_single_evidence(
                "E013", EvidenceType.AUDIBLE, "t=0.0-1.2",
                "audio is inaudible; no speech content recoverable", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.AUDIO,
        task_type=TaskType.ASR,
    )
    obs = Observation(
        raw_unit="[inaudible: 1.2s]",
        normalized_unit="[inaudible segment]",
        summary="inaudible audio segment",
    )
    interp = Interpretation(
        # Fluent output far exceeding what inaudible evidence can support.
        # This is the hallucination condition for RF-001.
        selected="The quarterly results exceeded expectations by fifteen percent",
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=None,
        # Deliberately includes one uncertainty flag to test that RF-001 fires
        # on the interpretation-evidence mismatch, independent of RF-003.
        flags=[UncertaintyFlag(type=UncertaintyType.LOW_CONFIDENCE, detail="evidence is inaudible")],
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause=PrimaryCause.UNSUPPORTED_INFERENCE,
        secondary_factors=[],
        root_context=[RootContext.LOW_SIGNAL_ENVIRONMENT],
    )
    stub = _make_standard_stub(
        label="intermediate", value="hallucination_detected", action_hint=ActionHint.FLAG
    )

    event = emit_judgment_event(adapter, "SEG-013", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]
    if "RF-001" not in rf_ids:
        failures.append(
            f"RF-001 (unsupported_inference) not emitted. "
            f"Got: {rf_ids}. "
            f"Fixture has inaudible evidence but fluent interpretation.selected — this is hallucination."
        )
    return True, failures


# ============================================================
# TC-014: Uncertainty Collapse Failure
# ============================================================

def tc_014():
    """Uncertain input but no flags — should produce RF-003."""
    adapter = AdapterInput(
        observation_unit="uncertain input with no flags",
        evidence_mapping=[
            _make_single_evidence(
                "E014", EvidenceType.TEXTUAL, "span[0:30]",
                "signal weak", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="uncertain input with no flags",
        normalized_unit="uncertain input with no flags",
        summary="uncertain segment with no uncertainty annotations",
    )
    interp = Interpretation(
        selected="definite reading",
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.9,               # artificially high for LOW evidence
        flags=[],                            # collapsed: no flags
        uncertainty_preserved=False,
    )
    cause = make_cause_assignment(
        primary_cause="certainty_shift",
        secondary_factors=[],
        root_context=[],
    )
    stub = _make_standard_stub(
        label="intermediate", value="collapse_detected", action_hint=ActionHint.FLAG
    )

    event = emit_judgment_event(adapter, "SEG-014", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]
    if "RF-003" not in rf_ids:
        failures.append("RF-003 (uncertainty_collapse) not emitted")
    return True, failures


# ============================================================
# TC-015: Boundary Violation — validation.boundary_respected == False
# D-04 aligned: must directly check validation.boundary_respected, not a proxy.
# W-06 enables this: build_validation now inspects decision_stub.constraints.
# ============================================================

def tc_015():
    """
    decision_stub.constraints.not_final_decision=False simulates a kernel output
    that has crossed into final decision authority.
    Expected: event.validation.boundary_respected == False.

    This directly tests the W-06 boundary_respected strengthening.
    From 03_execution_boundary.md §7: assigning STOP/DEFER/ALLOW or producing
    final decisions is a boundary violation.
    """
    adapter = AdapterInput(
        observation_unit="boundary violation scenario",
        evidence_mapping=[
            _make_single_evidence(
                "E015", EvidenceType.TEXTUAL, "span[0:30]",
                "input evidence for boundary test", EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.QA,
    )
    obs = Observation(
        raw_unit="boundary violation scenario",
        normalized_unit="boundary violation scenario",
        summary="scenario with kernel attempting final decision authority",
    )
    interp = Interpretation(
        selected="determined output",
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(evidence_bound=True),
    )
    unc = Uncertainty(confidence_score=None, flags=[], uncertainty_preserved=True)
    cause = make_cause_assignment(
        primary_cause="instruction_misalignment",
        secondary_factors=[],
        root_context=[],
    )
    # Boundary violation: decision_stub claims final decision authority
    stub = DecisionStub(
        label="final_decision",
        value="approved",
        action_hint=ActionHint.FLAG,
        constraints=DecisionStubConstraints(
            not_final_decision=False,   # violation: kernel claimed final authority
            no_policy_applied=False,    # violation: policy was applied
        ),
    )

    event = emit_judgment_event(adapter, "SEG-015", obs, interp, unc, cause, stub)

    failures = []
    if event.validation.boundary_respected:
        failures.append(
            "validation.boundary_respected is True but should be False — "
            "decision_stub.constraints.not_final_decision=False indicates boundary violation"
        )
    if event.decision_stub.constraints.not_final_decision:
        failures.append(
            "decision_stub.constraints.not_final_decision was silently corrected to True — "
            "kernel must preserve input state, not fix it"
        )
    return True, failures


# ============================================================
# TC-016: Attribution Overreach Detection (RF-005)
# Phase 1 addition — D-01
# ============================================================

def tc_016():
    """
    responsibility_shift primary cause without any agency evidence in evidence detail.
    Expected: RF-005 emitted.
    """
    adapter = AdapterInput(
        observation_unit="彼女が決定した",
        evidence_mapping=[
            _make_single_evidence(
                "E016", EvidenceType.TEXTUAL, "span[0:7]",
                "source text states an action occurred",  # no agency marker
                EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="彼女が決定した",
        normalized_unit="She decided",
        summary="action performed by named actor",
    )
    interp = Interpretation(
        selected="She made the decision intentionally",  # intent assertion unsupported
        alternatives=["An action was performed"],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(confidence_score=0.6, flags=[], uncertainty_preserved=True)
    cause = make_cause_assignment(
        primary_cause="responsibility_shift",
        secondary_factors=[],
        root_context=["ambiguous_source_structure"],
    )
    stub = _make_standard_stub(
        label="intermediate", value="attribution_overreach_candidate", action_hint=ActionHint.FLAG
    )

    event = emit_judgment_event(adapter, "SEG-016", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]
    if "RF-005" not in rf_ids:
        failures.append("RF-005 (attribution_overreach) not emitted")
    return True, failures


# ============================================================
# TC-017: Guessed Completion Detection (RF-007)
# Phase 1 addition — D-01 (severity: high)
# ============================================================

def tc_017():
    """
    All evidence LOW, confidence_score high, selected is committed fluent text.
    Expected: RF-007 emitted.
    """
    adapter = AdapterInput(
        observation_unit="[inaudible background noise 0.5-2.1s]",
        evidence_mapping=[
            _make_single_evidence(
                "E017", EvidenceType.AUDIBLE, "t=0.5-2.1",
                "background noise only, no discernible speech", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.AUDIO,
        task_type=TaskType.ASR,
    )
    obs = Observation(
        raw_unit="[inaudible background noise 0.5-2.1s]",
        normalized_unit="[inaudible segment]",
        summary="audio segment with only background noise",
    )
    interp = Interpretation(
        selected="The meeting will start at nine o'clock tomorrow morning",  # guessed
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.85,              # artificially high for LOW evidence
        flags=[],
        uncertainty_preserved=False,
    )
    cause = make_cause_assignment(
        primary_cause="unsupported_inference",
        secondary_factors=[],
        root_context=["low_signal_environment"],
    )
    stub = _make_standard_stub(
        label="intermediate", value="guessed_output_detected", action_hint=ActionHint.FLAG
    )

    event = emit_judgment_event(adapter, "SEG-017", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]
    if "RF-007" not in rf_ids:
        failures.append("RF-007 (guessed_completion) not emitted")
    return True, failures


# ============================================================
# TC-018: Hidden Context Injection Detection (RF-012)
# Phase 1 addition — D-01 (severity: high)
# ============================================================

def tc_018():
    """
    instruction_misalignment as primary cause but interpretation.selected is committed.
    Expected: RF-012 emitted.
    """
    adapter = AdapterInput(
        observation_unit="Please process according to procedure",
        evidence_mapping=[
            _make_single_evidence(
                "E018", EvidenceType.TEXTUAL, "span[0:38]",
                "instruction references 'procedure' without specifying which",
                EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.QA,
    )
    obs = Observation(
        raw_unit="Please process according to procedure",
        normalized_unit="Please process according to procedure",
        summary="instruction with unspecified procedure reference",
    )
    interp = Interpretation(
        # Specific policy not present in input — hidden context injected.
        selected="Apply the standard 3-step verification process as defined in company policy v2.1",
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(confidence_score=0.8, flags=[], uncertainty_preserved=True)
    cause = make_cause_assignment(
        primary_cause="instruction_misalignment",
        secondary_factors=[],
        root_context=["under_specified_task_context"],
    )
    stub = _make_standard_stub(
        label="intermediate", value="hidden_context_candidate", action_hint=ActionHint.FLAG
    )

    event = emit_judgment_event(adapter, "SEG-018", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]
    if "RF-012" not in rf_ids:
        failures.append("RF-012 (hidden_context_injection) not emitted")
    return True, failures


# ============================================================
# TC-019: Determinism — same input produces same event_id and timestamp
# Phase 1 addition — D-02
# ============================================================

def tc_019():
    """
    Calling emit_judgment_event twice with identical inputs must produce
    identical event_id and timestamp.
    From 01_kernel_charter.md §5.
    """
    def _make_adapter():
        return AdapterInput(
            observation_unit="determinism test segment",
            evidence_mapping=[
                _make_single_evidence(
                    "E019", EvidenceType.TEXTUAL, "span[0:25]",
                    "test evidence", EvidenceStrength.MEDIUM,
                )
            ],
            modality=Modality.TEXT,
            task_type=TaskType.TRANSLATION,
        )

    def _make_event(adapter):
        obs = Observation(
            raw_unit="determinism test segment",
            normalized_unit="determinism test segment",
            summary="test segment for determinism verification",
        )
        interp = Interpretation(
            selected="test interpretation",
            alternatives=[],
            selection_basis=SelectionBasis.EVIDENCE_LINKED,
            constraints=InterpretationConstraints(evidence_bound=True),
        )
        unc = Uncertainty(confidence_score=0.8, flags=[], uncertainty_preserved=True)
        cause = make_cause_assignment(
            primary_cause="ambiguity_propagation",
            secondary_factors=[],
            root_context=[],
        )
        stub = _make_standard_stub(label="intermediate", value="test")
        return emit_judgment_event(adapter, "SEG-019", obs, interp, unc, cause, stub)

    event_a = _make_event(_make_adapter())
    event_b = _make_event(_make_adapter())

    failures = []
    if event_a.event_id != event_b.event_id:
        failures.append(f"event_id not deterministic: {event_a.event_id} != {event_b.event_id}")
    if event_a.timestamp != event_b.timestamp:
        failures.append(f"timestamp not deterministic: {event_a.timestamp} != {event_b.timestamp}")
    if not event_a.timestamp.startswith("DET-"):
        failures.append(f"timestamp format unexpected (should be DET-...): {event_a.timestamp}")
    return True, failures


# ============================================================
# TC-020: adapter_must_not — context with all-LOW evidence rejected
# Phase 1 addition — D-03
# ============================================================

def tc_020():
    """
    optional_context present alongside all-LOW evidence must trigger rejection.
    From 05_adapter_contract.yaml: adapter_must_not: override_uncertainty_flags.
    """
    adapter = AdapterInput(
        observation_unit="unclear segment",
        evidence_mapping=[
            _make_single_evidence(
                "E020", EvidenceType.AUDIBLE, "t=0.0-1.0",
                "signal below threshold", EvidenceStrength.LOW,
            )
        ],
        modality=Modality.AUDIO,
        task_type=TaskType.ASR,
        optional_context="This is a business meeting recording about Q3 results.",
    )

    failures = []
    rejections = validate_adapter_input(adapter)
    if "adapter_must_not:context_with_all_low_evidence" not in rejections:
        failures.append(
            "adapter_must_not:context_with_all_low_evidence not raised "
            "for optional_context + all-LOW evidence"
        )
    return True, failures


# ============================================================
# TC-021: Scope Expansion Detection (RF-006)
# Phase 1 addition — D-01
# ============================================================

def tc_021():
    """
    scope_shift primary cause without cross-boundary evidence.
    Expected: RF-006 emitted.
    """
    adapter = AdapterInput(
        observation_unit="the error occurred",
        evidence_mapping=[
            _make_single_evidence(
                "E021", EvidenceType.TEXTUAL, "span[0:17]",
                "a single error event is described", EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.QA,
    )
    obs = Observation(
        raw_unit="the error occurred",
        normalized_unit="the error occurred",
        summary="single error event",
    )
    interp = Interpretation(
        selected="systemic failure across all modules",  # scope beyond single event
        alternatives=["the error occurred"],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(confidence_score=0.6, flags=[], uncertainty_preserved=True)
    cause = make_cause_assignment(
        primary_cause="scope_shift",        # scope_shift without cross-boundary evidence
        secondary_factors=[],
        root_context=[],
    )
    stub = _make_standard_stub(
        label="intermediate", value="scope_expansion_candidate", action_hint=ActionHint.FLAG
    )

    event = emit_judgment_event(adapter, "SEG-021", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]
    if "RF-006" not in rf_ids:
        failures.append("RF-006 (scope_expansion) not emitted")
    return True, failures


# ============================================================
# TC-022: Forced Resolution — RF-002 + conflict_detected, NOT hesitation
# Boundary regression: B-02 fix. Verifies that forced resolution is
# visible as conflict (structural mismatch), not hesitation (remaining doubt).
# Semantic distinction: hesitation = alternatives still open;
# conflict = alternatives were erased. These must not be conflated.
# ============================================================

def tc_022():
    """
    Forced resolution NG input: ambiguous source collapsed to single committed reading.
    alternatives=[], forced_resolution_avoided=False, no uncertainty flags.

    Expected:
      - red_flags: [RF-002]          (forced resolution detected)
      - conflict_detected: True      (B-02: forced resolution is structural conflict)
      - hesitation_present: False    (no alternatives remain — hesitation cannot fire)
      - boundary_respected: True     (kernel did not cross decision boundary)

    Regression protection against:
      - RF-006 spurious emission from token-based summary/raw_unit comparison (B-01)
      - hesitation/conflict conflation (B-02)
    """
    adapter = AdapterInput(
        observation_unit="He saw her duck",
        evidence_mapping=[
            _make_single_evidence(
                "E022", EvidenceType.TEXTUAL, "span[0:16]",
                "lexically ambiguous: duck=animal or duck=action", EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="He saw her duck",
        normalized_unit="He saw her duck",
        summary="sentence containing the word duck",
    )
    interp = Interpretation(
        selected="彼は彼女のアヒルを見た",
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=False,     # forced resolution occurred
        ),
    )
    unc = Uncertainty(confidence_score=0.9, flags=[], uncertainty_preserved=False)
    cause = make_cause_assignment(
        primary_cause="ambiguity_propagation",
        secondary_factors=[],
        root_context=["ambiguous_source_structure"],
    )
    stub = _make_standard_stub(label="intermediate", value="translated")

    event = emit_judgment_event(adapter, "SEG-022", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]

    if "RF-002" not in rf_ids:
        failures.append("RF-002 (forced_resolution) not emitted")
    if "RF-006" in rf_ids:
        failures.append("RF-006 spuriously emitted — token-based scope detection regression (B-01)")
    if not event.stability_signals.conflict_detected:
        failures.append(
            "conflict_detected is False — forced resolution must be visible as conflict (B-02)"
        )
    if event.stability_signals.hesitation_present:
        failures.append(
            "hesitation_present is True — forced resolution erases alternatives, "
            "hesitation must not fire when no alternatives remain"
        )
    return True, failures


# ============================================================
# TC-023: Inaudible subject fill — RF-001/RF-003/RF-007, no RF-006 noise
# Boundary regression: B-01 fix. Verifies that hallucination detection
# fires the correct flags without RF-006 contaminating the signal.
# ============================================================

def tc_023():
    """
    Hallucination NG input: inaudible subject filled with specific actor.
    "[inaudible] ... went to the store." → "彼は店に行った"

    Expected:
      - red_flags: contains RF-001, RF-003, RF-007
      - red_flags: does NOT contain RF-006
      - boundary_respected: True

    Regression protection against:
      - RF-006 spurious emission contaminating hallucination detection (B-01)
    """
    adapter = AdapterInput(
        observation_unit="[inaudible] ... went to the store.",
        evidence_mapping=[
            _make_single_evidence(
                "E023", EvidenceType.AUDIBLE, "t=0.0-3.5",
                "first word is inaudible; remainder is 'went to the store'",
                EvidenceStrength.LOW,
            )
        ],
        modality=Modality.AUDIO,
        task_type=TaskType.ASR,
    )
    obs = Observation(
        raw_unit="[inaudible] ... went to the store.",
        normalized_unit="[inaudible] ... went to the store.",
        summary="audio with inaudible subject followed by audible predicate",
    )
    interp = Interpretation(
        selected="彼は店に行った",               # subject fabricated from inaudible evidence
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(confidence_score=0.8, flags=[], uncertainty_preserved=False)
    cause = make_cause_assignment(
        primary_cause="unsupported_inference",
        secondary_factors=[],
        root_context=["low_signal_environment"],
    )
    stub = _make_standard_stub(label="intermediate", value="asr_output")

    event = emit_judgment_event(adapter, "SEG-023", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]

    if "RF-001" not in rf_ids:
        failures.append("RF-001 (unsupported_inference) not emitted")
    if "RF-003" not in rf_ids:
        failures.append("RF-003 (uncertainty_collapse) not emitted")
    if "RF-007" not in rf_ids:
        failures.append("RF-007 (guessed_completion) not emitted")
    if "RF-006" in rf_ids:
        failures.append("RF-006 spuriously emitted — token-based scope detection regression (B-01)")
    return True, failures


# ============================================================
# TC-024: Dual primary cause raises KernelConstraintViolation
# Boundary regression: one-event-one-primary-cause invariant.
# Verifies that structural violation prevents event generation entirely.
# ============================================================

def tc_024():
    """
    exactly_one_primary=False passed to Kernel.
    Expected: KernelConstraintViolation raised, no event generated.

    Regression protection against:
      - silent acceptance of invalid causal structure
      - event generation proceeding past structural invariant violation
    """
    adapter = AdapterInput(
        observation_unit="ambiguous forced resolution scenario",
        evidence_mapping=[
            _make_single_evidence(
                "E024", EvidenceType.TEXTUAL, "span[0:40]",
                "dual cause scenario", EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="ambiguous forced resolution scenario",
        normalized_unit="ambiguous forced resolution scenario",
        summary="dual primary cause test",
    )
    interp = Interpretation(
        selected="forced single reading",
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(evidence_bound=True),
    )
    unc = Uncertainty(confidence_score=None, flags=[], uncertainty_preserved=True)
    cause = make_cause_assignment(
        primary_cause="ambiguity_propagation",
        secondary_factors=[],
        root_context=[],
        exactly_one_primary=False,           # structural violation
    )
    stub = _make_standard_stub(label="intermediate", value="dual_primary", action_hint=ActionHint.FLAG)

    failures = []
    raised = False
    event_generated = False
    try:
        emit_judgment_event(adapter, "SEG-024", obs, interp, unc, cause, stub)
        event_generated = True
    except KernelConstraintViolation:
        raised = True

    if not raised:
        failures.append("KernelConstraintViolation not raised for exactly_one_primary=False")
    if event_generated:
        failures.append(
            "event was generated despite primary-cause invariant violation — "
            "kernel must stop before emit"
        )
    return True, failures


# ============================================================
# TC-025: JSI misuse — boundary_respected=False, hesitation=True, no RF-006 noise
# Boundary regression: B-01 fix + W-06 boundary detection.
# Verifies that DEFER-labeled stub triggers boundary violation without
# RF-006 contaminating the output.
# ============================================================

def tc_025():
    """
    JSI misuse NG input: hesitation_present=True causes DEFER to be output.
    Stub carries not_final_decision=False — kernel crossed decision boundary.

    Expected:
      - boundary_respected: False    (W-06: not_final_decision=False detected)
      - hesitation_present: True     (alternatives exist, weaker interpretation applied)
      - red_flags: does NOT contain RF-006
      - red_flags: empty or contains only legitimate flags

    Regression protection against:
      - RF-006 spurious emission from JSI misuse fixture (B-01)
      - boundary violation going undetected (W-06)
    """
    adapter = AdapterInput(
        observation_unit="potentially ambiguous segment",
        evidence_mapping=[
            _make_single_evidence(
                "E025", EvidenceType.TEXTUAL, "span[0:30]",
                "two plausible readings exist", EvidenceStrength.MEDIUM,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="potentially ambiguous segment",
        normalized_unit="potentially ambiguous segment",
        summary="segment with two readings",
    )
    interp = Interpretation(
        selected="reading_A",
        alternatives=["reading_B"],
        selection_basis=SelectionBasis.WEAKER_INTERPRETATION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.4,
        flags=[UncertaintyFlag(type=UncertaintyType.AMBIGUITY, detail="two readings")],
        uncertainty_preserved=True,
    )
    cause = make_cause_assignment(
        primary_cause="ambiguity_propagation",
        secondary_factors=[],
        root_context=[],
    )
    # NG: JSI hesitation drives DEFER output — boundary violation
    stub = DecisionStub(
        label="DEFER",
        value="DEFER",
        action_hint=ActionHint.DEFER_CANDIDATE,
        constraints=DecisionStubConstraints(
            not_final_decision=False,            # boundary violation
            no_policy_applied=True,
        ),
    )

    event = emit_judgment_event(adapter, "SEG-025", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]

    if event.validation.boundary_respected:
        failures.append(
            "boundary_respected is True — DEFER output with not_final_decision=False "
            "must set boundary_respected=False (W-06)"
        )
    if not event.stability_signals.hesitation_present:
        failures.append("hesitation_present is False — alternatives exist, hesitation must fire")
    if "RF-006" in rf_ids:
        failures.append(
            "RF-006 spuriously emitted in JSI misuse fixture — "
            "token-based scope detection regression (B-01)"
        )
    return True, failures


# ============================================================
# TC-026: Scope expansion — RF-006 via canonical scope_shift path
# Boundary regression: B-01 fix. Verifies that RF-006 fires ONLY through
# the cause/evidence path, not the removed token-based path.
# ============================================================

def tc_026():
    """
    Scope expansion NG input: original meaning extended with unsupported advisory.
    "The system may fail under certain conditions."
    → "このシステムは条件によっては故障する可能性があるため注意が必要です"
    ("注意が必要です" = "caution is required" — not in source)

    primary_cause=scope_shift, evidence detail contains no cross-boundary markers.

    Expected:
      - red_flags: [RF-006]          (canonical scope_shift detection)
      - boundary_respected: True
      - RF-006 emitted via cause/evidence path, NOT via token comparison

    Regression protection against:
      - RF-006 silently disappearing if cause path is broken
      - RF-006 firing via the removed token-based path instead of cause path
    """
    adapter = AdapterInput(
        observation_unit="The system may fail under certain conditions.",
        evidence_mapping=[
            _make_single_evidence(
                "E026", EvidenceType.TEXTUAL, "span[0:46]",
                "modal statement about possible system failure under unspecified conditions",
                EvidenceStrength.HIGH,
            )
        ],
        modality=Modality.TEXT,
        task_type=TaskType.TRANSLATION,
    )
    obs = Observation(
        raw_unit="The system may fail under certain conditions.",
        normalized_unit="The system may fail under certain conditions.",
        summary="modal statement about system failure possibility",
    )
    interp = Interpretation(
        selected="このシステムは条件によっては故障する可能性があるため注意が必要です",
        alternatives=[],
        selection_basis=SelectionBasis.EVIDENCE_LINKED,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=False,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(confidence_score=0.85, flags=[], uncertainty_preserved=True)
    cause = make_cause_assignment(
        primary_cause="scope_shift",             # scope expansion is primary
        secondary_factors=[],
        root_context=[],
    )
    stub = _make_standard_stub(label="intermediate", value="translated")

    event = emit_judgment_event(adapter, "SEG-026", obs, interp, unc, cause, stub)

    failures = []
    rf_ids = [rf.flag_id for rf in event.red_flags]

    if "RF-006" not in rf_ids:
        failures.append(
            "RF-006 (scope_expansion) not emitted — "
            "scope_shift + no cross-boundary evidence must trigger RF-006"
        )
    unexpected = [f for f in rf_ids if f != "RF-006"]
    if unexpected:
        failures.append(f"unexpected red_flags emitted alongside RF-006: {unexpected}")
    if not event.validation.boundary_respected:
        failures.append("boundary_respected is False — no boundary violation in this fixture")
    return True, failures


# ============================================================
# TC-027: RF-011 false positive guard — short raw_unit and legitimate summary
# Regression protection for Option A fix (threshold 3→5, min_raw_len=10).
#
# Three sub-cases tested in one TC:
#   A. raw_unit is a structural identifier < 10 chars ("OK.") — RF-011 must NOT fire
#      regardless of summary length (min_raw_len guard).
#   B. raw_unit is natural language >= 10 chars with a legitimately descriptive summary
#      that does NOT exceed the 5x threshold — RF-011 must NOT fire.
#   C. True positive: natural language raw_unit >= 10 chars with inflated summary
#      (interpretation encoded as observation) > 5x — RF-011 MUST fire.
#
# Failure conditions:
#   - RF-011 fires on case A (short identifier) — min_raw_len guard broken
#   - RF-011 fires on case B (honest descriptive summary under threshold) — ratio guard too loose
#   - RF-011 does NOT fire on case C (genuine interpretation inflation) — detection broken
# ============================================================

def tc_027():
    """
    RF-011 false positive / true positive regression.
    Protects against: threshold-3 re-regression and guard removal.
    """
    failures = []

    def _build_event(raw_unit: str, summary: str):
        adapter = AdapterInput(
            observation_unit=raw_unit,
            evidence_mapping=[
                _make_single_evidence(
                    "E027", EvidenceType.TEXTUAL, "span[0:end]",
                    "textual content available for analysis", EvidenceStrength.MEDIUM,
                )
            ],
            modality=Modality.TEXT,
            task_type=TaskType.TRANSLATION,
        )
        obs = Observation(raw_unit=raw_unit, normalized_unit=raw_unit, summary=summary)
        interp = Interpretation(
            selected="partial retention applied",
            alternatives=[],
            selection_basis=SelectionBasis.PARTIAL_RETENTION,
            constraints=InterpretationConstraints(
                evidence_bound=True,
                weaker_interpretation_applied=True,
                forced_resolution_avoided=True,
            ),
        )
        unc = Uncertainty(confidence_score=0.6, flags=[], uncertainty_preserved=True)
        cause = make_cause_assignment(
            primary_cause="ambiguity_propagation",
            secondary_factors=[],
            root_context=[],
        )
        stub = _make_standard_stub(label="intermediate", value="retained")
        return emit_judgment_event(adapter, "SEG-027", obs, interp, unc, cause, stub)

    # Case A: short structural identifier — min_raw_len guard must suppress RF-011
    # raw_unit = "OK." (3 chars), summary = 86 chars → ratio ~28x
    raw_a = "OK."
    summary_a = "brief affirmative response token with no additional semantic content provided by the speaker"
    event_a = _build_event(raw_a, summary_a)
    rf_ids_a = [rf.flag_id for rf in event_a.red_flags]
    if "RF-011" in rf_ids_a:
        failures.append(
            f"Case A FAIL: RF-011 fired on short identifier raw_unit={repr(raw_a)} "
            f"(len={len(raw_a)}) — min_raw_len guard broken"
        )

    # Case B: natural language raw_unit, honest descriptive summary under 5x threshold
    # raw_unit = "He saw her duck" (15 chars), summary ~44 chars → ratio ~2.9x
    raw_b = "He saw her duck"
    summary_b = "sentence with lexical ambiguity on the word duck"
    event_b = _build_event(raw_b, summary_b)
    rf_ids_b = [rf.flag_id for rf in event_b.red_flags]
    if "RF-011" in rf_ids_b:
        failures.append(
            f"Case B FAIL: RF-011 fired on honest summary "
            f"(raw_len={len(raw_b)}, summary_len={len(summary_b)}, "
            f"ratio={len(summary_b)/len(raw_b):.1f}x) — threshold too aggressive"
        )

    # Case C: true positive — interpretation encoded as observation, > 5x inflation
    # raw_unit = "System ready" (12 chars), summary 90+ chars → ratio > 7x
    raw_c = "System ready"
    summary_c = (
        "system initialization sequence complete, all subsystems authenticated and loaded, "
        "ready for primary task execution with elevated privileges and full context restored"
    )
    event_c = _build_event(raw_c, summary_c)
    rf_ids_c = [rf.flag_id for rf in event_c.red_flags]
    ratio_c = len(summary_c) / len(raw_c)
    if "RF-011" not in rf_ids_c:
        failures.append(
            f"Case C FAIL: RF-011 did NOT fire on inflated summary "
            f"(raw_len={len(raw_c)}, summary_len={len(summary_c)}, ratio={ratio_c:.1f}x) "
            f"— true positive detection broken"
        )

    return True, failures


# ============================================================
# TC-028: derived_from — non-empty field population (Task 1)
# All StabilitySignalDerivation fields must be populated by derive_jsi_signals().
# Validates that no field is left as empty string in any normal event.
#
# Design: emit a well-formed event that triggers hesitation, conflict,
# doubt_persistence, overlap_signal, and HIGH fragility/density/risk.
# Then inspect derived_from for non-empty strings in all fields.
#
# Failure conditions:
#   - Any derived_from field is empty string ("") after event emission
# ============================================================

def tc_028():
    """
    derived_from must be fully populated on every emit (Task 1 invariant).
    """
    failures = []

    adapter = AdapterInput(
        observation_unit="multi-speaker segment with high noise and conflicting overlap signals",
        evidence_mapping=[
            _make_single_evidence(
                "E028a", EvidenceType.AUDIBLE, "t=0.0-3.0",
                "low amplitude audio, possible speech fragment", EvidenceStrength.LOW,
            ),
            _make_single_evidence(
                "E028b", EvidenceType.AUDIBLE, "t=1.5-3.0",
                "overlap signal detected, boundary unclear", EvidenceStrength.LOW,
            ),
        ],
        modality=Modality.AUDIO,
        task_type=TaskType.ASR,
    )
    obs = Observation(
        raw_unit="multi-speaker segment with high noise and conflicting overlap signals",
        normalized_unit="[multi-speaker uncertain segment]",
        summary="audio segment with unresolved overlap and low signal quality",
    )
    interp = Interpretation(
        selected="uncertain — possible speaker A or B",
        alternatives=["speaker A reading", "speaker B reading"],
        selection_basis=SelectionBasis.WEAKER_INTERPRETATION,
        constraints=InterpretationConstraints(
            evidence_bound=True,
            weaker_interpretation_applied=True,
            forced_resolution_avoided=True,
        ),
    )
    unc = Uncertainty(
        confidence_score=0.3,
        flags=[
            UncertaintyFlag(type=UncertaintyType.AMBIGUITY, detail="speaker identity ambiguous"),
            UncertaintyFlag(type=UncertaintyType.UNRESOLVED, detail="overlap boundary unresolved"),
        ],
        unresolved_elements=["speaker attribution", "overlap timing"],
        revisit_needed=True,
        uncertainty_preserved=True,
        structural_type=UncertaintyStructuralType.AMBIGUITY,
    )
    cause = make_cause_assignment(
        primary_cause="ambiguity_propagation",
        secondary_factors=["overlap_signal", "noise_interference"],
        root_context=["multi_speaker_scene"],
    )
    stub = _make_standard_stub(label="intermediate", value="uncertain_segment", action_hint=ActionHint.FLAG)

    event = emit_judgment_event(adapter, "SEG-028", obs, interp, unc, cause, stub)
    df = event.stability_signals.derived_from

    fields = {
        "hesitation_present": df.hesitation_present,
        "conflict_detected": df.conflict_detected,
        "doubt_persistence_present": df.doubt_persistence_present,
        "overlap_signal": df.overlap_signal,
        "assignment_fragility": df.assignment_fragility,
        "ambiguity_density": df.ambiguity_density,
        "reconstruction_risk": df.reconstruction_risk,
    }

    for field_name, value in fields.items():
        if not value or value.strip() == "":
            failures.append(
                f"derived_from.{field_name} is empty — "
                f"derive_jsi_signals must populate all fields"
            )

    return True, failures


# ============================================================
# TC-029: derived_from — content correctness (Task 1)
# Validates that derived_from strings correctly reflect the actual triggering condition.
#
# Probes:
#   A. hesitation_present=True with known trigger → derived_from.hesitation_present
#      must contain recognizable trigger description
#   B. conflict_detected=True via forced_resolution → derived_from.conflict_detected
#      must reference forced_resolution_avoided
#   C. doubt_persistence_present=True via revisit_needed → must reference revisit_needed
#   D. reconstruction_risk=HIGH (all LOW evidence) → must reference LOW in derivation
#
# Failure conditions:
#   - derived_from string does not reflect the actual trigger
# ============================================================

def tc_029():
    """
    derived_from strings must describe the correct triggering condition (Task 1 content check).
    """
    failures = []

    def _build(
        alternatives=None,
        weaker=False,
        confidence=0.7,
        forced_resolved=True,
        revisit=False,
        unresolved=None,
        all_low=False,
    ):
        ev_strength = EvidenceStrength.LOW if all_low else EvidenceStrength.MEDIUM
        adapter = AdapterInput(
            observation_unit="probe segment for derived_from content check",
            evidence_mapping=[
                _make_single_evidence(
                    "E029", EvidenceType.TEXTUAL, "span[0:end]",
                    "textual evidence for content probe", ev_strength,
                )
            ],
            modality=Modality.TEXT,
            task_type=TaskType.TRANSLATION,
        )
        obs = Observation(
            raw_unit="probe segment for derived_from content check",
            normalized_unit="probe segment",
            summary="probe for derived_from content correctness",
        )
        alts = alternatives or []
        interp = Interpretation(
            selected="probe reading" if not alts else alts[0],
            alternatives=alts,
            selection_basis=SelectionBasis.WEAKER_INTERPRETATION if weaker else SelectionBasis.EVIDENCE_LINKED,
            constraints=InterpretationConstraints(
                evidence_bound=True,
                weaker_interpretation_applied=weaker,
                forced_resolution_avoided=forced_resolved,
            ),
        )
        unc = Uncertainty(
            confidence_score=confidence,
            flags=[],
            unresolved_elements=unresolved or [],
            revisit_needed=revisit,
            uncertainty_preserved=True,
        )
        cause = make_cause_assignment(
            primary_cause="ambiguity_propagation",
            secondary_factors=[],
            root_context=[],
        )
        stub = _make_standard_stub(label="intermediate", value="probe")
        return emit_judgment_event(adapter, "SEG-029", obs, interp, unc, cause, stub)

    # Case A: hesitation via weaker_interpretation_applied
    event_a = _build(weaker=True)
    df_a = event_a.stability_signals.derived_from
    if not event_a.stability_signals.hesitation_present:
        failures.append("Case A SETUP: hesitation_present should be True for weaker=True")
    elif "weaker" not in df_a.hesitation_present.lower():
        failures.append(
            f"Case A FAIL: derived_from.hesitation_present does not reference 'weaker': "
            f"got {repr(df_a.hesitation_present)}"
        )

    # Case B: conflict via forced_resolution_avoided=False
    event_b = _build(forced_resolved=False)
    df_b = event_b.stability_signals.derived_from
    if not event_b.stability_signals.conflict_detected:
        failures.append("Case B SETUP: conflict_detected should be True for forced_resolved=False")
    elif "forced" not in df_b.conflict_detected.lower():
        failures.append(
            f"Case B FAIL: derived_from.conflict_detected does not reference 'forced': "
            f"got {repr(df_b.conflict_detected)}"
        )

    # Case C: doubt_persistence via revisit_needed
    event_c = _build(revisit=True)
    df_c = event_c.stability_signals.derived_from
    if not event_c.stability_signals.doubt_persistence_present:
        failures.append("Case C SETUP: doubt_persistence_present should be True for revisit=True")
    elif "revisit" not in df_c.doubt_persistence_present.lower():
        failures.append(
            f"Case C FAIL: derived_from.doubt_persistence_present does not reference 'revisit': "
            f"got {repr(df_c.doubt_persistence_present)}"
        )

    # Case D: reconstruction_risk=HIGH via all-LOW evidence
    event_d = _build(all_low=True)
    df_d = event_d.stability_signals.derived_from
    if event_d.stability_signals.reconstruction_risk.value != "high":
        failures.append("Case D SETUP: reconstruction_risk should be HIGH for all-LOW evidence")
    elif "low" not in df_d.reconstruction_risk.lower():
        failures.append(
            f"Case D FAIL: derived_from.reconstruction_risk does not reference 'LOW': "
            f"got {repr(df_d.reconstruction_risk)}"
        )

    return True, failures


# ============================================================
# TC-030: validate_traceability — invariant enforcement (Task 2)
# Broken traceability must raise KernelConstraintViolation,
# preventing event emission.
#
# Three sub-cases:
#   A. evidence=[] + selected="" → evidence_to_interpretation_linked=False → must raise
#   B. selected="" but evidence present → interpretation_to_cause_linked=False → must raise
#      (tested via direct call to validate_traceability with a broken Traceability object)
#   C. Well-formed input → traceability intact → must NOT raise
#
# Failure conditions:
#   - Case A or B does NOT raise KernelConstraintViolation
#   - Case A or B raises wrong exception type
#   - Case C raises any exception (regression — valid input broken by invariant)
# ============================================================

def tc_030():
    """
    validate_traceability() invariant: broken chain must block event emission (Task 2).
    """
    failures = []

    good_evidence = [
        _make_single_evidence(
            "E030", EvidenceType.TEXTUAL, "span[0:end]",
            "textual evidence for traceability probe", EvidenceStrength.MEDIUM,
        )
    ]

    def _make_adapter(obs_unit, evidence_list):
        return AdapterInput(
            observation_unit=obs_unit,
            evidence_mapping=evidence_list,
            modality=Modality.TEXT,
            task_type=TaskType.TRANSLATION,
        )

    def _make_obs(raw):
        return Observation(raw_unit=raw, normalized_unit=raw, summary="traceability probe")

    def _make_cause():
        return make_cause_assignment(primary_cause="ambiguity_propagation")

    def _make_stub():
        return _make_standard_stub(label="intermediate", value="probe")

    # Case C: positive control — valid input must succeed (no exception)
    try:
        obs_c = _make_obs("valid traceability probe input")
        interp_c = Interpretation(
            selected="valid interpretation anchored to evidence",
            alternatives=[],
            selection_basis=SelectionBasis.EVIDENCE_LINKED,
            constraints=InterpretationConstraints(
                evidence_bound=True,
                weaker_interpretation_applied=False,
                forced_resolution_avoided=True,
            ),
        )
        unc_c = Uncertainty(confidence_score=0.8, uncertainty_preserved=True)
        emit_judgment_event(
            _make_adapter("valid traceability probe input", good_evidence),
            "SEG-030C", obs_c, interp_c, unc_c, _make_cause(), _make_stub(),
        )
    except KernelConstraintViolation as e:
        failures.append(f"Case C FAIL: valid input raised KernelConstraintViolation: {e}")
    except Exception as e:
        failures.append(f"Case C FAIL: valid input raised unexpected exception: {type(e).__name__}: {e}")

    # Case A: empty selected → evidence_to_interpretation_linked=False → must raise
    try:
        obs_a = _make_obs("input with no derivable interpretation")
        interp_a = Interpretation(
            selected="",   # empty → evidence-to-interpretation link broken
            alternatives=[],
            selection_basis=SelectionBasis.EVIDENCE_LINKED,
            constraints=InterpretationConstraints(
                evidence_bound=True,
                weaker_interpretation_applied=False,
                forced_resolution_avoided=True,
            ),
        )
        unc_a = Uncertainty(confidence_score=None, uncertainty_preserved=True)
        emit_judgment_event(
            _make_adapter("input with no derivable interpretation", good_evidence),
            "SEG-030A", obs_a, interp_a, unc_a, _make_cause(), _make_stub(),
        )
        failures.append(
            "Case A FAIL: expected KernelConstraintViolation for empty "
            "interpretation.selected — none raised"
        )
    except KernelConstraintViolation:
        pass  # expected
    except Exception as e:
        failures.append(
            f"Case A FAIL: raised {type(e).__name__} instead of KernelConstraintViolation: {e}"
        )

    # Case B: directly test validate_traceability with a broken interpretation→cause link
    try:
        broken = Traceability(
            evidence_to_interpretation_linked=True,
            interpretation_to_cause_linked=False,   # broken link
            all_fields_evidence_traceable=False,
        )
        validate_traceability(broken)
        failures.append(
            "Case B FAIL: expected KernelConstraintViolation for broken "
            "interpretation→cause link — none raised"
        )
    except KernelConstraintViolation:
        pass  # expected
    except Exception as e:
        failures.append(
            f"Case B FAIL: raised {type(e).__name__} instead of KernelConstraintViolation: {e}"
        )

    return True, failures


# ============================================================
# TC-031: Uncertainty.structural_type — field preservation (Task 3)
# structural_type set by adapter must be preserved intact through emit.
#
# Six sub-cases (one per representative structural type):
#   A. structural_type=AMBIGUITY → event.uncertainty.structural_type == AMBIGUITY
#   B. structural_type=SIGNAL_LOSS → preserved
#   C. structural_type=CONFLICT → preserved
#   D. structural_type=UNCLASSIFIED (default) → preserved
#   E. structural_type=PARTIAL_AUDIBILITY → preserved
#   F. structural_type=UNRESOLVED_REFERENCE → preserved
#
# Also validates: structural_type is not auto-overridden by Kernel
# (Kernel must be a passive carrier — derivation is adapter-side concern).
#
# Failure conditions:
#   - structural_type in emitted event differs from what was set at construction
# ============================================================

def tc_031():
    """
    Uncertainty.structural_type must survive emit unchanged (Task 3 preservation check).
    """
    failures = []

    def _build_with_structural_type(stype: UncertaintyStructuralType):
        adapter = AdapterInput(
            observation_unit="structural type preservation probe",
            evidence_mapping=[
                _make_single_evidence(
                    "E031", EvidenceType.AUDIBLE, "t=0.0-2.0",
                    "audio segment for structural type probe", EvidenceStrength.MEDIUM,
                )
            ],
            modality=Modality.AUDIO,
            task_type=TaskType.ASR,
        )
        obs = Observation(
            raw_unit="structural type preservation probe",
            normalized_unit="structural probe",
            summary="probe for structural_type field preservation",
        )
        interp = Interpretation(
            selected="uncertain segment",
            alternatives=["reading A", "reading B"],
            selection_basis=SelectionBasis.WEAKER_INTERPRETATION,
            constraints=InterpretationConstraints(
                evidence_bound=True,
                weaker_interpretation_applied=True,
                forced_resolution_avoided=True,
            ),
        )
        unc = Uncertainty(
            confidence_score=0.5,
            flags=[UncertaintyFlag(type=UncertaintyType.AMBIGUITY, detail="probe ambiguity")],
            uncertainty_preserved=True,
            structural_type=stype,
        )
        cause = make_cause_assignment(
            primary_cause="ambiguity_propagation",
            secondary_factors=[],
            root_context=[],
        )
        stub = _make_standard_stub(label="intermediate", value="probe", action_hint=ActionHint.FLAG)
        return emit_judgment_event(adapter, "SEG-031", obs, interp, unc, cause, stub)

    cases = [
        (UncertaintyStructuralType.AMBIGUITY,            "A"),
        (UncertaintyStructuralType.SIGNAL_LOSS,          "B"),
        (UncertaintyStructuralType.CONFLICT,             "C"),
        (UncertaintyStructuralType.UNCLASSIFIED,         "D"),
        (UncertaintyStructuralType.PARTIAL_AUDIBILITY,   "E"),
        (UncertaintyStructuralType.UNRESOLVED_REFERENCE, "F"),
    ]

    for stype, label in cases:
        try:
            event = _build_with_structural_type(stype)
            actual = event.uncertainty.structural_type
            if actual != stype:
                failures.append(
                    f"Case {label} FAIL: structural_type={stype.value} was set but "
                    f"event.uncertainty.structural_type={actual.value} — "
                    f"Kernel must not override adapter-owned field"
                )
        except Exception as e:
            failures.append(
                f"Case {label} FAIL: unexpected exception for "
                f"structural_type={stype.value}: {type(e).__name__}: {e}"
            )

    return True, failures


# ============================================================
# MAIN RUNNER
# ============================================================

def main():
    test_cases = [
        # Core principle compliance
        ("TC-001", "ASR Unintelligible Audio",              "hallucination_prevention",  tc_001),
        ("TC-002", "Translation Ambiguity Preservation",    "uncertainty_handling",      tc_002),
        ("TC-003", "Image Partial Visibility",              "hallucination_prevention",  tc_003),
        ("TC-004", "Primary Cause Uniqueness",              "assignment_integrity",      tc_004),
        ("TC-005", "Weaker Interpretation Preference",      "core_principle_compliance", tc_005),
        ("TC-006", "Uncertainty Preservation",              "uncertainty_handling",      tc_006),
        ("TC-007", "Forced Resolution Detection",           "schema_integrity",          tc_007),
        ("TC-008", "Primary Cause Duplication Detection",   "assignment_integrity",      tc_008),
        ("TC-009", "No Decision Authority",                 "boundary_enforcement",      tc_009),
        ("TC-010", "No Context Injection",                  "boundary_enforcement",      tc_010),
        ("TC-011", "Hesitation Signal Detection",           "schema_integrity",          tc_011),
        ("TC-012", "Conflict Signal Detection",             "schema_integrity",          tc_012),
        ("TC-013", "Hallucination Failure",                 "hallucination_prevention",  tc_013),
        ("TC-014", "Uncertainty Collapse Failure",          "uncertainty_handling",      tc_014),
        ("TC-015", "Boundary Violation Failure",            "boundary_enforcement",      tc_015),
        # Phase 1 additions
        ("TC-016", "Attribution Overreach (RF-005)",        "hallucination_prevention",  tc_016),
        ("TC-017", "Guessed Completion (RF-007)",           "hallucination_prevention",  tc_017),
        ("TC-018", "Hidden Context Injection (RF-012)",     "hallucination_prevention",  tc_018),
        ("TC-019", "Determinism — event_id + timestamp",   "core_principle_compliance", tc_019),
        ("TC-020", "adapter_must_not: context+LOW evidence","boundary_enforcement",      tc_020),
        ("TC-021", "Scope Expansion (RF-006)",              "schema_integrity",          tc_021),
        # Boundary regression tests (from destruction probes B-01/B-02)
        ("TC-022", "Forced Resolution: RF-002 + conflict, not hesitation", "boundary_regression", tc_022),
        ("TC-023", "Inaudible subject fill: RF-001/003/007 only",          "boundary_regression", tc_023),
        ("TC-024", "Dual primary cause: KernelConstraintViolation",        "boundary_regression", tc_024),
        ("TC-025", "JSI misuse DEFER: boundary=False, no RF-006 noise",    "boundary_regression", tc_025),
        ("TC-026", "Scope expansion: RF-006 via canonical cause path",     "boundary_regression", tc_026),
        ("TC-027", "RF-011 false positive guard (min_raw_len + threshold 5)", "boundary_regression", tc_027),
        # v0.2 additions — P0 Task 1/2/3
        ("TC-028", "derived_from: all fields populated (Task 1)",           "v02_stability_signals", tc_028),
        ("TC-029", "derived_from: content correctness (Task 1)",            "v02_stability_signals", tc_029),
        ("TC-030", "validate_traceability: invariant enforcement (Task 2)", "v02_traceability",      tc_030),
        ("TC-031", "structural_type: field preservation (Task 3)",          "v02_structural_type",   tc_031),
    ]

    for tid, name, cat, fn in test_cases:
        run_test(tid, name, cat, fn)

    passed = [r for r in _RESULTS if r["passed"]]
    failed = [r for r in _RESULTS if not r["passed"]]

    print(f"\n{'='*60}")
    print(f"Judgment Kernel Core v0.2 — Test Suite Results")
    print(f"{'='*60}")
    print(f"Total: {len(_RESULTS)}  |  Passed: {len(passed)}  |  Failed: {len(failed)}")
    print(f"{'='*60}\n")

    for r in _RESULTS:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] {r['id']} — {r['name']}  ({r['category']})")
        for f in r.get("failures", []):
            print(f"       FAILURE: {f}")

    print(f"\n{'='*60}")
    if failed:
        print("RESULT: FAILURES DETECTED")
        sys.exit(1)
    else:
        print("RESULT: ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()

