"""
Judgment Kernel Core v0.2
Status: Implementation
Source specs: 01_kernel_charter.md through 09_test_suite.yaml

THIS MODULE:
- structures observation
- extracts evidence
- structures interpretation
- preserves uncertainty
- assigns one primary cause
- emits judgment events
- emits JSI signals with derivation provenance (v0.2)
- detects red flags (local only)
- enforces traceability as an invariant (v0.2)

THIS MODULE DOES NOT:
- make STOP / DEFER / ALLOW decisions
- select repair operators (JRO)
- perform audit or validation decisions
- generate handoff packets
- execute governance logic
- perform temporal tracking
- infer hidden context
- apply policy rules

v0.2 additions (from ADR-001):
  Task 1 — StabilitySignals.derived_from: each signal records its triggering condition.
  Task 2 — validate_traceability() is an invariant; broken chain blocks event emission.
  Task 3 — Uncertainty.structural_type: adapter-owned passive carrier; Kernel does not override.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================
# SECTION 1: ENUMERATIONS
# All values strictly from spec.
# ============================================================

class Modality(str, Enum):
    TEXT       = "text"
    AUDIO      = "audio"
    IMAGE      = "image"
    VIDEO      = "video"
    MULTIMODAL = "multimodal"


class TaskType(str, Enum):
    TRANSLATION = "translation"
    ASR         = "asr"
    IMAGE       = "image"
    VIDEO       = "video"
    QA          = "qa"
    MULTIMODAL  = "multimodal"


class EvidenceType(str, Enum):
    TEXTUAL    = "textual"
    AUDIBLE    = "audible"
    VISIBLE    = "visible"
    TEMPORAL   = "temporal"
    MULTIMODAL = "multimodal"


class EvidenceStrength(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class SelectionBasis(str, Enum):
    EVIDENCE_LINKED       = "evidence_linked"
    WEAKER_INTERPRETATION = "weaker_interpretation"
    PARTIAL_RETENTION     = "partial_retention"


class UncertaintyType(str, Enum):
    HESITATION            = "hesitation"
    AMBIGUITY             = "ambiguity"
    LOW_CONFIDENCE        = "low_confidence"
    PARTIAL_OBSERVABILITY = "partial_observability"
    PARTIAL_AUDIBILITY    = "partial_audibility"
    PARTIAL_VISIBILITY    = "partial_visibility"
    UNINTELLIGIBLE        = "unintelligible"
    UNRESOLVED            = "unresolved"
    REVISIT_NEEDED        = "revisit_needed"


class UncertaintyStructuralType(str, Enum):
    """
    Structural classification of uncertainty source. Added in v0.2 (Task 3 from ADR-001).

    Distinct from UncertaintyType (which describes *how* uncertain):
    this classifies *why* uncertainty exists structurally.
    Used for downstream aggregation and pattern detection.

    Ownership: adapter sets this at construction.
    Kernel carries it passively — never auto-derives or overwrites.
    """
    AMBIGUITY            = "ambiguity"            # multiple valid interpretations co-exist
    SIGNAL_LOSS          = "signal_loss"          # audio/visual signal below recoverable threshold
    CONFLICT             = "conflict"             # evidence sources contradict each other
    PARTIAL_VISIBILITY   = "partial_visibility"   # visual input incomplete or occluded
    PARTIAL_AUDIBILITY   = "partial_audibility"   # audio input incomplete or inaudible
    UNRESOLVED_REFERENCE = "unresolved_reference" # referent cannot be identified from input
    UNCLASSIFIED         = "unclassified"         # structural type not yet determinable


class ActionHint(str, Enum):
    KEEP            = "keep"
    EDIT            = "edit"
    FLAG            = "flag"
    DEFER_CANDIDATE = "defer_candidate"


class FragilityLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


# Primary cause taxonomy — strictly from 06_assignment_logic.md §10
class PrimaryCause(str, Enum):
    UNSUPPORTED_INFERENCE        = "unsupported_inference"
    FORCED_RESOLUTION            = "forced_resolution"
    CERTAINTY_SHIFT              = "certainty_shift"
    SCOPE_SHIFT                  = "scope_shift"
    RESPONSIBILITY_SHIFT         = "responsibility_shift"
    AMBIGUITY_PROPAGATION        = "ambiguity_propagation"
    PARTIAL_AUDIBILITY           = "partial_audibility"
    OVERLAP_MISATTRIBUTION       = "overlap_misattribution"
    PARTIAL_VISIBILITY_OVERREACH = "partial_visibility_overreach"
    INSTRUCTION_MISALIGNMENT     = "instruction_misalignment"
    UNKNOWN                      = "unknown"   # unknown-state fallback


# Secondary factor taxonomy — strictly from 06_assignment_logic.md §10
class SecondaryFactor(str, Enum):
    FLUENCY_PRESSURE        = "fluency_pressure"
    NOISE_INTERFERENCE      = "noise_interference"
    TERMINOLOGY_INSTABILITY = "terminology_instability"
    OVERLAP_SIGNAL          = "overlap_signal"
    WEAK_SOURCE_CLARITY     = "weak_source_clarity"
    CERTAINTY_SHIFT         = "certainty_shift"
    FORCED_RESOLUTION       = "forced_resolution"
    PARTIAL_AUDIBILITY      = "partial_audibility"
    UNSUPPORTED_ATTRIBUTION = "unsupported_attribution"
    SCOPE_RISK              = "scope_risk"


# Root context taxonomy — strictly from 06_assignment_logic.md §10
class RootContext(str, Enum):
    AMBIGUOUS_SOURCE_STRUCTURE   = "ambiguous_source_structure"
    LOW_SIGNAL_ENVIRONMENT       = "low_signal_environment"
    MULTI_SPEAKER_SCENE          = "multi_speaker_scene"
    PARTIAL_VISIBILITY_CONDITION = "partial_visibility_condition"
    UNDER_SPECIFIED_TASK_CONTEXT = "under_specified_task_context"


# Red flag IDs — strictly from 08_red_flag_library.yaml
class RedFlagID(str, Enum):
    RF_001 = "RF-001"
    RF_002 = "RF-002"
    RF_003 = "RF-003"
    RF_004 = "RF-004"
    RF_005 = "RF-005"
    RF_006 = "RF-006"
    RF_007 = "RF-007"
    RF_008 = "RF-008"
    RF_009 = "RF-009"
    RF_010 = "RF-010"
    RF_011 = "RF-011"
    RF_012 = "RF-012"


# ============================================================
# SECTION 2: EXCEPTIONS
# Defined before data structures — referenced throughout.
# ============================================================

class KernelConstraintViolation(Exception):
    """Raised when a core Kernel invariant is violated."""
    pass


class AdapterInputRejected(Exception):
    """Raised when adapter input fails structural validation."""
    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__(f"Adapter input rejected: {reasons}")


# ============================================================
# SECTION 3: CORE DATA STRUCTURES
# From 04_judgment_event_schema.yaml and related specs.
# ============================================================

@dataclass
class Evidence:
    evidence_id: str
    type: EvidenceType
    source_location: str
    detail: str
    strength: Optional[EvidenceStrength] = None


@dataclass
class InterpretationConstraints:
    evidence_bound: bool = True
    weaker_interpretation_applied: bool = False
    forced_resolution_avoided: bool = True


@dataclass
class Interpretation:
    selected: str                          # chosen interpretation; must be non-empty for valid traceability
    alternatives: list[str] = field(default_factory=list)
    selection_basis: SelectionBasis = SelectionBasis.EVIDENCE_LINKED
    constraints: InterpretationConstraints = field(default_factory=InterpretationConstraints)


@dataclass
class UncertaintyFlag:
    type: UncertaintyType
    detail: str


@dataclass
class Uncertainty:
    confidence_score: Optional[float]      # 0.0–1.0 or None
    flags: list[UncertaintyFlag] = field(default_factory=list)
    unresolved_elements: list[str] = field(default_factory=list)
    revisit_needed: bool = False
    uncertainty_preserved: bool = True
    structural_type: UncertaintyStructuralType = UncertaintyStructuralType.UNCLASSIFIED
    # v0.2 (Task 3): classifies *why* uncertainty exists (for downstream aggregation).
    # Adapter sets this. Kernel carries it passively — no auto-derivation, no overwrite.


@dataclass
class CauseValidation:
    exactly_one_primary: bool
    no_primary_duplication: bool


@dataclass
class CauseAssignment:
    primary_cause: PrimaryCause            # exactly one; Enum enforced at construction boundary
    secondary_factors: list[SecondaryFactor] = field(default_factory=list)
    root_context: list[RootContext] = field(default_factory=list)
    validation: CauseValidation = field(
        default_factory=lambda: CauseValidation(
            exactly_one_primary=True,
            no_primary_duplication=True,
        )
    )


@dataclass
class StabilitySignalDerivation:
    """
    Records the structural reason each StabilitySignals field became its value.
    Added in v0.2 (Task 1 from ADR-001).

    Populated by derive_jsi_signals(). Never left empty by Kernel.
    Enables downstream auditing of *why* each signal fired.
    """
    hesitation_present: str = ""        # e.g. "alternatives=2, weaker_interpretation_applied=True"
    conflict_detected: str = ""         # e.g. "forced_resolution_avoided=False"
    doubt_persistence_present: str = "" # e.g. "uncertainty.revisit_needed=True"
    overlap_signal: str = ""            # e.g. "secondary_factors=2"
    assignment_fragility: str = ""      # e.g. "no evidence", "alternatives=3"
    ambiguity_density: str = ""         # e.g. "ambiguity_flags=2, alternatives=3"
    reconstruction_risk: str = ""       # e.g. "all 2 evidence entries are LOW"


@dataclass
class StabilitySignals:
    hesitation_present: bool = False
    conflict_detected: bool = False
    doubt_persistence_present: bool = False
    overlap_signal: bool = False
    assignment_fragility: FragilityLevel = FragilityLevel.LOW
    ambiguity_density: FragilityLevel = FragilityLevel.LOW
    reconstruction_risk: FragilityLevel = FragilityLevel.LOW
    derived_from: StabilitySignalDerivation = field(default_factory=StabilitySignalDerivation)
    # v0.2 (Task 1): derived_from is populated by derive_jsi_signals().
    # Kernel guarantees it is never left empty.


@dataclass
class RedFlag:
    flag_id: str
    name: str
    violated_principles: list[str]
    evidence_ref: str


@dataclass
class DecisionStubConstraints:
    not_final_decision: bool = True
    no_policy_applied: bool = True


@dataclass
class DecisionStub:
    label: str                             # intermediate label only — NOT a final decision
    value: str
    action_hint: ActionHint
    constraints: DecisionStubConstraints = field(default_factory=DecisionStubConstraints)


@dataclass
class Traceability:
    evidence_to_interpretation_linked: bool
    interpretation_to_cause_linked: bool
    all_fields_evidence_traceable: bool


@dataclass
class ValidationBlock:
    schema_valid: bool
    evidence_present: bool
    interpretation_evidence_linked: bool
    uncertainty_if_needed_present: bool
    primary_cause_valid: bool
    boundary_respected: bool


@dataclass
class Observation:
    raw_unit: str
    normalized_unit: str
    summary: str                           # minimal factual description only; no interpretation


@dataclass
class JudgmentEvent:
    # --- Meta ---
    event_id: str
    timestamp: str
    segment_id: str
    task_type: TaskType
    modality: Modality
    version: str

    # --- Judgment layers ---
    observation: Observation
    evidence: list[Evidence]
    interpretation: Interpretation
    uncertainty: Uncertainty
    cause_assignment: CauseAssignment
    stability_signals: StabilitySignals
    red_flags: list[RedFlag]
    decision_stub: DecisionStub
    traceability: Traceability
    validation: ValidationBlock


# ============================================================
# SECTION 4: ADAPTER INPUT CONTRACT
# From 05_adapter_contract.yaml.
# Adapter determines WHAT to observe. Kernel determines HOW to judge.
# ============================================================

@dataclass
class AdapterInput:
    """
    Required inputs from Adapter to Kernel.
    Adapter determines WHAT to observe; Kernel determines HOW to judge.
    """
    observation_unit: str                  # required
    evidence_mapping: list[Evidence]       # required
    modality: Modality                     # required
    task_type: TaskType                    # required
    optional_context: Optional[str] = None # explicit only; no inference
    diff_information: Optional[str] = None # explicit diffs only


# ============================================================
# SECTION 5: CAUSE NORMALIZATION HELPERS
# From W-03: convert string inputs to Enum at the construction boundary.
# Use make_cause_assignment() instead of constructing CauseAssignment directly with strings.
# ============================================================

def normalize_primary_cause(value: str | PrimaryCause) -> PrimaryCause:
    """
    Accepts PrimaryCause enum or a string matching a PrimaryCause value.
    Raises KernelConstraintViolation if the value is not in the PrimaryCause taxonomy.
    """
    if isinstance(value, PrimaryCause):
        return value
    try:
        return PrimaryCause(value)
    except ValueError:
        raise KernelConstraintViolation(
            f"primary_cause '{value}' is not a valid PrimaryCause. "
            f"Allowed: {[e.value for e in PrimaryCause]}"
        )


def normalize_secondary_factors(values: list[str | SecondaryFactor]) -> list[SecondaryFactor]:
    """
    Accepts a list of SecondaryFactor enums or matching strings.
    Raises KernelConstraintViolation on any invalid value.
    """
    result: list[SecondaryFactor] = []
    for v in values:
        if isinstance(v, SecondaryFactor):
            result.append(v)
        else:
            try:
                result.append(SecondaryFactor(v))
            except ValueError:
                raise KernelConstraintViolation(
                    f"secondary_factor '{v}' is not a valid SecondaryFactor. "
                    f"Allowed: {[e.value for e in SecondaryFactor]}"
                )
    return result


def normalize_root_context(values: list[str | RootContext]) -> list[RootContext]:
    """
    Accepts a list of RootContext enums or matching strings.
    Raises KernelConstraintViolation on any invalid value.
    """
    result: list[RootContext] = []
    for v in values:
        if isinstance(v, RootContext):
            result.append(v)
        else:
            try:
                result.append(RootContext(v))
            except ValueError:
                raise KernelConstraintViolation(
                    f"root_context '{v}' is not a valid RootContext. "
                    f"Allowed: {[e.value for e in RootContext]}"
                )
    return result


def make_cause_assignment(
    primary_cause: str | PrimaryCause,
    secondary_factors: list[str | SecondaryFactor] | None = None,
    root_context: list[str | RootContext] | None = None,
    exactly_one_primary: bool = True,
    no_primary_duplication: bool = True,
) -> CauseAssignment:
    """
    Canonical constructor for CauseAssignment with full type enforcement.
    All string inputs are normalized to Enum values at this boundary.
    Use this instead of constructing CauseAssignment directly with strings.
    """
    return CauseAssignment(
        primary_cause=normalize_primary_cause(primary_cause),
        secondary_factors=normalize_secondary_factors(secondary_factors or []),
        root_context=normalize_root_context(root_context or []),
        validation=CauseValidation(
            exactly_one_primary=exactly_one_primary,
            no_primary_duplication=no_primary_duplication,
        ),
    )


# ============================================================
# SECTION 6: ADAPTER INPUT VALIDATION
# From 05_adapter_contract.yaml.
# ============================================================

def validate_adapter_input(adapter_input: AdapterInput) -> list[str]:
    """
    Returns a list of rejection reasons. Empty list = valid input.
    Rejection conditions from 05_adapter_contract.yaml.

    Checks:
      (a) Required fields are present.
      (b) adapter_must_not violations detectable at the structural input boundary.

    Semantic violations (hidden inference, fluency collapse, etc.) are caught
    downstream by detect_red_flags() at the event level.
    """
    rejections: list[str] = []

    # --- (a) Required fields ---
    if not adapter_input.observation_unit:
        rejections.append("missing_observation_unit")
    if not adapter_input.evidence_mapping:
        rejections.append("missing_evidence_mapping")
    if adapter_input.modality is None:
        rejections.append("missing_modality")
    if adapter_input.task_type is None:
        rejections.append("missing_task_type")

    # --- (b) adapter_must_not: structural signals only ---
    #
    # must_not: assign_multiple_primary_causes
    #   → Not applicable at AdapterInput level; enforced by _enforce_single_primary().
    #
    # must_not: force_resolution_without_evidence
    #   → Structural pre-check only; full detection via RF-002/RF-003 at event level.
    #   → No additional rejection here — covered by missing_evidence_mapping above.
    #
    # must_not: inject_missing_information
    #   → optional_context vs evidence_mapping mismatch is a downstream concern (RF-012).
    #
    # must_not: replace_observation_with_interpretation
    #   → observation_unit empty is caught by missing_observation_unit above.
    #
    # must_not: perform_hidden_inference / collapse_ambiguity_for_fluency /
    #           convert_weak_signal_to_strong_claim / apply_policy_or_business_rules
    #   → Semantic behaviors not detectable from AdapterInput structure alone.
    #   → Detected downstream via RF-005, RF-006, RF-007, RF-012.
    #
    # must_not: override_uncertainty_flags (structural signal)
    #   → If ALL evidence entries have strength=LOW AND optional_context is present,
    #     context risks becoming a de-facto evidence substitute → reject structurally.
    if adapter_input.evidence_mapping:
        has_strength_set = any(
            e.strength is not None for e in adapter_input.evidence_mapping
        )
        all_low = has_strength_set and all(
            e.strength == EvidenceStrength.LOW
            for e in adapter_input.evidence_mapping
            if e.strength is not None
        )
        if all_low and adapter_input.optional_context is not None:
            rejections.append("adapter_must_not:context_with_all_low_evidence")

    return rejections


# ============================================================
# SECTION 7: RED FLAG LIBRARY
# From 08_red_flag_library.yaml.
# All detection is local and structural only.
# Flags do NOT trigger decisions. Flags do NOT replace cause assignment.
# ============================================================

_RED_FLAG_DEFINITIONS: dict[str, dict] = {
    "RF-001": {
        "name": "unsupported_inference",
        "violated_principles": ["evidence_first", "no_hallucination"],
    },
    "RF-002": {
        "name": "forced_resolution",
        "violated_principles": [
            "uncertainty_preservation",
            "weaker_interpretation_preferred",
            "no_hallucination",
        ],
    },
    "RF-003": {
        "name": "uncertainty_collapse",
        "violated_principles": ["uncertainty_preservation"],
    },
    "RF-004": {
        "name": "over_strong_interpretation",
        "violated_principles": ["weaker_interpretation_preferred", "evidence_first"],
    },
    "RF-005": {
        "name": "attribution_overreach",
        "violated_principles": [
            "weaker_interpretation_preferred",
            "evidence_first",
            "no_hallucination",
        ],
    },
    "RF-006": {
        "name": "scope_expansion",
        "violated_principles": ["evidence_first", "weaker_interpretation_preferred"],
    },
    "RF-007": {
        "name": "guessed_completion",
        "violated_principles": ["no_hallucination", "evidence_first"],
    },
    "RF-008": {
        "name": "primary_cause_duplication",
        "violated_principles": ["one_event_one_primary_cause"],
    },
    "RF-009": {
        "name": "causal_inflation",
        "violated_principles": ["one_event_one_primary_cause", "evidence_first"],
    },
    "RF-010": {
        "name": "evidence_gap_masking",
        "violated_principles": ["evidence_first", "uncertainty_preservation"],
    },
    "RF-011": {
        "name": "interpretation_observation_swap",
        "violated_principles": ["evidence_first"],
    },
    "RF-012": {
        "name": "hidden_context_injection",
        "violated_principles": ["evidence_first", "no_hallucination"],
    },
}

# Vocabulary sets used in red flag detection — module-level constants for clarity.
_RF_UNINTELLIGIBLE_MARKERS: frozenset[str] = frozenset({
    "inaudible", "unintelligible", "no speech", "no content", "unclear", "indistinct",
    "unrecoverable", "not recoverable", "below threshold",
})

_RF_UNKNOWN_STATE_PREFIXES: frozenset[str] = frozenset({
    "unintelligible", "unclear", "uncertain", "insufficient_evidence",
    "revisit_needed", "unknown_object", "unknown", "[inaudible", "[unclear", "[uncertain",
})

_RF_UNKNOWN_STATES: frozenset[str] = frozenset({
    "unintelligible", "unclear", "uncertain", "insufficient_evidence",
    "revisit_needed", "unknown_object", "unknown",
})

_RF_AGENCY_MARKERS: frozenset[str] = frozenset({
    "subject", "actor", "agent", "intent", "speaker", "role", "responsible",
})

_RF_INTENT_MARKERS: frozenset[str] = frozenset({
    "intentionally", "deliberately", "meant to", "in order to", "wanted to", "decided to",
})

_RF_SCOPE_MARKERS: frozenset[str] = frozenset({
    "cross", "multiple", "prior", "previous", "context", "global", "batch",
})

_RF_FORBIDDEN_AUTHORITY_TOKENS: frozenset[str] = frozenset({
    "STOP", "DEFER", "ALLOW", "REJECT", "APPROVE",
})


def _make_red_flag(flag_id: str, evidence_ref: str) -> RedFlag:
    """Construct a RedFlag from the library definition and a caller-supplied evidence reference."""
    defn = _RED_FLAG_DEFINITIONS[flag_id]
    return RedFlag(
        flag_id=flag_id,
        name=defn["name"],
        violated_principles=list(defn["violated_principles"]),
        evidence_ref=evidence_ref,
    )


def detect_red_flags(
    evidence: list[Evidence],
    interpretation: Interpretation,
    uncertainty: Uncertainty,
    cause_assignment: CauseAssignment,
    observation: Observation,
) -> list[RedFlag]:
    """
    Local structural red flag detection.
    Returns a list of applicable RedFlag instances.
    Does NOT make decisions. Does NOT escalate. No severity arbitration.
    From 03_execution_boundary.md §3.8.
    """
    flags: list[RedFlag] = []

    # Precompute shared derived values used across multiple flag checks.
    _selected_lower = interpretation.selected.lower().strip()
    _selected_is_unknown_state = any(
        _selected_lower.startswith(p) for p in _RF_UNKNOWN_STATE_PREFIXES
    )
    _selected_is_unknown = _selected_lower in _RF_UNKNOWN_STATES

    _all_evidence_low = bool(evidence) and all(
        e.strength == EvidenceStrength.LOW
        for e in evidence
        if e.strength is not None
    )
    _has_strength_set = any(e.strength is not None for e in evidence)

    # ------------------------------------------------------------------
    # RF-001: unsupported_inference
    # Spec triggers: claim_without_evidence_link, interpretation_exceeds_observation,
    #   inferred_content_present_without_support.
    # ------------------------------------------------------------------
    # Case A: no evidence at all but interpretation makes a claim
    if interpretation.selected and not evidence:
        flags.append(_make_red_flag("RF-001", "evidence[]"))

    # Case B: all evidence is unintelligible/inaudible yet interpretation is a fluent claim
    if evidence and not _selected_is_unknown_state:
        all_evidence_unintelligible = all(
            any(m in e.detail.lower() for m in _RF_UNINTELLIGIBLE_MARKERS)
            for e in evidence
        )
        if all_evidence_unintelligible:
            if not any(rf.flag_id == "RF-001" for rf in flags):
                flags.append(_make_red_flag(
                    "RF-001",
                    "all evidence is unintelligible/inaudible but interpretation.selected is a fluent committed claim",
                ))

    # ------------------------------------------------------------------
    # RF-002: forced_resolution
    # Trigger: alternatives empty + weaker_interpretation_applied=False + forced_resolution_avoided=False
    # ------------------------------------------------------------------
    if (
        not interpretation.alternatives
        and not interpretation.constraints.weaker_interpretation_applied
        and not interpretation.constraints.forced_resolution_avoided
    ):
        flags.append(_make_red_flag(
            "RF-002",
            "interpretation.alternatives, interpretation.constraints",
        ))

    # ------------------------------------------------------------------
    # RF-003: uncertainty_collapse
    # Trigger: low-strength evidence exists but no uncertainty flags emitted
    # ------------------------------------------------------------------
    low_strength_evidence = [e for e in evidence if e.strength == EvidenceStrength.LOW]
    if low_strength_evidence and not uncertainty.flags:
        flags.append(_make_red_flag("RF-003", "evidence[strength=low], uncertainty.flags"))

    # ------------------------------------------------------------------
    # RF-004: over_strong_interpretation
    # Trigger: weaker_interpretation_applied=False when alternatives exist
    # ------------------------------------------------------------------
    if len(interpretation.alternatives) > 0 and not interpretation.constraints.weaker_interpretation_applied:
        flags.append(_make_red_flag(
            "RF-004",
            "interpretation.alternatives, interpretation.constraints.weaker_interpretation_applied",
        ))

    # ------------------------------------------------------------------
    # RF-005: attribution_overreach
    # Spec triggers: agency_added_without_source_support, intent_inferred_without_cues,
    #   speaker_role_fixed_without_evidence.
    # ------------------------------------------------------------------
    # Case A: primary_cause is responsibility_shift but evidence contains no agency markers
    if cause_assignment.primary_cause == PrimaryCause.RESPONSIBILITY_SHIFT:
        evidence_details_lower = " ".join(e.detail.lower() for e in evidence)
        has_agency_evidence = any(m in evidence_details_lower for m in _RF_AGENCY_MARKERS)
        if not has_agency_evidence:
            flags.append(_make_red_flag(
                "RF-005",
                "cause_assignment.primary_cause=responsibility_shift without agency evidence in evidence[].detail",
            ))

    # Case B: selected interpretation asserts intent not present in evidence
    selected_lower = interpretation.selected.lower()
    if any(m in selected_lower for m in _RF_INTENT_MARKERS):
        evidence_details_lower = " ".join(e.detail.lower() for e in evidence)
        if not any(m in evidence_details_lower for m in _RF_INTENT_MARKERS):
            if not any(rf.flag_id == "RF-005" for rf in flags):
                flags.append(_make_red_flag(
                    "RF-005",
                    "interpretation.selected contains intent assertion not supported by evidence[].detail",
                ))

    # ------------------------------------------------------------------
    # RF-006: scope_expansion
    # Spec triggers: interpretation extends beyond observable scope,
    #   content outside observation boundary referenced,
    #   cross-segment reasoning not explicitly provided.
    # Detection: cause/evidence path only (token-based removed in v0.1 — see ADR-001 D-06).
    # ------------------------------------------------------------------
    if cause_assignment.primary_cause == PrimaryCause.SCOPE_SHIFT:
        evidence_details_lower = " ".join(e.detail.lower() for e in evidence)
        has_scope_evidence = any(m in evidence_details_lower for m in _RF_SCOPE_MARKERS)
        if not has_scope_evidence:
            flags.append(_make_red_flag(
                "RF-006",
                "cause_assignment.primary_cause=scope_shift without cross-boundary evidence in evidence[].detail",
            ))

    # ------------------------------------------------------------------
    # RF-007: guessed_completion
    # Spec triggers: missing audio/visual filled with guessed content,
    #   high reconstruction_risk with confident output.
    # ------------------------------------------------------------------
    # Case A: all evidence LOW but selected is a committed fluent claim
    if _all_evidence_low and _has_strength_set and not _selected_is_unknown:
        flags.append(_make_red_flag(
            "RF-007",
            "evidence[].strength=LOW (all) but interpretation.selected is not an unknown-state value",
        ))

    # Case B: high confidence_score alongside all-LOW evidence
    if (
        _all_evidence_low and _has_strength_set
        and uncertainty.confidence_score is not None
        and uncertainty.confidence_score > 0.7
    ):
        if not any(rf.flag_id == "RF-007" for rf in flags):
            flags.append(_make_red_flag(
                "RF-007",
                "uncertainty.confidence_score > 0.7 with all-LOW evidence — probable guessed completion",
            ))

    # ------------------------------------------------------------------
    # RF-008: primary_cause_duplication
    # Triggers: exactly_one_primary=False, or primary repeated in secondary_factors.
    # ------------------------------------------------------------------
    if not cause_assignment.validation.exactly_one_primary:
        flags.append(_make_red_flag("RF-008", "cause_assignment.validation.exactly_one_primary"))

    if cause_assignment.primary_cause in cause_assignment.secondary_factors:
        if not any(rf.flag_id == "RF-008" for rf in flags):
            flags.append(_make_red_flag(
                "RF-008",
                "cause_assignment.primary_cause duplicated in secondary_factors",
            ))

    # ------------------------------------------------------------------
    # RF-009: causal_inflation
    # Trigger: secondary_factors count exceeds 3 for a single event.
    # ------------------------------------------------------------------
    if len(cause_assignment.secondary_factors) > 3:
        flags.append(_make_red_flag("RF-009", "cause_assignment.secondary_factors"))

    # ------------------------------------------------------------------
    # RF-010: evidence_gap_masking
    # Trigger: observation summary non-empty but evidence list empty.
    # ------------------------------------------------------------------
    if observation.summary and not evidence:
        flags.append(_make_red_flag("RF-010", "observation.summary, evidence[]"))

    # ------------------------------------------------------------------
    # RF-011: interpretation_observation_swap
    # Trigger: observation.summary substantially longer than raw_unit,
    #   indicating interpretation has been encoded as observation.
    # Guard (from ADR-001 D-05):
    #   raw_unit must be >= 10 chars (short tokens produce meaningless ratios).
    # Threshold: summary > raw_unit * 5 (raised from 3x to reduce false positives).
    # Option B (vocabulary-based detection) deferred to v0.3+.
    # ------------------------------------------------------------------
    if observation.summary and observation.raw_unit:
        raw_len = len(observation.raw_unit)
        if raw_len >= 10 and len(observation.summary) > raw_len * 5:
            flags.append(_make_red_flag(
                "RF-011",
                "observation.summary length exceeds raw_unit * 5 — probable interpretation encoded as observation",
            ))

    # ------------------------------------------------------------------
    # RF-012: hidden_context_injection
    # Spec triggers: external_assumption_used, inferred_scenario_used_as_fact,
    #   unprovided_background_fills_gap.
    # ------------------------------------------------------------------
    # Case A: cause=instruction_misalignment but interpretation is a committed claim
    if (
        cause_assignment.primary_cause == PrimaryCause.INSTRUCTION_MISALIGNMENT
        and not _selected_is_unknown
    ):
        flags.append(_make_red_flag(
            "RF-012",
            "cause=instruction_misalignment but interpretation.selected is committed — hidden context likely used",
        ))

    # Case B: root_context=under_specified_task_context + committed interpretation without weaker_interpretation
    if (
        RootContext.UNDER_SPECIFIED_TASK_CONTEXT in cause_assignment.root_context
        and not _selected_is_unknown
        and not interpretation.constraints.weaker_interpretation_applied
    ):
        if not any(rf.flag_id == "RF-012" for rf in flags):
            flags.append(_make_red_flag(
                "RF-012",
                "root_context=under_specified_task_context but interpretation.selected is committed without weaker_interpretation_applied",
            ))

    # Case C: selected interpretation length far exceeds raw_unit (fabricated content)
    if (
        not evidence  # defensive check; adapter rejection would normally catch this first
        or (
            observation.raw_unit
            and len(interpretation.selected) > len(observation.raw_unit) * 4
            and not _selected_is_unknown
        )
    ):
        if not any(rf.flag_id == "RF-012" for rf in flags):
            flags.append(_make_red_flag(
                "RF-012",
                "interpretation.selected length far exceeds raw_unit — probable hidden context injection",
            ))

    return flags


# ============================================================
# SECTION 8: JSI SIGNAL DERIVATION
# From 07_jsi_signals.yaml.
# Signals describe state. They do NOT prescribe actions.
# v0.2 (Task 1): each signal records its triggering condition in derived_from.
# ============================================================

def derive_jsi_signals(
    interpretation: Interpretation,
    uncertainty: Uncertainty,
    cause_assignment: CauseAssignment,
    evidence: list[Evidence],
) -> StabilitySignals:
    """
    Emit lightweight, non-authoritative JSI stability signals.

    Signals must not trigger decisions. Signals must not override evidence.
    Each signal's derivation reason is recorded in the returned StabilitySignals.derived_from.
    Kernel guarantees derived_from is never left empty.
    """
    # --- hesitation_present ---
    # True when: alternatives exist, weaker_interpretation was applied,
    # or confidence_score is below the 0.5 threshold.
    _hesitation_reasons: list[str] = []
    if len(interpretation.alternatives) > 0:
        _hesitation_reasons.append(f"alternatives={len(interpretation.alternatives)}")
    if interpretation.constraints.weaker_interpretation_applied:
        _hesitation_reasons.append("weaker_interpretation_applied=True")
    if uncertainty.confidence_score is not None and uncertainty.confidence_score < 0.5:
        _hesitation_reasons.append(f"confidence_score={uncertainty.confidence_score}<0.5")
    hesitation_present = bool(_hesitation_reasons)

    # --- conflict_detected ---
    # True when: evidence_bound=False (interpretation not anchored to evidence),
    # exactly_one_primary=False (causal structure broken), or
    # forced_resolution_avoided=False (alternatives were erased, not resolved).
    # NOTE: forced resolution erases alternatives, so hesitation cannot co-fire.
    # conflict_detected captures this distinct state (see ADR-001 D-07).
    _conflict_reasons: list[str] = []
    if not interpretation.constraints.evidence_bound:
        _conflict_reasons.append("evidence_bound=False")
    if not cause_assignment.validation.exactly_one_primary:
        _conflict_reasons.append("exactly_one_primary=False")
    if not interpretation.constraints.forced_resolution_avoided:
        _conflict_reasons.append("forced_resolution_avoided=False")
    conflict_detected = bool(_conflict_reasons)

    # --- doubt_persistence_present ---
    # True when: revisit_needed is flagged or unresolved elements remain.
    _doubt_reasons: list[str] = []
    if uncertainty.revisit_needed:
        _doubt_reasons.append("uncertainty.revisit_needed=True")
    if len(uncertainty.unresolved_elements) > 0:
        _doubt_reasons.append(f"unresolved_elements={len(uncertainty.unresolved_elements)}")
    doubt_persistence_present = bool(_doubt_reasons)

    # --- overlap_signal ---
    # True when secondary_factors are present, indicating competing causal contributors.
    _overlap_reason = (
        f"secondary_factors={len(cause_assignment.secondary_factors)}"
        if cause_assignment.secondary_factors
        else ""
    )
    overlap_signal = len(cause_assignment.secondary_factors) > 0

    # --- assignment_fragility ---
    # HIGH: no evidence at all, or exactly_one_primary constraint is broken.
    # MEDIUM: multiple alternative interpretations compete.
    # LOW: single interpretation, evidence present.
    if not evidence or not cause_assignment.validation.exactly_one_primary:
        assignment_fragility = FragilityLevel.HIGH
        _fragility_reason = "no evidence" if not evidence else "exactly_one_primary=False"
    elif len(interpretation.alternatives) > 1:
        assignment_fragility = FragilityLevel.MEDIUM
        _fragility_reason = f"alternatives={len(interpretation.alternatives)}"
    else:
        assignment_fragility = FragilityLevel.LOW
        _fragility_reason = "single interpretation, evidence present"

    # --- ambiguity_density ---
    # HIGH: >= 2 ambiguity/unresolved flags, or > 2 alternatives.
    # MEDIUM: any ambiguity flag or any alternatives present.
    # LOW: no ambiguity flags, no alternatives.
    ambiguity_flags = [
        f for f in uncertainty.flags
        if f.type in (UncertaintyType.AMBIGUITY, UncertaintyType.UNRESOLVED)
    ]
    if len(ambiguity_flags) >= 2 or len(interpretation.alternatives) > 2:
        ambiguity_density = FragilityLevel.HIGH
        _ambiguity_reason = (
            f"ambiguity_flags={len(ambiguity_flags)}, alternatives={len(interpretation.alternatives)}"
        )
    elif ambiguity_flags or len(interpretation.alternatives) > 0:
        ambiguity_density = FragilityLevel.MEDIUM
        _ambiguity_reason = (
            f"ambiguity_flags={len(ambiguity_flags)}, alternatives={len(interpretation.alternatives)}"
        )
    else:
        ambiguity_density = FragilityLevel.LOW
        _ambiguity_reason = "no ambiguity flags, no alternatives"

    # --- reconstruction_risk ---
    # HIGH: no evidence, or all evidence is LOW-strength.
    # MEDIUM: some evidence is LOW-strength.
    # LOW: no LOW-strength evidence present.
    low_evidence = [e for e in evidence if e.strength == EvidenceStrength.LOW]
    if not evidence or len(low_evidence) == len(evidence):
        reconstruction_risk = FragilityLevel.HIGH
        _reconstruction_reason = (
            "no evidence" if not evidence
            else f"all {len(low_evidence)} evidence entries are LOW"
        )
    elif low_evidence:
        reconstruction_risk = FragilityLevel.MEDIUM
        _reconstruction_reason = f"{len(low_evidence)}/{len(evidence)} evidence entries are LOW"
    else:
        reconstruction_risk = FragilityLevel.LOW
        _reconstruction_reason = "no LOW-strength evidence"

    # --- Assemble derived_from (v0.2 Task 1) ---
    derived_from = StabilitySignalDerivation(
        hesitation_present=(
            ", ".join(_hesitation_reasons) if _hesitation_reasons else "no triggering conditions"
        ),
        conflict_detected=(
            ", ".join(_conflict_reasons) if _conflict_reasons else "no triggering conditions"
        ),
        doubt_persistence_present=(
            ", ".join(_doubt_reasons) if _doubt_reasons else "no triggering conditions"
        ),
        overlap_signal=_overlap_reason if _overlap_reason else "no secondary factors",
        assignment_fragility=_fragility_reason,
        ambiguity_density=_ambiguity_reason,
        reconstruction_risk=_reconstruction_reason,
    )

    return StabilitySignals(
        hesitation_present=hesitation_present,
        conflict_detected=conflict_detected,
        doubt_persistence_present=doubt_persistence_present,
        overlap_signal=overlap_signal,
        assignment_fragility=assignment_fragility,
        ambiguity_density=ambiguity_density,
        reconstruction_risk=reconstruction_risk,
        derived_from=derived_from,
    )


# ============================================================
# SECTION 9: TRACEABILITY
# From 04_judgment_event_schema.yaml.
# v0.2 (Task 2): validate_traceability() is an invariant enforced in emit_judgment_event().
# ============================================================

def build_traceability(
    evidence: list[Evidence],
    interpretation: Interpretation,
    cause_assignment: CauseAssignment,
) -> Traceability:
    """
    Build the traceability chain for a judgment event.

    Links:
      evidence → interpretation: evidence exists and interpretation.selected is non-empty.
      interpretation → cause: interpretation.selected and primary_cause are both non-empty.
      all_traceable: both links hold.
    """
    evidence_to_interpretation = bool(evidence) and bool(interpretation.selected)
    interpretation_to_cause = bool(interpretation.selected) and bool(cause_assignment.primary_cause)
    all_traceable = evidence_to_interpretation and interpretation_to_cause
    return Traceability(
        evidence_to_interpretation_linked=evidence_to_interpretation,
        interpretation_to_cause_linked=interpretation_to_cause,
        all_fields_evidence_traceable=all_traceable,
    )


def validate_traceability(traceability: Traceability) -> None:
    """
    Traceability invariant enforcement. Added in v0.2 (Task 2 from ADR-001).

    Raises KernelConstraintViolation if any link in the traceability chain is broken.
    Called in emit_judgment_event() immediately after build_traceability().

    Invariant: a JudgmentEvent with broken traceability MUST NOT be emitted.
    This prevents downstream consumers from silently trusting untraceable events.

    Conditions that trigger a violation:
      - evidence_to_interpretation_linked=False: interpretation has no evidence anchor.
      - interpretation_to_cause_linked=False: cause assignment has no interpretation anchor.
      - all_fields_evidence_traceable=False: the full chain is broken.
    """
    failures: list[str] = []
    if not traceability.evidence_to_interpretation_linked:
        failures.append(
            "evidence_to_interpretation_linked=False: interpretation is not anchored to evidence"
        )
    if not traceability.interpretation_to_cause_linked:
        failures.append(
            "interpretation_to_cause_linked=False: cause assignment is not anchored to interpretation"
        )
    if not traceability.all_fields_evidence_traceable:
        failures.append(
            "all_fields_evidence_traceable=False: full traceability chain is broken"
        )
    if failures:
        raise KernelConstraintViolation(
            "Traceability invariant violated — event cannot be emitted: " + "; ".join(failures)
        )


# ============================================================
# SECTION 10: VALIDATION BLOCK
# From 04_judgment_event_schema.yaml.
# ============================================================

def build_validation(
    evidence: list[Evidence],
    interpretation: Interpretation,
    uncertainty: Uncertainty,
    cause_assignment: CauseAssignment,
    red_flags: list[RedFlag],
    decision_stub: DecisionStub | None = None,
) -> ValidationBlock:
    """
    Build the validation block for a judgment event.

    schema_valid: True if execution reached this point (structural check passed).
    evidence_present: evidence list is non-empty.
    interpretation_evidence_linked: both evidence and interpretation.selected are non-empty.
    uncertainty_if_needed_present: low-strength evidence requires uncertainty flags.
    primary_cause_valid: primary_cause is set and validation flags are True.
    boundary_respected: decision_stub does not contain forbidden authority tokens
                        and no RF-008 (causal invariant violation) is present.
    """
    schema_valid = True  # structural check passes if execution reached this point
    evidence_present = bool(evidence)
    interpretation_evidence_linked = bool(evidence) and bool(interpretation.selected)

    # uncertainty_if_needed_present: low-strength evidence requires at least one uncertainty flag
    low_strength = [e for e in evidence if e.strength == EvidenceStrength.LOW]
    uncertainty_if_needed_present = not low_strength or bool(uncertainty.flags)

    primary_cause_valid = (
        bool(cause_assignment.primary_cause)
        and cause_assignment.validation.exactly_one_primary
        and cause_assignment.validation.no_primary_duplication
    )

    # boundary_respected — W-06: structural compliance with execution boundary.
    # From 03_execution_boundary.md §7 (Boundary Violation Indicators):
    #   - assigning STOP / DEFER / ALLOW
    #   - producing conclusions not traceable to input
    #   - using JSI or RF to drive action
    #   - applying policy or business rules
    # boundary_respected = False when ANY of the following hold:
    #   (a) decision_stub.constraints.not_final_decision is False
    #   (b) decision_stub.constraints.no_policy_applied is False
    #   (c) decision_stub.label or .value contains a forbidden authority token
    #   (d) RF-008 (causal invariant violation) is present
    boundary_respected = True

    if decision_stub is not None:
        # (a) + (b): constraint flags
        if not decision_stub.constraints.not_final_decision:
            boundary_respected = False
        if not decision_stub.constraints.no_policy_applied:
            boundary_respected = False

        # (c): forbidden authority tokens in label or value
        if (
            decision_stub.label.upper() in _RF_FORBIDDEN_AUTHORITY_TOKENS
            or decision_stub.value.upper() in _RF_FORBIDDEN_AUTHORITY_TOKENS
        ):
            boundary_respected = False

    # (d): RF-008 indicates a kernel-internal causal invariant violation
    if any(rf.flag_id == "RF-008" for rf in red_flags):
        boundary_respected = False

    return ValidationBlock(
        schema_valid=schema_valid,
        evidence_present=evidence_present,
        interpretation_evidence_linked=interpretation_evidence_linked,
        uncertainty_if_needed_present=uncertainty_if_needed_present,
        primary_cause_valid=primary_cause_valid,
        boundary_respected=boundary_respected,
    )


# ============================================================
# SECTION 11: INTERNAL HELPERS
# Determinism and single-primary enforcement.
# ============================================================

def _enforce_single_primary(cause_assignment: CauseAssignment) -> None:
    """
    Enforce the exactly-one-primary-cause invariant.
    From 02_core_principles.yaml: one_event_one_primary_cause.
    From 06_assignment_logic.md §2.

    Raises KernelConstraintViolation if the constraint is violated.
    The validation flags reflect caller intent; Kernel enforces them here.
    """
    if not cause_assignment.primary_cause:
        raise KernelConstraintViolation(
            "primary_cause is required and must not be empty"
        )
    if not cause_assignment.validation.exactly_one_primary:
        raise KernelConstraintViolation(
            "cause_assignment.validation.exactly_one_primary must be True"
        )
    if not cause_assignment.validation.no_primary_duplication:
        raise KernelConstraintViolation(
            "cause_assignment.validation.no_primary_duplication must be True"
        )


def _deterministic_event_id(segment_id: str, adapter_input: AdapterInput) -> str:
    """
    Produce a deterministic event ID from segment_id and adapter_input fields.
    Same input always yields the same ID (from 01_kernel_charter.md §5).
    Format: EVT-<hex16>
    """
    raw = (
        f"{segment_id}|{adapter_input.observation_unit}"
        f"|{adapter_input.modality}|{adapter_input.task_type}"
    )
    return "EVT-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()


def _deterministic_timestamp(segment_id: str, adapter_input: AdapterInput) -> str:
    """
    Produce a deterministic timestamp-shaped token derived from input fields.
    NOT a real wall-clock time (from 01_kernel_charter.md §5: identical input → identical output).
    Format: DET-<hex16>  — prefix makes clear this is not a real timestamp.
    """
    raw = (
        f"ts|{segment_id}|{adapter_input.observation_unit}"
        f"|{adapter_input.modality}|{adapter_input.task_type}"
    )
    return "DET-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()


# ============================================================
# SECTION 12: KERNEL ENTRY POINT
# emit_judgment_event() is the single public entry point.
# ============================================================

def emit_judgment_event(
    adapter_input: AdapterInput,
    segment_id: str,
    observation: Observation,
    interpretation: Interpretation,
    uncertainty: Uncertainty,
    cause_assignment: CauseAssignment,
    decision_stub: DecisionStub,
) -> JudgmentEvent:
    """
    Emit a structured JudgmentEvent. This is the sole public entry point for the Kernel.

    Processing pipeline (in order):
      1. Validate adapter input — reject structurally invalid inputs immediately.
      2. Enforce single primary cause — raise if causal invariant is violated.
      3. Derive JSI stability signals — with full derived_from provenance (v0.2 Task 1).
      4. Detect red flags — local, structural, non-decisional.
      5. Build traceability chain.
      6. Validate traceability — raise if chain is broken (v0.2 Task 2 invariant).
      7. Build validation block.
      8. Assemble and return JudgmentEvent.

    This function does NOT:
      - make STOP / DEFER / ALLOW decisions
      - apply policy or governance logic
      - infer hidden context
      - perform temporal tracking
      - select repair operators

    Identical inputs produce identical outputs (deterministic).
    """

    # 1. Adapter input validation
    rejection_reasons = validate_adapter_input(adapter_input)
    if rejection_reasons:
        raise AdapterInputRejected(rejection_reasons)

    # 2. Enforce single primary cause (06_assignment_logic.md §2)
    _enforce_single_primary(cause_assignment)

    # 3. Evidence reference (from adapter)
    evidence = adapter_input.evidence_mapping

    # 4. Derive JSI signals (with derived_from provenance)
    stability_signals = derive_jsi_signals(
        interpretation=interpretation,
        uncertainty=uncertainty,
        cause_assignment=cause_assignment,
        evidence=evidence,
    )

    # 5. Detect red flags (local, non-decisional)
    red_flags = detect_red_flags(
        evidence=evidence,
        interpretation=interpretation,
        uncertainty=uncertainty,
        cause_assignment=cause_assignment,
        observation=observation,
    )

    # 6. Build traceability chain
    traceability = build_traceability(
        evidence=evidence,
        interpretation=interpretation,
        cause_assignment=cause_assignment,
    )

    # 7. Validate traceability invariant (v0.2 Task 2)
    # Must occur BEFORE event assembly. Broken traceability = event must not be emitted.
    validate_traceability(traceability)

    # 8. Build validation block
    validation = build_validation(
        evidence=evidence,
        interpretation=interpretation,
        uncertainty=uncertainty,
        cause_assignment=cause_assignment,
        red_flags=red_flags,
        decision_stub=decision_stub,
    )

    # 9. Assemble and return the event
    event = JudgmentEvent(
        event_id=_deterministic_event_id(segment_id, adapter_input),
        timestamp=_deterministic_timestamp(segment_id, adapter_input),
        segment_id=segment_id,
        task_type=adapter_input.task_type,
        modality=adapter_input.modality,
        version="v0.2",
        observation=observation,
        evidence=evidence,
        interpretation=interpretation,
        uncertainty=uncertainty,
        cause_assignment=cause_assignment,
        stability_signals=stability_signals,
        red_flags=red_flags,
        decision_stub=decision_stub,
        traceability=traceability,
        validation=validation,
    )

    # Kernel stops here.
    # Per 03_execution_boundary.md §6: once the event is emitted, Kernel MUST NOT continue.
    return event

