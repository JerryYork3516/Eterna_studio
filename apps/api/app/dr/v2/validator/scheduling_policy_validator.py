"""Scheduling policy validation — enum legality (schema-guaranteed) + internal
consistency. Pure data checks; no scheduler is created or run.

The consistency rule table lives in `scheduling_consistency_findings` and is
reused by the compile-layer Scheduling Validity Gate to avoid drift.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..dr_v0_2_schema import (
    DigitalResidentV02Gate,
    InterruptPolicy,
    PreemptionPolicy,
    PriorityModel,
    SchedulingMode,
)
from .dr_validation_result import DRValidationResult, finding


def scheduling_consistency_findings(model: DigitalResidentV02Gate) -> List[Dict[str, Any]]:
    """Return cross-field scheduling-policy findings (no side effects)."""
    sp = model.scheduling_policy
    out: List[Dict[str, Any]] = []

    if sp.mode == SchedulingMode.serial and sp.preemption != PreemptionPolicy.disabled:
        out.append(
            finding("FAIL", "DR_SCHED_SERIAL_PREEMPTION", "serial mode cannot use preemption", "scheduling_policy.preemption")
        )
    if sp.mode == SchedulingMode.serial and sp.interrupt_policy == InterruptPolicy.immediate:
        out.append(
            finding("FAIL", "DR_SCHED_SERIAL_INTERRUPT", "serial mode cannot use immediate interrupt", "scheduling_policy.interrupt_policy")
        )
    if sp.mode == SchedulingMode.adaptive and sp.priority_model == PriorityModel.fifo:
        out.append(
            finding("FAIL", "DR_SCHED_ADAPTIVE_PRIORITY", "adaptive mode needs a ranking priority_model (not fifo)", "scheduling_policy.priority_model")
        )
    if sp.preemption == PreemptionPolicy.priority_based and sp.priority_model == PriorityModel.fifo:
        out.append(
            finding("FAIL", "DR_SCHED_PREEMPTION_NO_PRIORITY", "priority_based preemption needs a priority_model (not fifo)", "scheduling_policy.priority_model")
        )
    if sp.interrupt_policy == InterruptPolicy.immediate and sp.preemption == PreemptionPolicy.disabled:
        out.append(
            finding("WARNING", "DR_SCHED_INTERRUPT_NO_PREEMPTION", "immediate interrupt usually needs preemption", "scheduling_policy.preemption")
        )
    if sp.mode == SchedulingMode.serial and sp.max_parallel_hint > 1:
        out.append(
            finding("WARNING", "DR_SCHED_SERIAL_PARALLEL", "serial mode ignores max_parallel_hint > 1", "scheduling_policy.max_parallel_hint")
        )
    if sp.mode == SchedulingMode.semi_parallel and sp.max_parallel_hint < 2:
        out.append(
            finding("WARNING", "DR_SCHED_SEMIPARALLEL_HINT", "semi_parallel mode usually sets max_parallel_hint >= 2", "scheduling_policy.max_parallel_hint")
        )
    return out


def validate_scheduling(model: DigitalResidentV02Gate, result: DRValidationResult) -> None:
    result.add_all(scheduling_consistency_findings(model))
