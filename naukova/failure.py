"""Failure-state stress test with time-weighted 24 h proxies (document 72).

R_fail = shared_auth_factor * target_availability * P(at least one available role-valid branch)
V_fail = R_fail * (V_normal / R_normal)
B_fail = R_fail * (1 - V_fail)
Values at the horizon are time-weighted exposure proxies (binary stress state until the
recovery time, then normal operation); they are NOT the probability of an incident within 24 h.
"""
from __future__ import annotations

from .compromise import Result, graph_prob
from .network import Network
from .params import FAILURE_STATES, HORIZON_HOURS, PARAMETER_SETS, SCENARIOS


def stress(net: Network, normal: Result, params: dict, state_id: str) -> dict:
    fs = FAILURE_STATES[state_id]
    col = 0 if net.version == "Baseline" else 1
    spec = SCENARIOS[normal.scenario_id]
    shared = fs["identity"][col] * fs["mfa"][col]
    target_ok = 0.0 if fs["target_down"] else 1.0
    miss = 1.0
    for r in normal.routes:
        if not set(r.intermediates) & set(fs["failed"]):
            miss *= 1 - graph_prob(r, params)
    branch = 1 - miss if normal.routes else 0.0
    R = shared * target_ok * branch
    ratio = normal.V / normal.R if normal.R else 0.0
    V = R * ratio
    hours = fs["hours"] if fs["hours"] is not None else net.recovery_hours(spec["target"])
    hours = min(float(hours), HORIZON_HOURS)
    w = (HORIZON_HOURS - hours) / HORIZON_HOURS

    def tw(normal_value, failed_value):
        return w * normal_value + (1 - w) * failed_value

    V24, R24 = tw(normal.V, V), tw(normal.R, R)
    effect = ("no_immediate_effect" if abs(R - normal.R) < 1e-12 else
              "route_unavailable" if R == 0 else "degraded")
    return {
        "state": state_id, "state_name": fs["name"], "scenario": normal.scenario_id,
        "version": net.version, "recovery_hours": hours, "shared_auth_factor": shared,
        "branch_probability": branch, "V": V, "R": R, "B": R * (1 - V),
        "V_24h": V24, "R_24h": R24, "B_24h": R24 * (1 - V24), "effect": effect,
    }


def stress_table(base_net, corr_net, base_results, corr_results, params=None) -> list[dict]:
    params = params or PARAMETER_SETS["Base"]
    rows = []
    for sid in base_results:
        for state in FAILURE_STATES:
            for net, res in ((base_net, base_results[sid]), (corr_net, corr_results[sid])):
                rows.append(stress(net, res, params, state))
    return rows
