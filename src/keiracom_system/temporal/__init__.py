"""keiracom_system.temporal — Temporal workflow engine integration.

Phase A6 build per bd Agency_OS-(A6).
"""

from .audit_activity import build_audit_event, emit_audit_event
from .client import (
    DEFAULT_NAMESPACE,
    DEFAULT_TASK_QUEUE,
    TemporalConnectError,
    connect,
    from_env,
)
from .fleet_supervisor_workflow import (
    FLEET_SUPERVISOR_WORKFLOW_ID,
    AgentStateUpdate,
    _infer_agent_type,
)
from .signal_helpers import signal_fleet_supervisor, signal_fleet_supervisor_sync
from .v1_chain_workflow import (
    CHAIN_WORKFLOW_ID_PREFIX,
    V1_CHAIN_TASK_QUEUE,
    ChainStepInput,
    ChainStepOutput,
    ChainWorkflowInput,
    V1ChainWorkflow,
)

__all__ = [
    "AgentStateUpdate",
    "CHAIN_WORKFLOW_ID_PREFIX",
    "ChainStepInput",
    "ChainStepOutput",
    "ChainWorkflowInput",
    "DEFAULT_NAMESPACE",
    "DEFAULT_TASK_QUEUE",
    "FLEET_SUPERVISOR_WORKFLOW_ID",
    "TemporalConnectError",
    "V1_CHAIN_TASK_QUEUE",
    "V1ChainWorkflow",
    "_infer_agent_type",
    "build_audit_event",
    "connect",
    "emit_audit_event",
    "from_env",
    "signal_fleet_supervisor",
    "signal_fleet_supervisor_sync",
]
