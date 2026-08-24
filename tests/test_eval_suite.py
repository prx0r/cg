"""Eval layer: gates, lexicographic, layered suite (ported + verified)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogym_kernel.eval import (LayeredSuite, Objective, QualityGate,
                               gates_pass, lexicographic_compare,
                               non_inferior_paired, run_layered_campaign,
                               wilson)


def test_gate_blocks_cheap_garbage():
    g = QualityGate("accuracy", mode="noninferior", margin=0.005)
    ok, _ = gates_pass.__module__ and __import__("cogym_kernel.eval", fromlist=["check_gate"]).check_gate(
        g, {"accuracy": 0.5}, {"accuracy": 0.9}), True
    from cogym_kernel.eval import check_gate
    r = check_gate(g, {"accuracy": 0.5}, {"accuracy": 0.9})
    assert not r.passed if hasattr(r, "passed") else not r[0]


def test_lexicographic_gates_dominate():
    assert lexicographic_compare({"cash_cost": 0.01}, False,
                                 {"cash_cost": 5.0}, True) == 1


def test_noninferior_paired_honesty():
    base = [0.9] * 30; cand = [0.895] * 30
    res = non_inferior_paired(base, cand, margin=0.005)
    assert res["non_inferior"] is True and res["n_pairs"] == 30
    bad = non_inferior_paired(base, [0.7] * 30, margin=0.005)
    assert bad["non_inferior"] is False


def test_wilson_extremes():
    lo = wilson(0, 10); hi = wilson(10, 10)
    assert lo["hi"] < 0.35 and hi["lo"] > 0.65


def _suite():
    return LayeredSuite(dev=(("d",1),("d",2),("d",3)), validation=(("v",11),),
                        n_secret=2, secret_instance_fn=lambda s: ("s", s))


def test_layered_campaign_promotes_and_fails_closed():
    q = {"good": 10.0, "meh": 2.0}
    rep = run_layered_campaign(list(q),
                               lambda c, L: {"objective": q[c]},
                               lambda m: m["objective"] > 0, None) \
        if False else run_layered_campaign(
            list(q), lambda c, L: {"objective": q[c]},
            _suite(), lambda m: m["objective"] > 0)
    assert rep["status"] == "PROMOTED" and rep["champion"] == "good"
    extinct = run_layered_campaign(["bad"], lambda c, L: {"objective": -1},
                                   _suite(), lambda m: False)
    assert extinct["status"] == "EXTINCT"
