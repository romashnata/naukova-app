"""Synthetic parameters of the pilot model (Synthetic v1), taken from documents 62-72.

All values are synthetic model parameters, not empirical frequencies.
"""

# Parameter sets for sensitivity analysis (document 68, Sensitivity_Parameters).
PARAMETER_SETS = {
    "Low": {"P-G01": 0.90, "P-G02": 0.80, "P-G03": 0.75, "P-G04": 0.85,
            "C01": 0.10, "C07": 0.05, "C03": 0.08, "C06": 0.10,
            "C09": 0.15, "C10": 0.08, "C11": 0.10},
    "Base": {"P-G01": 0.95, "P-G02": 0.90, "P-G03": 0.90, "P-G04": 0.95,
             "C01": 0.20, "C07": 0.10, "C03": 0.15, "C06": 0.20,
             "C09": 0.25, "C10": 0.15, "C11": 0.20},
    "High": {"P-G01": 0.99, "P-G02": 0.97, "P-G03": 0.98, "P-G04": 0.99,
             "C01": 0.35, "C07": 0.20, "C03": 0.30, "C06": 0.35,
             "C09": 0.45, "C10": 0.30, "C11": 0.35},
}

# Graph-transition parameter by the access_roles value of the traversed edge.
ROLE_TO_PARAM = {
    "public_users": "P-G01", "external_api_clients": "P-G01",
    "api_service_account": "P-G02",
    "privileged_admins": "P-G03",
    "application_admins": "P-G04", "database_admins": "P-G04", "backup_operators": "P-G04",
}

# Derived condition: independent alternatives, 1 - (1 - C01)(1 - C07).
DERIVED = {"C01_OR_C07": ("C01", "C07")}

# Pilot compromise scenarios (documents 63-65). Each is a Baseline/Corrected pair.
#   roles           access_roles values the actor may use on route edges
#   pre             conditions applied once before any route (shared factor, counted once)
#   node_conditions conditions applied when a route passes through the node
#   post            conditions applied once on the target (shared factor, counted once)
SCENARIOS = {
    "PC01": dict(name="Public Service", start="N01", target="N06",
                 roles={"public_users"}, pre=[], node_conditions={}, post=["C03"]),
    "PC02": dict(name="API Gateway -> Internal App", start="N01", target="N20",
                 roles={"external_api_clients", "api_service_account"}, pre=[],
                 node_conditions={"N09": ["C03", "C06"]}, post=["C09"]),
    "PC03": dict(name="ERP", start="N13", target="N17",
                 roles={"privileged_admins", "application_admins"},
                 pre=["C01_OR_C07"], node_conditions={}, post=["C09"]),
    "PC04": dict(name="HR Database", start="N13", target="N22",
                 roles={"privileged_admins", "database_admins"},
                 pre=["C01_OR_C07"], node_conditions={}, post=["C11"]),
    "PC05": dict(name="Backup Infrastructure", start="N13", target="N29",
                 roles={"privileged_admins", "backup_operators"},
                 pre=["C01_OR_C07"], node_conditions={}, post=["C10"]),
}

# Failure states (document 72, Failure_Assumptions). Factors are synthetic stress parameters.
#   failed       nodes that are down (routes through them are removed)
#   identity/mfa availability factor of the shared service as (Baseline, Corrected)
#   target_down  the scenario target itself is unavailable
#   hours        fixed recovery time; None -> recovery_time_hours of the target node
FAILURE_STATES = {
    "FS00": dict(name="Normal operation", failed=(), identity=(1, 1), mfa=(1, 1), target_down=False, hours=0),
    "FS01": dict(name="Primary Jump Server unavailable", failed=("N14",), identity=(1, 1), mfa=(1, 1), target_down=False, hours=2),
    "FS02": dict(name="Secondary Jump Server unavailable", failed=("N32",), identity=(1, 1), mfa=(1, 1), target_down=False, hours=2),
    "FS03": dict(name="Both Jump Servers unavailable", failed=("N14", "N32"), identity=(1, 1), mfa=(1, 1), target_down=False, hours=2),
    "FS04": dict(name="Primary Identity unavailable", failed=(), identity=(0.5, 0.9), mfa=(1, 1), target_down=False, hours=2),
    "FS05": dict(name="Secondary Identity unavailable", failed=(), identity=(1, 1), mfa=(1, 1), target_down=False, hours=4),
    "FS06": dict(name="Identity layer unavailable", failed=(), identity=(0, 0), mfa=(1, 1), target_down=False, hours=2),
    "FS07": dict(name="Primary MFA unavailable", failed=(), identity=(1, 1), mfa=(0, 0.9), target_down=False, hours=4),
    "FS08": dict(name="Secondary MFA unavailable", failed=(), identity=(1, 1), mfa=(1, 1), target_down=False, hours=4),
    "FS09": dict(name="MFA layer unavailable", failed=(), identity=(1, 1), mfa=(0, 0), target_down=False, hours=4),
    "FS10": dict(name="Target node unavailable", failed=(), identity=(1, 1), mfa=(1, 1), target_down=True, hours=None),
}

HORIZON_HOURS = 24
