"""Orchestration: load both networks, run scenarios, sensitivity and stress tests."""
from __future__ import annotations

from pathlib import Path

from .compromise import compare, evaluate
from .failure import stress_table
from .network import load_network
from .params import FAILURE_STATES, PARAMETER_SETS, SCENARIOS
from .reach import PROFILES, analyse_profile

DATA = Path(__file__).resolve().parent.parent / "data"


def load_both(baseline=None, corrected=None):
    return (load_network(baseline or DATA / "baseline.xlsx", "Baseline"),
            load_network(corrected or DATA / "corrected.xlsx", "Corrected"))


def reachability(base, corr) -> list[dict]:
    rows = []
    for net in (base, corr):
        for profile in PROFILES:
            r = analyse_profile(net, profile)
            rows.append({
                "version": net.version, "profile": profile, "start": r["start"],
                "reachable_nodes": r["reachable_nodes"],
                "reached_targets": ", ".join(r["reached_targets"]),
                "unreached_targets": ", ".join(r["unreached_targets"]),
            })
    return rows


def compromise(base, corr, param_set="Base"):
    params = PARAMETER_SETS[param_set]
    b = {s: evaluate(base, s, params) for s in SCENARIOS}
    c = {s: evaluate(corr, s, params) for s in SCENARIOS}
    return b, c, [compare(b[s], c[s]) for s in SCENARIOS]


def sensitivity(base, corr) -> list[dict]:
    rows = []
    for pset in PARAMETER_SETS:
        _, _, comp = compromise(base, corr, pset)
        for r in comp:
            rows.append({"parameter_set": pset, **r})
    return rows


def robustness(sens_rows: list[dict]) -> dict:
    changed = [r for r in sens_rows if r["routes"].split(" -> ")[0] != r["routes"].split(" -> ")[1]]
    unchanged = [r for r in sens_rows if r not in changed]
    rel = [r["rel_dV"] for r in changed]
    return {
        "pair_results": len(sens_rows),
        "changed_pair_results": len(changed),
        "dV_positive": sum(r["dV"] > 0 for r in changed),
        "dB_positive": sum(r["dB"] > 0 for r in changed),
        "unchanged_all_zero": all(abs(r["dV"]) < 1e-12 for r in unchanged),
        "min_rel_increase": min(rel) if rel else None,
        "max_rel_increase": max(rel) if rel else None,
        "robust": bool(changed) and all(r["dV"] > 0 and r["dB"] > 0 for r in changed),
    }


def failure(base, corr, param_set="Base") -> list[dict]:
    b, c, _ = compromise(base, corr, param_set)
    keep = [s for s in SCENARIOS if len(c[s].routes) != len(b[s].routes)]  # scenarios changed by the correction
    b = {s: b[s] for s in keep}
    c = {s: c[s] for s in keep}
    return stress_table(base, corr, b, c, PARAMETER_SETS[param_set])


def failure_summary(rows: list[dict]) -> list[dict]:
    out = []
    for state, fs in FAILURE_STATES.items():
        sel = [r for r in rows if r["state"] == state]
        def avg(version, key):
            v = [r[key] for r in sel if r["version"] == version]
            return sum(v) / len(v) if v else 0.0
        out.append({
            "state": state, "name": fs["name"],
            "R_base": avg("Baseline", "R"), "R_corr": avg("Corrected", "R"),
            "dR": avg("Corrected", "R") - avg("Baseline", "R"),
            "B24_base": avg("Baseline", "B_24h"), "B24_corr": avg("Corrected", "B_24h"),
        })
    return out
