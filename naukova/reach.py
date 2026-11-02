"""Level 1: role-valid reachability (strict role-conditioned subgraphs)."""
from __future__ import annotations

from collections import deque

from .network import Network

# Relation types included in a strict role subgraph (document 30). depends_on, stores_data_on,
# sends_logs_to, backs_up_to, replicates_to and recovers_from are never subject transitions
# (document 47): they only matter for impact and resilience. authenticates_via is part of the
# subgraph for reachability but does not move the same subject (document 41), so compromise
# routes use ROUTE_RELATIONS instead.
TRAVERSABLE = ("network_connection", "authenticates_via", "accesses", "administers")
ROUTE_RELATIONS = ("accesses", "administers")

# Directly included access_roles per actor profile (document 37, "Include" decisions).
PROFILES = {
    "External User": ("N01", {"external_traffic", "public_users"}),
    "Standard Employee": ("N24", {"employees"}),
    "Contractor": ("N26", {"contractors", "employees_and_contractors", "remote_users"}),
    "System Administrator": ("N13", {"infrastructure_admins", "privileged_admins", "system_admins"}),
    "Service Account": ("N20", {"application_agent", "application_service_accounts",
                                "database_agent", "internal_app_service_account"}),
}

TARGETS = ("N10", "N13", "N17", "N22", "N23", "N29")


def role_subgraph(net: Network, roles: set[str], relations=TRAVERSABLE) -> dict[str, list[tuple[str, str]]]:
    """Adjacency {node: [(neighbour, edge_id)]} using only edges whose access_roles is included."""
    adj: dict[str, list[tuple[str, str]]] = {}
    for e in net.edges:
        if e.relation_type in relations and e.access_roles in roles:
            for a, b in e.directed():
                adj.setdefault(a, []).append((b, e.edge_id))
    return adj


def shortest_paths(adj, start: str) -> dict[str, list[str]]:
    """BFS; returns {node: [start, ..., node]} for every reachable node."""
    paths = {start: [start]}
    q = deque([start])
    while q:
        u = q.popleft()
        for v, _ in adj.get(u, ()):
            if v not in paths:
                paths[v] = paths[u] + [v]
                q.append(v)
    return paths


def analyse_profile(net: Network, profile: str, targets=TARGETS) -> dict:
    start, roles = PROFILES[profile]
    adj = role_subgraph(net, roles)
    paths = shortest_paths(adj, start)
    reached = {t: paths[t] for t in targets if t in paths}
    return {
        "version": net.version, "profile": profile, "start": start,
        "reachable_nodes": len(paths),
        "reached_targets": reached,
        "unreached_targets": [t for t in targets if t not in paths],
    }


# ---- 108-scenario matrix: 9 final roles x 6 targets x 2 versions (documents 44, 45, 59) ----
# Role-valid transitions here are accesses/administers only: network_connection gives technical
# reachability and authenticates_via does not move the same subject (documents 41, 47), so neither
# makes a target "reached". Conditional access_roles values are excluded (conservative rule).
ROLES_108 = {
    "External User": ("N01", {"external_traffic", "public_users"}),
    "External API Client": ("N01", {"external_api_clients"}),
    "Standard Employee": ("N24", {"employees"}),
    "Contractor": ("N26", {"contractors", "employees_and_contractors", "remote_users"}),
    "Service Account": ("N20", {"application_agent", "application_service_accounts",
                                "database_agent", "internal_app_service_account"}),
    "Infrastructure Administrator": ("N13", {"system_admins", "infrastructure_admins", "privileged_admins"}),
    "Application Administrator": ("N13", {"privileged_admins", "application_admins"}),
    "Database Administrator": ("N13", {"privileged_admins", "database_admins"}),
    "Backup Operator": ("N13", {"privileged_admins", "backup_operators"}),
}


def role_routes(net: Network, start: str, target: str, roles: set[str], max_edges: int = 4):
    """All simple role-valid routes (list of node lists); [[start]] when target == start."""
    if target == start:
        return [[start]]
    adj: dict[str, list[str]] = {}
    for e in net.edges:
        if e.relation_type in ROUTE_RELATIONS and e.access_roles in roles:
            for a, b in e.directed():
                adj.setdefault(a, []).append(b)
    out = []

    def dfs(path):
        if path[-1] == target:
            out.append(list(path))
            return
        if len(path) > max_edges:
            return
        for nxt in adj.get(path[-1], ()):
            if nxt not in path:
                dfs(path + [nxt])

    dfs([start])
    return out


def matrix_108(base: Network, corr: Network) -> list[dict]:
    rows = []
    for role, (start, roles) in ROLES_108.items():
        for target in TARGETS:
            for net in (base, corr):
                routes = role_routes(net, start, target, roles)
                rows.append({
                    "scenario_id": f"{role.replace(' ', '_')}-{target}-{net.version[0]}",
                    "actor_profile": role, "start": start, "target": target,
                    "version": net.version,
                    "result": "reached" if routes else "not_reached",
                    "route_count": len(routes),
                    "routes": "; ".join(" > ".join(r) for r in routes),
                })
    return rows
