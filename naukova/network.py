"""Loading of the Baseline / Corrected synthetic network from xlsx files."""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


@dataclass(frozen=True)
class Edge:
    edge_id: str
    source: str
    target: str
    relation_type: str
    direction: str
    access_roles: str
    security_controls: str = ""
    dependency_strength: float = 1.0

    def directed(self):
        """Yield (from, to) pairs after expanding bidirectional edges."""
        yield self.source, self.target
        if self.direction == "bidirectional":
            yield self.target, self.source


@dataclass
class Network:
    version: str
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def name(self, node_id: str) -> str:
        return self.nodes[node_id]["node_name"]

    def recovery_hours(self, node_id: str) -> float:
        return float(self.nodes[node_id]["recovery_time_hours"])


def _rows(ws):
    it = ws.iter_rows(values_only=True)
    header = [str(h).strip() for h in next(it)]
    for row in it:
        if row[0] is None:
            continue
        yield dict(zip(header, row))


def load_network(path: str | Path, version: str) -> Network:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    net = Network(version=version)
    for r in _rows(wb["Nodes"]):
        net.nodes[r["node_id"]] = r
    for r in _rows(wb["Edges"]):
        net.edges.append(Edge(
            r["edge_id"], r["source"], r["target"], r["relation_type"],
            r["direction"], str(r["access_roles"]).strip(),
            str(r.get("security_controls") or ""),
            float(r.get("dependency_strength") or 1.0),
        ))
    return net
