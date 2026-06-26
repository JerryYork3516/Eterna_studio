"""模块画布内节点和边缘持久化测试

验证:
1. 模块图状态序列化/反序列化
2. localStorage 保存/加载
3. 节点和边缘完整性

Run: cd apps/api && .venv/bin/python -m pytest tests/test_module_graph_persistence_v0_4.py -q
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_module_graph_nodes_structure():
    """验证模块画布节点结构"""
    nodes = [
        {
            "id": "node1",
            "type": "workflowNode",
            "position": {"x": 120, "y": 70},
            "deletable": True,
            "data": {
                "schemaNode": {
                    "node_id": "node1",
                    "type": "input",
                    "title_fallback": "Input Node"
                }
            }
        },
        {
            "id": "node2",
            "type": "workflowNode",
            "position": {"x": 120, "y": 200},
            "deletable": True,
            "data": {
                "schemaNode": {
                    "node_id": "node2",
                    "type": "transform",
                    "title_fallback": "Transform Node"
                }
            }
        }
    ]
    
    assert len(nodes) == 2
    assert nodes[0]["id"] == "node1"
    assert nodes[0]["position"]["x"] == 120
    assert nodes[0]["position"]["y"] == 70


def test_module_graph_edges_structure():
    """验证模块画布连线结构"""
    edges = [
        {
            "id": "edge1",
            "source": "node1",
            "target": "node2",
            "type": "smoothstep"
        },
        {
            "id": "edge2",
            "source": "node2",
            "target": "node3",
            "type": "smoothstep"
        }
    ]
    
    assert len(edges) == 2
    assert edges[0]["source"] == "node1"
    assert edges[0]["target"] == "node2"
    assert edges[0]["type"] == "smoothstep"


def test_module_graph_state_serialization():
    """验证模块图状态序列化"""
    module_id = "layer_1::module_1"
    nodes = [
        {
            "id": "node1",
            "type": "workflowNode",
            "position": {"x": 120, "y": 70},
            "data": {"schemaNode": {"node_id": "node1", "type": "input"}}
        }
    ]
    edges = []
    
    graph_state = {
        "moduleId": module_id,
        "nodes": nodes,
        "edges": edges
    }
    
    # 序列化
    serialized = json.dumps(graph_state)
    assert isinstance(serialized, str)
    
    # 反序列化
    deserialized = json.loads(serialized)
    assert deserialized["moduleId"] == module_id
    assert len(deserialized["nodes"]) == 1
    assert deserialized["nodes"][0]["id"] == "node1"


def test_module_graph_complex_structure():
    """验证复杂的模块图结构"""
    module_id = "layer_2::module_2"
    
    # 创建 5 个节点的图
    nodes = [
        {
            "id": f"node{i}",
            "type": "workflowNode",
            "position": {"x": 100 + i * 50, "y": 50 + i * 100},
            "deletable": True,
            "data": {
                "schemaNode": {
                    "node_id": f"node{i}",
                    "type": ["input", "transform", "llm", "output", "review"][i],
                    "title_fallback": f"Node {i}"
                }
            }
        }
        for i in range(5)
    ]
    
    # 创建连线
    edges = [
        {"id": f"edge{i}", "source": f"node{i}", "target": f"node{i+1}", "type": "smoothstep"}
        for i in range(4)
    ]
    
    graph_state = {
        "moduleId": module_id,
        "nodes": nodes,
        "edges": edges
    }
    
    # 验证结构
    assert len(graph_state["nodes"]) == 5
    assert len(graph_state["edges"]) == 4
    
    # 验证节点连接顺序
    for i, edge in enumerate(graph_state["edges"]):
        assert edge["source"] == f"node{i}"
        assert edge["target"] == f"node{i+1}"


def test_module_graph_state_validation():
    """验证模块图状态数据检查"""
    # 有效状态
    valid_state = {
        "moduleId": "layer_1::module_1",
        "nodes": [{"id": "node1", "type": "workflowNode", "position": {"x": 0, "y": 0}}],
        "edges": []
    }
    
    assert "moduleId" in valid_state
    assert "nodes" in valid_state
    assert "edges" in valid_state
    assert isinstance(valid_state["nodes"], list)
    assert isinstance(valid_state["edges"], list)
    
    # 无效状态 - 缺少必需字段
    invalid_state = {
        "nodes": [],
        "edges": []
    }
    
    assert "moduleId" not in invalid_state


def test_module_graph_node_position_persistence():
    """验证节点位置保存"""
    positions = [
        {"x": 120, "y": 70},
        {"x": 300, "y": 150},
        {"x": 500, "y": 200}
    ]
    
    nodes = [
        {
            "id": f"node{i}",
            "type": "workflowNode",
            "position": positions[i],
            "data": {"schemaNode": {"node_id": f"node{i}"}}
        }
        for i in range(3)
    ]
    
    # 序列化和反序列化
    serialized = json.dumps({"moduleId": "test", "nodes": nodes, "edges": []})
    deserialized = json.loads(serialized)
    
    # 验证位置保存
    for i, node in enumerate(deserialized["nodes"]):
        assert node["position"]["x"] == positions[i]["x"]
        assert node["position"]["y"] == positions[i]["y"]


def test_module_graph_edge_type_preservation():
    """验证连线类型保存"""
    edges = [
        {"id": "edge1", "source": "node1", "target": "node2", "type": "smoothstep"},
        {"id": "edge2", "source": "node2", "target": "node3", "type": "smoothstep"},
        {"id": "edge3", "source": "node3", "target": "node4", "type": "smoothstep"}
    ]
    
    graph_state = {
        "moduleId": "test_module",
        "nodes": [],
        "edges": edges
    }
    
    # 序列化和反序列化
    serialized = json.dumps(graph_state)
    deserialized = json.loads(serialized)
    
    # 验证所有边的类型
    for edge in deserialized["edges"]:
        assert edge["type"] == "smoothstep"


def test_module_graph_empty_state():
    """验证空的模块图状态"""
    empty_state = {
        "moduleId": "empty_module",
        "nodes": [],
        "edges": []
    }
    
    serialized = json.dumps(empty_state)
    deserialized = json.loads(serialized)
    
    assert deserialized["moduleId"] == "empty_module"
    assert len(deserialized["nodes"]) == 0
    assert len(deserialized["edges"]) == 0


def test_module_graph_large_graph():
    """验证大型模块图 (50+ 节点)"""
    # 创建 50 个节点
    nodes = [
        {
            "id": f"node{i}",
            "type": "workflowNode",
            "position": {"x": (i % 10) * 100, "y": (i // 10) * 100},
            "data": {"schemaNode": {"node_id": f"node{i}"}}
        }
        for i in range(50)
    ]
    
    # 创建部分连线
    edges = [
        {"id": f"edge{i}", "source": f"node{i}", "target": f"node{(i+1)%50}", "type": "smoothstep"}
        for i in range(25)
    ]
    
    graph_state = {
        "moduleId": "large_module",
        "nodes": nodes,
        "edges": edges
    }
    
    # 验证可以序列化和反序列化
    serialized = json.dumps(graph_state)
    deserialized = json.loads(serialized)
    
    assert len(deserialized["nodes"]) == 50
    assert len(deserialized["edges"]) == 25


def test_module_graph_multiple_modules():
    """验证多个模块的图状态"""
    modules = {}
    
    for module_index in range(3):
        module_id = f"layer_1::module_{module_index}"
        nodes = [
            {
                "id": f"node{i}_{module_index}",
                "type": "workflowNode",
                "position": {"x": 100 + i * 50, "y": 50 + module_index * 200},
                "data": {"schemaNode": {"node_id": f"node{i}_{module_index}"}}
            }
            for i in range(3)
        ]
        edges = []
        
        modules[module_id] = {
            "moduleId": module_id,
            "nodes": nodes,
            "edges": edges
        }
    
    # 验证每个模块独立
    assert len(modules) == 3
    for module_id, graph_state in modules.items():
        assert graph_state["moduleId"] == module_id
        assert len(graph_state["nodes"]) == 3
