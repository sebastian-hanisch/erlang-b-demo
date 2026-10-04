"""Formeln: Erlang B von Hand und gegen die Summenformel, Geburts-Sterbe-Kette mit Stellplätzen, Little, Bemessung, Überlast, k → ∞."""

import math

import numpy as np
import pytest

import erb_formulas as F


def test_erlang_b_by_hand():
    assert F.erlang_b(0, 3.0) == 1.0                                   # keine Spur: alles geht verloren
    assert F.erlang_b(1, 1.0) == pytest.approx(0.5)                    # a/(1+a)
    assert F.erlang_b(2, 1.0) == pytest.approx(1 / 5)                  # (a²/2)/(1 + a + a²/2) = 0.5/2.5
    assert F.erlang_b(3, 2.0) == pytest.approx((8 / 6) / (1 + 2 + 2 + 8 / 6))


@pytest.mark.parametrize("c,a", [(1, 0.5), (5, 4.0), (10, 7.0), (50, 40.0), (200, 180.0), (200, 250.0)])
def test_recursion_matches_the_explicit_sum(c, a):
    assert F.erlang_b(c, a) == pytest.approx(F.erlang_b_direct(c, a), rel=1e-10)


def test_blocking_without_stellplaetze_equals_erlang_b():
    for c, a in ((3, 2.0), (10, 9.0), (25, 30.0)):
        assert F.blocking(c, a, 0) == pytest.approx(F.erlang_b(c, a), rel=1e-12)


def test_mm1k_by_hand():
    """c = 1, k = 1: Zustände 0, 1, 2 mit Gewichten 1, a, a²; bei a = 1 je 1/3; bei a = 2: B = 4/7."""
    assert F.state_probabilities(1, 1.0, 1) == pytest.approx([1 / 3] * 3)
    assert F.blocking(1, 2.0, 1) == pytest.approx(4 / 7)


def test_state_probabilities_sum_to_one_and_have_the_right_shape():
    pi = F.state_probabilities(4, 3.0, 3)
    assert len(pi) == 8 and sum(pi) == pytest.approx(1.0)
    assert pi[1] / pi[0] == pytest.approx(3.0) and pi[4] / pi[3] == pytest.approx(3.0 / 4)      # a/min(n, c)
    assert pi[6] / pi[5] == pytest.approx(3.0 / 4)                                            # hinter c: a/c


def test_state_probabilities_against_a_linear_solve():
    """Unabhängige Gegenprobe: Gleichgewicht der Kette M/M/2/4 (a = 1.5) als lineares System π Q = 0."""
    c, k, a = 2, 2, 1.5
    n = c + k + 1
    q = np.zeros((n, n))
    for i in range(n):
        if i < n - 1:
            q[i, i + 1] = a
        if i > 0:
            q[i, i - 1] = min(i, c)
        q[i, i] = -q[i].sum()
    system = np.vstack([q.T[:-1], np.ones(n)])
    rhs = np.zeros(n)
    rhs[-1] = 1.0
    assert F.state_probabilities(c, a, k) == pytest.approx(np.linalg.solve(system, rhs))


def test_carried_load_and_utilisation():
    """Beschäftigte Spuren im Mittel = a·(1 − B) = Σ min(n, c)·π_n (zwei Wege)."""
    for c, a, k in ((5, 4.0, 0), (5, 6.0, 3), (12, 10.0, 5)):
        pi = F.state_probabilities(c, a, k)
        assert F.carried_load(c, a, k) == pytest.approx(sum(min(n, c) * p for n, p in enumerate(pi)), rel=1e-12)
        assert F.utilisation(c, a, k) == pytest.approx(F.carried_load(c, a, k) / c)


def test_wait_of_accepted_trucks_by_hand_and_k_zero():
    """c = 1, k = 1, a = 1: π = 1/3 je; L_q = π_2 = 1/3, angenommen 1 − B = 2/3, also W_q = 1/2. Bei k = 0 wartet niemand."""
    assert F.mean_wait_accepted(1, 1.0, 1) == pytest.approx(0.5)
    assert F.mean_wait_accepted(5, 4.0, 0) == 0.0


def test_more_stellplaetze_lower_the_loss_and_raise_the_wait():
    ks = (0, 2, 5, 10, 20)
    b = [F.blocking(10, 9.0, k) for k in ks]
    w = [F.mean_wait_accepted(10, 9.0, k) for k in ks]
    assert all(x > y for x, y in zip(b, b[1:])) and all(x < y for x, y in zip(w, w[1:]))


def test_large_k_approaches_erlang_c_wait():
    """k → ∞ (bei a < c): die Wartezeit der Angenommenen nähert sich der Erlang-C-Wartezeit, der Verlust verschwindet."""
    assert F.mean_wait_accepted(10, 8.0, 400) == pytest.approx(F.mmc_wait(10, 8.0), rel=1e-6)
    assert F.blocking(10, 8.0, 400) < 1e-12


def test_erlang_c_and_mmc_wait_by_hand():
    assert F.erlang_c(2, 1.0) == pytest.approx(1 / 3) and F.mmc_wait(2, 1.0) == pytest.approx(1 / 3)       # M/M/2, a = 1
    with pytest.raises(ValueError):
        F.erlang_c(3, 3.0)


def test_overload_is_stable_and_blocking_tends_to_one_minus_c_over_a():
    """Ein Verlustsystem ist bei jeder Last stabil: B → 1 − c/a für a → ∞ (alle Spuren ständig belegt)."""
    for a in (50.0, 500.0, 5000.0):
        b = F.blocking(10, a, 0)
        assert 0 < b < 1 and abs(b - (1 - 10 / a)) < 10 / a * 0.2 + 0.01
    assert F.blocking(10, 5000.0, 0) == pytest.approx(1 - 10 / 5000, abs=2e-3)


def test_blocking_rises_with_load_and_falls_with_spuren():
    assert all(F.erlang_b(10, a) < F.erlang_b(10, a + 1) for a in (1.0, 5.0, 9.0, 15.0))
    assert all(F.erlang_b(c, 9.0) > F.erlang_b(c + 1, 9.0) for c in (1, 5, 10, 20))


def test_min_servers_by_hand_and_minimality():
    assert F.min_servers(1.0, 0.2) == 2 and F.min_servers(1.0, 0.1) == 3          # B(1,1)=.5, B(2,1)=.2 (nicht ≤ .2 streng: gleich), B(3,1)=1/16
    for a, target, k in ((10.0, 0.01, 0), (20.0, 0.001, 0), (10.0, 0.01, 5)):
        c = F.min_servers(a, target, k)
        assert F.blocking(c, a, k) <= target < F.blocking(c - 1, a, k)


def test_rejected_per_hour_and_minutes():
    assert F.rejected_per_hour(18.0, 0.1) == pytest.approx(36.0)               # 360 Lkw je Stunde, davon 10 %
    assert F.to_minutes(1.5) == 4.5


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        F.erlang_b(-1, 1.0)
    with pytest.raises(ValueError):
        F.state_probabilities(0, 1.0, 0)
    with pytest.raises(ValueError):
        F.min_servers(5.0, 1.5)
