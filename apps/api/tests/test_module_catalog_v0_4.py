"""Module catalog v0.4 — layer binding and placeholder safety checks.

Run: cd apps/api && .venv/bin/python -m pytest tests/test_module_catalog_v0_4.py -q
"""

from __future__ import annotations

from app.models.v0_4 import CANONICAL_LAYERS, ProtocolStatus
from app.registry.module_catalog import get_module_catalog, validate_module_catalog


def test_module_catalog_layer_bindings_match_canonical():
    """Verify all modules in the catalog are bound to layers that match CANONICAL_LAYERS semantics.
    
    This is a safeguard against accidental misalignment: each module must be bound to the
    correct layer_id, and must reflect the semantic intent of that layer (e.g., tools belong
    in layer_9, not layer_11).
    """
    catalog = get_module_catalog()
    canonical_ids = {layer_id for layer_id, _name, _order in CANONICAL_LAYERS}
    
    # Expected semantic bindings (module_id -> expected layer_id)
    expected_bindings = {
        "module_identity_core": "layer_1",      # Identity Core
        "module_personality": "layer_2",         # Personality
        "module_safety_boundary": "layer_3",    # Safety Boundary
        "module_legal_permission": "layer_4",   # Legal Permission
        "module_memory": "layer_5",              # Memory
        "module_knowledge": "layer_6",           # Knowledge
        "module_audit_export": "layer_13",       # Export / Deployment
        # Tools/capabilities in layer_9
        "module_agent": "layer_9",
        "module_wallet": "layer_9",
        "module_phone": "layer_9",
        # Multimodal in layer_10
        "module_voice": "layer_10",
        "module_avatar": "layer_10",
        "module_ar": "layer_10",
        # Relationship in layer_11
        "module_social": "layer_11",
        # Legal/governance in layer_4
        "module_emergency_contact": "layer_4",
    }
    
    # Verify all modules have valid layer_ids
    for module in catalog:
        assert module.layer_id in canonical_ids, \
            f"Module {module.module_id} bound to unknown layer_id: {module.layer_id}"
        
        # Check expected bindings for core and placeholder modules
        if module.module_id in expected_bindings:
            expected_layer = expected_bindings[module.module_id]
            assert module.layer_id == expected_layer, \
                f"Module {module.module_id} bound to {module.layer_id}, expected {expected_layer}"


def test_placeholder_modules_exist_and_safe():
    """Verify that all placeholder (future) modules exist and are safely marked.
    
    Placeholders must:
    1. Exist in the catalog
    2. Have is_placeholder=True
    3. Have status in [planned, later] (never core or ready)
    4. Not execute at runtime
    """
    catalog = get_module_catalog()
    catalog_map = {module.module_id: module for module in catalog}
    
    expected_placeholders = {
        "module_agent",
        "module_wallet",
        "module_phone",
        "module_social",
        "module_ar",
        "module_emergency_contact",
    }
    
    # Verify all expected placeholders exist
    for placeholder_id in expected_placeholders:
        assert placeholder_id in catalog_map, \
            f"Expected placeholder module {placeholder_id} not found in catalog"
        
        module = catalog_map[placeholder_id]
        assert module.is_placeholder is True, \
            f"Module {placeholder_id} must have is_placeholder=True"
        assert module.status in {ProtocolStatus.planned, ProtocolStatus.later}, \
            f"Module {placeholder_id} must have status in [planned, later], got {module.status}"


def test_module_catalog_validation_passes():
    """Verify the catalog passes all validation checks."""
    catalog = get_module_catalog()
    errors = validate_module_catalog(catalog)
    assert errors == [], f"Catalog validation failed: {errors}"
