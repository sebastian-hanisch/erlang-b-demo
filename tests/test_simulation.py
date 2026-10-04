"""Simulation: Verteilung der Dauer einzeln (von Hand), Mini-Instanz von Hand gerechnet, Little als exakte Pfad-Identität, Invarianten,
Vergleich gegen die exakte Kette (exponentielle Dauer) und die Unempfindlichkeit von Erlang B (k = 0) samt ihrem Bruch (k > 0)."""

import math

import pytest

import erb_constants as C
import erb_formulas as F
import erb_simulation as S
from conftest import ScriptedRng


# ---------------------------------------------------------------- Einheit: Verteilung der Dauer

def test_draw_service_by_hand():
    assert S.draw_service("det", ScriptedRng()) == 1.0
    assert S.draw_service("unif", ScriptedRng(uniform_values=[0.25])) == pytest.approx(0.5)
    assert S.draw_service("exp", ScriptedRng(exp_values=[0.7])) == 0.7
    # lognormal: u1 = 0.5, u2 = 0.25 → cos(π/2) = 0, also z = 0 und die Dauer ist der Median exp(μ) = 1/√5
    # (rng.uniform() wird als 1 − u1 gelesen: Skript 0.5 → u1 = 0.5, Skript 0.25 → u2 = 0.25)
    assert S.draw_service("logn", ScriptedRng(uniform_values=[0.5, 0.25])) == pytest.approx(1 / math.sqrt(5), rel=1e-9)
    with pytest.raises(ValueError):
        S.draw_service("zipf", ScriptedRng())


@pytest.mark.parametrize("kind", C.KINDS)
def test_every_distribution_has_mean_one(kind):
    rng = S.SplitMix64(7)
    n = 400_000
    mean = sum(S.draw_service(kind, rng) for _ in range(n)) / n
    assert mean == pytest.approx(1.0, abs=0.02 if kind == "logn" else 0.01)


def test_lognormal_has_the_stated_median_and_a_heavy_tail():
    rng = S.SplitMix64(11)
    xs = sorted(S.draw_service("logn", rng) for _ in range(100_000))
    assert xs[len(xs) // 2] == pytest.approx(1 / math.sqrt(5), rel=0.02)               # Median exp(μ)
    assert sum(1 for x in xs if x > 5) / len(xs) > 0.02                                # schwerer Schwanz (ein Fünffaches des Mittels)


# ---------------------------------------------------------------- Mini-Instanz von Hand

def test_hand_computed_mini_instance(blocking_mini_streams):
    """Siehe conftest: c = 1, k = 1, vier Lkw, Ankünfte 0.5 / 0.7 / 0.9 / 2.9, Lkw 3 geht verloren, Lkw 2 wartet 0.8. Integrale über [0, 2.9]:
    Lkw im Gate 0 / 1 / 2 / 1 / 0 auf 0.5 / 0.2 / 0.8 / 1.0 / 0.4 → ∫ = 0.2 + 1.6 + 1.0 = 2.8; beschäftigte Spur 2.0; Zustandszeiten
    0.9 / 1.2 / 0.8."""
    res, g = S.simulate(1, 1.0, 1, "exp", 4, seed=0, warm_fraction=0.0, rngs=blocking_mini_streams, return_gate=True)
    assert (res.arrivals, res.lost) == (4, 1) and res.blocking() == pytest.approx(0.25)
    assert res.horizon == pytest.approx(2.9)
    assert g.wait_n == 3 and g.wait_sum == pytest.approx(0.8) and res.mean_wait == pytest.approx(0.8 / 3)     # Lkw 1 (0), Lkw 2 (0.8), Lkw 4 (0)
    assert g.area_system == pytest.approx(2.8) and g.area_busy == pytest.approx(2.0)
    assert res.state_fraction == pytest.approx([0.9 / 2.9, 1.2 / 2.9, 0.8 / 2.9])
    assert res.utilisation == pytest.approx(2.0 / 2.9)
    assert g.completed == 2 and g.sojourn_sum == pytest.approx(1.0 + 1.8)           # Lkw 1: 0.5 → 1.5 (1.0); Lkw 2: 0.7 → 2.5 (1.8)


def test_a_departure_before_the_next_arrival_frees_the_lane_first():
    """c = 1, k = 0, Dauer 0.4: Lkw 1 bei 1.0 (Ende 1.4), Lkw 2 bei 2.0 findet die Spur frei – nicht verloren."""
    rngs = (ScriptedRng(exp_values=[1.0, 1.0, 100.0]), ScriptedRng(exp_values=[0.4, 0.4]))
    res = S.simulate(1, 1.0, 0, "exp", 2, seed=0, warm_fraction=0.0, rngs=rngs)
    assert (res.arrivals, res.lost) == (2, 0)


def test_without_stellplaetze_the_second_truck_is_lost_while_the_lane_is_busy():
    rngs = (ScriptedRng(exp_values=[1.0, 0.2, 100.0]), ScriptedRng(exp_values=[5.0]))
    res = S.simulate(1, 1.0, 0, "exp", 2, seed=0, warm_fraction=0.0, rngs=rngs)
    assert (res.arrivals, res.lost) == (2, 1)


# ---------------------------------------------------------------- Invarianten und Gegenproben

@pytest.mark.parametrize("c,a,k,kind", [(5, 4.0, 0, "exp"), (5, 5.5, 3, "exp"), (6, 7.0, 4, "det"), (4, 4.5, 2, "logn"), (3, 4.0, 5, "unif")])
def test_littles_law_holds_exactly_along_the_path(c, a, k, kind):
    """Ohne Einschwingen und ohne Löschen gilt für [0, T] EXAKT: ∫ Lkw im Gate dt = Σ Verweilzeiten der fertigen Lkw + Σ (T − Ankunft) der
    noch im Gate (in Abfertigung oder auf dem Stellplatz); ebenso ∫ Beschäftigte dt = Σ Dauern der fertigen + Σ bisherige Zeit in
    Abfertigung, und ∫ Wartende dt = Σ Wartezeiten der begonnenen + Σ (T − Ankunft) der noch Wartenden."""
    res, g = S.simulate(c, a, k, kind, 20_000, seed=3, warm_fraction=0.0, return_gate=True)
    T = g.clock
    in_system = sum(T - arr for _, arr in g.busy) + sum(T - arr for arr in g.queue)
    assert g.area_system == pytest.approx(g.sojourn_sum + in_system, rel=1e-9)
    waiting = sum(T - arr for arr in g.queue)
    assert g.area_system - g.area_busy == pytest.approx(g.wait_sum + waiting, rel=1e-6, abs=1e-6)


def test_state_invariants_after_a_run():
    res, g = S.simulate(6, 7.0, 3, "exp", 5_000, seed=9, warm_fraction=0.0, return_gate=True)
    assert len(g.busy) <= g.c and len(g.queue) <= g.k
    assert len(g.queue) == 0 or len(g.busy) == g.c                      # niemand wartet bei freier Spur
    assert sum(res.state_fraction) == pytest.approx(1.0) and len(res.state_fraction) == 6 + 3 + 1
    assert res.arrivals == 5_000 and 0 <= res.lost < res.arrivals
    assert g.state_time[-1] > 0                                         # bei Überlast ist das Gate zeitweise ganz voll


def test_same_seed_same_result_and_different_seed_differs():
    a, b, c = S.simulate(8, 8.0, 2, "exp", 8_000, 5), S.simulate(8, 8.0, 2, "exp", 8_000, 5), S.simulate(8, 8.0, 2, "exp", 8_000, 6)
    assert a == b and a.lost != c.lost


def test_carried_load_equals_the_load_times_one_minus_blocking():
    """Auslastung der Spuren = a(1 − B)/c: aus derselben Simulation, zwei Wege (Zeitintegral gegen Verlustzahl)."""
    res = S.simulate(20, 18.0, 0, "exp", 200_000, 11)
    assert res.utilisation == pytest.approx(18.0 * (1 - res.blocking()) / 20, abs=0.01)


# ---------------------------------------------------------------- Referenz: exakte Kette und Unempfindlichkeit

def _band(c, a, k, kind, reps=4, customers=250_000, seed0=100):
    runs = [S.simulate(c, a, k, kind, customers, seed0 + 17 * r).blocking() for r in range(reps)]
    mean = sum(runs) / len(runs)
    se = (sum((x - mean) ** 2 for x in runs) / (len(runs) - 1) / len(runs)) ** 0.5
    return mean, se


@pytest.mark.parametrize("c,a,k", [(5, 4.0, 0), (10, 9.0, 5), (3, 4.0, 2)])
def test_simulation_matches_the_exact_chain_for_exponential_service(c, a, k):
    exact = F.blocking(c, a, k)
    mean, se = _band(c, a, k, "exp")
    assert abs(mean - exact) < max(4 * se, 0.02 * exact), (exact, mean, se)


def test_wait_and_state_distribution_match_the_exact_chain():
    res = S.simulate(5, 5.0, 4, "exp", 400_000, 21)
    pi = F.state_probabilities(5, 5.0, 4)
    assert res.mean_wait == pytest.approx(F.mean_wait_accepted(5, 5.0, 4), abs=0.02)
    assert max(abs(x - y) for x, y in zip(res.state_fraction, pi)) < 0.01


@pytest.mark.parametrize("kind", ["det", "unif", "logn"])
def test_erlang_b_is_insensitive_to_the_service_distribution(kind):
    """k = 0: die Verlustwahrscheinlichkeit hängt nur vom Mittel der Dauer ab (Erlang B gilt für jede Verteilung)."""
    exact = F.erlang_b(10, 7.0)
    mean, se = _band(10, 7.0, 0, kind)
    assert abs(mean - exact) < max(4 * se, 0.03 * exact), (kind, exact, mean, se)


def test_the_insensitivity_breaks_with_stellplaetze():
    """k = 5: feste Dauer verliert deutlich weniger, lognormale deutlich mehr als die exponentielle Rechnung (c = 10, a = 9)."""
    exact = F.blocking(10, 9.0, 5)
    det, _ = _band(10, 9.0, 5, "det")
    logn, _ = _band(10, 9.0, 5, "logn")
    assert det < 0.8 * exact and logn > 1.08 * exact, (exact, det, logn)


def test_overload_runs_and_loses_about_one_minus_c_over_a():
    res = S.simulate(10, 30.0, 0, "exp", 100_000, 4)
    assert res.blocking() == pytest.approx(F.erlang_b(10, 30.0), abs=0.01)
    assert res.utilisation == pytest.approx(30.0 * (1 - F.erlang_b(10, 30.0)) / 10, abs=0.01)           # a(1 − B)/c = 0.964


def test_clock_conservation():
    """Der Lauf endet bei der letzten Ankunft; der ausgewertete Zeitraum ist Endzeit minus Beginn der Messung."""
    res, g = S.simulate(4, 3.0, 2, "exp", 3_000, 2, warm_fraction=0.2, return_gate=True)
    assert res.horizon == pytest.approx(g.clock - g.t_start) and g.t_start > 0
    assert res.arrivals == 3_000 - int(0.2 * 3_000)
