"""Hindsight wrapper layer — Phase 2 build wave 2 item 1.

Canonical key citations (per audit-dispatch checklist):

ceo:memory_abstraction_layer_v1 — eleven_agreed_positions #3:
    "Six query primitives: Ingest, Recall, Synthesize, Supersede, Trace, Delete"

ceo:memory_abstraction_layer_v1 — substantive_lock item 4:
    "V1 primitives as thin domain wrappers around Hindsight TEMPR + Opinion/Reflect
     pathway (CARA citation removed pending Viktor confirmation; bd Agency_OS-wlfd
     assigned to Aiden for Viktor-relay)"

ceo:memory_abstraction_layer_v1 — phase_2_1_spike_verdict.items.vi_domain_mapping:
    "FAVOURABLE — 3 of 4 direct (Decision→World, Artifact→Experience,
     TaskContext→Observation); AntiPattern→Opinion needs ~50-100 LoC wrapper.
     Atlas PR #1129."

Exports:
- DecisionWrapper       — Decision → Hindsight World
- ArtifactWrapper       — Artifact → Hindsight Experience
- TaskContextWrapper    — TaskContext → Hindsight Observation
- AntiPatternWrapper    — AntiPattern → Hindsight Opinion (with supersession edge)
- compose_audit_record  — Trace primitive composition (Aiden gate D)
- AuditRecord           — structured audit-trail dataclass
"""

from .antipattern_wrapper import AntiPatternWrapper
from .artifact_wrapper import ArtifactWrapper
from .decision_wrapper import DecisionWrapper
from .taskcontext_wrapper import TaskContextWrapper
from .trace_composition import AuditRecord, compose_audit_record

__all__ = [
    "AntiPatternWrapper",
    "ArtifactWrapper",
    "AuditRecord",
    "DecisionWrapper",
    "TaskContextWrapper",
    "compose_audit_record",
]
