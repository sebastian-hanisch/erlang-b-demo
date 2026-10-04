"""Auswertung: Live-Lauf mit exakten Bezugswerten, Bemessungstabelle, Studienzelle, Vollständigkeit der vorgerechneten Datei."""

import pytest

import erb_constants as C
import erb_evaluation as E
import erb_formulas as F


def test_offer_and_mean_and_se_by_hand():
    assert E.offer(20, 90) == pytest.approx(18.0) and E.offer(10, 130) == pytest.approx(13.0)
    assert E.mean_and_se([1.0, 3.0]) == (2.0, 1.0) and E.mean_and_se([5.0]) == (5.0, None)


def test_nearest_picks_the_closest_option_and_the_smaller_on_a_tie():
    assert E.nearest(C.STUDY_C, 5) == 10 and E.nearest(C.STUDY_C, 30) == 20 and E.nearest(C.STUDY_C, 35) == 20
    assert E.nearest(C.STUDY_RHO_PCT, 90) == 80 and E.nearest(C.STUDY_K, 20) == 10 and E.nearest(C.STUDY_K, 3) == 2


def test_live_report_structure_and_reference_values():
    r = E.live_report(10, 90, 3, "exp", seed=3, customers=8_000)
    assert r["a"] == pytest.approx(9.0) and r["blocking_exact"] == pytest.approx(F.blocking(10, 9.0, 3))
    assert len(r["pi_exact"]) == len(r["pi_sim"]) == 14 and r["wait_exact"] == pytest.approx(F.mean_wait_accepted(10, 9.0, 3))
    assert r["rejected_exact"] == pytest.approx(F.rejected_per_hour(9.0, r["blocking_exact"]))
    assert r["wait_mmc"] == pytest.approx(F.mmc_wait(10, 9.0)) and r["util_exact"] == pytest.approx(F.utilisation(10, 9.0, 3))
    assert r["blocking_sim"] == r["sim"].blocking()


def test_live_report_has_no_unbounded_queue_value_under_overload():
    assert E.live_report(10, 120, 0, "exp", seed=3, customers=4_000)["wait_mmc"] is None


def test_sizing_table_by_hand_and_minimality():
    rows = E.sizing_table((5, 10), (0.01, 0.001))
    assert [(r["a"], r["target"], r["c"]) for r in rows] == [(5, 0.01, 11), (5, 0.001, 14), (10, 0.01, 18), (10, 0.001, 21)]
    assert rows[0]["rho"] == pytest.approx(5 / 11)
    for r in rows:
        assert F.blocking(r["c"], r["a"], 0) <= r["target"] < F.blocking(r["c"] - 1, r["a"], 0)


def test_sizing_with_stellplaetze_needs_fewer_spuren():
    assert E.sizing_table((10,), (0.01,), k=5)[0]["c"] < E.sizing_table((10,), (0.01,), k=0)[0]["c"]


def test_study_cell_run_small_structure():
    cell = E.study_cell_run(10, 100, 2, "exp", 10_000, 5, reps=3)
    assert cell["reps"] == 3 and len(cell["bs"]) == 3 and cell["blocking"] == pytest.approx(sum(cell["bs"]) / 3) and cell["blocking_se"] > 0
    assert cell["blocking_exact"] == pytest.approx(F.blocking(10, 10.0, 2)) and 0 < cell["util"] < 1
    assert E.study_cell_run(10, 100, 0, "det", 4_000, 5, reps=1)["blocking_se"] is None


def test_precomputed_file_is_complete():
    pre = E.load_precomputed()
    keys = {(x["c"], x["rho_pct"], x["k"], x["kind"]) for x in pre["study"]}
    assert keys == {(c, r, k, kd) for c in C.STUDY_C for r in C.STUDY_RHO_PCT for k in C.STUDY_K for kd in C.STUDY_KINDS}
    assert pre["study_customers"] == C.STUDY_CUSTOMERS and pre["study_reps"] == C.STUDY_REPS and pre["warmup_fraction"] == C.WARMUP_FRACTION
    for x in pre["study"]:
        assert x["reps"] == C.STUDY_REPS and x["customers"] == C.STUDY_CUSTOMERS and len(x["bs"]) == C.STUDY_REPS
        assert x["blocking_exact"] == pytest.approx(F.blocking(x["c"], E.offer(x["c"], x["rho_pct"]), x["k"]))


def test_study_cell_lookup_and_missing_cell():
    pre = E.load_precomputed()
    assert E.study_cell(pre, 20, 100, 5, "det")["kind"] == "det"
    with pytest.raises(KeyError):
        E.study_cell(pre, 21, 100, 5, "det")
