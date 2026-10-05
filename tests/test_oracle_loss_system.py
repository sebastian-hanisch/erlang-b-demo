"""Orakel mit anderem Rechenweg: (1) Verlust, Auslastung und Wartezeit der Angenommenen gegen das lineare Gleichungssystem der abgeschnittenen Kette M/M/c/(c+k) (statt der Gewichtsformel),
Erlang B in exakter Bruchrechnung; (2) Spurbedarf per Brute Force; (3) die Ereignissimulation gegen eine Kunde-für-Kunde-Rechnung (Belegung = Zahl der Angenommenen, deren Abgang noch aussteht;
Wartezeit, Zeit je Zustand und Auslastung aus absoluten Zeiten) mit denselben Zufallsströmen, für alle vier Verteilungen der Abfertigungsdauer."""

import math
import random
from fractions import Fraction

import numpy as np
import pytest

import erb_formulas as F
import erb_simulation as S


def _ctmc(c, k, a):
    n = c + k + 1
    q = np.zeros((n, n))
    for i in range(n - 1):
        q[i, i + 1] = a
        q[i + 1, i] = min(i + 1, c)
    np.fill_diagonal(q, -q.sum(axis=1))
    m = np.vstack([q.T[:-1], np.ones(n)])
    b = np.zeros(n)
    b[-1] = 1.0
    return np.linalg.solve(m, b)


def test_blocking_utilisation_and_wait_equal_the_linear_system():
    rng = random.Random(3)
    for _ in range(60):
        c, k, a = rng.randint(1, 25), rng.choice([0, 0, 1, 2, 5, 10, 20]), rng.uniform(0.1, 1.6) * 25
        a = min(a, 1.6 * c)
        pi = _ctmc(c, k, a)
        assert F.blocking(c, a, k) == pytest.approx(pi[-1], abs=1e-10)
        carried = sum(min(n, c) * pi[n] for n in range(c + k + 1))
        assert F.carried_load(c, a, k) == pytest.approx(carried, abs=1e-9)
        assert F.utilisation(c, a, k) == pytest.approx(carried / c, abs=1e-9)
        if k > 0:
            # eine Ankunft, die n ≥ c vor sich findet und angenommen wird, wartet n − c + 1 Abfertigungen mit Rate c
            wait = sum(pi[n] * (n - c + 1) / c for n in range(c, c + k)) / (1 - pi[-1])
            assert F.mean_wait_accepted(c, a, k) == pytest.approx(wait, abs=1e-9)
        else:
            assert F.mean_wait_accepted(c, a, k) == 0.0


@pytest.mark.parametrize("c,a", [(1, Fraction(1, 3)), (7, Fraction(13, 2)), (50, Fraction(45)), (100, Fraction(97)), (203, Fraction(200)), (20, Fraction(36))])
def test_erlang_b_equals_exact_rational_arithmetic(c, a):
    b = a ** c / math.factorial(c) / sum(a ** j / math.factorial(j) for j in range(c + 1))
    assert F.erlang_b(c, float(a)) == pytest.approx(float(b), rel=1e-10)
    assert F.erlang_b_direct(c, float(a)) == pytest.approx(float(b), rel=1e-9)
    assert F.blocking(c, float(a), 0) == pytest.approx(float(b), rel=1e-9)


def test_min_servers_equals_a_brute_force_search():
    for a in (0.5, 2.5, 5, 10, 33.3, 50):
        for target in (0.5, 0.1, 0.01):
            for k in (0, 2, 10):
                c = F.min_servers(a, target, k)
                assert _ctmc(c, k, a)[-1] <= target and (c == 1 or _ctmc(c - 1, k, a)[-1] > target)


def _naive(c, a, k, kind, n, seed, warm_fraction):
    gap, svc = S.streams(seed)
    arr, t = [], 0.0
    for _ in range(n):
        t += gap.expovariate(a)
        arr.append(t)
    warm = int(warm_fraction * n)
    deps, starts, acc, free, lost = [], [], [], [0.0] * c, []
    for ti in arr:
        if sum(1 for d in deps if d > ti) >= c + k:
            lost.append(True)
            continue
        lost.append(False)
        j = min(range(c), key=lambda x: free[x])
        st = max(ti, free[j])
        free[j] = st + S.draw_service(kind, svc)
        deps.append(free[j])
        starts.append(st)
        acc.append(ti)
    t_start, t_end = (0.0 if warm == 0 else arr[warm]), arr[-1]
    waits = [s - ar for s, ar in zip(starts, acc) if t_start <= s <= t_end]
    cur, tp, spent, busy = 0, 0.0, {}, 0.0
    for tt, delta in sorted([(ar, 1) for ar in acc] + [(d, -1) for d in deps]):
        lo, hi = max(tp, t_start), min(tt, t_end)
        if hi > lo:
            spent[cur] = spent.get(cur, 0.0) + hi - lo
            busy += min(cur, c) * (hi - lo)
        cur, tp = cur + delta, tt
    if t_end > max(tp, t_start):
        spent[cur] = spent.get(cur, 0.0) + t_end - max(tp, t_start)
        busy += min(cur, c) * (t_end - max(tp, t_start))
    horizon = t_end - t_start
    return n - warm, sum(lost[warm:]), (sum(waits) / len(waits) if waits else float("nan")), {s: v / horizon for s, v in spent.items()}, busy / (c * horizon)


@pytest.mark.parametrize("kind", ["exp", "det", "unif", "logn"])
def test_event_simulation_equals_a_customer_by_customer_recursion(kind):
    rng = random.Random(9)
    for _ in range(30):
        c, k, n = rng.randint(1, 6), rng.choice([0, 0, 1, 3, 6]), rng.randint(20, 250)
        a, seed, warm = rng.uniform(0.3, 1.8) * c, rng.randint(0, 10 ** 6), rng.choice([0.0, 0.1, 0.25])
        res = S.simulate(c, a, k, kind, n, seed, warm_fraction=warm)
        arrivals, lost, mean_wait, fractions, util = _naive(c, a, k, kind, n, seed, warm)
        assert (res.arrivals, res.lost) == (arrivals, lost)
        if not math.isnan(mean_wait):
            assert res.mean_wait == pytest.approx(mean_wait, abs=1e-9)
        for state, value in enumerate(res.state_fraction):
            assert value == pytest.approx(fractions.get(state, 0.0), abs=1e-9)
        assert res.utilisation == pytest.approx(util, abs=1e-9)
