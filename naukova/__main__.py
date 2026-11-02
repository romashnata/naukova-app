"""Command line: python -m naukova [--out results.xlsx] [--baseline F] [--corrected F]"""
from __future__ import annotations

import argparse

from . import analysis as an
from .reach import matrix_108


def table(rows: list[dict], cols: list[str], fmt="{:.4f}") -> str:
    def f(v):
        if v is None:
            return "n/a"
        return fmt.format(v) if isinstance(v, float) else str(v)
    cells = [[f(r[c]) for c in cols] for r in rows]
    w = [max(len(c), *(len(x[i]) for x in cells)) for i, c in enumerate(cols)]
    line = lambda xs: "  ".join(x.ljust(w[i]) for i, x in enumerate(xs))
    return "\n".join([line(cols), line(["-" * n for n in w])] + [line(x) for x in cells])


def write_xlsx(path, sheets: dict[str, list[dict]]):
    import openpyxl
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name[:31])
        if rows:
            cols = list(rows[0])
            ws.append(cols)
            for r in rows:
                ws.append([r[c] for c in cols])
    wb.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="naukova", description=__doc__)
    ap.add_argument("--baseline")
    ap.add_argument("--corrected")
    ap.add_argument("--param-set", default="Base", choices=["Low", "Base", "High"])
    ap.add_argument("--out", help="write all result tables to this .xlsx file")
    a = ap.parse_args(argv)

    base, corr = an.load_both(a.baseline, a.corrected)
    print(f"Baseline: {len(base.nodes)} nodes, {len(base.edges)} edges | "
          f"Corrected: {len(corr.nodes)} nodes, {len(corr.edges)} edges\n")

    reach = an.reachability(base, corr)
    print("Level 1 - strict role-valid reachability")
    print(table(reach, ["version", "profile", "start", "reachable_nodes", "reached_targets"]), "\n")

    m108 = matrix_108(base, corr)
    print("Level 1 - matrix of 108 role scenarios (9 roles x 6 targets x 2 versions)")
    reached = [r for r in m108 if r["result"] == "reached"]
    print(f"  reached: {len(reached)} of {len(m108)} "
          f"(Baseline {sum(r['version'] == 'Baseline' for r in reached)}, "
          f"Corrected {sum(r['version'] == 'Corrected' for r in reached)})")
    print(table(reached, ["actor_profile", "target", "version", "route_count", "routes"]), "\n")

    b, c, comp = an.compromise(base, corr, a.param_set)
    print(f"Level 2 - compromise scenarios, parameter set: {a.param_set}")
    for s in c:
        for r in c[s].routes:
            print(f"  {s}-C  {r.text()}")
    print(table(comp, ["scenario", "name", "routes", "V_base", "V_corr", "dV", "R_base", "R_corr",
                       "dR", "B_base", "B_corr", "dB", "C_VR", "tradeoff"]), "\n")

    sens = an.sensitivity(base, corr)
    rob = an.robustness(sens)
    print("Sensitivity (Low / Base / High):")
    print(table(sens, ["parameter_set", "scenario", "V_base", "V_corr", "dV", "rel_dV", "dB"]))
    print("\nRobustness:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rob.items()}, "\n")

    fail = an.failure(base, corr, a.param_set)
    fsum = an.failure_summary(fail)
    print("Failure states (mean over scenarios changed by the correction)")
    print(table(fsum, ["state", "name", "R_base", "R_corr", "dR", "B24_base", "B24_corr"]))
    print("\nNote: all probabilities are synthetic model parameters; 24h values are "
          "time-weighted proxies, not incident probabilities.")

    if a.out:
        write_xlsx(a.out, {"Reachability": reach, "Matrix_108": m108, "Comparison": comp, "Sensitivity": sens,
                           "Failure_States": fail, "Failure_Summary": fsum})
        print(f"\nSaved: {a.out}")


if __name__ == "__main__":
    main()
