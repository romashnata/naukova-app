"""Checks that the program reproduces the reference values in the research package (files 38, 66-72)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from naukova import analysis as an  # noqa: E402
from naukova.reach import analyse_profile, matrix_108  # noqa: E402


class Reproduce(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.corr = an.load_both()

    def test_network_size(self):
        self.assertEqual((len(self.base.nodes), len(self.base.edges)), (30, 153))
        self.assertEqual((len(self.corr.nodes), len(self.corr.edges)), (35, 326))

    def test_strict_reachability_doc38(self):
        expected = {  # (version, profile): (reachable nodes, targets)
            ("Baseline", "Standard Employee"): (7, ["N10"]),
            ("Baseline", "System Administrator"): (8, ["N10", "N13"]),
            ("Corrected", "System Administrator"): (12, ["N10", "N13"]),
            ("Corrected", "External User"): (3, []),
        }
        for (v, p), (n, t) in expected.items():
            net = self.base if v == "Baseline" else self.corr
            r = analyse_profile(net, p)
            self.assertEqual((r["reachable_nodes"], list(r["reached_targets"])), (n, t))

    def test_matrix_108_doc59(self):
        m = matrix_108(self.base, self.corr)
        self.assertEqual(len(m), 108)
        reached = [r for r in m if r["result"] == "reached"]
        self.assertEqual(len(reached), 16)
        for v in ("Baseline", "Corrected"):
            self.assertEqual(sum(r["version"] == v for r in reached), 8)
        cnt = {(r["actor_profile"], r["target"], r["version"]): r["route_count"] for r in reached}
        for role, t in (("Application Administrator", "N17"), ("Database Administrator", "N22"),
                        ("Database Administrator", "N23"), ("Backup Operator", "N29")):
            self.assertEqual((cnt[(role, t, "Baseline")], cnt[(role, t, "Corrected")]), (1, 2))

    def test_metrics_doc68(self):
        _, _, comp = an.compromise(self.base, self.corr, "Base")
        by = {r["scenario"]: r for r in comp}
        self.assertAlmostEqual(by["PC01"]["V_base"], 0.1425)
        self.assertAlmostEqual(by["PC02"]["V_base"], 0.0064125)
        self.assertAlmostEqual(by["PC03"]["V_corr"], 0.06852825)
        self.assertAlmostEqual(by["PC03"]["R_corr"], 0.978975)
        self.assertAlmostEqual(by["PC03"]["B_corr"], 0.9118875564562501)
        self.assertAlmostEqual(by["PC03"]["C_VR"], 0.07)
        self.assertAlmostEqual(by["PC05"]["C_VR"], 0.042)
        self.assertEqual(by["PC03"]["routes"], "1 -> 2")

    def test_sensitivity_doc68(self):
        rob = an.robustness(an.sensitivity(self.base, self.corr))
        self.assertEqual((rob["pair_results"], rob["dV_positive"], rob["dB_positive"]), (15, 9, 9))
        self.assertTrue(rob["robust"] and rob["unchanged_all_zero"])
        self.assertAlmostEqual(rob["min_rel_increase"], 0.0298)
        self.assertAlmostEqual(rob["max_rel_increase"], 0.3625)

    def test_failure_states_doc72(self):
        summ = {r["state"]: r for r in an.failure_summary(an.failure(self.base, self.corr))}
        self.assertAlmostEqual(summ["FS01"]["B24_base"], 0.7493512125)
        self.assertAlmostEqual(summ["FS01"]["B24_corr"], 0.9161005899928125)
        self.assertAlmostEqual(summ["FS04"]["R_corr"], 0.8810775)
        self.assertAlmostEqual(summ["FS10"]["B24_corr"], 0.8031264918934374)
        self.assertTrue(all(r["dR"] >= 0 for r in summ.values()))


if __name__ == "__main__":
    unittest.main()
