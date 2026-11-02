"""Level 2: compromise scenarios and the metrics V, R, S, B and C_VR.

V_s  = P(target compromised)           = pre * P(at least one route succeeds) * post
R_s  = P(>= 1 role-valid route usable) = 1 - prod(1 - prod(graph-transition probabilities))
S_s  = 1 - V_s
B_s  = R_s * (1 - V_s)                 (pilot index, within-model only)
C_VR = dV / dR when dR > 0

Alternative routes share the entry condition and the target condition; those factors are
counted once, so routes are conditionally alternative, not fully independent.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .network import Edge, Network
from .params import DERIVED, ROLE_TO_PARAM, SCENARIOS
from .reach import ROUTE_RELATIONS


@dataclass
class Route:
    nodes: list[str]
    edges: list[Edge]

    @property
    def intermediates(self) -> list[str]:
        return self.nodes[1:-1]

    def text(self) -> str:
        parts = [self.nodes[0]]
        for e, n in zip(self.edges, self.nodes[1:]):
            parts.append(f"-{e.edge_id}-> {n}")
        return " ".join(parts)


def cond(params: dict, cid: str) -> float:
    if cid in DERIVED:
        a, b = DERIVED[cid]
        return 1 - (1 - params[a]) * (1 - params[b])
    return params[cid]


def find_routes(net: Network, spec: dict, max_edges: int = 3) -> list[Route]:
    """All simple role-valid routes start -> target over accesses/administers edges."""
    adj: dict[str, list[tuple[str, Edge]]] = {}
    for e in net.edges:
        if e.relation_type in ROUTE_RELATIONS and e.access_roles in spec["roles"]:
            for a, b in e.directed():
                adj.setdefault(a, []).append((b, e))
    routes: list[Route] = []

    def dfs(node, nodes, edges):
        if node == spec["target"]:
            routes.append(Route(list(nodes), list(edges)))
            return
        if len(edges) >= max_edges:
            return
        for nxt, e in adj.get(node, ()):
            if nxt not in nodes:
                dfs(nxt, nodes + [nxt], edges + [e])

    if spec["start"] in net.nodes and spec["target"] in net.nodes:
        dfs(spec["start"], [spec["start"]], [])
    return routes


def graph_prob(route: Route, params: dict) -> float:
    p = 1.0
    for e in route.edges:
        p *= params[ROLE_TO_PARAM[e.access_roles]]
    return p


@dataclass
class Result:
    scenario_id: str
    version: str
    name: str
    routes: list[Route]
    V: float
    R: float
    pre: float = 1.0
    post: float = 1.0
    route_cond: list[float] = field(default_factory=list)
    route_graph: list[float] = field(default_factory=list)

    @property
    def S(self) -> float:
        return 1 - self.V

    @property
    def B(self) -> float:
        return self.R * (1 - self.V)


def evaluate(net: Network, sid: str, params: dict, spec: dict | None = None) -> Result:
    spec = spec or SCENARIOS[sid]
    routes = find_routes(net, spec)
    pre = 1.0
    for c in spec["pre"]:
        pre *= cond(params, c)
    post = 1.0
    for c in spec["post"]:
        post *= cond(params, c)
    graph, full = [], []
    for r in routes:
        g = graph_prob(r, params)
        c = 1.0
        for n in r.nodes:
            for cid in spec["node_conditions"].get(n, ()):
                c *= cond(params, cid)
        graph.append(g)
        full.append(g * c)
    miss_v = miss_r = 1.0
    for g, f in zip(graph, full):
        miss_v *= 1 - f
        miss_r *= 1 - g
    V = pre * (1 - miss_v) * post if routes else 0.0
    R = (1 - miss_r) if routes else 0.0
    return Result(sid, net.version, spec["name"], routes, V, R, pre, post, full, graph)


def compare(base: Result, corr: Result) -> dict:
    dV, dR, dB = corr.V - base.V, corr.R - base.R, corr.B - base.B
    unchanged = abs(dR) < 1e-12 and abs(dV) < 1e-12
    return {
        "scenario": base.scenario_id, "name": base.name,
        "routes": f"{len(base.routes)} -> {len(corr.routes)}",
        "V_base": base.V, "V_corr": corr.V, "dV": dV,
        "R_base": base.R, "R_corr": corr.R, "dR": dR,
        "B_base": base.B, "B_corr": corr.B, "dB": dB,
        "rel_dV": dV / base.V if base.V else 0.0,
        "C_VR": dV / dR if dR > 1e-12 else None,
        "tradeoff": "unchanged" if unchanged else
                    "balance_improved" if dB > 0 else "balance_worsened",
    }
