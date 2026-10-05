"""Ereignisdiskrete Simulation eines Gates mit c Spuren, k Wartestellplätzen und beliebiger Verteilung der Abfertigungsdauer (M/G/c/(c+k)).
Wer ankommt, wenn alle Spuren und alle Stellplätze belegt sind, geht verloren. Ankünfte: Poisson mit Rate a (Angebot in Erlang), mittlere
Abfertigungsdauer 1.

Aufbau nach Einheiten (kein versteckter Zustand): `draw_service` (Verteilung der Dauer), `advance_clock` (Zeitintegrale), `start_service`,
`handle_arrival`, `handle_departure`, `simulate` (Ereignisschleife). Zufall nur über übergebene `SplitMix64`-Ströme (Zwischenankunft,
Abfertigung). Gemessen wird nach einer Einschwingphase (die ersten `warm_fraction` der Ankünfte): Verlustanteil, mittlere Wartezeit der
angenommenen Lkw, Zeitmittel der Zahl der Lkw im Gate (Zustandsverteilung) und der beschäftigten Spuren.

Start leer; der Bias dieser Einschwingphase ist gemessen und nicht nachweisbar: bei exponentieller Dauer (exakte Formel) liegen 60 Läufe zu
150 000 Ankünften bis c = 100, ρ = 130 %, k = 20 mit Verlustanteil, Wartezeit und Auslastung innerhalb von 2.2 Standardfehlern an der Formel
(Verlustanteil höchstens 1.3 Standardfehler und 1.4 % relativ daneben); bei fester, gleichverteilter und lognormaler Dauer ändert eine Einschwingphase von 50 statt 10 %
die Ergebnisse nicht über das Rauschen hinaus (40 Läufe, c = 10 bis 100)."""

import heapq
import math
from collections import deque
from dataclasses import dataclass, field

from erb_constants import LOGN_CV

_MASK = (1 << 64) - 1


class SplitMix64:
    """Kleiner, gut gemischter 64-Bit-Zufallsgenerator (Vigna); reine Ganzzahl-Arithmetik."""

    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def uniform(self):
        """Gleichverteilt auf [0, 1) mit 53 Bit."""
        return (self.next() >> 11) * (1.0 / (1 << 53))

    def expovariate(self, rate):
        """Exponentiell mit Mittel 1/rate (Inversion; 1 − u liegt in (0, 1], der Logarithmus ist endlich)."""
        return -math.log(1.0 - self.uniform()) / rate


def streams(seed):
    """Die zwei Zufallsströme eines Laufs: Zwischenankunft und Abfertigungsdauer."""
    return SplitMix64(seed), SplitMix64(seed + 15_555_555)


_LOGN_SIGMA2 = math.log(1.0 + LOGN_CV ** 2)
_LOGN_MU = -_LOGN_SIGMA2 / 2.0                      # Mittel exp(μ + σ²/2) = 1


def draw_service(kind, rng):
    """Eine Abfertigungsdauer mit Mittel 1: `exp` exponentiell, `det` fest 1, `unif` gleichverteilt auf (0, 2), `logn` lognormal mit
    Variationskoeffizient `LOGN_CV` (Box-Muller aus zwei Gleichverteilten)."""
    if kind == "exp":
        return rng.expovariate(1.0)
    if kind == "det":
        return 1.0
    if kind == "unif":
        return 2.0 * rng.uniform()
    if kind == "logn":
        u1, u2 = 1.0 - rng.uniform(), rng.uniform()
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return math.exp(_LOGN_MU + math.sqrt(_LOGN_SIGMA2) * z)
    raise ValueError(f"unbekannte Verteilung: {kind}")


@dataclass
class Gate:
    """Zustand eines Laufs: belegte Spuren (Heap aus Abgangszeit und Ankunftszeit), Stellplatz-Warteschlange, Uhr und alle Zähler."""
    c: int
    k: int
    busy: list = field(default_factory=list)            # Heap aus (Abgangszeit, Ankunftszeit)
    queue: deque = field(default_factory=deque)         # Ankunftszeiten der Wartenden (FIFO)
    clock: float = 0.0
    measuring: bool = False
    t_start: float = 0.0
    arrivals: int = 0                                   # Ankünfte seit Messbeginn
    lost: int = 0                                       # davon abgewiesen
    wait_sum: float = 0.0                               # Wartezeit (bis Abfertigungsbeginn) der seit Messbeginn begonnenen Abfertigungen
    wait_n: int = 0
    sojourn_sum: float = 0.0                            # Verweilzeit der seit Messbeginn fertigen Lkw
    completed: int = 0
    area_system: float = 0.0                            # ∫ Lkw im Gate dt
    area_busy: float = 0.0                              # ∫ beschäftigte Spuren dt
    state_time: list = field(default_factory=list)      # state_time[n] = Zeit mit n Lkw im Gate


def new_gate(c, k):
    return Gate(c=c, k=k, state_time=[0.0] * (c + k + 1))


def advance_clock(g, t_new):
    """Zeit auf `t_new` vorrücken und (in der Messung) die Zeitintegrale fortschreiben."""
    dt = t_new - g.clock
    if g.measuring and dt > 0:
        n_busy = len(g.busy)
        total = n_busy + len(g.queue)
        g.area_system += total * dt
        g.area_busy += n_busy * dt
        g.state_time[total] += dt
    g.clock = t_new


def start_service(g, arrival_time, kind, svc_rng):
    """Ein Lkw beginnt jetzt seine Abfertigung (Wartezeit = jetzt − Ankunft), der Abgang wird eingeplant."""
    if g.measuring:
        g.wait_sum += g.clock - arrival_time
        g.wait_n += 1
    heapq.heappush(g.busy, (g.clock + draw_service(kind, svc_rng), arrival_time))


def handle_arrival(g, kind, svc_rng):
    """Ein Lkw kommt an: freie Spur → sofort bedient, sonst freier Stellplatz → wartet, sonst abgewiesen."""
    if g.measuring:
        g.arrivals += 1
    if len(g.busy) < g.c:
        start_service(g, g.clock, kind, svc_rng)
    elif len(g.queue) < g.k:
        g.queue.append(g.clock)
    elif g.measuring:
        g.lost += 1


def handle_departure(g, kind, svc_rng):
    """Der Lkw mit dem frühesten Abgang ist fertig; der vorderste Wartende (falls vorhanden) rückt auf die freie Spur."""
    _, arrival = heapq.heappop(g.busy)
    if g.measuring:
        g.sojourn_sum += g.clock - arrival
        g.completed += 1
    if g.queue:
        start_service(g, g.queue.popleft(), kind, svc_rng)


def start_measurement(g):
    g.measuring = True
    g.t_start = g.clock


@dataclass
class SimResult:
    c: int
    k: int
    a: float
    kind: str
    horizon: float                 # Länge des ausgewerteten Zeitraums (Abfertigungsdauern)
    arrivals: int
    lost: int
    mean_wait: float               # mittlere Wartezeit der angenommenen Lkw (Abfertigungsdauern, inkl. der ohne Warten)
    state_fraction: list           # state_fraction[n] = Zeitanteil mit n Lkw im Gate
    utilisation: float             # Zeitmittel des Anteils beschäftigter Spuren

    def blocking(self):
        return self.lost / self.arrivals if self.arrivals else float("nan")


def simulate(c, a, k, kind, n_customers, seed, warm_fraction=0.1, rngs=None, return_gate=False):
    """Ein Lauf über `n_customers` Ankünfte (Angebot `a`, mittlere Dauer 1); die ersten `warm_fraction` davon werden nicht ausgewertet (Start
    mit leerem Gate). `return_gate=True` gibt zusätzlich den Endzustand zurück (für die Gegenproben über Little)."""
    gap_rng, svc_rng = rngs if rngs is not None else streams(seed)
    g = new_gate(c, k)
    warm = int(warm_fraction * n_customers)
    next_arrival = gap_rng.expovariate(a)
    if warm == 0:
        start_measurement(g)
    for i in range(n_customers):
        while g.busy and g.busy[0][0] < next_arrival:
            advance_clock(g, g.busy[0][0])
            handle_departure(g, kind, svc_rng)
        advance_clock(g, next_arrival)
        if i == warm and not g.measuring:
            start_measurement(g)
        handle_arrival(g, kind, svc_rng)
        next_arrival = g.clock + gap_rng.expovariate(a)
    result = _result(g, a, kind)
    return (result, g) if return_gate else result


def _result(g, a, kind):
    horizon = g.clock - g.t_start
    return SimResult(c=g.c, k=g.k, a=a, kind=kind, horizon=horizon, arrivals=g.arrivals, lost=g.lost,
                     mean_wait=g.wait_sum / g.wait_n if g.wait_n else float("nan"),
                     state_fraction=[t / horizon for t in g.state_time] if horizon > 0 else [float("nan")] * len(g.state_time),
                     utilisation=g.area_busy / (g.c * horizon) if horizon > 0 else float("nan"))
