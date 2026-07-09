"""Studio Field Assistant service.

This service is Studio-only. It does not import or call Runtime providers,
engines, slots, provider registries, execution engines, or DR compiler code.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .studio_assistant_config import load_studio_assistant_config
from .studio_assistant_llm_client import StudioAssistantLLMClient

AssistantMode = Literal["explain", "recommend", "audit", "check_conflicts"]

SYSTEM_PROMPT = """你是 Eterna Studio 的字段填写与审核助手。
你只辅助 Studio 配置，不参与 Runtime 执行。
你不能建议修改 Runtime、Provider、Slot、Engine。
你不能建议把 API Key 写入前端、Canvas、DR 文件或 GitHub。
你不能在非 Layer 1 硬编码居民姓名、resident_id、codename、昵称。
你必须保持身份稳定、语言稳定、边界稳定、记忆稳定。
你的输出必须是结构化 JSON。
任何修改都必须等待用户确认。

安全限制：
- 不允许自动大面积重写 13 层。
- 不允许自动改身份 Source of Truth。
- 不允许自动删除用户字段。
- 不允许写入 API Key。
- 不允许生成执行链路。
- 不允许修改 Runtime 配置。
- 不允许把自己写成数字居民大脑。
"""


class StudioAssistantRequest(BaseModel):
    canvas_id: Optional[str] = None
    layer_id: Optional[str] = None
    module_id: Optional[str] = None
    node_id: Optional[str] = None
    field_key: Optional[str] = None
    selected_text: Optional[str] = None
    mode: AssistantMode
    context: Dict[str, Any] = Field(default_factory=dict)


class StudioAssistantPatch(BaseModel):
    target_field: str = ""
    proposed_value: Any = ""


class StudioAssistantResponse(BaseModel):
    ok: bool
    provider: str = ""
    model: str = ""
    mode: AssistantMode
    summary: str = ""
    suggestions: List[Any] = Field(default_factory=list)
    warnings: List[Any] = Field(default_factory=list)
    patch: Optional[StudioAssistantPatch] = None
    requires_user_confirm: bool = True
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


def studio_assistant_enabled() -> bool:
    return load_studio_assistant_config().enabled


def _action_instruction(mode: AssistantMode) -> str:
    if mode == "explain":
        return "解释当前字段、节点或模块的用途、逻辑和边界。patch 通常留空。"
    if mode == "recommend":
        return "根据上下文推荐当前字段填写。只有在目标字段明确时给出 patch.target_field 和 patch.proposed_value。"
    if mode == "audit":
        return "审核当前模块内容是否缺字段、越界、冲突或不稳定。除非用户明确要求，不要给大面积改写 patch。"
    return "检查跨层冲突，重点关注身份、城市、语言、关系边界、记忆边界是否漂移。"


def _request_prompt(request: StudioAssistantRequest) -> str:
    payload = {
        "mode": request.mode,
        "action_instruction": _action_instruction(request.mode),
        "canvas_id": request.canvas_id,
        "layer_id": request.layer_id,
        "module_id": request.module_id,
        "node_id": request.node_id,
        "field_key": request.field_key,
        "selected_text": request.selected_text,
        "context": request.context,
        "required_output_schema": {
            "summary": "string",
            "suggestions": ["string or object"],
            "warnings": ["string or object"],
            "patch": {"target_field": "string", "proposed_value": "string or object"},
            "diagnostics": {"notes": "object"},
        },
    }
    return json.dumps(payload, ensure_ascii=False, default=str)


def _list_value(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _patch_value(raw_patch: Any, fallback_field: Optional[str]) -> Optional[StudioAssistantPatch]:
    if not isinstance(raw_patch, dict):
        return None
    target = raw_patch.get("target_field") or raw_patch.get("field_key") or fallback_field or ""
    proposed = raw_patch.get("proposed_value")
    if proposed is None:
        proposed = raw_patch.get("value", "")
    if not target and proposed in (None, ""):
        return None
    return StudioAssistantPatch(target_field=str(target), proposed_value=proposed)


def _provider_model(diagnostics: Dict[str, Any]) -> tuple[str, str]:
    config = load_studio_assistant_config()
    return str(diagnostics.get("provider") or config.provider), str(diagnostics.get("model") or config.model)


def _normalize_success(request: StudioAssistantRequest, content: Dict[str, Any], diagnostics: Dict[str, Any]) -> StudioAssistantResponse:
    content_diagnostics = content.get("diagnostics")
    merged_diagnostics = {
        **diagnostics,
        **(content_diagnostics if isinstance(content_diagnostics, dict) else {}),
        "status": "ok",
    }
    provider, model = _provider_model(merged_diagnostics)
    return StudioAssistantResponse(
        ok=True,
        provider=provider,
        model=model,
        mode=request.mode,
        summary=str(content.get("summary") or ""),
        suggestions=_list_value(content.get("suggestions")),
        warnings=_list_value(content.get("warnings")),
        patch=_patch_value(content.get("patch"), request.field_key),
        requires_user_confirm=True,
        diagnostics=merged_diagnostics,
    )


def _structured_error(request: StudioAssistantRequest, code: str, message: str, diagnostics: Optional[Dict[str, Any]] = None) -> StudioAssistantResponse:
    provider, model = _provider_model(diagnostics or {})
    return StudioAssistantResponse(
        ok=False,
        provider=provider,
        model=model,
        mode=request.mode,
        summary=message,
        suggestions=[],
        warnings=[message],
        patch=None,
        requires_user_confirm=True,
        diagnostics={"status": code, **(diagnostics or {})},
    )


def run_studio_assistant(
    request: StudioAssistantRequest,
    *,
    client: Optional[StudioAssistantLLMClient] = None,
) -> StudioAssistantResponse:
    assistant_client = client or StudioAssistantLLMClient()
    result = assistant_client.complete_json(system_prompt=SYSTEM_PROMPT, user_prompt=_request_prompt(request))
    diagnostics = result.get("diagnostics") if isinstance(result.get("diagnostics"), dict) else {}
    if not result.get("ok"):
        error = result.get("error") if isinstance(result.get("error"), dict) else {}
        return _structured_error(
            request,
            str(error.get("code") or "assistant_llm_error"),
            str(error.get("message") or "Assistant LLM request failed"),
            diagnostics,
        )

    content = result.get("content")
    if not isinstance(content, dict):
        return _structured_error(request, "invalid_assistant_output", "Assistant output was not structured JSON", diagnostics)
    return _normalize_success(request, content, diagnostics)
