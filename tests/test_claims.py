"""JEDE Zahl aus README und App-Texten wird hier nachgerechnet: Formelwerte exakt, Studien-Zahlen aus der vorgerechneten Datei (3 Läufe à
600 000 Ankünfte je Zelle). Die Datei ist fest; ändern sich die Zahlen nach einer neuen Rechnung, müssen README und Hilfetexte nachgezogen
werden. Wartezeiten in Minuten bei 3 min mittlerer Abfertigung."""

import pytest

import erb_constants as C
import erb_evaluation as E
import erb_formulas as F

PRE = E.load_precomputed()


def cell(c, rho, k, kind):
    return E.study_cell(PRE, c, rho, k, kind)


def dev(c, rho, k, kind):
    """Abweichung des simulierten Verlusts von der exponentiellen Rechnung in Prozent."""
    x = cell(c, rho, k, kind)
    return 100 * (x["blocking"] / x["blocking_exact"] - 1)


GRID = [(c, r) for c in C.STUDY_C for r in C.STUDY_RHO_PCT]


def test_erlang_b_is_insensitive_to_the_service_distribution_in_every_cell():
    """README: Ohne Stellplätze liegen alle 36 Zellen (3 Spurzahlen × 3 Lasten × 4 Verteilungen) höchstens 4.3 % neben Erlang B, im Mittel 0.5 %."""
    devs = [abs(dev(c, r, 0, kind)) for c, r in GRID for kind in C.STUDY_KINDS]
    assert len(devs) == 36 and round(max(devs), 1) == 4.3 and round(sum(devs) / len(devs), 1) == 0.5


def test_exponential_service_agrees_with_the_exact_chain_for_every_k():
    """README: Mit exponentieller Dauer stimmt die Simulation in allen 36 Zellen (auch mit Stellplätzen) mit der Kette überein: höchstens
    4.1 % Abweichung, im Mittel 0.7 %."""
    devs = [abs(dev(c, r, k, "exp")) for c, r in GRID for k in C.STUDY_K]
    assert len(devs) == 36 and round(max(devs), 1) == 4.1 and round(sum(devs) / len(devs), 1) == 0.7


def test_stellplaetze_break_the_insensitivity_in_a_fixed_order():
    """README: Mit Stellplätzen verliert feste Dauer weniger, gleichverteilte etwas weniger, lognormale mehr als die exponentielle Rechnung: in allen
    27 Zellen mit k ≥ 2 gilt fest < gleichverteilt < exponentiell < lognormal. Spanne fest −80.6 % bis −2.1 %, lognormal +0.1 % bis +104.7 %."""
    cells = [(c, r, k) for c, r in GRID for k in (2, 5, 10)]
    assert len(cells) == 27
    for c, r, k in cells:
        assert dev(c, r, k, "det") < dev(c, r, k, "unif") < dev(c, r, k, "exp") < dev(c, r, k, "logn"), (c, r, k)
    det, logn = [dev(c, r, k, "det") for c, r, k in cells], [dev(c, r, k, "logn") for c, r, k in cells]
    assert (round(min(det), 1), round(max(det), 1)) == pytest.approx((-80.6, -2.1), abs=0.051)
    assert (round(min(logn), 1), round(max(logn), 1)) == pytest.approx((0.1, 104.7), abs=0.051)


def test_the_break_grows_with_k_shrinks_with_load_and_with_spuren():
    """README: Der Bruch wächst mit k (bei Last ≤ 100 % in allen sechs Zellen), schrumpft mit der Last (k = 5, alle Spurzahlen) und mit der
    Spurzahl (k = 5, Last 80 und 100 %). Beispiel 20 Spuren, Last 100 %: fest −6.2 / −20.0 / −32.5 % bei k = 2 / 5 / 10, lognormal +2.0 / +5.7 / +18.7 %."""
    for c in C.STUDY_C:
        for r in (80, 100):
            d, l = [dev(c, r, k, "det") for k in (2, 5, 10)], [dev(c, r, k, "logn") for k in (2, 5, 10)]
            assert d[0] > d[1] > d[2] and l[0] < l[1] < l[2], (c, r)
        for kind in ("det", "logn"):
            ds = [abs(dev(c, r, 5, kind)) for r in C.STUDY_RHO_PCT]
            assert ds[0] > ds[1] > ds[2], (c, kind)
    for r in (80, 100):
        for kind in ("det", "logn"):
            ds = [abs(dev(c, r, 5, kind)) for c in C.STUDY_C]
            assert ds[0] > ds[1] > ds[2], (r, kind)
    assert [round(dev(20, 100, k, "det"), 1) for k in (2, 5, 10)] == pytest.approx([-6.2, -20.0, -32.5], abs=0.051)
    assert [round(dev(20, 100, k, "logn"), 1) for k in (2, 5, 10)] == pytest.approx([2.0, 5.7, 18.7], abs=0.051)


def test_overload_weakens_the_break_but_does_not_remove_it_for_fixed_service():
    """README: Bei Überlast (Last 120 %) beträgt der Bruch höchstens 10.5 % (fest, 10 Spuren, 5 Stellplätze); die Rangfolge der Verteilungen bleibt."""
    worst = max(abs(dev(c, 120, k, kind)) for c in C.STUDY_C for k in (2, 5, 10) for kind in ("det", "unif", "logn"))
    assert round(worst, 1) == 10.5 and round(dev(10, 120, 5, "det"), 1) == -10.5


def test_waiting_time_of_accepted_trucks_hardly_depends_on_the_distribution_in_one_cell():
    """README (10 Spuren, Last 100 %, 5 Stellplätze): mittlere Wartezeit der Angenommenen fest 0.51, exponentiell 0.52 (exakt), lognormal 0.53 min,
    obwohl der Verlust um −27 % bzw. +12 % abweicht."""
    m = lambda kind: round(3 * cell(10, 100, 5, kind)["wait"], 2)
    assert (m("det"), round(3 * F.mean_wait_accepted(10, 10.0, 5), 2), m("logn")) == (0.51, 0.52, 0.53)
    assert round(dev(10, 100, 5, "det")) == -27 and round(dev(10, 100, 5, "logn")) == 12


def test_sizing_numbers_quoted_in_readme():
    """README (exponentielle Dauer, k = 0): Spuren für Verlust ≤ 1 %: 11 / 18 / 30 / 64 / 117 / 221 bei Angebot 5 / 10 / 20 / 50 / 100 / 200 mit Last
    45 / 56 / 67 / 78 / 85 / 90 %; für ≤ 0.1 %: 14 / 21 / 35 / 71 / 128 / 238 mit Last 36 / 48 / 57 / 70 / 78 / 84 %."""
    rows = E.sizing_table(C.SIZING_OFFERS, C.SIZING_TARGETS)
    one = [r for r in rows if r["target"] == 0.01]
    tenth = [r for r in rows if r["target"] == 0.001]
    assert [r["c"] for r in one] == [11, 18, 30, 64, 117, 221] and [r["c"] for r in tenth] == [14, 21, 35, 71, 128, 238]
    assert [round(100 * r["rho"]) for r in one] == [45, 56, 67, 78, 85, 90]
    assert [round(100 * r["rho"]) for r in tenth] == [36, 48, 57, 70, 78, 84]


def test_stellplatz_numbers_quoted_in_readme():
    """README (10 Spuren, Angebot 9): Verlust 16.8 / 10.6 / 6.1 / 3.0 / 0.9 / 0.03 % bei k = 0 / 2 / 5 / 10 / 20 / 50, Wartezeit der Angenommenen
    0 / 0.12 / 0.38 / 0.79 / 1.39 / 1.95 min."""
    ks = (0, 2, 5, 10, 20, 50)
    assert [round(100 * F.blocking(10, 9.0, k), 2) for k in ks] == pytest.approx([16.80, 10.57, 6.13, 2.95, 0.88, 0.03], abs=0.005)
    assert [round(3 * F.mean_wait_accepted(10, 9.0, k), 2) for k in ks] == pytest.approx([0.0, 0.12, 0.38, 0.79, 1.39, 1.95], abs=0.005)
    assert F.mmc_wait(10, 9.0) > F.mean_wait_accepted(10, 9.0, 50)           # die Wartezeit bleibt unter der unbegrenzten Schlange (Erlang C)


def test_default_scenario_numbers_quoted_in_readme_and_presets():
    """README/Presets: 20 Spuren, Last 90 % (18 Erlang = 360 Lkw je Stunde): exakt 10.92 % Verlust (39 Lkw je Stunde), Auslastung 80 %; mit 10
    Stellplätzen 2.32 % (8 je Stunde, Wartezeit 0.31 min); Überlast 120 %: 25.7 % Verlust (123 von 480 je Stunde), Auslastung 89 %."""
    assert round(100 * F.blocking(20, 18.0, 0), 2) == 10.92 and round(F.rejected_per_hour(18.0, F.blocking(20, 18.0, 0))) == 39
    assert round(100 * F.utilisation(20, 18.0, 0)) == 80 and round(18.0 * C.TRUCKS_PER_ERLANG_HOUR) == 360
    assert round(100 * F.blocking(20, 18.0, 10), 2) == 2.32 and round(F.rejected_per_hour(18.0, F.blocking(20, 18.0, 10))) == 8
    assert round(3 * F.mean_wait_accepted(20, 18.0, 10), 2) == 0.31
    assert round(100 * F.blocking(20, 24.0, 0), 1) == 25.7 and round(F.rejected_per_hour(24.0, F.blocking(20, 24.0, 0))) == 123
    assert round(100 * F.utilisation(20, 24.0, 0)) == 89 and round(24.0 * C.TRUCKS_PER_ERLANG_HOUR) == 480


def test_preset_help_numbers():
    """PRESET_HELP: jede Zahl aus den vier Texten (siehe erb_constants)."""
    h = C.PRESET_HELP
    t = h["Gate ohne Warteraum (Erlang B)"]
    assert all(x in t for x in ("10.9 %", "39 je Stunde", "80 %", "360 Lkw")) and format(100 * F.blocking(20, 18.0, 0), ".1f") == "10.9"
    t = h["Mit 10 Stellplätzen"]
    assert all(x in t for x in ("2.3 %", "8 Lkw", "0.3 min")) and format(100 * F.blocking(20, 18.0, 10), ".1f") == "2.3"
    t = h["Feste Abfertigung, 5 Stellplätze"]
    exp_b, det_b = F.blocking(10, 10.0, 5), cell(10, 100, 5, "det")["blocking"]
    assert format(100 * exp_b, ".1f") == "10.4" and format(100 * det_b, ".1f") == "7.5" and round(100 * (1 - det_b / exp_b)) == 27
    assert all(x in t for x in ("10.4 %", "7.5 %", "27 %"))
    t = h["Überlast (120 %)"]
    assert all(x in t for x in ("25.7 %", "123 von 480", "89 %"))


def test_default_live_run_numbers():
    """README: Standardlauf (Seed 35, 150 000 Ankünfte): 11.35 % Verlust (exakt 10.92 %), 41 abgewiesene Lkw je Stunde (exakt 39), Auslastung 80.6 %."""
    r = E.live_report(20, 90, 0, "exp", seed=35)
    assert (round(100 * r["blocking_sim"], 2), round(100 * r["blocking_exact"], 2)) == pytest.approx((11.35, 10.92), abs=0.0051)
    assert (round(r["rejected_sim"]), round(r["rejected_exact"])) == (41, 39) and round(100 * r["util_sim"], 1) == pytest.approx(80.6, abs=0.06)


def test_noise_level_of_the_study_quoted_in_readme():
    """README: Der größte relative Standardfehler einer Zelle beträgt 6.0 % (Mittel aus 3 Läufen), meist unter 1.5 %."""
    rel = [x["blocking_se"] / x["blocking"] for x in PRE["study"]]
    assert round(100 * max(rel), 1) == 6.0
    assert sum(1 for r in rel if r < 0.015) >= 0.6 * len(rel)
