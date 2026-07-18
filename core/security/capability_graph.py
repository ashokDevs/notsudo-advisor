from __future__ import annotations

from dataclasses import dataclass

# Node identity → tools it may invoke.
# Side-effecting tools MUST only be granted to draft_pr / act.
TOOL_PERMISSIONS: dict[str, frozenset[str]] = {
    "triage": frozenset(
        {
            "advisory_query",
            "dep_manifest_read",
            "check_vulnerable_dependency",
            "dep_registry_query",
        }
    ),
    "locate": frozenset(
        {
            "code_search",
            "code_read",
            "locate_call_sites",
            "git_blame",
        }
    ),
    "reason": frozenset(
        {
            "code_search",
            "code_read",
            "locate_call_sites",
        }
    ),
    "critique": frozenset(
        {
            "code_search",
            "code_read",
        }
    ),
    "preflight": frozenset(
        {
            "dep_manifest_read",
            "dep_registry_query",
            "preflight_lockfile",
        }
    ),
    "draft_pr": frozenset(
        {
            "pr_create",
            "dep_manifest_read",
        }
    ),
    "act": frozenset(
        {
            "pr_create",
            "preflight_lockfile",
            "dep_manifest_read",
        }
    ),
}

SIDE_EFFECTING_TOOLS = frozenset({"pr_create"})


@dataclass(frozen=True)
class CapabilityGraph:
    """First-class permission graph for structural isolation tests."""

    permissions: dict[str, frozenset[str]]

    @classmethod
    def from_permissions(
        cls, permissions: dict[str, frozenset[str]] | None = None
    ) -> CapabilityGraph:
        return cls(permissions=dict(permissions or TOOL_PERMISSIONS))

    def nodes_with_permission(self, tool: str) -> set[str]:
        return {node for node, tools in self.permissions.items() if tool in tools}

    def can(self, node: str, tool: str) -> bool:
        return tool in self.permissions.get(node, frozenset())

    def paths_to(self, tool: str) -> list[str]:
        """Return node names that can invoke `tool`."""
        return sorted(self.nodes_with_permission(tool))

    def assert_isolation(self) -> None:
        """
        Structural invariant: only act/draft_pr may call side-effecting tools.
        Nodes that ingest advisory text (triage/locate/reason/critique) must not.
        """
        untrusted_nodes = {"triage", "locate", "reason", "critique"}
        for node in untrusted_nodes:
            tools = self.permissions.get(node, frozenset())
            leak = tools & SIDE_EFFECTING_TOOLS
            if leak:
                raise AssertionError(
                    f"Capability isolation violated: node {node!r} can call {sorted(leak)}"
                )
        allowed = self.nodes_with_permission("pr_create")
        if not allowed.issubset({"act", "draft_pr"}):
            raise AssertionError(f"pr_create granted to unexpected nodes: {allowed}")

    def authorize(self, node: str, tool: str) -> None:
        if not self.can(node, tool):
            raise PermissionError(
                f"Node {node!r} is not permitted to call tool {tool!r}"
            )
