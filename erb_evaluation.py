"""Auswertung: Live-Lauf gegen die exakten Werte, Bemessungstabelle, vorgerechnete Studie (Spuren × Last × Stellplätze × Verteilung der
Dauer). Die teure Studie steht vorgerechnet in `precomputed_sweep.json` (Generator: generate_precomputed.py, Laden: `load_precomputed`)."""

import json
import math
from pathlib import Path

import erb_constants as C
import erb_formulas as F
from erb_simulation import simulate

PRECOMPUTED_PATH = Path(__file__).resolve().parent / "precomputed_sweep.json"


def offer(c, rho_pct):
    """Angebot a (Erlang) bei c Spuren und Last `rho_pct` Prozent (a = c·ρ)."""
    return c * rho_pct / 100.0


def mean_and_se(values):
    """Mittelwert und Standardfehler des Mittelwerts unabhängiger Wiederholungen (None bei nur einer)."""
    n = len(values)
    m = sum(values) / n
    if n < 2:
        return m, None
    var = sum((v - m) ** 2 for v in values) / (n - 1)
    return m, math.sqrt(var / n)


def live_report(c, rho_pct, k, kind, seed, customers=C.LIVE_CUSTOMERS):
    """Ein Live-Lauf und die exakten Bezugswerte (exponentielle Dauer): Verlust, Zustandsverteilung, Wartezeit, Auslastung, abgewiesene Lkw."""
    a = offer(c, rho_pct)
    res = simulate(c, a, k, kind, customers, seed, warm_fraction=C.WARMUP_FRACTION)
    b_exact = F.blocking(c, a, k)
    return {"sim": res, "a": a, "blocking_sim": res.blocking(), "blocking_exact": b_exact, "pi_exact": F.state_probabilities(c, a, k),
            "pi_sim": res.state_fraction, "wait_sim": res.mean_wait, "wait_exact": F.mean_wait_accepted(c, a, k),
            "util_sim": res.utilisation, "util_exact": F.utilisation(c, a, k),
            "rejected_sim": F.rejected_per_hour(a, res.blocking()), "rejected_exact": F.rejected_per_hour(a, b_exact),
            "wait_mmc": F.mmc_wait(c, a) if a < c else None}


def sizing_table(offers, targets, k=0):
    """Je Angebot und Verlustziel: nötige Spurzahl und die dabei erreichte Last je Spur (a/c); Zeilen {a, ziel, c, rho}."""
    rows = []
    for a in offers:
        for target in targets:
            c = F.min_servers(a, target, k)
            rows.append({"a": a, "target": target, "c": c, "rho": a / c})
    return rows


def study_cell_run(c, rho_pct, k, kind, customers, seed, reps):
    """Eine Studienzelle: `reps` unabhängige Läufe (Seeds seed, seed + 1000, …); Mittel und Standardfehler des Verlusts, mittlere Wartezeit der
    Angenommenen, Auslastung; dazu der exakte Verlust bei exponentieller Dauer als Bezug."""
    a = offer(c, rho_pct)
    runs = [simulate(c, a, k, kind, customers, seed + 1000 * r, warm_fraction=C.WARMUP_FRACTION) for r in range(reps)]
    blocking, blocking_se = mean_and_se([r.blocking() for r in runs])
    wait, _ = mean_and_se([r.mean_wait for r in runs])
    util, _ = mean_and_se([r.utilisation for r in runs])
    return {"c": c, "rho_pct": rho_pct, "k": k, "kind": kind, "reps": reps, "customers": customers, "blocking": blocking,
            "blocking_se": blocking_se, "bs": [r.blocking() for r in runs], "wait": wait, "util": util,
            "blocking_exact": F.blocking(c, a, k)}


def load_precomputed():
    return json.loads(PRECOMPUTED_PATH.read_text(encoding="utf-8"))


def nearest(options, value):
    """Nächster Wert aus `options` (bei Gleichstand der kleinere)."""
    return min(options, key=lambda o: (abs(o - value), o))


def study_cell(pre, c, rho_pct, k, kind):
    for cell in pre["study"]:
        if cell["c"] == c and cell["rho_pct"] == rho_pct and cell["k"] == k and cell["kind"] == kind:
            return cell
    raise KeyError((c, rho_pct, k, kind))
