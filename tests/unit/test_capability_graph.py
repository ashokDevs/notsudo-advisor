from __future__ import annotations

import pytest

from core.security.capability_graph import SIDE_EFFECTING_TOOLS, TOOL_PERMISSIONS, CapabilityGraph


def test_isolation_invariant() -> None:
    g = CapabilityGraph.from_permissions()
    g.assert_isolation()


def test_pr_create_only_on_act_nodes() -> None:
    g = CapabilityGraph.from_permissions()
    holders = g.nodes_with_permission("pr_create")
    assert holders.issubset({"act", "draft_pr"})
    for node in ("triage", "locate", "reason", "critique"):
        assert not g.can(node, "pr_create")


def test_authorize_denies_side_effect_from_reason() -> None:
    g = CapabilityGraph.from_permissions()
    with pytest.raises(PermissionError):
        g.authorize("reason", "pr_create")


def test_untrusted_nodes_have_no_side_effects() -> None:
    for node in ("triage", "locate", "reason", "critique"):
        tools = TOOL_PERMISSIONS[node]
        assert not (tools & SIDE_EFFECTING_TOOLS)
