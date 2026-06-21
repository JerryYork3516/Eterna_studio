"""Enum definitions — Contract §1."""

from __future__ import annotations

from enum import Enum


class NodeType(str, Enum):
    input = "input"
    transform = "transform"
    model = "model"
    agent = "agent"
    review = "review"
    layer_container = "layer_container"
    output = "output"
    export = "export"


class NodeCategory(str, Enum):
    source = "source"
    processing = "processing"
    ai = "ai"
    control = "control"
    container = "container"
    sink = "sink"


class LockLevel(str, Enum):
    editable = "editable"
    review_required = "review_required"
    locked = "locked"
    system_locked = "system_locked"
    mixed = "mixed"  # M2: only valid on layer_container


class ReviewScope(str, Enum):
    node = "node"
    layer = "layer"
    package = "package"


class ReviewStatus(str, Enum):
    pending = "pending"
    passed = "passed"
    warning = "warning"
    failed = "failed"


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    warning = "warning"
    error = "error"
    skipped = "skipped"


class ChangeApprovalStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class ModuleTier(str, Enum):  # V7
    core = "core"      # 核心必需：缺失=error，为空=warning
    plugin = "plugin"  # 可插拔：  缺失=warning，为空=ok
    later = "later"    # 后期补充：缺失=ok，为空=ok
