"""Konstanten der Demo zu Erlang B: Regler, Voreinstellungen, Studien-Achsen. Zeiteinheit der Rechnung ist die mittlere Abfertigungsdauer
(= 1); angezeigt werden Minuten und Lkw je Stunde bei 3 min Mittel."""


def fmt_int(n):
    """Ganzzahl mit Punkt als Tausendertrenner (10000 -> 10.000)."""
    return f"{n:,}".replace(",", ".")


def fmt_pct(x, digits=0):
    """Anteil als Prozent mit Leerzeichen (0.086 -> "9 %", mit digits=1 "8.6 %")."""
    return f"{x:.{digits}%}".replace("%", " %")


MEAN_SERVICE_MIN = 3.0                               # mittlere Abfertigungsdauer je Spur (Minuten)
TRUCKS_PER_ERLANG_HOUR = 60.0 / MEAN_SERVICE_MIN     # 1 Erlang Angebot = 20 Lkw je Stunde bei 3 min Mittel

C_MIN, C_MAX, C_STEP, DEFAULT_C = 5, 100, 5, 20      # Zahl der Spuren
RHO_PCT_MIN, RHO_PCT_MAX, RHO_PCT_STEP, DEFAULT_RHO_PCT = 50, 130, 10, 90     # Angebot je Spur in Prozent (a = c·ρ; über 100 % Überlast)
K_OPTIONS = (0, 2, 5, 10, 20)                        # Wartestellplätze vor dem Gate
DEFAULT_K = 0
KINDS = ("exp", "det", "unif", "logn")               # Verteilung der Abfertigungsdauer (Mittel 1)
KIND_LABELS = {"exp": "exponentiell", "det": "fest", "unif": "gleichverteilt (0 bis 2)", "logn": "lognormal (cv 2)"}
DEFAULT_KIND = "exp"
LOGN_CV = 2.0                                        # Variationskoeffizient der Lognormalverteilung
SEED_MAX = 999999
DEFAULT_SEED = 35

LIVE_CUSTOMERS = 150_000                             # Ankünfte je Live-Lauf
WARMUP_FRACTION = 0.1                                # erster Anteil der Ankünfte eines Laufs wird nicht ausgewertet

# Vorgerechnete Studie (generate_precomputed.py)
STUDY_C = (10, 20, 50)
STUDY_RHO_PCT = (80, 100, 120)
STUDY_K = (0, 2, 5, 10)
STUDY_KINDS = KINDS
STUDY_CUSTOMERS = 600_000                            # Ankünfte je Wiederholung
STUDY_REPS = 3                                       # unabhängige Wiederholungen je Zelle

SIZING_TARGETS = (0.01, 0.001)                       # Verlust höchstens 1 % bzw. 0.1 %
SIZING_OFFERS = (5, 10, 20, 50, 100, 200)            # Angebot a (Erlang) der Bemessungstabelle

PRESET_ORDER = ("Gate ohne Warteraum (Erlang B)", "Mit 10 Stellplätzen", "Feste Abfertigung, 5 Stellplätze", "Überlast (120 %)")


def _preset(c=DEFAULT_C, rho_pct=DEFAULT_RHO_PCT, k=DEFAULT_K, kind=DEFAULT_KIND):
    return {"c": c, "rho_pct": rho_pct, "k": k, "kind": kind, "seed": DEFAULT_SEED}


PRESETS = {
    "Gate ohne Warteraum (Erlang B)": _preset(),
    "Mit 10 Stellplätzen": _preset(k=10),
    "Feste Abfertigung, 5 Stellplätze": _preset(c=10, rho_pct=100, k=5, kind="det"),
    "Überlast (120 %)": _preset(rho_pct=120),
}
# Zahlen aus der Formel bzw. der vorgerechneten Studie (je 3 Läufe à 600 000 Ankünfte, 3 min mittlere Abfertigung); tests/test_claims.py rechnet sie nach
PRESET_HELP = {
    "Gate ohne Warteraum (Erlang B)": "20 Spuren, Last 90 % (360 Lkw je Stunde): 10.9 % der Lkw werden abgewiesen (39 je Stunde), die Spuren sind zu 80 % ausgelastet.",
    "Mit 10 Stellplätzen": "20 Spuren, Last 90 %, 10 Stellplätze: 2.3 % Verlust (8 Lkw je Stunde); die angenommenen Lkw warten im Mittel 0.3 min.",
    "Feste Abfertigung, 5 Stellplätze": "10 Spuren, Last 100 %, 5 Stellplätze: exponentiell gerechnet 10.4 % Verlust, bei fester Abfertigung simuliert 7.5 % (27 % weniger): mit Warteplätzen zählt die Streuung.",
    "Überlast (120 %)": "20 Spuren, Last 120 %: 25.7 % der Lkw werden abgewiesen (123 von 480 je Stunde), die Spuren sind zu 89 % ausgelastet; ein Verlustsystem bleibt stabil.",
}
