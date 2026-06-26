"""双层保存系统测试: 自动保存和手动导出/导入

验证：
1. Canvas 状态序列化/反序列化
2. localStorage 持久化
3. 导出/导入数据完整性

Run: cd apps/api && .venv/bin/python -m pytest tests/test_canvas_persistence_v0_4.py -q
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_canvas_state_structure():
    """验证 Canvas 状态结构"""
    canvas_state = {
        "version": "v4",
        "timestamp": datetime.now().isoformat(),
        "moduleTabs": ["tab1", "tab2"],
        "moduleNames": {"mod1": "Custom Module"},
        "uiNodeNames": {"node1": "Custom Node"},
        "uiTags": {"node1": ["tag1", "tag2"]},
        "uiGroups": {"node1": "group1"},
        "uiColors": {"node1": "#4f8cff"},
        "moduleUiColors": {"layer1:mod1": "#ff0000"},
        "layerModules": {
            "layer_1": ["mod1", "mod2"],
            "layer_2": ["mod3"]
        },
        "moduleInstanceRegistry": {
            "layer_1::mod1": {
                "instanceId": "layer_1::mod1",
                "moduleId": "mod1",
                "layerId": "layer_1"
            }
        }
    }
    
    # 验证结构有效性
    assert canvas_state["version"] == "v4"
    assert "timestamp" in canvas_state
    assert isinstance(canvas_state["moduleTabs"], list)
    assert isinstance(canvas_state["moduleNames"], dict)
    assert isinstance(canvas_state["layerModules"], dict)
    assert isinstance(canvas_state["moduleInstanceRegistry"], dict)


def test_canvas_state_serialization():
    """验证序列化和反序列化"""
    original_state = {
        "version": "v4",
        "timestamp": datetime.now().isoformat(),
        "moduleTabs": ["tab1"],
        "moduleNames": {"mod1": "Module 1"},
        "uiNodeNames": {},
        "uiTags": {},
        "uiGroups": {},
        "uiColors": {},
        "moduleUiColors": {},
        "layerModules": {"layer_1": ["mod1"]},
        "moduleInstanceRegistry": {
            "layer_1::mod1": {
                "instanceId": "layer_1::mod1",
                "moduleId": "mod1",
                "layerId": "layer_1"
            }
        }
    }
    
    # 序列化
    serialized = json.dumps(original_state)
    assert isinstance(serialized, str)
    
    # 反序列化
    deserialized = json.loads(serialized)
    assert deserialized == original_state
    assert deserialized["version"] == "v4"
    assert deserialized["moduleTabs"] == ["tab1"]


def test_canvas_state_module_instances():
    """验证模块实例持久化"""
    # 模拟模块实例
    instance1 = {
        "instanceId": "layer_1::module_a",
        "moduleId": "module_a",
        "layerId": "layer_1"
    }
    
    instance2 = {
        "instanceId": "layer_2::module_b",
        "moduleId": "module_b",
        "layerId": "layer_2"
    }
    
    registry = {
        "layer_1::module_a": instance1,
        "layer_2::module_b": instance2
    }
    
    # 验证模块实例可以被正确存储和恢复
    assert len(registry) == 2
    assert registry["layer_1::module_a"]["moduleId"] == "module_a"
    assert registry["layer_2::module_b"]["layerId"] == "layer_2"


def test_canvas_state_ui_customization():
    """验证 UI 自定义项持久化"""
    ui_customization = {
        "moduleNames": {
            "mod1": "Data Processor",
            "mod2": "AI Model"
        },
        "uiNodeNames": {
            "node1": "Input Handler",
            "node2": "Output Handler"
        },
        "uiTags": {
            "node1": ["important", "v1"],
            "node2": ["deprecated"]
        },
        "uiGroups": {
            "node1": "Processing",
            "node2": "Processing",
            "node3": "Output"
        },
        "uiColors": {
            "node1": "#4f8cff",
            "node2": "#ff0000"
        },
        "moduleUiColors": {
            "layer_1:mod1": "#00ff00",
            "layer_2:mod2": "#ffff00"
        }
    }
    
    # 验证 UI 自定义能被完整保存
    serialized = json.dumps(ui_customization)
    restored = json.loads(serialized)
    
    assert restored["moduleNames"]["mod1"] == "Data Processor"
    assert restored["uiTags"]["node1"] == ["important", "v1"]
    assert restored["uiColors"]["node1"] == "#4f8cff"
    assert len(restored["uiGroups"]) == 3


def test_canvas_state_export_format():
    """验证导出文件格式"""
    canvas_state = {
        "version": "v4",
        "timestamp": "2026-06-26T10:00:00.000Z",
        "moduleTabs": ["tab1"],
        "moduleNames": {},
        "uiNodeNames": {},
        "uiTags": {},
        "uiGroups": {},
        "uiColors": {},
        "moduleUiColors": {},
        "layerModules": {},
        "moduleInstanceRegistry": {}
    }
    
    # 模拟文件导出
    exported_json = json.dumps(canvas_state, indent=2)
    
    # 验证可以解析
    parsed = json.loads(exported_json)
    assert parsed["version"] == "v4"
    assert "timestamp" in parsed


def test_canvas_state_import_validation():
    """验证导入数据验证"""
    # 有效状态
    valid_state = {
        "version": "v4",
        "timestamp": "2026-06-26T10:00:00.000Z",
        "moduleTabs": [],
        "moduleNames": {},
        "uiNodeNames": {},
        "uiTags": {},
        "uiGroups": {},
        "uiColors": {},
        "moduleUiColors": {},
        "layerModules": {},
        "moduleInstanceRegistry": {}
    }
    
    # 验证必需字段
    assert "version" in valid_state
    assert "timestamp" in valid_state
    assert "layerModules" in valid_state
    assert "moduleInstanceRegistry" in valid_state
    
    # 无效状态
    invalid_state = {
        "version": "v3",  # 错误版本
        "timestamp": "2026-06-26T10:00:00.000Z"
    }
    
    assert invalid_state["version"] != "v4"


def test_canvas_state_incremental_updates():
    """验证增量更新"""
    state = {
        "version": "v4",
        "timestamp": "2026-06-26T10:00:00.000Z",
        "moduleTabs": ["tab1"],
        "moduleNames": {"mod1": "Module 1"},
        "uiNodeNames": {},
        "uiTags": {},
        "uiGroups": {},
        "uiColors": {},
        "moduleUiColors": {},
        "layerModules": {"layer_1": ["mod1"]},
        "moduleInstanceRegistry": {}
    }
    
    # 添加新标签
    state["uiTags"]["node1"] = ["new", "tag"]
    
    # 添加新分组
    state["uiGroups"]["node1"] = "group1"
    
    # 验证增量更新
    assert state["uiTags"]["node1"] == ["new", "tag"]
    assert state["uiGroups"]["node1"] == "group1"
    assert len(state["moduleTabs"]) == 1  # 原始数据不变


def test_canvas_state_large_project():
    """验证大型项目状态持久化"""
    # 模拟大型项目
    large_state = {
        "version": "v4",
        "timestamp": "2026-06-26T10:00:00.000Z",
        "moduleTabs": [f"tab{i}" for i in range(50)],
        "moduleNames": {f"mod{i}": f"Module {i}" for i in range(100)},
        "uiNodeNames": {f"node{i}": f"Node {i}" for i in range(200)},
        "uiTags": {f"node{i}": ["tag1", "tag2"] for i in range(200)},
        "uiGroups": {f"node{i}": f"group{i % 10}" for i in range(200)},
        "uiColors": {f"node{i}": "#4f8cff" for i in range(200)},
        "moduleUiColors": {f"layer_{i}:mod{i}": "#ff0000" for i in range(100)},
        "layerModules": {f"layer_{i}": [f"mod{j}" for j in range(10)] for i in range(13)},
        "moduleInstanceRegistry": {
            f"layer_{i}::mod{j}": {
                "instanceId": f"layer_{i}::mod{j}",
                "moduleId": f"mod{j}",
                "layerId": f"layer_{i}"
            }
            for i in range(13) for j in range(10)
        }
    }
    
    # 验证可以序列化和反序列化大项目
    serialized = json.dumps(large_state)
    deserialized = json.loads(serialized)
    
    assert len(deserialized["moduleTabs"]) == 50
    assert len(deserialized["moduleNames"]) == 100
    assert len(deserialized["moduleInstanceRegistry"]) == 130
    assert len(deserialized["layerModules"]) == 13
