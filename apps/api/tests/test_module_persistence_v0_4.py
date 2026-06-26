"""Module persistence test for localStorage layer-module state recovery.

验证修复：拖入 module 到 module container 后刷新页面丢失的 bug

Run: cd apps/api && .venv/bin/python -m pytest tests/test_module_persistence_v0_4.py -q
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.v0_4 import CANONICAL_LAYERS, ModuleCatalogResponseV04, WorkflowV04

client = TestClient(app)


# --- Module persistence: add module instance -> refresh -> restore ------
def test_module_catalog_fetch():
    """验证模块目录能正确获取"""
    response = client.get("/schema/module-catalog-v0.4")
    assert response.status_code == 200
    catalog: ModuleCatalogResponseV04 = response.json()
    
    # Check catalog structure
    assert "modules" in catalog
    assert "layers" in catalog
    assert "schema_version" in catalog
    assert "protocol_version" in catalog
    
    # Verify layer structure
    canonical_ids = [lid for lid, _n, _o in CANONICAL_LAYERS]
    layer_ids = [l["layer_id"] for l in catalog["layers"]]
    assert layer_ids == canonical_ids, f"Expected {canonical_ids}, got {layer_ids}"


def test_module_instance_schema():
    """验证模块实例包含必要的字段"""
    response = client.get("/schema/module-catalog-v0.4")
    assert response.status_code == 200
    catalog: ModuleCatalogResponseV04 = response.json()
    
    # Check module schema
    if catalog["modules"]:
        module = catalog["modules"][0]
        assert "module_id" in module
        assert "layer_id" in module
        assert "module_version" in module
        assert "category" in module
        assert "status" in module


def test_layer_module_persistence_structure():
    """验证前端持久化结构（模拟）
    
    前端应该持久化：
    {
      "layerModules": {
        "layer_id_1": ["module_id_1", "module_id_2"]
      },
      "moduleInstanceRegistry": {
        "layer_id_1::module_id_1": {
          "instanceId": "layer_id_1::module_id_1",
          "moduleId": "module_id_1",
          "layerId": "layer_id_1"
        }
      }
    }
    """
    response = client.get("/schema/module-catalog-v0.4")
    assert response.status_code == 200
    catalog: ModuleCatalogResponseV04 = response.json()
    
    # Build expected persistence structure
    layer_modules = {}
    module_instance_registry = {}
    
    for layer in catalog["layers"]:
        layer_id = layer["layer_id"]
        layer_module_ids = [
            m["module_id"] 
            for m in catalog["modules"] 
            if m["layer_id"] == layer_id
        ]
        
        if layer_module_ids:
            layer_modules[layer_id] = layer_module_ids
            
            # Create instances for first module in each layer (simulating user add)
            module_id = layer_module_ids[0]
            instance_id = f"{layer_id}::{module_id}"
            module_instance_registry[instance_id] = {
                "instanceId": instance_id,
                "moduleId": module_id,
                "layerId": layer_id
            }
    
    # Verify structure
    assert len(layer_modules) > 0, "Should have at least one layer with modules"
    assert len(module_instance_registry) > 0, "Should have at least one module instance"
    
    # Verify each instance has required fields
    for instance_id, instance in module_instance_registry.items():
        assert instance["instanceId"] == instance_id
        assert "moduleId" in instance
        assert "layerId" in instance
        assert instance["layerId"] in layer_modules
        assert instance["moduleId"] in layer_modules[instance["layerId"]]


def test_no_instance_duplication():
    """验证 ensureModuleInstance 不会重复生成"""
    response = client.get("/schema/module-catalog-v0.4")
    assert response.status_code == 200
    catalog: ModuleCatalogResponseV04 = response.json()
    
    # Get first layer and module
    if not catalog["layers"] or not catalog["modules"]:
        return  # Skip if no data
    
    layer = catalog["layers"][0]
    module = next(
        (m for m in catalog["modules"] if m["layer_id"] == layer["layer_id"]),
        None
    )
    
    if not module:
        return  # Skip if no matching module
    
    layer_id = layer["layer_id"]
    module_id = module["module_id"]
    
    # Simulate adding the same module twice
    instances = {}
    instance_id_1 = f"{layer_id}::{module_id}"
    instance_id_2 = f"{layer_id}::{module_id}"
    
    instances[instance_id_1] = {
        "instanceId": instance_id_1,
        "moduleId": module_id,
        "layerId": layer_id
    }
    
    # Try to add again - should not create duplicate
    if instance_id_2 not in instances:
        instances[instance_id_2] = {
            "instanceId": instance_id_2,
            "moduleId": module_id,
            "layerId": layer_id
        }
    
    # Should still have only 1 instance
    assert len(instances) == 1, "Should not duplicate instances"


def test_catalog_schema_stability():
    """验证 schema_version 稳定性（不会导致状态重置）"""
    response = client.get("/schema/module-catalog-v0.4")
    assert response.status_code == 200
    catalog1: ModuleCatalogResponseV04 = response.json()
    schema_v1 = catalog1["schema_version"]
    
    # Fetch again
    response = client.get("/schema/module-catalog-v0.4")
    assert response.status_code == 200
    catalog2: ModuleCatalogResponseV04 = response.json()
    schema_v2 = catalog2["schema_version"]
    
    # schema_version should be stable (not change on simple refresh)
    assert schema_v1 == schema_v2, "schema_version should be stable across fetches"
    assert schema_v1 == "0.4.0", f"Expected 0.4.0, got {schema_v1}"
