"""Erlang B - wenn das Gate voll ist - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Achtes Stück der Konzepte-Linie "Warteschlangentheorie und Simulation": Das Terminal-Gate hat c Spuren und k Wartestellplätze davor; wer
bei vollem Gate ankommt, wird abgewiesen. Ohne Stellplätze ist das das Erlang-Verlustsystem (Erlang B), dessen Verlustwahrscheinlichkeit nur
vom Mittel der Abfertigungsdauer abhängt. Die Demo zeigt Zustandsverteilung, Bemessung, die Unempfindlichkeit gegen die Streuung der
Dauer (und ihren Bruch mit Stellplätzen) und den Tausch von Verlust gegen Wartezeit. Siehe README für die Einordnung in die Linie.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import erb_constants as C
import erb_formulas as F
from erb_evaluation import live_report, load_precomputed, nearest, offer, sizing_table, study_cell
from erb_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed,
                         sync_query_params)
from erb_visualization import (build_insensitivity_chart, build_load_chart, build_sizing_chart, build_state_chart,
                               build_stellplatz_chart, kind_label)

st.set_page_config(page_title="Erlang B – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _precomputed():
    return load_precomputed()


@st.cache_data(show_spinner=False)
def _live(c, rho_pct, k, kind, seed):
    return live_report(c, rho_pct, k, kind, seed)


def _min(x):
    """Zeit in Abfertigungsdauern → Text in Minuten."""
    return f"{F.to_minutes(x):.2f} min"


st.title("🚪 Erlang B: wenn das Gate voll ist")
st.markdown(
    """
Bisher warteten alle Lkw, so lange es dauerte. Echte Gates haben aber **begrenzten Platz**: Wer bei besetzten Spuren und vollem
Aufstellplatz ankommt, **wird abgewiesen**. Ohne Aufstellplatz heißt das Modell **Erlang-Verlustsystem**, und seine Verlustwahrscheinlichkeit
**Erlang B** hat eine überraschende Eigenschaft: Sie hängt **nur vom Mittel** der Abfertigungsdauer ab, nicht von deren Streuung. Mit
**Wartestellplätzen** davor verschwindet diese Eigenschaft, dafür tauscht jeder Stellplatz Verlust gegen Wartezeit.
"""
)
st.caption(
    "Achtes Stück der Linie „Warteschlangentheorie und Simulation“, aufbauend auf "
    "[mmc-queue-demo](https://sebastianhanisch-mmc-queue-demo.streamlit.app/) (unbegrenzte Schlange, Erlang C) und "
    "[erlang-a-demo](https://sebastianhanisch-erlang-a-demo.streamlit.app/) (Geduld null ist Erlang B). Jedes Folgestück hebt eine der "
    "Annahmen unter „Wo die Annahmen enden“ auf."
)

with st.expander("So funktioniert das Gate mit Verlust", expanded=True):
    st.markdown(
        """
- **Gate:** c Spuren, davor k Wartestellplätze (FIFO). Lkw kommen mit dem Angebot a (Erlang) an: a = c·Last, bei 3 min mittlerer
  Abfertigung sind 1 Erlang 20 Lkw je Stunde. Ist alles belegt, geht der Lkw verloren.
- **Erlang B** (k = 0): B(c, a) = (aᶜ/c!) / Σⱼ≤c aʲ/j!, berechnet über die Rekursion Bⱼ = a·Bⱼ₋₁/(j + a·Bⱼ₋₁). Sie gilt für **jede** Verteilung der
  Dauer mit dem gleichen Mittel (Unempfindlichkeit) und für jede Last, auch Überlast: ein Verlustsystem ist immer stabil.
- **Mit Stellplätzen** (k > 0): Für exponentielle Dauer ist es eine Geburts-Sterbe-Kette mit exakter Lösung. Für andere Verteilungen gibt es
  hier keine Formel, die Simulation zeigt die Abweichung.
- **Simulation:** Ereignisse für Ankunft und Abgang, Dauer exponentiell, fest, gleichverteilt oder lognormal (cv 2), die ersten 10 %
  der Ankünfte werden nicht ausgewertet.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_cols = st.columns(len(C.PRESET_ORDER))
for i, name in enumerate(C.PRESET_ORDER):
    with preset_cols[i]:
        st.button(name, key=f"preset_{name}", width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name] or None)

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    c = st.slider("Spuren c", *bounds("c_slider"), step=C.C_STEP, key="c_slider", help="So viele Lkw können gleichzeitig abgefertigt werden.")
    rho_pct = st.slider("Last je Spur (a/c)", *bounds("rho_slider"), step=C.RHO_PCT_STEP, key="rho_slider", format="%d %%",
                        help="Angebot a = c·Last in Erlang; über 100 % ist Überlast, ein Verlustsystem bleibt dabei stabil.")
    k = st.select_slider("Wartestellplätze k", options=C.K_OPTIONS, key="k_select",
                         help="Plätze vor dem Gate; 0 = Erlang B (kein Warteraum).")
    kind = st.selectbox("Verteilung der Abfertigungsdauer", C.KINDS, key="kind_select", format_func=kind_label,
                        help="Alle mit dem gleichen Mittel von 3 min.")
    seed = st.number_input("Zufalls-Seed", min_value=bounds("seed_input")[0], max_value=bounds("seed_input")[1], step=1,
                           key="seed_input", help="Bestimmt alle Zufallszahlen der Simulation.")
    st.button("🎲 Neuen Lauf würfeln", on_click=randomize_seed)

c, rho_pct, k, seed = int(c), int(rho_pct), int(k), int(seed)
a = offer(c, rho_pct)
sync_query_params({"c_slider": c, "rho_slider": rho_pct, "k_select": k, "kind_select": kind, "seed_input": seed})

pre = _precomputed()
study_c, study_rho, study_k = nearest(C.STUDY_C, c), nearest(C.STUDY_RHO_PCT, rho_pct), nearest(C.STUDY_K, k)
with st.spinner("Simuliere das Gate …"):
    live = _live(c, rho_pct, k, kind, seed)

st.markdown("---")
st.markdown("## 🚪 Ein Gate mit Verlust")
st.caption(
    f"{c} Spuren, Last {rho_pct} % (Angebot {a:.1f} Erlang = {C.fmt_int(round(a * C.TRUCKS_PER_ERLANG_HOUR))} Lkw je Stunde), {k} Wartestellplätze, "
    f"Dauer {kind_label(kind)}. Simuliert: {C.fmt_int(C.LIVE_CUSTOMERS)} Ankünfte (die ersten {C.fmt_pct(C.WARMUP_FRACTION)} nicht ausgewertet)."
)
r1 = st.columns(3)
r1[0].metric("Verlust (Simulation)", C.fmt_pct(live["blocking_sim"], 2))
r1[1].metric("Verlust (exakt, exponentielle Dauer)", C.fmt_pct(live["blocking_exact"], 2),
             help="Bei k = 0 (Erlang B) gilt dieser Wert für jede Verteilung der Dauer; mit Stellplätzen nur für die exponentielle.")
r1[2].metric("Abgewiesene Lkw je Stunde (Simulation)", f"{live['rejected_sim']:.0f}", help=f"Exakt (exponentiell): {live['rejected_exact']:.0f}.")
r2 = st.columns(3)
r2[0].metric("Auslastung der Spuren (Simulation)", C.fmt_pct(live["util_sim"], 1), help=f"Exakt: a(1 − B)/c = {C.fmt_pct(live['util_exact'], 1)}.")
r2[1].metric("Wartezeit der Angenommenen (Simulation)", _min(live["wait_sim"]), help=f"Exakt (exponentiell): {_min(live['wait_exact'])}.")
if live["wait_mmc"] is not None:
    r2[2].metric("Unbegrenzte Schlange (Erlang C, Stück 3)", _min(live["wait_mmc"]), help="Gleiche Spuren und Last, aber unbegrenzter Warteraum.")
else:
    r2[2].metric("Unbegrenzte Schlange (Erlang C, Stück 3)", "instabil", help="Bei Last ab 100 % wüchse die unbegrenzte Schlange ohne Ende.")

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Wie viele Lkw sind im Gate?**")
    st.plotly_chart(build_state_chart(live["pi_exact"], live["pi_sim"], c), width="stretch", key=f"state_{c}_{rho_pct}_{k}_{kind}_{seed}")
with col_b:
    st.markdown("**Verlust über die Last (exponentielle Dauer)**")
    st.plotly_chart(build_load_chart(c, k, a), width="stretch", key=f"load_{c}_{k}_{rho_pct}")
if kind != "exp" and k > 0:
    st.warning(
        f"Die exakte Zustandsverteilung und der exakte Verlust gelten nur für **exponentielle** Dauer. Bei {kind_label(kind)} und {k} Stellplätzen "
        "weicht die Simulation davon ab (Abschnitt „Wie wichtig ist die Streuung?“)."
    )
elif kind != "exp":
    st.success(f"Ohne Stellplätze gilt Erlang B auch bei Dauer {kind_label(kind)}: Simulation und exakter Wert stimmen bis auf Zufall überein.")
st.info(
    f"Von {C.fmt_int(round(a * C.TRUCKS_PER_ERLANG_HOUR))} Lkw je Stunde werden etwa **{live['rejected_sim']:.0f}** abgewiesen "
    f"({C.fmt_pct(live['blocking_sim'], 1)}); die Spuren sind dabei zu {C.fmt_pct(live['util_sim'], 0)} ausgelastet, nicht zu {rho_pct} %: "
    "abgewiesene Lkw belasten sie nicht."
)
st.caption(
    f"Ein Live-Lauf ist kurz ({C.fmt_int(C.LIVE_CUSTOMERS)} Ankünfte): bei kleinem Verlust zählt er nur wenige hundert abgewiesene Lkw und "
    "streut um Zehntel des Wertes. Die Studie unten mittelt je drei lange Läufe."
)

st.markdown("---")
st.subheader("📐 Wie viele Spuren für ein Verlustziel?")
st.markdown(
    f"Kleinste Spurzahl, bei der höchstens 1 % bzw. 0.1 % der Lkw abgewiesen werden (exponentielle Dauer, {k} Stellplätze), und die Last, die "
    "die Spuren dabei tragen. **Große Anlagen dürfen heißer laufen.**"
)
st.plotly_chart(build_sizing_chart(k), width="stretch", key=f"sizing_{k}")
rows = sizing_table(C.SIZING_OFFERS, C.SIZING_TARGETS, k)
by_offer = {}
for r in rows:
    by_offer.setdefault(r["a"], {})[r["target"]] = r
table = "| Angebot a (Erlang) | Lkw je Stunde | Spuren für 1 % | Last | Spuren für 0.1 % | Last |\n|---|---|---|---|---|---|\n"
for off in C.SIZING_OFFERS:
    r1_, r2_ = by_offer[off][0.01], by_offer[off][0.001]
    table += (f"| {off} | {C.fmt_int(round(off * C.TRUCKS_PER_ERLANG_HOUR))} | {r1_['c']} | {C.fmt_pct(r1_['rho'])} | {r2_['c']} | "
              f"{C.fmt_pct(r2_['rho'])} |\n")
st.markdown(table)
small, big = by_offer[C.SIZING_OFFERS[0]][0.01], by_offer[C.SIZING_OFFERS[-1]][0.01]
st.info(
    f"Bei Angebot {C.SIZING_OFFERS[0]} braucht ein Verlust von höchstens 1 % **{small['c']} Spuren** und trägt nur {C.fmt_pct(small['rho'])} Last je Spur; "
    f"bei Angebot {C.SIZING_OFFERS[-1]} reichen **{big['c']} Spuren** bei {C.fmt_pct(big['rho'])} Last."
)

st.markdown("---")
st.subheader("🔬 Wie wichtig ist die Streuung der Abfertigung?")
st.markdown(
    f"Abweichung des simulierten Verlusts von der **exponentiellen** Rechnung für {study_c} Spuren und Last {study_rho} %, je Verteilung der "
    f"Dauer und Zahl der Stellplätze; Fehlerbalken = Standardfehler. Je Zelle {pre['study_reps']} Läufe à {C.fmt_int(pre['study_customers'])} Ankünfte."
)
st.plotly_chart(build_insensitivity_chart(pre, study_c, study_rho), width="stretch", key=f"insens_{study_c}_{study_rho}")
header = "| Verteilung | " + " | ".join(f"k = {kk}" for kk in C.STUDY_K) + " |\n|---|" + "---|" * len(C.STUDY_K) + "\n"
body = ""
for kd in C.STUDY_KINDS:
    body += f"| {kind_label(kd)} | " + " | ".join(
        f"{100 * (study_cell(pre, study_c, study_rho, kk, kd)['blocking'] / study_cell(pre, study_c, study_rho, kk, kd)['blocking_exact'] - 1):+.0f} %"
        for kk in C.STUDY_K) + " |\n"
st.markdown(header + body)
d0 = [abs(study_cell(pre, study_c, study_rho, 0, kd)["blocking"] / study_cell(pre, study_c, study_rho, 0, kd)["blocking_exact"] - 1)
      for kd in C.STUDY_KINDS]
det_k, logn_k = (study_cell(pre, study_c, study_rho, study_k, kd) for kd in ("det", "logn"))
st.info(
    f"Ohne Stellplätze liegen alle vier Verteilungen höchstens {100 * max(d0):.1f} % neben Erlang B (Rauschen). Mit {study_k} Stellplätzen "
    f"verliert die feste Abfertigung {100 * (det_k['blocking'] / det_k['blocking_exact'] - 1):+.0f} %, die lognormale "
    f"{100 * (logn_k['blocking'] / logn_k['blocking_exact'] - 1):+.0f} % gegenüber der exponentiellen Rechnung."
    if study_k > 0 else
    f"Ohne Stellplätze liegen alle vier Verteilungen höchstens {100 * max(d0):.1f} % neben Erlang B (Rauschen): der Verlust hängt nicht von der "
    "Streuung der Dauer ab. Mit Stellplätzen (Regler links) verschwindet das."
)

st.markdown("---")
st.subheader("🔬 Was bringen Stellplätze?")
st.markdown(
    f"Verlust und mittlere Wartezeit der angenommenen Lkw über die Zahl der Stellplätze ({c} Spuren, Last {rho_pct} %, exponentielle Dauer, exakt)."
)
st.plotly_chart(build_stellplatz_chart(c, a, pre), width="stretch", key=f"stell_{c}_{rho_pct}")
b0, b10, b20 = F.blocking(c, a, 0), F.blocking(c, a, 10), F.blocking(c, a, 20)
st.info(
    f"Bei {c} Spuren und Last {rho_pct} % sinkt der Verlust von {C.fmt_pct(b0, 1)} (ohne Stellplätze) auf {C.fmt_pct(b10, 1)} mit 10 und "
    f"{C.fmt_pct(b20, 1)} mit 20 Stellplätzen; dafür warten die angenommenen Lkw im Mittel {_min(F.mean_wait_accepted(c, a, 10))} bzw. "
    f"{_min(F.mean_wait_accepted(c, a, 20))}. Bei Überlast bringt jeder Stellplatz weniger."
)

st.markdown("---")
st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Abgewiesene Lkw kommen nicht wieder** | Wer es später erneut versucht, erhöht das Angebot; Wiederholer machen das Verlustsystem schwerer zu rechnen. | kein Folgestück |
| **Verluste sind häufig genug zum Messen** | Bei Verlusten von einem Millionstel sieht ein gewöhnlicher Lauf kaum einen abgewiesenen Lkw; die Simulation braucht dann Tricks. | **[Seltene Ereignisse (Splitting)](https://sebastianhanisch-splitting-demo.streamlit.app/)** |
| **Mit Wartestellplätzen: exponentielle Dauer** | Die Streuung der Dauer verändert den Verlust stark (Abschnitt oben); für allgemeine Dauer gibt es hier keine Formel. | **[M/G/1, Kingman-Näherung](https://sebastianhanisch-mg1-kingman-demo.streamlit.app/)** |
| **Alle Lkw gleich wichtig** | Eilige Lkw dürfen nicht abgewiesen werden; das verschiebt den Verlust zwischen den Klassen. | **[Prioritätsklassen](https://sebastianhanisch-priority-queue-demo.streamlit.app/)** |
| **Konstante Ankunftsrate** | Echte Gates haben Wellen; Erlang B muss dann zu jeder Zeit mit dem aktuellen Angebot gerechnet werden. | **[Zeitvariable Ankünfte](https://sebastianhanisch-time-varying-arrivals-demo.streamlit.app/)** |
| **Ein Gate** | Abgewiesene Lkw laufen in die nächste Station (Straße, anderes Gate); Verluste fließen durch das Netz. | **[Jackson-Netze](https://sebastianhanisch-jackson-network-demo.streamlit.app/)** |
"""
)
st.caption(
    "Verwandt im Portfolio: [mmc-queue-demo](https://sebastianhanisch-mmc-queue-demo.streamlit.app/) (Stück 3: dieselben Spuren mit "
    "unbegrenzter Schlange, der Grenzfall k → ∞), [erlang-a-demo](https://sebastianhanisch-erlang-a-demo.streamlit.app/) (Stück 4: Abwanderung "
    "mit Geduld null ist Erlang B), [mm1-queue-demo](https://sebastianhanisch-mm1-queue-demo.streamlit.app/) (Stück 1), die "
    "Rettungsdienst-Demo [ems-demo](https://sebastianhanisch-ems-demo.streamlit.app/) (prüft ihr Hypercube-Modell an der Erlang-B-Formel) und die "
    "Hafen-Demo [truck-appointment-demo](https://sebastianhanisch-truck-appointment-demo.streamlit.app/) (Terminvergabe für Lkw)."
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** $M/G/c/(c+k)$: Poisson-Ankünfte mit Rate $\lambda$, mittlere Abfertigungsdauer 1, Angebot $a = \lambda$ (Erlang), $c$ Spuren, $k$
Wartestellplätze (FIFO); wer bei $c + k$ Lkw im Gate ankommt, geht verloren.

**Erlang B** ($k = 0$):
$$B(c, a) = \frac{a^c / c!}{\sum_{j=0}^{c} a^j / j!}, \qquad B_j = \frac{a\,B_{j-1}}{j + a\,B_{j-1}},\ B_0 = 1.$$
Die Formel gilt für **jede** Verteilung der Dauer mit Mittel 1 (Unempfindlichkeit des Erlang-Verlustsystems) und für jedes $a > 0$.

**Mit Stellplätzen, exponentielle Dauer** (Geburts-Sterbe-Kette): $\pi_n \propto a^n/n!$ für $n \le c$, $\pi_n \propto \pi_c\,(a/c)^{n-c}$ für
$c < n \le c+k$. Verlust $B = \pi_{c+k}$ (PASTA), Auslastung $a(1-B)/c$, mittlere Wartezeit der Angenommenen
$W_q = \sum_{n>c}(n-c)\pi_n / \bigl(a(1-B)\bigr)$ (Little). Für $k \to \infty$ und $a < c$ wird daraus die Erlang-C-Wartezeit aus Stück 3.

**Simulation.** Ereignisse Ankunft und Abgang (Abgänge in einem Heap), FIFO-Stellplätze, Zeitintegrale der Lkw im Gate und der beschäftigten
Spuren. Gegenproben: das Gesetz von Little gilt entlang jedes Pfades exakt; für exponentielle Dauer stimmen Verlust, Wartezeit und
Zustandsverteilung mit der Kette überein; ohne Stellplätze stimmen auch feste, gleichverteilte und lognormale Dauer mit Erlang B überein.

Implementiert in `erb_formulas.py` (Erlang B, Kette, Bemessung), `erb_simulation.py` (Verteilungen, Ereignisschleife), `erb_evaluation.py`
(Live-Lauf, Studienzelle), `generate_precomputed.py` (vorgerechnete Studie).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html))."
)
