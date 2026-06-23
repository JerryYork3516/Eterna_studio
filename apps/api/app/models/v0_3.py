"""Schema Contract v0.3 DTOs.

This module is intentionally contract-only: no LLM, TTS, AR runtime, database,
workflow execution, or object references that could create circular graphs.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION_V0_3 = "0.3.0"


class V03BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NodeStatus(str, Enum):
    ready = "READY"
    mock = "MOCK"
    disabled = "DISABLED"


class AuditStatus(str, Enum):
    pass_ = "PASS"
    warning = "WARNING"
    fail = "FAIL"


class AuditLevel(str, Enum):
    node = "node"
    module = "module"
    layer = "layer"
    resident = "resident"


class NodeInputType(str, Enum):
    text = "text"
    textarea = "textarea"
    number = "number"
    select = "select"
    multi_select = "multi_select"
    slider = "slider"
    boolean = "boolean"
    color = "color"
    json = "json"
    tags = "tags"
    key_value = "key_value"
    file = "file"


class AuditFinding(V03BaseModel):
    status: AuditStatus
    level: AuditLevel
    code: str
    message: str
    path: str


class AuditReportV03(V03BaseModel):
    schema_version: Literal["0.3.0"] = SCHEMA_VERSION_V0_3
    status: AuditStatus = AuditStatus.pass_
    findings: List[AuditFinding] = Field(default_factory=list)


class NodeInputOption(V03BaseModel):
    value: str
    label: str


class NodeInputField(V03BaseModel):
    key: str
    type: NodeInputType
    label: str
    required: bool = False
    default: Optional[Any] = None
    placeholder: Optional[str] = None
    options: List[NodeInputOption] = Field(default_factory=list)
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    accept: Optional[List[str]] = None
    multiple: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OutputSchemaField(V03BaseModel):
    key: str
    type: Literal["string", "number", "boolean", "object", "array", "null"]
    required: bool = False
    description: Optional[str] = None


class NodeUiState(V03BaseModel):
    collapsed: bool = False
    position: Dict[str, float] = Field(default_factory=dict)
    size: Dict[str, float] = Field(default_factory=dict)
    color: Optional[str] = None
    selected: bool = False


class WorkflowMetadataV03(V03BaseModel):
    description: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    ui_language: Optional[Literal["zh", "en"]] = None
    mock: bool = True


class NodeV03(V03BaseModel):
    id: str
    type: str
    label: str
    category: str
    status: NodeStatus
    input_schema: List[NodeInputField] = Field(default_factory=list)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    output_schema: List[OutputSchemaField] = Field(default_factory=list)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    ui: NodeUiState = Field(default_factory=NodeUiState)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EdgeV03(V03BaseModel):
    id: str
    source_node_id: str
    source_output: str
    target_node_id: str
    target_input: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModuleV03(V03BaseModel):
    id: str
    name: str
    layer_id: Optional[str] = None
    node_ids: List[str] = Field(default_factory=list)
    output_schema: List[OutputSchemaField] = Field(default_factory=list)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LayerV03(V03BaseModel):
    id: str
    name: str
    module_ids: List[str] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)
    output_schema: List[OutputSchemaField] = Field(default_factory=list)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowV03(V03BaseModel):
    id: str
    name: str
    schema_version: Literal["0.3.0"] = SCHEMA_VERSION_V0_3
    layers: List[LayerV03] = Field(default_factory=list)
    modules: List[ModuleV03] = Field(default_factory=list)
    nodes: List[NodeV03] = Field(default_factory=list)
    edges: List[EdgeV03] = Field(default_factory=list)
    metadata: WorkflowMetadataV03 = Field(default_factory=WorkflowMetadataV03)


class ResidentIdentity(V03BaseModel):
    name: str = ""
    role: str = "digital_resident"
    description: Optional[str] = None
    disclosure: str = "AI-generated digital resident; synthetic persona."


class ResidentPersonality(V03BaseModel):
    traits: List[str] = Field(default_factory=list)
    speaking_style: str = ""
    boundaries: List[str] = Field(default_factory=list)


class ResidentDialogue(V03BaseModel):
    tone: str = "warm"
    formality: str = "casual"
    sample: str = ""


class ResidentVoiceProfile(V03BaseModel):
    voice_id: str = "mock_voice"
    pitch: str = "medium"
    speed: float = 1.0
    timbre: str = "neutral"
    mock: bool = True


class ResidentAvatar(V03BaseModel):
    preset: str = "mock_avatar"
    color: str = "#7aa2f7"
    density: float = 0.6
    motion: str = "idle"
    mock: bool = True


class ResidentMetadata(V03BaseModel):
    schema_version: Literal["0.3.0"] = SCHEMA_VERSION_V0_3
    mock: bool = True
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ResidentInstanceV03(V03BaseModel):
    identity: ResidentIdentity = Field(default_factory=ResidentIdentity)
    personality: ResidentPersonality = Field(default_factory=ResidentPersonality)
    dialogue: ResidentDialogue = Field(default_factory=ResidentDialogue)
    voice_profile: ResidentVoiceProfile = Field(default_factory=ResidentVoiceProfile)
    avatar: ResidentAvatar = Field(default_factory=ResidentAvatar)
    metadata: ResidentMetadata = Field(default_factory=ResidentMetadata)


class UiStateV03(V03BaseModel):
    """Frontend-only state. It must never be embedded in output DTOs."""

    selected_node_id: Optional[str] = None
    viewport: Dict[str, float] = Field(default_factory=dict)
    panels: Dict[str, Any] = Field(default_factory=dict)


class RuntimeContextV03(V03BaseModel):
    """Execution-only context. Contract type only; no endpoint executes it."""

    run_id: str
    workflow_id: Optional[str] = None
    current_node_id: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)


class OutputDtoV03(V03BaseModel):
    """Final JSON output DTO. No UI state or runtime context is allowed here."""

    schema_version: Literal["0.3.0"] = SCHEMA_VERSION_V0_3
    kind: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowValidationResponseV03(V03BaseModel):
    schema_version: Literal["0.3.0"] = SCHEMA_VERSION_V0_3
    valid: bool
    audit: AuditReportV03


class ResidentCompileRequestV03(V03BaseModel):
    workflow: Optional[Any] = None
    resident_instance: Optional[ResidentInstanceV03] = None
    ui_state: Optional[UiStateV03] = None
    runtime_context: Optional[RuntimeContextV03] = None


class ResidentCompileResponseV03(V03BaseModel):
    schema_version: Literal["0.3.0"] = SCHEMA_VERSION_V0_3
    resident_instance: ResidentInstanceV03
    audit: AuditReportV03


class ResidentPreviewRequestV03(V03BaseModel):
    resident_instance: ResidentInstanceV03
    ui_state: Optional[UiStateV03] = None


class ResidentPreviewResponseV03(V03BaseModel):
    schema_version: Literal["0.3.0"] = SCHEMA_VERSION_V0_3
    preview: OutputDtoV03
    audit: AuditReportV03


class NodeRegistryEntry(V03BaseModel):
    type: str
    category: str
    display_name: str
    description: str
    input_schema: List[NodeInputField] = Field(default_factory=list)
    output_schema: List[OutputSchemaField] = Field(default_factory=list)
    status: NodeStatus
    mock_executor: Optional[str] = None
    audit_rules: List[str] = Field(default_factory=list)
