"""Studio Field Assistant service.

This service is Studio-only. It does not import or call Runtime providers,
engines, slots, provider registries, execution engines, or DR compiler code.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .studio_assistant_deepseek_client import StudioAssistantDeepSeekClient, env_flag

AssistantMode = Literal["explain", "recommend", "audit", "check_conflicts"]

SYSTEM_PROMPT = """你是 Eterna Studio 的字段填写与审核助手。
你只辅助 Studio 配置，不参与 Runtime 执行。
不要生成 Runtime、Provider、Slot、Engine 代码。
不要建议把 API Key 写入前端、Canvas 或 DR。
不要硬编码居民姓名到非 Layer 1。
只输出结构化建议。
任何修改必须用户确认。
优先保持身份稳定、边界稳定、语言稳定、记忆稳定。

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
    mode: AssistantMode
    summary: str = ""
    suggestions: List[Any] = Field(default_factory=list)
    warnings: List[Any] = Field(default_factory=list)
    patch: Optional[StudioAssistantPatch] = None
    requires_user_confirm: bool = True
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


def studio_assistant_enabled() -> bool:
    return env_flag("STUDIO_ASSISTANT_ENABLED", default=True)


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


def _normalize_success(request: StudioAssistantRequest, content: Dict[str, Any], diagnostics: Dict[str, Any]) -> StudioAssistantResponse:
    content_diagnostics = content.get("diagnostics")
    merged_diagnostics = {
        **diagnostics,
        **(content_diagnostics if isinstance(content_diagnostics, dict) else {}),
        "status": "ok",
    }
    return StudioAssistantResponse(
        ok=True,
        mode=request.mode,
        summary=str(content.get("summary") or ""),
        suggestions=_list_value(content.get("suggestions")),
        warnings=_list_value(content.get("warnings")),
        patch=_patch_value(content.get("patch"), request.field_key),
        requires_user_confirm=True,
        diagnostics=merged_diagnostics,
    )


def _structured_error(request: StudioAssistantRequest, code: str, message: str, diagnostics: Optional[Dict[str, Any]] = None) -> StudioAssistantResponse:
    return StudioAssistantResponse(
        ok=False,
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
    client: Optional[StudioAssistantDeepSeekClient] = None,
) -> StudioAssistantResponse:
    if not studio_assistant_enabled():
        return _structured_error(
            request,
            "disabled",
            "Studio Assistant is disabled by STUDIO_ASSISTANT_ENABLED=false",
            {"enabled": False},
        )

    assistant_client = client or StudioAssistantDeepSeekClient()
    result = assistant_client.complete_json(system_prompt=SYSTEM_PROMPT, user_prompt=_request_prompt(request))
    diagnostics = result.get("diagnostics") if isinstance(result.get("diagnostics"), dict) else {}
    if not result.get("ok"):
        error = result.get("error") if isinstance(result.get("error"), dict) else {}
        return _structured_error(
            request,
            str(error.get("code") or "deepseek_error"),
            str(error.get("message") or "DeepSeek request failed"),
            diagnostics,
        )

    content = result.get("content")
    if not isinstance(content, dict):
        return _structured_error(request, "invalid_assistant_output", "Assistant output was not structured JSON", diagnostics)
    return _normalize_success(request, content, diagnostics)

