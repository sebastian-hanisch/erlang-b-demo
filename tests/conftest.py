import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class ScriptedRng:
    """Liefert vorgegebene Werte statt Zufall (Mini-Instanzen von Hand gerechnet). `expovariate(rate)` ignoriert die Rate und gibt der
    Reihe nach die Werte zurück, `uniform()` ebenso aus einer eigenen Liste."""

    def __init__(self, exp_values=(), uniform_values=()):
        self.exp_values, self.uniform_values = list(exp_values), list(uniform_values)
        self.n_exp = self.n_uniform = 0

    def expovariate(self, rate):
        v = self.exp_values[self.n_exp]
        self.n_exp += 1
        return v

    def uniform(self):
        v = self.uniform_values[self.n_uniform]
        self.n_uniform += 1
        return v


@pytest.fixture
def blocking_mini_streams():
    """1 Spur, 1 Wartestellplatz (c = 1, k = 1), exponentielle Abfertigung (Skript, Dauer je 1.0), Zwischenankünfte 0.5 / 0.2 / 0.2 / 2.0
    (Ankünfte bei 0.5, 0.7, 0.9, 2.9; die fünfte Zeit wird gezogen, aber nicht gebraucht).
    Von Hand: Lkw 1 startet bei 0.5 (Ende 1.5); Lkw 2 (0.7) wartet auf dem Stellplatz; Lkw 3 (0.9) findet Spur und Stellplatz belegt und
    geht verloren; bei 1.5 startet Lkw 2 (Wartezeit 0.8, Ende 2.5); Lkw 4 (2.9) findet das Gate leer."""
    return ScriptedRng(exp_values=[0.5, 0.2, 0.2, 2.0, 100.0]), ScriptedRng(exp_values=[1.0, 1.0, 1.0])
