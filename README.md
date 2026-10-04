# Erlang B – wenn das Gate voll ist (Streamlit-Demo)

**[→ Demo live ausprobieren](https://sebastianhanisch-erlang-b-demo.streamlit.app/)**

Interaktive Demo zum **Gate mit begrenztem Platz**, an dem abgewiesen wird, wer bei besetzten Spuren und vollem Aufstellplatz ankommt.
**Achtes Stück der Konzepte-Linie „Warteschlangentheorie und Simulation“** im Portfolio von [Sebastian Hanisch](https://sebastianhanisch.net)
(Operations Research und Machine Learning): ein Verfahren, ein wachsendes Beispiel, jedes Folgestück hebt genau eine Annahme auf.

Die Stücke 1 bis 7 ließen jeden Lkw warten, so lange es dauerte. Hier hat das Gate **c Spuren und k Wartestellplätze davor**; ist beides belegt,
geht der Lkw verloren. Ohne Stellplätze (k = 0) ist das das **Erlang-Verlustsystem**, dessen Verlustwahrscheinlichkeit **Erlang B** heißt.
Es ist der Grenzfall der Abwanderung aus [erlang-a-demo](https://github.com/sebastian-hanisch/erlang-a-demo) (Geduld null) und das Gegenstück zur
unbegrenzten Schlange aus [mmc-queue-demo](https://github.com/sebastian-hanisch/mmc-queue-demo) (k → ∞).

## Kernfrage

Wie viele Spuren braucht ein Gate für ein Verlustziel, warum hängt Erlang B nicht von der Streuung der Abfertigung ab, und was bleibt davon
übrig, sobald Wartestellplätze davor liegen?

## Modell und Methodik

- **Gate:** c Spuren (5 bis 100), davor k Wartestellplätze (0 bis 20, FIFO), Poisson-Ankünfte mit Angebot a = c·Last (Last 50 bis 130 %), mittlere
  Abfertigung 3 min; bei 3 min Mittel sind 1 Erlang 20 Lkw je Stunde. Wer bei vollem Gate ankommt, wird abgewiesen.
- **Erlang B** (`erb_formulas.py`): B(c, a) = (aᶜ/c!) / Σⱼ≤c aʲ/j!, berechnet über die stabile Rekursion Bⱼ = a·Bⱼ₋₁/(j + a·Bⱼ₋₁); gegengeprüft mit
  der Summenformel (Logarithmen). Die Formel gilt für **jede** Verteilung der Dauer mit dem gleichen Mittel und für jede Last, auch Überlast.
- **Mit Stellplätzen** ist die Kette M/M/c/(c+k) ein Geburts-Sterbe-Prozess mit exakter Lösung (nur für exponentielle Dauer); Verlust π_{c+k}, Auslastung
  a(1 − B)/c, Wartezeit der Angenommenen über Little. Gegenprobe: lineares Gleichungssystem für M/M/2/4.
- **Simulation** (`erb_simulation.py`): Ereignisse Ankunft und Abgang (Abgänge in einem Heap), FIFO-Stellplätze, SplitMix64 mit getrennten Strömen für
  Zwischenankunft und Abfertigung; Dauer exponentiell, fest, gleichverteilt (0 bis 2) oder lognormal (Variationskoeffizient 2), alle mit Mittel 1; die
  ersten 10 % der Ankünfte werden nicht ausgewertet.
- **Gegenproben:** (1) das Gesetz von Little gilt entlang jedes Pfades **exakt** (Verweilzeiten, Wartezeiten, Beschäftigte); (2) für exponentielle Dauer
  stimmen Verlust, Wartezeit und Zustandsverteilung mit der Kette überein; (3) eine von Hand gerechnete Mini-Instanz (eine Spur, ein Stellplatz, vier
  Lkw); (4) jede der vier Verteilungen hat das Mittel 1, die lognormale den Median 1/√5.
- **Vorgerechnete Studie** (`generate_precomputed.py` → `precomputed_sweep.json`, rund zwei Minuten parallel): 3 Spurzahlen (10, 20, 50) × 3 Lasten (80, 100,
  120 %) × 4 Stellplatzzahlen (0, 2, 5, 10) × 4 Verteilungen, je 3 Läufe à 600 000 Ankünfte. Live läuft ein Lauf mit 150 000 Ankünften.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stehen in `tests/test_claims.py`. Wartezeiten in Minuten bei 3 min mittlerer Abfertigung.

| Frage | Befund |
|---|---|
| Hängt Erlang B von der Streuung der Dauer ab? | **Nein.** Ohne Stellplätze liegen alle 36 Zellen (3 Spurzahlen × 3 Lasten × 4 Verteilungen) höchstens **4.3 %** neben Erlang B, im Mittel 0.5 %. |
| Gilt das auch mit Stellplätzen? | **Nein.** In allen 27 Zellen mit k ≥ 2 gilt die Rangfolge **fest < gleichverteilt < exponentiell < lognormal**. Gegenüber der exponentiellen Rechnung weicht der Verlust bei fester Dauer um −2.1 % bis **−80.6 %** ab (weniger Verlust), bei lognormaler um +0.1 % bis **+104.7 %** (mehr Verlust). |
| Wovon hängt der Bruch ab? | Er wächst mit k (bei Last ≤ 100 % in allen sechs Zellen), schrumpft mit der Last (k = 5, alle Spurzahlen) und mit der Spurzahl (k = 5, Last 80 und 100 %). 20 Spuren, Last 100 %: fest **−6.2 / −20.0 / −32.5 %** bei k = 2 / 5 / 10, lognormal +2.0 / +5.7 / +18.7 %. Bei Überlast (120 %) höchstens 10.5 %. |
| Und die Wartezeit der Angenommenen? | In dem einen geprüften Fall (10 Spuren, Last 100 %, 5 Stellplätze) kaum: fest 0.51, exponentiell 0.52, lognormal 0.53 min, obwohl der Verlust um −27 % bzw. +12 % abweicht. |
| Stimmt die exponentielle Kette? | Ja: Simulation und Kette weichen in allen 36 Zellen mit exponentieller Dauer höchstens 4.1 % ab (im Mittel 0.7 %), auch mit Stellplätzen. |
| Wie viele Spuren für 1 % Verlust? | Angebot 5 / 10 / 20 / 50 / 100 / 200 Erlang: **11 / 18 / 30 / 64 / 117 / 221** Spuren, Last je Spur **45 / 56 / 67 / 78 / 85 / 90 %**. Für 0.1 %: 14 / 21 / 35 / 71 / 128 / 238 Spuren bei 36 / 48 / 57 / 70 / 78 / 84 %. Große Anlagen dürfen heißer laufen. |
| Was bringen Stellplätze? | 10 Spuren, Angebot 9: Verlust **16.8 / 10.6 / 6.1 / 3.0 / 0.9 / 0.03 %** bei k = 0 / 2 / 5 / 10 / 20 / 50, dabei warten die Angenommenen im Mittel 0 / 0.12 / 0.38 / 0.79 / 1.39 / 1.95 min; die unbegrenzte Schlange (Erlang C) läge darüber. |
| Standardszenario? | 20 Spuren, Last 90 % (360 Lkw je Stunde): **10.9 %** Verlust (39 Lkw je Stunde), Auslastung 80 %; mit 10 Stellplätzen 2.3 % (8 je Stunde, Wartezeit 0.3 min). Überlast 120 %: 25.7 % Verlust (123 von 480 je Stunde), Auslastung 89 %, das System bleibt stabil. |
| Wie verlässlich sind die Zahlen? | Der größte relative Standardfehler einer Zelle beträgt 6.0 % (Mittel aus 3 Läufen), die meisten liegen unter 1.5 %. |

## Befunde und Korrekturen gegenüber der Vorab-Messreihe

- **Die Richtung stimmt, die Größe hängt von Last und Spurzahl ab.** Die Vorab-Messreihe (10 Spuren, Angebot 9, 5 Stellplätze) nannte −38 % für feste und +18 %
  für lognormale Dauer; die Studie hat diese Zelle nicht, aber die Nachbarn: Last 80 % −50.2 / +29.8 %, Last 100 % −27.2 / +11.7 %. Der Wert dazwischen passt.
- **Der exakte Verlust der Vorab-Messreihe für die Stellplätze** (6.13 % bei k = 5, 10 Spuren, Angebot 9) ist identisch mit dem der Demo.
- **Der Live-Standardlauf liegt über dem exakten Wert.** Mit Seed 35 und 150 000 Ankünften: 11.35 % statt 10.92 %, 41 statt 39 abgewiesene Lkw je Stunde.
  Das ist Zufall eines kurzen Laufs: bei 135 000 ausgewerteten Ankünften zählt ein Verlust von 10.9 % rund 14 700 abgewiesene Lkw, ein Verlust von 1 % nur rund 1 350; die Studie mittelt drei lange Läufe.

## Ehrliche Grenzen

- Abgewiesene Lkw kommen **nicht wieder**; Wiederholer erhöhen das Angebot und sind nicht gerechnet.
- Mit Stellplätzen gibt es für nicht-exponentielle Dauer **keine Formel** in dieser Demo; die Abweichung wird nur gemessen. Es gibt auch keine Näherung
  (etwa mit Variationskoeffizient) dafür.
- Die Wartezeit ist nur für die exponentielle Dauer exakt berechnet; ihre Unempfindlichkeit wurde in **einer** Zelle geprüft.
- Alle Lkw sind gleich wichtig; eilige Lkw dürften nicht abgewiesen werden.
- Konstante Last, ein Gate. Die Studie deckt nur 10, 20, 50 Spuren, Last 80, 100, 120 % und k = 0, 2, 5, 10 ab; die App zeigt für andere Werte die nächste Zelle und sagt es.
- Der Live-Lauf ist kurz und streut bei kleinen Verlusten um Zehntel des Wertes.
- Sehr kleine Verluste (Millionstel) sind nicht Gegenstand: dort sieht ein gewöhnlicher Lauf kaum einen abgewiesenen Lkw.

## Verwandte Demos im Portfolio

- [`mmc-queue-demo`](https://github.com/sebastian-hanisch/mmc-queue-demo) (Stück 3): dieselben Spuren mit unbegrenzter Schlange (Erlang C), der Grenzfall k → ∞.
- [`erlang-a-demo`](https://github.com/sebastian-hanisch/erlang-a-demo) (Stück 4): Abwanderung; Geduld null ist Erlang B.
- [`mm1-queue-demo`](https://github.com/sebastian-hanisch/mm1-queue-demo) (Stück 1): eine Spur.
- [`ems-demo`](https://github.com/sebastian-hanisch/ems-demo): Rettungsdienst-Standortplanung; ihr Hypercube-Modell prüft sich an der Erlang-B-Formel.
- [`truck-appointment-demo`](https://github.com/sebastian-hanisch/truck-appointment-demo): Terminvergabe für Lkw am Hafen.

## Bewusst nicht umgesetzt

Jede dieser Annahmen hebt ein Folgestück der Linie auf:

| Annahme | Folgestück |
|---|---|
| Verluste sind häufig genug zum Messen | Seltene Ereignisse (Splitting) |
| Mit Stellplätzen: exponentielle Dauer | M/G/1, Kingman-Näherung |
| Alle Lkw gleich wichtig | Prioritätsklassen |
| Konstante Ankunftsrate | [Zeitvariable Ankünfte](https://github.com/sebastian-hanisch/time-varying-arrivals-demo) |
| Ein Gate | Jackson-Netze |

Kein Folgestück: Wiederholer abgewiesener Lkw.

## Tests

124 Tests, rund eine halbe Minute: Erlang B von Hand und gegen die Summenformel (auch für 200 Spuren), die Kette mit Stellplätzen von Hand und gegen ein lineares
System, Überlast (B → 1 − c/a), Bemessung auf Minimalität, k → ∞ gegen Erlang C, die Verteilungen der Dauer einzeln (Mittel, Median, Schwanz), eine von
Hand gerechnete Mini-Instanz (Ankunftszeiten, Verlust, Wartezeit, alle Zeitintegrale), das Gesetz von Little als exakte Pfad-Identität, Invarianten des
Zustands, gleicher Seed gleiches Ergebnis, Simulation gegen die Kette, die Unempfindlichkeit von Erlang B und ihr Bruch mit Stellplätzen,
Vollständigkeit der vorgerechneten Datei, Presets und Permalink, Diagramme (gesperrte Achsen), AppTest-Rauchtests mit festem Würfel-Seed, der
Smoke-Test der Portfolio-Vorlage, ein Quelltext-Test gegen Satz-Komma-Fehler und `test_claims.py` für jede Zahl dieser README.

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `erb_formulas.py` | Erlang B, Kette mit Stellplätzen, Bemessung, Erlang C |
| `erb_simulation.py` | Verteilungen der Dauer, Ereignisschleife, Zeitintegrale |
| `erb_evaluation.py` | Live-Lauf, Bemessungstabelle, Studienzelle, Laden |
| `generate_precomputed.py` | rechnet die Studie vor → `precomputed_sweep.json` |
| `erb_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `erb_presets.py`, `erb_constants.py` | Presets, Permalink, Grenzen |
| `tests/` | siehe oben |

## Literatur

- Erlang, A. K. (1917): Løsning af nogle Problemer fra Sandsynlighedsregningen af Betydning for de automatiske Telefoncentraler. *Elektroteknikeren* (englisch:
  Solution of some problems in the theory of probabilities of significance in automatic telephone exchanges; Verlust- und Wartezeitformeln).
- Sevastyanov, B. A. (1957): ergodischer Satz für Markov-Prozesse und seine Anwendung auf Bediensysteme mit Verlusten. *Teoriya Veroyatnostei i ee
  Primeneniya* (Theory of Probability and its Applications); verallgemeinert die Erlang-Formel auf beliebige Verteilung der Dauer (Unempfindlichkeit).
  Titel und Seiten nicht einzeln belegt, nur Zeitschrift und Jahr.

## Lokal ausführen

```
pip install -r requirements.txt
streamlit run app.py
```

Tests: `pip install -r requirements-dev.txt` und `python -m pytest tests/ -v`. Studie neu rechnen: `python generate_precomputed.py`.

Gebaut mit Streamlit und Plotly.
