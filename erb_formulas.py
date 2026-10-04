"""Formeln zu Erlang B und dem Gate mit Wartestellplätzen: c Spuren, k Stellplätze davor, Ankünfte Poisson mit Angebot a (Erlang, mittlere
Abfertigungsdauer = 1), wer ankommt, wenn alle Spuren und alle Stellplätze belegt sind, geht verloren.

**Erlang B** (k = 0): B(c, a) = (a^c/c!) / Σ_{j≤c} a^j/j!, berechnet über die stabile Rekursion B_j = a·B_{j−1}/(j + a·B_{j−1}). Die Formel gilt
für **jede** Verteilung der Abfertigungsdauer mit dem Mittel 1 (Unempfindlichkeit des Erlang-Verlustsystems); die Simulation prüft das nach.
Für k > 0 ist die Kette M/M/c/(c+k) ein Geburts-Sterbe-Prozess mit π_n ∝ a^n/n! für n ≤ c und π_n ∝ π_c·(a/c)^{n−c} danach; das gilt nur für
exponentielle Dauer. Das Angebot darf über c liegen (Überlast): ein Verlustsystem ist immer stabil.

Zum Vergleich: Erlang C (k → ∞, Kopie aus mmc-queue-demo, bewusst ohne Import zwischen Repos)."""

import math

from erb_constants import TRUCKS_PER_ERLANG_HOUR


def erlang_b(c, a):
    """Erlang-B-Verlustwahrscheinlichkeit über die stabile Rekursion B_j = a·B_{j−1}/(j + a·B_{j−1})."""
    if c < 0 or a < 0:
        raise ValueError("c und a müssen nicht negativ sein")
    b = 1.0
    for j in range(1, c + 1):
        b = a * b / (j + a * b)
    return b


def state_probabilities(c, a, k):
    """Gleichgewichtsverteilung π_0 … π_{c+k} der Zahl der Lkw im Gate bei exponentieller Dauer (Geburts-Sterbe-Kette M/M/c/(c+k))."""
    if c < 1 or k < 0 or a <= 0:
        raise ValueError("c ≥ 1, k ≥ 0, a > 0 erwartet")
    w = [1.0]
    for n in range(1, c + k + 1):
        w.append(w[-1] * a / min(n, c))
    total = sum(w)
    return [x / total for x in w]


def blocking(c, a, k=0):
    """Verlustwahrscheinlichkeit des Gates mit k Stellplätzen bei exponentieller Dauer: π_{c+k} (PASTA)."""
    return state_probabilities(c, a, k)[-1]


def carried_load(c, a, k=0):
    """Mittlere Zahl beschäftigter Spuren = a·(1 − B) (Little auf die Spuren)."""
    return a * (1.0 - blocking(c, a, k))


def utilisation(c, a, k=0):
    """Auslastung je Spur: a·(1 − B)/c."""
    return carried_load(c, a, k) / c


def mean_wait_accepted(c, a, k):
    """Mittlere Wartezeit der angenommenen Lkw (Abfertigungsdauern, exponentielle Dauer): L_q/(a(1 − B)); null bei k = 0."""
    if k == 0:
        return 0.0
    pi = state_probabilities(c, a, k)
    lq = sum((n - c) * pi[n] for n in range(c + 1, c + k + 1))
    return lq / (a * (1.0 - pi[-1]))


def erlang_c(c, a):
    """Erlang C: Wahrscheinlichkeit zu warten bei unendlicher Schlange, C = B/(1 − ρ(1 − B)); nur für c > a."""
    rho = a / c
    if rho >= 1:
        raise ValueError("c ≤ a: keine stationäre Verteilung")
    b = erlang_b(c, a)
    return b / (1 - rho * (1 - b))


def mmc_wait(c, a):
    """Mittlere Wartezeit (Abfertigungsdauern) bei unendlicher Schlange vor c Spuren (k → ∞): C(c, a)/(c − a); nur für c > a."""
    return erlang_c(c, a) / (c - a)


def min_servers(a, target, k=0):
    """Kleinste Spurzahl c, bei der die Verlustwahrscheinlichkeit höchstens `target` beträgt."""
    if not 0 < target < 1:
        raise ValueError("Ziel muss in (0, 1) liegen")
    c = 1
    while blocking(c, a, k) > target:
        c += 1
    return c


def rejected_per_hour(a, b):
    """Abgewiesene Lkw je Stunde: Ankunftsrate a/3 min = 20·a je Stunde, davon der Anteil b."""
    return TRUCKS_PER_ERLANG_HOUR * a * b


def to_minutes(x, mean_service_min=3.0):
    """Zeit in Abfertigungsdauern → Minuten."""
    return x * mean_service_min


def erlang_b_direct(c, a):
    """Erlang B über die Summenformel (Logarithmen, stabil) (Gegenprobe zur Rekursion; für große c)."""
    logs = [j * math.log(a) - math.lgamma(j + 1) for j in range(c + 1)]
    m = max(logs)
    return math.exp(logs[c] - m) / sum(math.exp(x - m) for x in logs)
