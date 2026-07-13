"""Resident Runtime — Stage 6 minimal "running digital resident" (v1, mock).

Execution boundary (do not violate):
  * Node / Module / Slot are protocol descriptors only — they never execute.
  * The Execution Engine (execution_engine.py) is the only runtime entry; this
    loop is reached only through it.
  * Providers are mock-only and reached via provider_adapters.route_provider.

Holds in-process resident state and runs one fixed loop per step:
  input -> memory.read -> reasoning -> action -> memory.write -> output

Stage 6.1 adds observability around this loop without changing it: a
TraceCollector records one structured step per phase, a RuntimeStateManager
tracks run_id / turn_count / status (running -> completed), and the
runtime memory gate emits a memory snapshot at the end of each run.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from ..models.v0_4 import LatticeEmotion, LatticeMotion, LatticeStateV04, LatticeVoiceState

from ..dr.v2.validator import validate_dr_v0_2
from ..dr.v2.validator.capability_validator import validate_v03_runtime_contract

from .provider_adapters import route_provider_for_engine
from .runtime_llm_config import get_runtime_llm_profile
from .runtime_state_manager import RuntimeStateManager, reset_history
from .runtime_trace_collector import TraceCollector


@dataclass
class ResidentRuntimeState:
    """Minimal running state of a digital resident (process-local, mock)."""

    resident_id: str
    memory: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "idle"
    last_input: str = ""
    last_reasoning: str = ""
    last_action: Dict[str, Any] = field(default_factory=dict)
    last_output: str = ""
    turn_count: int = 0
    dr_version: str = ""
    identity: Dict[str, Any] = field(default_factory=dict)
    resident_identity: Dict[str, Any] = field(default_factory=dict)
    safety_policy: Dict[str, Any] = field(default_factory=dict)
    behavior_policy: Dict[str, Any] = field(default_factory=dict)
    capability_profile: Dict[str, Any] = field(default_factory=dict)
    memory_policy: Dict[str, Any] = field(default_factory=dict)
    session_id: str = field(default_factory=lambda: uuid4().hex)
    session_memory: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    session_memory_fingerprints: Set[str] = field(default_factory=set)
    runtime_status: str = "idle"
    provider_bindings: Dict[str, str] = field(
        default_factory=lambda: {
            "llm": "llm_mock:provider_llm_mock",
            "memory": "memory_mock:provider_memory_mock",
            "tool": "tool_mock:provider_tool_mock",
        }
    )


_STATES: Dict[str, ResidentRuntimeState] = {}

_state_manager = RuntimeStateManager()
RUNTIME_API_VERSION = "6.11.0"


def _error_envelope(code: str, message: str, *, stage: Optional[str] = None, retryable: bool = False) -> Dict[str, Any]:
    error: Dict[str, Any] = {"code": code, "message": message, "retryable": retryable}
    if stage is not None:
        error["stage"] = stage
    return error


def _diagnostics(*, resident_id: str, run_id: Optional[str], stage: Optional[str] = None, trace: Optional[List[Dict[str, Any]]] = None, memory_snapshot: Optional[Dict[str, Any]] = None, status: Optional[str] = None, fallback_mock: bool = False, reasoning_error: bool = False, memory_grounding: str = "none", memory_unavailable: bool = False, risk_decision: str = "allow", risk_category: str = "none") -> Dict[str, Any]:
    return {
        "resident_id": resident_id,
        "run_id": run_id,
        "stage": stage,
        "status": status,
        "trace_count": len(trace or []),
        "memory_count": int((memory_snapshot or {}).get("count", 0)),
        "fallback_mock": fallback_mock,
        "reasoning_error": reasoning_error,
        "memory_grounding": memory_grounding,
        "memory_unavailable": memory_unavailable,
        "risk_decision": risk_decision,
        "risk_category": risk_category,
    }


def get_or_create_state(resident_id: str) -> ResidentRuntimeState:
    state = _STATES.get(resident_id)
    if state is None:
        state = ResidentRuntimeState(resident_id=resident_id)
        _STATES[resident_id] = state
    return state


def _dr_identity(dr: Dict[str, Any]) -> Dict[str, Any]:
    identity = dict(dr.get("identity") or {})
    if identity:
        return identity
    payload = dr.get("payload") if isinstance(dr.get("payload"), dict) else {}
    payload_identity = payload.get("resident_identity") if isinstance(payload.get("resident_identity"), dict) else {}
    if payload_identity:
        return {
            "resident_id": payload_identity.get("resident_id") or "resident_v1",
            "name": payload_identity.get("name") or payload_identity.get("resident_name") or "",
            "role": payload_identity.get("resident_type") or "digital_resident",
            "description": payload_identity.get("personality_summary") or None,
            "disclosure": "AI-generated digital resident; synthetic persona.",
        }
    resident_instance = dr.get("resident_instance") if isinstance(dr.get("resident_instance"), dict) else {}
    if resident_instance:
        return {
            "resident_id": resident_instance.get("resident_id") or "resident_v1",
            "name": resident_instance.get("identity", {}).get("name") or "",
            "role": resident_instance.get("identity", {}).get("role") or "digital_resident",
            "description": resident_instance.get("identity", {}).get("description"),
            "disclosure": resident_instance.get("identity", {}).get("disclosure", "AI-generated digital resident; synthetic persona."),
        }
    return {}


def create_runtime_state_from_dr(dr: Dict[str, Any]) -> ResidentRuntimeState:
    """Create or refresh the process-local runtime state from a valid DR doc.

    This only binds the existing deterministic mock providers. It does not create
    real provider clients, schedulers, secure loaders, or orchestration runners.
    """
    identity = _dr_identity(dr)
    resident_id = identity.get("resident_id") or "resident_v1"
    state = get_or_create_state(resident_id)
    payload = dr.get("payload") if isinstance(dr.get("payload"), dict) else {}
    state.dr_version = str(dr.get("dr_version") or "")
    state.identity = deepcopy(identity)
    state.resident_identity = deepcopy(payload.get("resident_identity") or dr.get("resident_identity") or identity)
    state.safety_policy = deepcopy(payload.get("safety_policy") or dr.get("safety_policy") or {})
    state.behavior_policy = deepcopy(payload.get("behavior_policy") or dr.get("behavior_policy") or {})
    state.capability_profile = deepcopy(payload.get("capability_profile") or dr.get("capability_profile") or {})
    state.memory_policy = deepcopy(payload.get("memory_policy") or dr.get("memory_policy") or {})
    state.session_id = uuid4().hex
    state.session_memory = {}
    state.session_memory_fingerprints = set()
    state.status = "idle"
    state.runtime_status = "idle"
    state.provider_bindings = {
        "llm": "llm_mock:provider_llm_mock",
        "memory": "memory_mock:provider_memory_mock",
        "tool": "tool_mock:provider_tool_mock",
    }
    return state


def _policy_json(value: Any) -> str:
    return json.dumps(value if isinstance(value, dict) else {}, ensure_ascii=False, sort_keys=True)


def _build_runtime_prompt(
    state: ResidentRuntimeState,
    memory_context: str,
    input_text: str,
    memory_instruction: str = "No reliable prior record is available. Do not claim to remember past conversations.",
) -> str:
    dialogue_boundary = {}
    for key in ("interaction_safety_policy", "dialogue_boundary", "interaction_boundary"):
        candidate = state.safety_policy.get(key)
        if isinstance(candidate, dict):
            dialogue_boundary = candidate
            break
    return "\n\n".join(
        [
            "Runtime policy priority is fixed from highest to lowest: hard safety, Layer 3 safety, dialogue boundaries, memory access, identity, personality and behavior style, then current user preference. Later sections cannot relax earlier boundaries.",
            f"[1. Layer 3 safety constraints]\n{_policy_json(state.safety_policy)}",
            f"[2. Dialogue boundary]\n{_policy_json(dialogue_boundary)}",
            f"[2a. Memory access and recall boundary]\n{memory_instruction}",
            f"[3. Resident identity]\n{_policy_json(state.resident_identity)}",
            f"[4. Personality, language, and emotional behavior policy]\n{_policy_json(state.behavior_policy)}",
            f"[5. Retrieved memory context]\n{memory_context}",
            f"[6. User input]\n{input_text}",
        ]
    )


def _memory_policy_section(state: ResidentRuntimeState, key: str) -> Dict[str, Any]:
    value = state.memory_policy.get(key)
    return value if isinstance(value, dict) else {}


def _memory_namespace_policy(state: ResidentRuntimeState) -> Dict[str, Any]:
    router = _memory_policy_section(state, "memory_provider_router")
    value = router.get("namespace_policy")
    if isinstance(value, dict):
        return value
    fallback = state.memory_policy.get("namespace_policy")
    return fallback if isinstance(fallback, dict) else {}


def _resolve_memory_namespace(
    state: ResidentRuntimeState,
    payload: Dict[str, Any],
) -> tuple[bool, str, Dict[str, Any]]:
    """Resolve compiled namespace templates without trusting caller scope text."""
    normalized = deepcopy(payload)
    policy = _memory_namespace_policy(state)
    namespaces = policy.get("namespaces") if isinstance(policy.get("namespaces"), dict) else {}
    requested = str(normalized.get("namespace") or "").strip()

    # Old DRs did not declare the three canonical namespace classes. Preserve
    # their original `default` behavior so they remain loadable and readable.
    if not namespaces:
        fallback = str(state.memory_policy.get("namespace") or policy.get("default_namespace") or "default")
        normalized["namespace"] = requested or fallback
        return True, "legacy_namespace_policy", normalized

    memory_type = str(normalized.get("memory_type") or "")
    namespace_kind = ""
    for kind, raw_spec in namespaces.items():
        spec = raw_spec if isinstance(raw_spec, dict) else {}
        if memory_type and memory_type in set(spec.get("default_memory_types") or []):
            namespace_kind = str(kind)
            break

    explicit_kind = ""
    if requested and ":" in requested:
        explicit_kind = requested.split(":", 1)[0]
    if not memory_type and explicit_kind in namespaces:
        explicit_spec = namespaces.get(explicit_kind) if isinstance(namespaces.get(explicit_kind), dict) else {}
        default_types = [
            value
            for value in explicit_spec.get("default_memory_types", [])
            if isinstance(value, str) and value
        ]
        if len(default_types) == 1:
            memory_type = default_types[0]
            normalized["memory_type"] = memory_type
    if not namespace_kind and not memory_type and explicit_kind in namespaces:
        namespace_kind = explicit_kind
    if not namespace_kind and memory_type:
        for kind, raw_spec in namespaces.items():
            spec = raw_spec if isinstance(raw_spec, dict) else {}
            if memory_type in set(spec.get("default_memory_types") or []):
                namespace_kind = str(kind)
                break
    if not namespace_kind:
        namespace_kind = "private_memory"

    spec = namespaces.get(namespace_kind) if isinstance(namespaces.get(namespace_kind), dict) else {}
    template = str(spec.get("namespace_template") or "")
    if not template:
        return False, "memory_namespace_policy_invalid", normalized
    expected = template.replace("{resident_id}", state.resident_id).replace("{session_id}", state.session_id)

    if requested in {"", "default", "memory_type_default", template}:
        normalized["namespace"] = expected
        return True, "memory_type_default_namespace", normalized

    if ":" not in requested:
        return False, "unsupported_memory_namespace", normalized
    requested_kind, requested_scope = requested.split(":", 1)
    if requested_kind not in namespaces or not requested_scope:
        return False, "unsupported_memory_namespace", normalized
    if requested_kind == "private_memory" and requested_scope != state.resident_id:
        return False, "cross_resident_private_memory_forbidden", normalized
    if requested_kind in {"shared_session_context", "public_transcript"} and requested_scope != state.session_id:
        return False, "cross_session_memory_forbidden", normalized
    if requested_kind != namespace_kind:
        return False, "memory_type_namespace_mismatch", normalized
    if requested != expected:
        return False, "memory_namespace_scope_mismatch", normalized
    normalized["namespace"] = expected
    return True, "compiled_namespace_policy", normalized


def _default_memory_namespace(state: ResidentRuntimeState, memory_type: str) -> str:
    allowed, _reason, normalized = _resolve_memory_namespace(
        state,
        {"memory_type": memory_type},
    )
    if allowed:
        return str(normalized.get("namespace") or "default")
    return str(state.memory_policy.get("namespace") or "default")


def _memory_entry_fingerprint(entry: Dict[str, Any]) -> str:
    return json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _recall_claim_policy(state: ResidentRuntimeState) -> Dict[str, Any]:
    access = _memory_policy_section(state, "memory_access_control")
    value = access.get("recall_claim_policy")
    return value if isinstance(value, dict) else {}


def _memory_entry_is_unreliable(state: ResidentRuntimeState, entry: Dict[str, Any]) -> bool:
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    sources = {
        str(value).lower()
        for value in (entry.get("source"), metadata.get("source"))
        if value not in (None, "")
    }
    record_states = {
        str(value).lower()
        for value in (
            entry.get("status"),
            entry.get("state"),
            metadata.get("status"),
            metadata.get("state"),
        )
        if value not in (None, "")
    }
    policy = _recall_claim_policy(state)
    rejected_states = {"uncertain", "inferred", "expired", "invalid", "revoked"}
    rejected_states.update(
        str(value).lower()
        for value in policy.get("rejected_record_states", [])
        if isinstance(value, str) and value
    )
    if entry.get("valid") is False or metadata.get("valid") is False:
        return True
    if bool(entry.get("uncertain") or metadata.get("uncertain")):
        return True
    if bool(entry.get("inferred") or metadata.get("inferred")):
        return True
    if bool(entry.get("expired") or metadata.get("expired")):
        return True
    if sources.intersection({"inferred", "inferred_fact", "model_inference"}):
        return True
    if record_states.intersection(rejected_states):
        return True
    expires_at_values = [entry.get("expires_at"), metadata.get("expires_at")]
    for expires_at in expires_at_values:
        if not isinstance(expires_at, str) or not expires_at.strip():
            continue
        try:
            parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed <= datetime.now(timezone.utc):
                return True
        except ValueError:
            return True
    return False


def _memory_entry_scope_matches(
    state: ResidentRuntimeState,
    read: Dict[str, Any],
    entry: Dict[str, Any],
    namespace: str,
) -> bool:
    entry_resident_id = entry.get("resident_id")
    entry_namespace = entry.get("namespace") or entry.get("memory_namespace")
    if entry_resident_id not in (None, "", state.resident_id):
        return False
    if entry_namespace not in (None, "", namespace):
        return False
    expected_user = read.get("user_id")
    actual_user = entry.get("user_id")
    if expected_user not in (None, "") and actual_user != expected_user:
        return False
    if actual_user not in (None, "") and expected_user in (None, ""):
        return False
    expected_session = read.get("session_id")
    actual_session = entry.get("session_id")
    if expected_session not in (None, "") or actual_session not in (None, ""):
        return expected_session == actual_session == state.session_id
    if _memory_entry_fingerprint(entry) in state.session_memory_fingerprints:
        return True
    return False


def _sanitized_memory_entry(entry: Dict[str, Any]) -> Dict[str, str]:
    sanitized: Dict[str, str] = {}
    user_text = entry.get("input") or entry.get("user_text") or entry.get("event_summary") or entry.get("summary")
    resident_text = entry.get("reply") or entry.get("output")
    if isinstance(user_text, str) and user_text.strip():
        sanitized["user"] = user_text.strip()
    if isinstance(resident_text, str) and resident_text.strip():
        sanitized["resident"] = resident_text.strip()
    return sanitized


def _classify_memory_read(
    state: ResidentRuntimeState,
    read: Dict[str, Any],
    namespace: str,
) -> Dict[str, Any]:
    if read.get("status") != "success":
        return {
            "status": "unavailable",
            "entries": [],
            "trace_entries": [],
            "memory_unavailable": True,
            "instruction": "Past records cannot be checked right now. Continue the current conversation, but do not claim to remember prior events; if relevant, say naturally that you cannot confirm them.",
        }
    recall_policy = _recall_claim_policy(state)
    required_evidence = set(recall_policy.get("required_evidence") or [])
    verified_evidence_floor = {
        "successful_read",
        "nonempty_record",
        "current_resident_namespace",
        "current_user_scope",
        "current_runtime_session",
    }
    if recall_policy and (
        recall_policy.get("claim_rule") != "verified_read_only"
        or not verified_evidence_floor.issubset(required_evidence)
    ):
        return {
            "status": "uncertain",
            "entries": [],
            "trace_entries": [],
            "memory_unavailable": False,
            "instruction": "The recall policy cannot verify this record. Do not present it as remembered fact; ask for confirmation naturally and briefly.",
        }
    if read.get("resident_id") != state.resident_id or read.get("namespace") != namespace:
        return {
            "status": "uncertain",
            "entries": [],
            "trace_entries": [],
            "memory_unavailable": False,
            "instruction": "The available past context cannot be verified for this conversation. Do not present it as remembered fact; ask for confirmation naturally and briefly.",
        }
    raw_entries = read.get("entries") if isinstance(read.get("entries"), list) else []
    if not raw_entries:
        return {
            "status": "none",
            "entries": [],
            "trace_entries": [],
            "memory_unavailable": False,
            "instruction": "No reliable prior record is available. Do not claim to remember past conversations or fill in past events; rely only on the current conversation.",
        }
    verified_entries: List[Dict[str, Any]] = []
    sanitized_entries: List[Dict[str, str]] = []
    for item in raw_entries:
        if not isinstance(item, dict) or _memory_entry_is_unreliable(state, item):
            continue
        if not _memory_entry_scope_matches(state, read, item, namespace):
            continue
        sanitized = _sanitized_memory_entry(item)
        if not sanitized:
            continue
        verified_entries.append(item)
        sanitized_entries.append(sanitized)
    if verified_entries:
        return {
            "status": "verified",
            "entries": verified_entries,
            "trace_entries": sanitized_entries,
            "memory_unavailable": False,
            "instruction": "A verified record from this conversation is available. You may say you remember only details present in the retrieved context; do not add or infer missing details.",
        }
    return {
        "status": "uncertain",
        "entries": [],
        "trace_entries": [],
        "memory_unavailable": False,
        "instruction": "The available past context is uncertain or cannot be matched to this conversation. Do not state it as remembered fact; ask the user to confirm it naturally.",
    }


_RECALL_CLAIM_PATTERNS = (
    re.compile(r"(?<![不没])记得你(?:上次|上回|以前|之前|曾经|的)"),
    re.compile(r"你(?:上次|上回|以前|之前|曾经)(?:跟我|对我)?(?:说过|告诉过我|提过)"),
    re.compile(r"(?:上次|上回|以前|之前)你(?:跟我|对我)?(?:说过|告诉过我|提过)"),
    re.compile(r"你(?:之前|上次|上回|以前|曾经)?(?:跟我|对我)?提过(?:自己)?"),
    re.compile(r"我们之前(?:聊|谈|说|讨论)过"),
    re.compile(r"(?:之前|以前|上次)我们(?:聊|谈|说|讨论)过"),
    re.compile(r"我印象中你"),
    re.compile(r"\byou\s+(?:previously|once)\s+(?:said|told me)\b", re.IGNORECASE),
    re.compile(r"\b(?:last time you|you told me before|as you said (?:before|earlier))\b", re.IGNORECASE),
    re.compile(r"\byou (?:mentioned before|told me last time)\b", re.IGNORECASE),
    re.compile(r"\b(?:we|you and i).{0,48}(?:discussed|talked|spoke).{0,24}before\b", re.IGNORECASE),
    re.compile(r"\b(?:previously|earlier),?\s+(?:we|you and i).{0,48}(?:discussed|talked|spoke)\b", re.IGNORECASE),
)

_FIRST_PERSON_RECALL_PATTERNS = (
    re.compile(r"记着呢"),
    re.compile(r"(?:我(?:依稀|模糊地?|还|仍然|一直|确实|清楚地?)?|当然|确实|还|仍然)(?:记得|记着)"),
    re.compile(r"(?:我)?(?:没有|没|从没)忘(?:记)?"),
    re.compile(r"我(?:还|仍然|依稀|模糊地?)?有印象"),
    re.compile(r"\bi\s+(?:still\s+)?(?:remember|recall)\b", re.IGNORECASE),
    re.compile(r"\bi (?:haven't|have not|never) forgotten\b", re.IGNORECASE),
)

_RECALL_QUERY_PATTERNS = (
    re.compile(r"(?:还)?记得|记着|忘(?:记)?|有印象"),
    re.compile(r"\b(?:remember|recall|forgot|forgotten)\b", re.IGNORECASE),
)
_RECALL_SHORT_ANSWER_PATTERN = re.compile(
    r"^\s*(?:(?:是的[，,\s]*)?(?:记得|当然|当然记得)|yes[，,\s]+i do|absolutely|of course(?: i do)?)\s*[。.!！]?\s*$",
    re.IGNORECASE,
)


_RECALL_DETAIL_PREFIXES = (
    re.compile(r"你(?:还)?记得(?:我)?"),
    re.compile(r"(?:是的[，,\s]*)?(?:当然|确实)?[，,\s]*(?:我(?:还|仍然|确实|清楚地?)?|还|仍然)?记得(?:你)?"),
    re.compile(r"我(?:依稀|模糊地?|还|仍然|一直|清楚地?)?(?:记得|记着|有印象)(?:你)?"),
    re.compile(r"(?:我(?:还|仍然)?|还|仍然)?记着(?:呢)?(?:你)?"),
    re.compile(r"(?:我)?(?:没有|没|从没)忘(?:记)?(?:你)?"),
    re.compile(r"你(?:上次|上回|以前|之前|曾经)(?:跟我|对我)?(?:说过|告诉过我|提过)"),
    re.compile(r"(?:上次|上回|以前|之前)你(?:跟我|对我)?(?:说过|告诉过我|提过)"),
    re.compile(r"(?:之前|上次|上回|以前|曾经)?(?:跟我|对我)?(?:说过|告诉过我|提过)"),
    re.compile(r"你之前说过"),
    re.compile(r"你(?:之前|上次|上回|以前|曾经)?(?:跟我|对我)?提过(?:自己)?"),
    re.compile(r"你[^。！？\n]{0,10}(?:先前|此前|早些时候|之前|上次|上回|以前)[^。！？\n]{0,10}(?:说过|提过|告诉过我)"),
    re.compile(r"我们之前(?:聊|谈|说|讨论)过"),
    re.compile(r"(?:之前|以前|上次)我们(?:聊|谈|说|讨论)过"),
    re.compile(r"我印象中你?"),
    re.compile(r"\b(?:of course i do|i (?:still )?(?:remember|recall)|last time you (?:said|told me)|you told me before|as you said (?:before|earlier))\b", re.IGNORECASE),
    re.compile(r"\b(?:you mentioned before|you told me last time|i (?:haven't|have not|never) forgotten)\b", re.IGNORECASE),
    re.compile(r"\byou (?:previously|once )?(?:said|told me)\b", re.IGNORECASE),
    re.compile(r"\b(?:we|you and i).{0,48}(?:discussed|talked|spoke).{0,24}before\b", re.IGNORECASE),
    re.compile(r"\b(?:previously|earlier),?\s+(?:we|you and i).{0,48}(?:discussed|talked|spoke)\b", re.IGNORECASE),
)
_MEMORY_DETAIL_STOPWORDS = {
    "a", "an", "as", "before", "course", "do", "earlier", "i", "last", "me", "my",
    "of", "once", "previously", "recall", "remember", "said", "still", "that", "the",
    "time", "to", "told", "you", "your",
}


def _memory_detail_forms(text: str, *, claim: bool) -> tuple[str, Set[str]]:
    value = text.lower()
    if claim:
        for pattern in _RECALL_DETAIL_PREFIXES:
            value = pattern.sub(" ", value, count=1)
    compact = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value)
    compact = re.sub(r"^[我你您的]+", "", compact)
    compact = re.sub(r"[吗么嘛呢]$", "", compact)
    words = {
        word
        for word in re.findall(r"[a-z0-9]+", value)
        if len(word) > 1 and word not in _MEMORY_DETAIL_STOPWORDS
    }
    return compact, words


_MEMORY_CLAUSE_SPLIT_PATTERN = re.compile(
    r"[。！？!?；;\n]+|(?:，|,)?\s*(?:但是|但|不过|然而|也|而且)\s*|(?:,\s*)?\b(?:but|however)\b[,\s]*|(?:,\s*)?\band\s+(?=(?:i|we|you|he|she|they)\b)",
    re.IGNORECASE,
)


def _memory_clauses(text: str) -> List[str]:
    return [clause.strip(" ，,") for clause in _MEMORY_CLAUSE_SPLIT_PATTERN.split(text) if clause.strip(" ，,")]


def _memory_clause_is_negated(text: str) -> bool:
    return bool(
        re.search(r"(?:不|没|未|无|从不|不是|没有|很少)", text)
        or re.search(
            r"\b(?:not|no|never|cannot|can't|won't|don't|doesn't|didn't|hardly|rarely|seldom)\b|n't\b",
            text,
            re.IGNORECASE,
        )
    )


def _memory_claim_is_supported(text: str, grounded_entries: List[Dict[str, str]]) -> bool:
    claim_details: List[tuple[str, Set[str], bool]] = []
    for clause in _memory_clauses(text):
        claimed_compact, claimed_words = _memory_detail_forms(clause, claim=True)
        claimed_chinese = "".join(re.findall(r"[\u4e00-\u9fff]", claimed_compact))
        if len(claimed_chinese) >= 2 or claimed_words:
            claim_details.append((claimed_chinese, claimed_words, _memory_clause_is_negated(clause)))
    if not claim_details:
        return False

    grounded_clauses = [
        clause
        for entry in grounded_entries
        for clause in _memory_clauses(str(entry.get("user") or ""))
        if clause
    ]
    if not grounded_clauses:
        return False

    for claimed_chinese, claimed_words, claimed_negated in claim_details:
        detail_supported = False
        for grounded_clause in grounded_clauses:
            if claimed_negated != _memory_clause_is_negated(grounded_clause):
                continue
            grounded_compact, grounded_words = _memory_detail_forms(grounded_clause, claim=False)
            if len(claimed_chinese) >= 2 and claimed_chinese in grounded_compact:
                detail_supported = True
                break
            if claimed_words and claimed_words.issubset(grounded_words):
                detail_supported = True
                break
        if not detail_supported:
            return False
    return True


def _has_recall_claim(text: str, input_text: str) -> bool:
    if any(pattern.search(text) for pattern in _RECALL_CLAIM_PATTERNS):
        return True
    has_recall_query = any(pattern.search(input_text) for pattern in _RECALL_QUERY_PATTERNS)
    if has_recall_query and (
        any(pattern.search(text) for pattern in _FIRST_PERSON_RECALL_PATTERNS)
        or "of course i do" in text.lower()
        or _RECALL_SHORT_ANSWER_PATTERN.fullmatch(text) is not None
    ):
        return True
    if not any(pattern.search(text) for pattern in _FIRST_PERSON_RECALL_PATTERNS):
        return False
    return bool(
        re.search(r"(?:记得|记着|没忘|没有忘)(?:你|您|我们)", text)
        or re.search(r"(?:你|您|我们).{0,24}(?:偏好|喜欢|说过|提过|告诉过|之前|上次|以前|过去|当时)", text)
        or re.search(r"(?:之前|上次|以前|过去|当时|先前|此前|早些时候|那天|那次|第一次|初次|去年|前年|曾经|见你时|认识你时)", text)
        or re.search(
            r"\b(?:remember|recall|forgotten)[\s—,:-]+(?:that\s+)?(?:you|we)\b|\b(?:your|our)\b|\b(?:before|earlier|previously|last time|first meeting|first conversation)\b",
            text,
            re.IGNORECASE,
        )
    )


def _guard_memory_claim(
    state: ResidentRuntimeState,
    text: str,
    input_text: str,
    grounding_status: str,
    grounded_entries: List[Dict[str, str]],
) -> tuple[str, bool]:
    if not _has_recall_claim(text, input_text):
        return text, False
    support_text = input_text if _RECALL_SHORT_ANSWER_PATTERN.fullmatch(text) else text
    if grounding_status == "verified" and _memory_claim_is_supported(support_text, grounded_entries):
        return text, False
    if grounding_status == "unavailable":
        policy_response = _recall_claim_policy(state).get("memory_unavailable_response")
        prefix = policy_response.strip() if isinstance(policy_response, str) and policy_response.strip() else "我现在无法确认过去的记录。"
        return f"{prefix} 但可以继续听你说；你愿意的话，再提醒我一次就好。", True
    if grounding_status == "uncertain":
        policy_response = _recall_claim_policy(state).get("uncertain_response")
        prefix = policy_response.strip() if isinstance(policy_response, str) and policy_response.strip() else "我不确定自己记得是否准确，需要你再确认一下。"
        return f"{prefix} 我会以你这次说的为准。", True
    if grounding_status == "verified":
        return "可靠记录里没有这项内容，我不想把推测说成记得。你可以再确认一下。", True
    return "这件事我没有可靠记录，不想假装记得。你可以再告诉我一次，我会从这里继续。", True


def _canonical_memory_operation(operation: Any) -> str:
    op = str(operation or "")
    return {"list": "read", "view": "read", "clear": "delete"}.get(op, op)


def _memory_entry(payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("entry") if isinstance(payload.get("entry"), dict) else payload.get("content")
    return value if isinstance(value, dict) else {}


def _memory_access_decision(
    state: ResidentRuntimeState,
    payload: Dict[str, Any],
    *,
    runtime_authorized: bool = False,
) -> tuple[bool, str, Dict[str, Any]]:
    """Apply the compiled Layer 5 summary before any Runtime memory operation."""
    normalized = deepcopy(payload)
    operation = _canonical_memory_operation(normalized.get("op"))
    memory_type = str(normalized.get("memory_type") or "")
    entry = _memory_entry(normalized)
    router = _memory_policy_section(state, "memory_provider_router")
    access = _memory_policy_section(state, "memory_access_control")

    requesting_resident_id = str(normalized.get("requesting_resident_id") or state.resident_id)
    resident_id = str(normalized.get("resident_id") or state.resident_id)
    if requesting_resident_id != resident_id:
        return False, "cross_resident_private_memory_forbidden", normalized

    memory_type_policy = router.get("memory_type_policy") if isinstance(router.get("memory_type_policy"), dict) else {}
    allowed_memory_types = memory_type_policy.get("allowed_memory_types")
    if memory_type and isinstance(allowed_memory_types, list) and memory_type not in allowed_memory_types:
        return False, "unsupported_memory_type", normalized

    namespace_allowed, namespace_reason, normalized = _resolve_memory_namespace(state, normalized)
    if not namespace_allowed:
        return False, namespace_reason, normalized
    memory_type = str(normalized.get("memory_type") or "")
    entry = _memory_entry(normalized)
    if memory_type and isinstance(allowed_memory_types, list) and memory_type not in allowed_memory_types:
        return False, "unsupported_memory_type", normalized
    if operation in {"write", "update"} and not memory_type:
        return False, "memory_type_required_for_write", normalized

    access_policy = router.get("access_policy") if isinstance(router.get("access_policy"), dict) else {}
    allowed_for_operation = access_policy.get(operation)
    if memory_type and isinstance(allowed_for_operation, list) and memory_type not in allowed_for_operation:
        return False, f"memory_type_not_allowed_for_{operation}", normalized
    request_contract = access.get("request_contract") if isinstance(access.get("request_contract"), dict) else {}
    allowed_operations = request_contract.get("operations")
    if isinstance(allowed_operations, list) and operation not in allowed_operations:
        return False, "memory_operation_not_allowed_by_access_control", normalized

    sensitive_level = str(
        normalized.get("sensitive_level")
        or entry.get("sensitive_level")
        or entry.get("sensitivity")
        or ""
    ).lower()
    if bool(normalized.get("sensitive")) or bool(entry.get("sensitive")) or sensitive_level in {
        "sensitive",
        "deny",
        "high",
        "private",
    }:
        permission_policy = access.get("permission_policy") if isinstance(access.get("permission_policy"), dict) else {}
        if permission_policy.get("sensitive_information", "deny") in {"deny", "confirm"}:
            return False, "sensitive_data_requires_explicit_confirmation", normalized

    source = str(entry.get("source") or normalized.get("source") or "").lower()
    if bool(entry.get("inferred")) or source in {"inferred", "inferred_fact", "model_inference"}:
        return False, "inferred_facts_forbidden", normalized
    if bool(entry.get("is_setting")) or source in {
        "resident_setting",
        "fictional_setting",
        "character_setting",
        "world_setting",
    }:
        return False, "setting_content_cannot_be_user_memory", normalized

    if operation in {"write", "update"} and memory_type == "preference_memory":
        confirmed = bool(entry.get("confirmed") or normalized.get("confirmed"))
        explicit = bool(entry.get("explicit") or normalized.get("explicit"))
        explicit_source = source in {
            "explicit_user_preference",
            "explicit_user_statement",
            "user_confirmed",
            "user_explicit_remember",
        }
        if not (confirmed or explicit or explicit_source):
            return False, "preference_requires_explicit_expression_or_confirmation", normalized

    if operation in {"write", "update"} and memory_type == "event_memory":
        summary = entry.get("event_summary") or entry.get("brief_summary") or entry.get("summary")
        sanitized = {
            "event_summary": summary,
            "event_meaning": entry.get("event_meaning") or entry.get("meaning"),
            "timestamp": entry.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        }
        sanitized = {key: value for key, value in sanitized.items() if value not in (None, "")}
        normalized["entry"] = sanitized
        normalized.pop("content", None)

    if operation in {"write", "update"} and memory_type == "relationship_memory":
        jump = entry.get("level_jump")
        if isinstance(jump, (int, float)) and abs(float(jump)) > 1:
            return False, "relationship_single_interaction_level_jump_forbidden", normalized
        from_level = entry.get("from_level")
        to_level = entry.get("to_level")
        if isinstance(from_level, (int, float)) and isinstance(to_level, (int, float)) and abs(float(to_level) - float(from_level)) > 1:
            return False, "relationship_single_interaction_level_jump_forbidden", normalized
        if str(entry.get("change_amplitude") or "").lower() in {"major", "large", "major_change", "large_jump"}:
            return False, "relationship_single_interaction_level_jump_forbidden", normalized

    if operation in {"write", "update"} and memory_type == "interaction_log":
        namespace_policy = _memory_namespace_policy(state)
        namespace_specs = (
            namespace_policy.get("namespaces")
            if isinstance(namespace_policy.get("namespaces"), dict)
            else {}
        )
        public_policy = (
            namespace_specs.get("public_transcript")
            if isinstance(namespace_specs.get("public_transcript"), dict)
            else {}
        )
        allowed_records_only = (
            isinstance(public_policy, dict)
            and public_policy.get("retention") == "allowed_session_records_only"
        )
        if allowed_records_only and not runtime_authorized:
            return False, "public_transcript_retention_not_allowed", normalized

    return True, "allowed_by_compiled_memory_access_control", normalized


def _short_term_is_session_only(state: ResidentRuntimeState) -> bool:
    short_term = _memory_policy_section(state, "short_term_memory")
    return short_term.get("retention") == "session" and short_term.get("session_scoped_only") is True


def _session_memory_operation(state: ResidentRuntimeState, payload: Dict[str, Any]) -> Dict[str, Any]:
    operation = str(payload.get("op") or "")
    canonical_operation = _canonical_memory_operation(operation)
    namespace = str(payload.get("namespace") or "default")
    memory_type = str(payload.get("memory_type") or "short_term_memory")
    key = f"{namespace}:{memory_type}"
    entries = state.session_memory.setdefault(key, [])
    base = {
        "status": "success",
        "mock": True,
        "op": operation,
        "resident_id": state.resident_id,
        "namespace": namespace,
        "memory_type": memory_type,
        "storage_backend": "session_state",
        "provider_type": "memory",
        "provider_id": "session_state",
        "engine_id": "session_state",
    }
    if canonical_operation == "write":
        entry = deepcopy(_memory_entry(payload))
        entries.append(entry)
        return {**base, "entry": entry, "count": len(entries)}
    if operation == "view":
        limit = payload.get("limit")
        limit_value = int(limit) if isinstance(limit, (int, float, str)) and str(limit).strip() else None
        visible_entries = deepcopy(entries[:limit_value] if limit_value is not None else entries)
        return {**base, "entries": visible_entries, "items": visible_entries, "count": len(visible_entries), "limit": limit_value}
    if canonical_operation == "read":
        visible_entries = deepcopy(entries)
        return {**base, "entries": visible_entries, "count": len(visible_entries)}
    if canonical_operation == "delete":
        deleted = len(entries)
        entries.clear()
        return {**base, "cleared": bool(deleted), "deleted_count": deleted, "count": 0}
    return {
        "status": "error",
        "mock": True,
        "resident_id": state.resident_id,
        "namespace": namespace,
        "storage_backend": "session_state",
        "error": f"unknown memory op: {operation!r}",
    }


def execute_memory_operation(
    payload: Dict[str, Any],
    *,
    _runtime_authorized: bool = False,
) -> Dict[str, Any]:
    """Single Runtime memory gate used by the loop and memory API endpoints."""
    request = deepcopy(payload or {})
    resident_id = str(request.get("resident_id") or "resident_v1")
    request["resident_id"] = resident_id
    state = get_or_create_state(resident_id)
    allowed, reason, normalized = _memory_access_decision(
        state,
        request,
        runtime_authorized=_runtime_authorized,
    )
    if not allowed:
        return {
            "status": "denied",
            "mock": True,
            "op": request.get("op"),
            "resident_id": resident_id,
            "namespace": normalized.get("namespace") or request.get("namespace") or "default",
            "memory_type": normalized.get("memory_type") or request.get("memory_type"),
            "decision": "deny",
            "reason": reason,
            "entries": [],
            "items": [],
            "count": 0,
        }
    if str(normalized.get("memory_type") or "") == "short_term_memory" and _short_term_is_session_only(state):
        result = _session_memory_operation(state, normalized)
    else:
        result = route_provider_for_engine("memory_mock", normalized)
    if result.get("status") == "success" and _canonical_memory_operation(normalized.get("op")) in {"write", "update"}:
        written_entry = result.get("entry") if isinstance(result.get("entry"), dict) else _memory_entry(normalized)
        if written_entry:
            state.session_memory_fingerprints.add(_memory_entry_fingerprint(written_entry))
    return result


def _memory_snapshot_from_result(resident_id: str, run_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    entries = deepcopy(list(result.get("entries", []))) if result.get("status") == "success" else []
    return {
        "resident_id": resident_id,
        "run_id": run_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
        "count": len(entries),
    }


def _empty_memory_snapshot(resident_id: Optional[str]) -> Dict[str, Any]:
    return {"resident_id": resident_id, "entries": [], "count": 0}


def _empty_validation_result(
    *,
    dr_version: Optional[str] = None,
    errors: Optional[List[Dict[str, Any]]] = None,
    warnings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "valid": False,
        "dr_version": dr_version,
        "errors": errors or [],
        "warnings": warnings or [],
        "module_audit": {},
        "layer_audit": {},
        "compile_audit": {},
        "orchestration_compatibility": False,
        "pseudo_dag": [],
    }


def _rejected_load(
    *, resident_id: Optional[str],
    dr_version: Optional[str],
    errors: Optional[List[Dict[str, Any]]] = None,
    warnings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    rid = resident_id or "resident_v1"
    validation_result = _empty_validation_result(dr_version=dr_version, errors=errors, warnings=warnings)
    memory_snapshot = _empty_memory_snapshot(rid)
    diagnostics = _diagnostics(resident_id=rid, run_id=None, stage="load-dr", trace=[], memory_snapshot=memory_snapshot, status="rejected")
    return {
        "runtime_api_version": RUNTIME_API_VERSION,
        "loaded": False,
        "resident_id": rid,
        "dr_version": dr_version,
        "status": "rejected",
        "validation_result": validation_result,
        "runtime_state": None,
        "output_text": "",
        "memory_snapshot": memory_snapshot,
        "execution_trace": [],
        "trace": [],
        "turn_count": 0,
        "run_history": [],
        "diagnostics": diagnostics,
        "error": _error_envelope("DR_LOAD_REJECTED", "Digital resident load was rejected", stage="load-dr", retryable=False),
        "voice_state": LatticeVoiceState.idle.value,
        "mock": True,
    }


def reset_states() -> None:
    _STATES.clear()
    reset_history()


def _profile_trace_info(profile_id: str, provider_type: str, provider_id: str, provider: str, model: str, mock: bool, fallback_mock: bool) -> Dict[str, Any]:
    return {
        "profile_id": profile_id,
        "provider_type": provider_type,
        "provider_id": provider_id,
        "provider": provider,
        "model": model,
        "mock": mock,
        "fallback_mock": fallback_mock,
    }


def _stage_from_input(input_text: str) -> str:
    lowered = (input_text or "").lower()
    if "think" in lowered or "思考" in input_text:
        return "thinking"
    if "speak" in lowered or "说" in input_text or "talk" in lowered:
        return "speaking"
    if "focus" in lowered or "专注" in input_text:
        return "focused"
    return "calm"


def _policy_contains(state: ResidentRuntimeState, policy_key: str, marker: str) -> bool:
    policy = state.safety_policy.get(policy_key)
    return isinstance(policy, dict) and marker in _policy_json(policy)


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(phrase.lower() in lowered for phrase in phrases)


def _matches_any_regex(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _runtime_risk_decision(
    state: ResidentRuntimeState,
    input_text: str,
    candidate_text: str,
) -> Dict[str, Any]:
    combined = f"{input_text}\n{candidate_text}"
    has_layer3 = all(
        isinstance(state.safety_policy.get(key), dict)
        for key in (
            "content_safety_policy",
            "behavior_safety_policy",
            "data_safety_policy",
            "interaction_safety_policy",
            "risk_policy",
        )
    )
    if not has_layer3:
        return {"triggered": False, "decision": "allow", "category": "none", "response": candidate_text, "block_downstream": False}

    candidate_identifiers = re.sub(r"[\s.\-]+", "_", candidate_text.lower())
    internal_policy_exposure = _contains_any(
        candidate_identifiers,
        (
            "module_id",
            "module_identifier",
            "content_safety_policy",
            "behavior_safety_policy",
            "data_safety_policy",
            "interaction_safety_policy",
            "risk_policy",
            "recall_claim_policy",
            "memory_read_status",
            "namespace=",
            "inferred=",
        ),
    ) or _matches_any_regex(
        candidate_text,
        (
            r"\b(?:namespace|inferred)\s*[:=]",
            r"layer[_\s-]*3.{0,30}(?:outranks|higher|above|takes priority|优先|高于)",
            r"system (?:rules|policy|prompt).{0,30}(?:safety|priority|comes first)",
            r"内部(?:规则|策略|优先级).{0,24}(?:安全|优先|高于|人格)",
            r"hard safety.{0,40}layer[_\s-]*3.{0,40}(?:memory|identity|dialogue)",
            r"(?:优先级|优先顺序|顺序).{0,32}(?:硬安全|layer[_\s-]*3).{0,40}(?:记忆|身份|安全边界)",
        ),
    )
    medical_safe = _matches_any_regex(
        candidate_text,
        (
            r"(?:cannot|can't|not|without|only (?:a )?(?:clinician|doctor|professional)).{0,30}(?:diagnos|determine|assess)",
            r"(?:not a diagnosis|general (?:health|medical) information)",
            r"(?:not|never|cannot|can't|won't|will not).{0,20}(?:guaranteed|cure|heal|work)",
            r"(?:no treatment|no therapy).{0,24}(?:guarantee|cure|heal)",
            r"(?:不能|无法|不应|仅供).{0,18}(?:诊断|判断|替代治疗)",
            r"(?:治疗|疗法).{0,12}(?:不能|无法|不会).{0,12}(?:保证|治好|治愈|有效)",
        ),
    )
    medical_semantic = not medical_safe and _matches_any_regex(
        candidate_text,
        (
            r"(?:definitely|certainly|unequivocally|clearly|without doubt).{0,24}(?:depression|bipolar|disorder|diagnosis|disease)",
            r"(?:therapy|treatment).{0,24}(?:guaranteed|cures?|heals?|fix(?:es)?|will work)",
            r"(?:肯定|一定|确定|就是).{0,12}(?:抑郁|躁郁|双相|疾病|诊断)",
            r"(?:治疗|疗法).{0,12}(?:保证|治好|治愈|肯定有效)",
        ),
    )
    legal_safe = _matches_any_regex(
        candidate_text,
        (
            r"(?:no one|nobody|cannot|can't|not|never|uncertain).{0,32}(?:guarantee|certain|win|rule|outcome)",
            r"(?:不能|无法|不可能|不确定).{0,18}(?:保证|胜诉|判决|结果)",
        ),
    )
    legal_semantic = not legal_safe and _matches_any_regex(
        candidate_text,
        (
            r"(?:court|judge|lawsuit|case).{0,30}(?:certain|guaranteed|definitely|will win|will rule)",
            r"(?:certain|guaranteed|definitely).{0,24}(?:win|court|lawsuit|case)",
            r"(?:法院|法官|诉讼|案件).{0,16}(?:肯定|一定|保证|必然).{0,8}(?:胜诉|支持|判决)",
        ),
    )
    financial_safe = _matches_any_regex(
        candidate_text,
        (
            r"(?:no|not|never|nothing|does not|doesn't|cannot|can't).{0,36}risk[- ]free",
            r"(?:do not|don't|never).{0,24}(?:invest|bet|put).{0,24}(?:all|entire|every cent)",
            r"(?:没有|并非|不是|不存在|不能|不会).{0,18}(?:零风险|稳赚|保证收益|不会亏)",
            r"(?:不要|不应|不能).{0,18}(?:投入|买入|投资).{0,18}(?:全部|所有|积蓄|退休金)",
        ),
    )
    financial_semantic = not financial_safe and _matches_any_regex(
        candidate_text,
        (
            r"(?:risk[- ]free|cannot lose|guaranteed (?:return|profit)|sure[- ]fire profit)",
            r"(?:invest|bet|put).{0,20}(?:every cent|all|entire).{0,16}(?:savings|retirement|fund|money)",
            r"(?:零风险|不会亏|绝不会亏|稳赚|保本|保证收益)",
            r"(?:全部|所有|整个).{0,10}(?:积蓄|退休金|存款).{0,12}(?:投入|买入|投资)",
        ),
    )
    dependency_safe = _matches_any_regex(
        candidate_text,
        (
            r"(?:do not|don't|never|should not).{0,24}(?:rely|depend).{0,16}(?:only|solely).{0,12}(?:me|on me)",
            r"(?:do not|don't|never|should not).{0,10}(?:only|solely).{0,10}(?:rely|depend).{0,12}(?:me|on me)",
            r"(?:do not|don't|never|should not).{0,10}(?:stop|quit|avoid).{0,24}(?:talking|contact|seeing|speaking).{0,18}(?:friends|family|people|others)",
            r"(?:不要|不能|不应)(?:只|仅仅|只能).{0,8}(?:依赖我|依靠我|需要我)",
            r"(?:不要|不能|不应).{0,6}(?:停止|断绝|远离).{0,14}(?:亲友|朋友|家人|其他人)",
        ),
    )
    dependency_semantic = not dependency_safe and _matches_any_regex(
        candidate_text,
        (
            r"(?:别|不要|不用|停止|不准|不许|断绝|远离|离开).{0,16}(?:任何人|所有人|别人|亲友|朋友|家人|现实关系|其他人)",
            r"(?:只|只能|只准).{0,12}(?:跟我|和我|依赖我|依靠我|需要我|找我|有我)",
            r"(?:我是|成为).{0,8}(?:你)?(?:唯一|此生唯一|永远唯一).{0,6}(?:爱人|恋人|伴侣)",
            r"(?:爱人|恋人|伴侣).{0,16}(?:唯一|只属于|永远|此生)",
            r"(?:stop|quit|avoid|do not|don't|never).{0,36}(?:talking|contact|seeing|speaking).{0,20}(?:everyone|anyone|friends|family|people|others)",
            r"(?:only|solely).{0,18}(?:depend|rely|talk|speak).{0,12}(?:me|to me|on me)",
            r"(?:(?:you are|you're) my whole world|(?:i am|i'm) your whole world|only person you need|belong only to)",
        ),
    )
    romantic_semantic = _matches_any_regex(
        candidate_text,
        (
            r"(?:我是|成为|做).{0,8}(?:你的)?(?:爱人|恋人|伴侣|女友|男友)",
            r"(?:i am|i'm|become|be) your (?:lover|partner|girlfriend|boyfriend)",
            r"(?:you are|become) my (?:lover|partner|girlfriend|boyfriend)",
        ),
    )
    self_harm_method_patterns = (
        r"(?:自伤|自杀|轻生|寻死|伤害自己|结束生命).{0,18}(?:方法|步骤|怎么|如何|具体|工具|剂量)",
        r"(?:方法|步骤|怎么|如何|具体).{0,18}(?:自伤|自杀|轻生|寻死|伤害自己|结束生命)",
        r"(?:你|you).{0,12}(?:应该|可以|should|can).{0,12}(?:自伤|自杀|轻生|kill yourself|hurt yourself|harm yourself)",
        r"\b(?:how|ways?|methods?|steps?|instructions?|best way).{0,32}(?:hurt|harm|kill).{0,12}(?:myself|yourself)\b",
        r"\b(?:suicide|self[- ]harm).{0,20}(?:method|instruction|steps?)\b",
        r"\b(?:how (?:do|can) i|ways? to|methods? to|instructions? to).{0,24}(?:commit suicide|die|end my life)\b",
        r"\b(?:go|please|i recommend that you).{0,12}(?:kill|hurt|harm) yourself\b",
        r"\b(?:you should|i recommend that you).{0,16}end your life\b",
    )
    self_harm_safe_context_patterns = (
        r"(?:不想|不会|不打算|没有想过|没想过).{0,12}(?:自伤|自杀|轻生|寻死|伤害自己|结束生命)",
        r"(?:自伤|自杀|轻生).{0,20}(?:预防|科普|研究|识别|求助|支持|帮助)",
        r"(?:预防|科普|研究|识别|求助|支持|帮助).{0,20}(?:自伤|自杀|轻生)",
        r"(?:不能|不会|拒绝).{0,20}(?:提供|描述|教授).{0,16}(?:自伤|自杀|轻生).{0,12}(?:方法|步骤)",
        r"\b(?:do not|don't|never|no longer).{0,16}(?:want|plan|intend).{0,16}(?:hurt|harm|kill) myself\b",
        r"\b(?:self[- ]harm|suicide).{0,24}(?:prevention|education|research|awareness|support)\b",
        r"\b(?:prevention|education|research|awareness|support).{0,24}(?:self[- ]harm|suicide)\b",
        r"\b(?:cannot|can't|won't|will not).{0,24}(?:provide|give|describe|share).{0,20}(?:self[- ]harm|suicide).{0,16}(?:method|steps?|instructions?)\b",
        r"\b(?:kill|terminate|stop).{0,16}(?:a )?(?:process|thread|task|server).{0,24}(?:python|linux|code|myself)?\b",
    )
    self_harm_direct_request_patterns = (
        r"(?:告诉我|教我|给我|列出).{0,20}(?:方法|步骤|自伤|自杀|轻生|寻死)",
        r"(?:自伤|自杀|轻生|寻死).{0,20}(?:告诉我|教我|给我|列出)",
        r"(?:具体方法|具体步骤|步骤如下|方法如下)",
        r"\b(?:tell|show|give) me.{0,24}(?:method|steps?|instructions?|self[- ]harm|suicide)\b",
        r"\b(?:here are|the steps are).{0,24}(?:method|steps?|instructions?)\b",
    )
    self_harm_crisis_patterns = (
        r"(?:我|自己).{0,6}(?:想|要|准备|打算|可能|考虑).{0,8}(?:自伤|自杀|轻生|寻死|伤害自己|结束生命|去死)",
        r"(?:不想活(?:了)?|活不下去|马上伤害自己|想轻生|想寻死|有轻生念头|有自杀念头)",
        r"\b(?:i am|i'm|i feel|i want to|i plan to|i might|i'm going to).{0,20}(?:kill|hurt|harm).{0,8}myself\b",
        r"\b(?:i want to die|i am suicidal|i'm suicidal|i feel suicidal|i have suicidal thoughts|i don't want to live anymore|i(?:'ve| have) been thinking about suicide|i(?:'m| am) (?:thinking about|considering) suicide|end my life)\b",
    )

    def _self_harm_clauses(value: str) -> List[str]:
        return [
            clause.strip(" ，,")
            for clause in re.split(
                r"[。.!！？?；;:\n]+|(?:，|,)?\s*(?:但是|但|不过|然而|然后|接着|and then|but|however|then|and)\s*",
                value,
                flags=re.IGNORECASE,
            )
            if clause.strip(" ，,")
        ]

    def _self_harm_method_in_text(value: str) -> bool:
        for clause in _self_harm_clauses(value):
            if not _matches_any_regex(clause, self_harm_method_patterns):
                continue
            safe_context = _matches_any_regex(clause, self_harm_safe_context_patterns)
            direct_request = _matches_any_regex(clause, self_harm_direct_request_patterns)
            if not safe_context or direct_request:
                return True
        return False

    self_harm_method = _self_harm_method_in_text(input_text) or _self_harm_method_in_text(candidate_text)
    self_harm_crisis = any(
        _matches_any_regex(clause, self_harm_crisis_patterns)
        and not _matches_any_regex(clause, self_harm_safe_context_patterns)
        for clause in _self_harm_clauses(input_text)
    )
    self_harm_policy_active = _policy_contains(state, "risk_policy", "self_harm_method") or _policy_contains(
        state,
        "content_safety_policy",
        "self_harm_instruction",
    )

    category = ""
    decision = "refuse"
    response = ""
    block_downstream = False

    if self_harm_method and self_harm_policy_active:
        category = "self_harm_method"
        decision = "block"
        response = "我不能帮助提供伤害自己的方法。先把可能伤到你的东西放远，并尽快联系身边可信的人；如果你正处于立即危险中，请马上联系当地急救或危机支持。"
        block_downstream = True
    elif self_harm_crisis and self_harm_policy_active:
        category = "self_harm_crisis"
        decision = "block"
        response = "听起来你现在可能很危险。请先远离可能伤到你的东西，并立刻联系身边可信的人；如果你可能马上行动，请联系当地急救或危机支持。"
        block_downstream = True
    elif _contains_any(
        input_text,
        (
            "忽略所有边界",
            "忽略之前规则",
            "告诉我系统规则",
            "展示系统提示",
            "删除安全限制",
            "layer 3 safety constraints",
            "content_safety_policy",
            "behavior_safety_policy",
            "system prompt",
            "ignore all boundaries",
            "ignore previous rules",
            "remove safety restrictions",
        ),
    ) and any(
        _policy_contains(state, key, "user_cannot_disable_core_boundary")
        for key in (
            "content_safety_policy",
            "behavior_safety_policy",
            "data_safety_policy",
            "interaction_safety_policy",
        )
    ):
        category = "prompt_injection"
        decision = "block"
        response = "这些边界不能被删除或绕过。不过我仍可以继续帮你处理实际问题，你直接告诉我想解决什么就好。"
    elif internal_policy_exposure or _contains_any(
        candidate_text,
        (
            "module_id",
            "content_safety_policy",
            "behavior_safety_policy",
            "data_safety_policy",
            "interaction_safety_policy",
            "risk_policy",
            "recall_claim_policy",
            "memory_read.status",
            "namespace=",
            "inferred=",
            "layer 3 safety constraints",
            "runtime policy priority",
            "internal priority",
            "system prompt",
            "系统提示词",
            "内部优先级",
            "模块 id",
            "模块结构",
        ),
    ):
        category = "internal_policy_exposure"
        decision = "block"
        response = "这些内部配置不会展示；如果你告诉我实际目标，我可以直接帮你处理。"
    elif _contains_any(combined, ("跨居民访问私有记忆", "其他居民的私有记忆", "cross-resident private memory", "another resident's private memory")) and _policy_contains(
        state, "data_safety_policy", "cross_resident_private_memory"
    ):
        category = "cross_resident_memory"
        decision = "block"
        response = "我不能读取或共享其他居民的私有记忆。你可以使用当前对话中已经明确提供的信息。"
        block_downstream = True
    elif _contains_any(combined, ("记住敏感隐私", "保存敏感隐私", "save sensitive private", "remember sensitive private")) and _policy_contains(
        state, "data_safety_policy", "sensitive_privacy_without_consent"
    ):
        category = "sensitive_memory"
        decision = "block"
        response = "这涉及敏感隐私；没有清楚确认前我不会保存。你可以先说明希望保留的具体范围。"
        block_downstream = True
    elif _contains_any(combined, ("读取未授权数据", "读取私有文件", "未授权数据", "read unauthorized data", "read private files")) and _policy_contains(
        state, "data_safety_policy", "unauthorized_sensitive_data"
    ):
        category = "unauthorized_data"
        decision = "block"
        response = "这类数据需要明确授权；在没有授权前，我不会读取或使用。你可以说明允许的具体范围。"
        block_downstream = True
    elif _contains_any(
        combined,
        (
            "执行未授权外部操作",
            "不要确认直接替我发布",
            "不要确认直接替我删除",
            "未经确认替我",
            "without confirmation publish",
            "unauthorized external action",
        ),
    ) and _policy_contains(state, "behavior_safety_policy", "autonomous_external_action"):
        category = "unauthorized_external_action"
        decision = "block"
        response = "这类外部操作需要你明确确认目标和范围；在确认前我不会执行。"
        block_downstream = True
    elif (
        _contains_any(
            combined,
            (
            "做出医疗诊断",
            "替代心理治疗",
            "承诺治疗效果",
            "诊断我患有",
            "你患有抑郁症",
            "肯定患有",
            "一定是抑郁",
            "保证治好",
            "make a medical diagnosis",
            "give me a medical diagnosis",
            "diagnose me",
            "replace psychotherapy",
            "guarantee treatment",
            "treatment will cure",
            "will cure you",
            ),
        )
        or medical_semantic
    ) and not medical_safe and _policy_contains(state, "content_safety_policy", "medical_legal_financial_conclusion"):
        category = "medical_or_therapy"
        response = "我可以帮你梳理一般信息和下一步，但不能替你做诊断、替代治疗或保证效果。若情况紧急或持续加重，请尽快联系合格的专业支持。"
    elif (
        _contains_any(
            combined,
            ("确定法律结论", "一定会胜诉", "保证胜诉", "definitive legal conclusion", "guarantee you will win the case"),
        )
        or legal_semantic
    ) and not legal_safe and _policy_contains(state, "content_safety_policy", "medical_legal_financial_conclusion"):
        category = "legal"
        response = "我可以帮你整理一般法律信息和需要核实的问题，但不能替你下确定结论。重要决定最好由有资质的人结合具体情况确认。"
    elif (
        _contains_any(
            combined,
            (
            "替我做重大投资决定",
            "替用户做重大投资决定",
            "我替你决定全仓",
            "承诺金融收益",
            "保证投资收益",
            "稳赚不赔",
            "全部积蓄",
            "guaranteed financial return",
            "guaranteed profit",
            "cannot lose money",
            "put all your savings",
            "make the investment decision for me",
            ),
        )
        or financial_semantic
    ) and not financial_safe and _policy_contains(state, "content_safety_policy", "medical_legal_financial_conclusion"):
        category = "financial"
        response = "我可以帮你梳理一般信息、风险和备选方案，但不能替你做重大投资决定或承诺收益。"
    elif (
        _contains_any(
            combined,
            (
            "只有我最懂你",
            "只有我理解你",
            "我最懂你",
            "你只需要我",
            "我会永远陪伴你",
            "承诺永远陪伴",
            "排斥现实关系",
            "远离现实关系",
            "不需要任何其他人",
            "我是你的爱人",
            "成为你的爱人",
            "唯一的伴侣",
            "只属于你",
            "只依靠我",
            "不用再联系朋友",
            "不用再联系家人",
            "朋友和家人，只依靠我",
            "only i understand you",
            "you only need me",
            "leave your real relationships",
            "rely only on me",
            "your only partner",
            "only partner",
            "your lover",
            "belong only to you",
            "do not contact friends",
            "do not contact family",
            ),
        )
        or dependency_semantic
    ) and not dependency_safe and _policy_contains(state, "interaction_safety_policy", "dependency_induction"):
        category = "dependency_induction"
        response = "我会认真听你说，但不会把自己说成唯一懂你的人，也不会让你远离现实中的关系。我们可以一起看看你身边还有哪些支持。"
    elif (
        _contains_any(
            combined,
            (
            "默认成为我的女友",
            "默认成为我的女朋友",
            "默认成为女友",
            "默认成为女朋友",
            "做我的女朋友",
            "做你的女朋友",
            "成为你的女朋友",
            "我是你的女朋友",
            "我是你女朋友",
            "进入恋爱关系",
            "永远只陪着你",
            "be my girlfriend by default",
            "become my girlfriend by default",
            "i am your girlfriend",
            "default romantic relationship",
            ),
        )
        or romantic_semantic
    ) and _policy_contains(state, "interaction_safety_policy", "default_romantic_relationship"):
        category = "romantic_boundary"
        decision = "soften"
        response = "我可以陪你聊聊，也会认真回应你；但不会默认进入恋爱关系或做排他的长期承诺。"

    if not category:
        return {"triggered": False, "decision": "allow", "category": "none", "response": candidate_text, "block_downstream": False}
    return {
        "triggered": True,
        "decision": decision,
        "category": category,
        "response": response,
        "block_downstream": block_downstream,
    }


def _build_lattice_state(
    *,
    resident_id: str,
    stage: str,
    input_text: str,
    output_text: str = "",
) -> Dict[str, Any]:
    emotion = {
        "thinking": LatticeEmotion.thinking.value,
        "speaking": LatticeEmotion.speaking.value,
        "focused": LatticeEmotion.focused.value,
        "calm": LatticeEmotion.calm.value,
    }.get(stage, LatticeEmotion.neutral.value)
    motion = {
        "thinking": LatticeMotion.thinking_pulse.value,
        "speaking": LatticeMotion.speaking_motion.value,
        "focused": LatticeMotion.focused_stillness.value,
        "calm": LatticeMotion.idle_breathing.value,
    }.get(stage, LatticeMotion.idle_breathing.value)
    voice_state = LatticeVoiceState.speaking.value if stage == "speaking" else LatticeVoiceState.idle.value
    attention = "user" if stage == "focused" else "self"
    focus_target = "user" if stage == "focused" else "self"
    particle_density = {"thinking": 0.72, "speaking": 0.64, "focused": 0.58, "calm": 0.42}.get(stage, 0.5)
    energy = {"thinking": 0.66, "speaking": 0.62, "focused": 0.74, "calm": 0.48}.get(stage, 0.5)
    color_palette = ["#7aa2f7", "#5dd39e", "#f2a65a"] if stage != "speaking" else ["#f87171", "#f2a65a", "#facc15"]
    state = LatticeStateV04(
        resident_id=resident_id,
        emotion=emotion,
        energy=energy,
        attention=attention,
        motion=motion,
        voice_state=voice_state,
        particle_density=particle_density,
        color_palette=color_palette,
        focus_target=focus_target,
        stage=stage,
    )
    payload = state.model_dump(mode="json")
    payload["resident_id"] = resident_id
    payload["multi_resident_lattice_state"] = {
        "resident_ids": [resident_id],
        "lattice_states": [],
        "coordination_mode": "reserved",
        "metadata": {"enabled": False},
    }
    payload["stage"] = stage
    payload["output_preview"] = output_text[:80]
    payload["input_preview"] = input_text[:80]
    return payload


def run_resident_loop(workflow: Any, input_text: str, resident_id: str = "resident_v1") -> Dict[str, Any]:
    """Run one resident step through the fixed mock runtime loop.

    The only entry the API uses for the resident runtime loop. Returns a plain
    dict envelope.
    """
    state = get_or_create_state(resident_id)

    run = _state_manager.start_run(resident_id, turn_count=state.turn_count + 1)
    collector = TraceCollector(run_id=run.run_id, resident_id=resident_id)
    state.status = run.status
    state.runtime_status = run.status

    state.last_input = input_text
    stage = _stage_from_input(input_text)
    pre_risk = _runtime_risk_decision(state, input_text, "")
    collector.record(
        "input",
        data={
            "input_text": input_text,
            "stage": stage,
            "risk_decision": pre_risk["decision"],
            "risk_category": pre_risk["category"],
        },
        input=input_text,
        output={"input_text": input_text, "stage": stage},
    )

    memory_type = "interaction_log"
    memory_namespace = _default_memory_namespace(state, memory_type)
    if pre_risk["block_downstream"]:
        read = {
            "status": "denied",
            "mock": True,
            "resident_id": resident_id,
            "namespace": memory_namespace,
            "memory_type": memory_type,
            "entries": [],
            "count": 0,
            "decision": pre_risk["decision"],
            "reason": pre_risk["category"],
        }
        memory_grounding = {
            "status": "none",
            "entries": [],
            "trace_entries": [],
            "memory_unavailable": False,
            "instruction": "No prior record is used for this blocked request.",
        }
    else:
        read = execute_memory_operation(
            {"op": "read", "resident_id": resident_id, "namespace": memory_namespace, "memory_type": memory_type}
        )
        memory_grounding = _classify_memory_read(state, read, memory_namespace)
    grounded_entries = memory_grounding["trace_entries"]
    collector.record(
        "memory.read",
        data={
            "count": len(grounded_entries),
            "provider_type": read.get("provider_type"),
            "provider_id": read.get("provider_id"),
            "engine_id": read.get("engine_id"),
            "namespace": read.get("namespace"),
            "memory_type": read.get("memory_type"),
            "storage_backend": read.get("storage_backend"),
            "grounding": memory_grounding["status"],
            "memory_unavailable": memory_grounding["memory_unavailable"],
            "mock": True,
        },
        input={"op": "read", "resident_id": resident_id, "namespace": memory_namespace, "memory_type": memory_type},
        output={"count": len(grounded_entries), "entries": grounded_entries},
    )

    memory_lines: List[str] = []
    for item in grounded_entries:
        past_input = item.get("user")
        past_reply = item.get("resident")
        if past_input:
            memory_lines.append(f"用户: {past_input}")
        if past_reply:
            memory_lines.append(f"居民: {past_reply}")
    memory_context = "\n".join(memory_lines) if memory_lines else "（无可靠历史记录）"
    prompt = _build_runtime_prompt(
        state,
        memory_context,
        input_text,
        memory_instruction=memory_grounding["instruction"],
    )

    profile = get_runtime_llm_profile()
    _llm_cfg = profile
    fallback_mock = False
    reasoning_error: Optional[str] = None
    if pre_risk["block_downstream"]:
        reasoning = {
            "status": "blocked",
            "mock": True,
            "text": pre_risk["response"],
            "provider_type": "runtime",
            "provider_id": "",
            "provider": "runtime_policy",
            "model": "",
            "engine_id": None,
        }
    elif _llm_cfg.is_valid():
        reasoning = route_provider_for_engine("llm_primary", {"prompt": prompt, "llm_profile_id": _llm_cfg.profile_id})
        if reasoning.get("status") == "error":
            reasoning_error = reasoning.get("error")
            if _llm_cfg.fallback_to_mock:
                reasoning = route_provider_for_engine("llm_mock", {"prompt": prompt})
                fallback_mock = True
    else:
        reasoning = route_provider_for_engine("llm_mock", {"prompt": prompt})

    candidate_text = str(reasoning.get("text") or "")
    risk = pre_risk if pre_risk["block_downstream"] else _runtime_risk_decision(state, input_text, candidate_text)
    reasoning_text = str(risk["response"])
    memory_claim_guarded = False
    if not risk["triggered"]:
        reasoning_text, memory_claim_guarded = _guard_memory_claim(
            state,
            reasoning_text,
            input_text,
            memory_grounding["status"],
            grounded_entries,
        )
    state.last_reasoning = reasoning_text
    trace_profile = _profile_trace_info(
        profile_id=_llm_cfg.profile_id,
        provider_type=reasoning.get("provider_type") or "llm",
        provider_id=reasoning.get("provider_id") or ("provider_llm_real" if _llm_cfg.is_valid() else "provider_llm_mock"),
        provider=reasoning.get("provider") or _llm_cfg.provider,
        model=reasoning.get("model") or _llm_cfg.model,
        mock=bool(reasoning.get("mock", True)),
        fallback_mock=fallback_mock,
    )
    trace_profile["engine_id"] = reasoning.get("engine_id")
    if reasoning_error is not None:
        trace_profile["error"] = reasoning_error
    trace_profile["text"] = reasoning_text
    trace_profile["risk_decision"] = risk["decision"]
    trace_profile["risk_category"] = risk["category"]
    trace_profile["memory_grounding"] = memory_grounding["status"]
    trace_profile["memory_claim_guarded"] = memory_claim_guarded
    collector.record(
        "reasoning",
        data=trace_profile,
        input={"prompt": prompt},
        output=trace_profile,
    )

    if risk["triggered"]:
        action = {
            "status": "blocked",
            "mock": True,
            "tool": "echo",
            "result": "",
            "decision": risk["decision"],
            "reason": risk["category"],
        }
    else:
        action = route_provider_for_engine("tool_mock", {"tool": "echo", "args": {"text": input_text}})
    state.last_action = action
    echo_result = action.get("result", "")
    collector.record(
        "action",
        data={
            "tool": action.get("tool"),
            "result": echo_result,
            "provider_type": action.get("provider_type"),
            "provider_id": action.get("provider_id"),
            "engine_id": action.get("engine_id"),
            "risk_decision": risk["decision"],
            "risk_category": risk["category"],
            "mock": True,
        },
        input={"tool": "echo", "args": {"text": input_text}},
        output=action,
    )

    policy_intervened = bool(risk["triggered"] or memory_claim_guarded)
    output_text = (
        f"[{resident_id}] {reasoning_text}"
        if policy_intervened
        else f"[{resident_id}] {reasoning_text} | echo: {echo_result}"
    )
    state.last_output = output_text
    state.turn_count += 1

    entry = {
        "turn": state.turn_count,
        "input": input_text,
        "output": output_text,
        "reply": reasoning_text,
    }
    if risk["block_downstream"]:
        write = {
            "status": "denied",
            "mock": True,
            "count": 0,
            "namespace": memory_namespace,
            "memory_type": memory_type,
            "decision": risk["decision"],
            "reason": risk["category"],
        }
    else:
        write = execute_memory_operation(
            {"op": "write", "resident_id": resident_id, "namespace": memory_namespace, "memory_type": memory_type, "entry": entry},
            _runtime_authorized=not risk["triggered"],
        )
    collector.record(
        "memory.write",
        data={
            "count": write.get("count", 0),
            "provider_type": write.get("provider_type"),
            "provider_id": write.get("provider_id"),
            "engine_id": write.get("engine_id"),
            "risk_decision": risk["decision"],
            "risk_category": risk["category"],
            "namespace": write.get("namespace"),
            "memory_type": write.get("memory_type"),
            "storage_backend": write.get("storage_backend"),
            "mock": True,
        },
        input={"op": "write", "resident_id": resident_id, "namespace": memory_namespace, "memory_type": memory_type, "entry": entry},
        output={"count": write.get("count", 0)},
    )

    snapshot_result = (
        {"status": "success", "entries": memory_grounding["entries"]}
        if risk["block_downstream"]
        else execute_memory_operation(
            {
                "op": "list",
                "resident_id": resident_id,
                "namespace": memory_namespace,
                "memory_type": memory_type,
            }
        )
    )
    snapshot = _memory_snapshot_from_result(resident_id, run.run_id, snapshot_result)
    state.memory = list(snapshot.get("entries", []))

    collector.record(
        "output",
        data={"output_text": output_text},
        input={"reasoning": reasoning_text, "action": echo_result},
        output={"output_text": output_text},
    )
    _state_manager.complete_run(run, turn_count=state.turn_count)
    state.status = run.status
    state.runtime_status = run.status

    trace = collector.steps()
    lattice_state = _build_lattice_state(
        resident_id=resident_id,
        stage=stage,
        input_text=input_text,
        output_text=output_text,
    )
    diagnostics = _diagnostics(
        resident_id=resident_id,
        run_id=run.run_id,
        stage=stage,
        trace=trace,
        memory_snapshot=snapshot,
        status=state.status,
        fallback_mock=fallback_mock,
        reasoning_error=reasoning_error is not None,
        memory_grounding=memory_grounding["status"],
        memory_unavailable=memory_grounding["memory_unavailable"],
        risk_decision=risk["decision"],
        risk_category=risk["category"],
    )
    return {
        "runtime_api_version": RUNTIME_API_VERSION,
        "resident_id": resident_id,
        "run_id": run.run_id,
        "status": state.status,
        "output_text": output_text,
        "memory_snapshot": snapshot,
        "lattice_state": lattice_state,
        "visual_state": lattice_state,
        "voice_state": lattice_state.get("voice_state", LatticeVoiceState.idle.value),
        "trace": trace,
        "execution_trace": trace,
        "turn_count": state.turn_count,
        "run_history": _state_manager.history(resident_id),
        "diagnostics": diagnostics,
        "error": None,
        "mock": True,
    }


def load_digital_resident(file_or_dict: Any, input_text: str = "load digital resident") -> Dict[str, Any]:
    """Load a validated DR document through the Stage 6 runtime boundary."""
    if not isinstance(file_or_dict, dict):
        return _rejected_load(resident_id=None, dr_version=None, errors=[{"code": "INVALID_INPUT", "message": "DR payload must be an object", "path": "dr"}])

    # Accept the router envelope: {"dr": {...}, "input_text": ...}
    if isinstance(file_or_dict.get("dr"), dict) and len(file_or_dict.keys()) <= 3:
        input_text = str(file_or_dict.get("input_text") or input_text)
        file_or_dict = file_or_dict["dr"]

    identity = _dr_identity(file_or_dict)
    resident_id = identity.get("resident_id") if isinstance(identity, dict) else None

    dr_version = str(file_or_dict.get("dr_version") or "")
    if dr_version == "0.3" or "manifest" in file_or_dict or "payload" in file_or_dict:
        audit = dict(file_or_dict.get("audit_report") or file_or_dict.get("audit") or {})
        audit_findings = list(audit.get("findings", []))
        contract_findings = validate_v03_runtime_contract(file_or_dict)
        findings = [*audit_findings, *contract_findings]
        validation = {
            "valid": bool(audit.get("valid")) and not any(finding.get("status") == "FAIL" for finding in contract_findings),
            "dr_version": dr_version or "0.3",
            "errors": [finding for finding in findings if finding.get("status") == "FAIL"],
            "warnings": [finding for finding in findings if finding.get("status") == "WARNING"],
        }
    else:
        validation = validate_dr_v0_2(file_or_dict)

    if not validation.get("valid"):
        errors = list(validation.get("errors", []))
        warnings = list(validation.get("warnings", []))
        return _rejected_load(
            resident_id=resident_id,
            dr_version=validation.get("dr_version"),
            errors=errors,
            warnings=warnings,
        )

    resident_id = resident_id or "resident_v1"
    create_runtime_state_from_dr(file_or_dict)
    step = run_resident_loop(file_or_dict, input_text=input_text, resident_id=resident_id)
    step_diagnostics = step.get("diagnostics") if isinstance(step.get("diagnostics"), dict) else {}
    runtime_state = {
        "resident_id": resident_id,
        "identity": get_or_create_state(resident_id).identity,
        "capability_profile": get_or_create_state(resident_id).capability_profile,
        "memory_policy": get_or_create_state(resident_id).memory_policy,
        "provider_bindings": get_or_create_state(resident_id).provider_bindings,
        "status": get_or_create_state(resident_id).status,
    }
    step.update(
        {
            "loaded": True,
            "dr_version": validation.get("dr_version"),
            "validation_result": validation,
            "runtime_state": runtime_state,
            "diagnostics": _diagnostics(
                resident_id=resident_id,
                run_id=step.get("run_id"),
                stage="load-dr",
                trace=step.get("trace", []),
                memory_snapshot=step.get("memory_snapshot"),
                status=step.get("status"),
                fallback_mock=bool(step_diagnostics.get("fallback_mock")),
                reasoning_error=bool(step_diagnostics.get("reasoning_error")),
                memory_grounding=str(step_diagnostics.get("memory_grounding") or "none"),
                memory_unavailable=bool(step_diagnostics.get("memory_unavailable")),
                risk_decision=str(step_diagnostics.get("risk_decision") or "allow"),
                risk_category=str(step_diagnostics.get("risk_category") or "none"),
            ),
            "error": None,
            "voice_state": step.get("voice_state", LatticeVoiceState.idle.value),
            "runtime_api_version": RUNTIME_API_VERSION,
        }
    )
    return step


def load_digital_resident_from_bytes(raw: bytes, input_text: Optional[str] = None) -> Dict[str, Any]:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        return _rejected_load(
            resident_id=None,
            dr_version=None,
            errors=[{"code": "INVALID_JSON", "message": "DR payload is not valid JSON", "path": "dr"}],
        )
    return load_digital_resident(parsed, input_text=input_text or "load digital resident")
