"""Plotly-Abbildungen der Erlang-B-Demo: Zustandsverteilung des Gates, Verlust über die Last, Bemessung (Auslastung bei Verlustziel),
Streuung der Abfertigung (Abweichung von der exponentiellen Rechnung), Stellplätze (Verlust und Wartezeit). Achsen sind gesperrt
(fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen."""

import plotly.graph_objects as go

import erb_constants as C
import erb_evaluation as E
import erb_formulas as F

SIM_COLOR = "#f58518"
EXACT_COLOR = "#4c78a8"
QUEUE_COLOR = "#9ecae9"
KIND_COLORS = {"exp": "#4c78a8", "det": "#e45756", "unif": "#72b7b2", "logn": "#b279a2"}


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height, legend_y=-0.25, top=10):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=top, b=10), legend=dict(orientation="h", y=legend_y),
                      plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def kind_label(kind):
    return C.KIND_LABELS[kind]


def build_state_chart(pi_exact, pi_sim, c):
    """Anteil der Zeit mit n Lkw im Gate: exakt (exponentielle Dauer, Balken; die Plätze hinter den Spuren heller) gegen Simulation (Punkte)."""
    ns = list(range(len(pi_exact)))
    colors = [EXACT_COLOR if n <= c else QUEUE_COLOR for n in ns]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ns, y=pi_exact, marker_color=colors, name="exakt (exponentielle Dauer)"))
    fig.add_trace(go.Scatter(x=ns, y=pi_sim, mode="markers", marker=dict(color=SIM_COLOR, size=8), name="Simulation"))
    fig.add_vline(x=c + 0.5, line=dict(color="#9d9d9d", dash="dash"))
    fig.update_xaxes(title_text="Lkw im Gate (links der Linie: Spuren, rechts: Stellplätze)", dtick=max(1, len(ns) // 12),
                     range=[-0.7, len(ns) - 0.3])
    fig.update_yaxes(title_text="Anteil der Zeit")
    return _base(fig, 340)


def build_load_chart(c, k, a_now):
    """Verlustwahrscheinlichkeit über das Angebot (exponentielle Dauer): ohne Stellplätze (Erlang B) und mit den gewählten; Punkt = Einstellung."""
    xs = [c * f / 100 for f in range(10, 161, 2)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=[100 * F.blocking(c, a, 0) for a in xs], mode="lines", line=dict(color="#9d9d9d", width=2.5, dash="dot"),
                             name="ohne Stellplätze (Erlang B)"))
    if k > 0:
        fig.add_trace(go.Scatter(x=xs, y=[100 * F.blocking(c, a, k) for a in xs], mode="lines", line=dict(color=EXACT_COLOR, width=2.5),
                                 name=f"mit {k} Stellplätzen"))
    fig.add_trace(go.Scatter(x=[a_now], y=[100 * F.blocking(c, a_now, k)], mode="markers", marker=dict(color=SIM_COLOR, size=12),
                             name="gewählte Einstellung"))
    fig.add_vline(x=c, line=dict(color="#9d9d9d", dash="dash"), annotation_text="Last 100 %")
    fig.update_xaxes(title_text=f"Angebot a in Erlang ({c} Spuren)")
    fig.update_yaxes(title_text="Verlust in %", ticksuffix=" %", rangemode="tozero")
    return _base(fig, 340)


def build_sizing_chart(k):
    """Last je Spur (a/c), die bei Verlustziel 1 % bzw. 0.1 % erreichbar ist, über das Angebot: große Anlagen dürfen heißer laufen."""
    offers = [2, 3, 5, 8, 10, 15, 20, 30, 50, 80, 100, 150, 200, 300]
    fig = go.Figure()
    for target, dash in zip(C.SIZING_TARGETS, ("solid", "dash")):
        rhos = [100 * a / F.min_servers(a, target, k) for a in offers]
        fig.add_trace(go.Scatter(x=offers, y=rhos, mode="lines+markers", line=dict(color=EXACT_COLOR, width=2.5, dash=dash),
                                 name=f"Verlust höchstens {C.fmt_pct(target, 1 if target < 0.01 else 0)}"))
    fig.update_xaxes(title_text="Angebot a in Erlang (logarithmisch)", type="log", tickvals=[2, 5, 10, 20, 50, 100, 300],
                     ticktext=["2", "5", "10", "20", "50", "100", "300"])
    fig.update_yaxes(title_text="erreichbare Last je Spur", ticksuffix=" %", range=[0, 100])
    return _base(fig, 340)


def build_insensitivity_chart(pre, c, rho_pct):
    """Abweichung des simulierten Verlusts von der exponentiellen Rechnung (in %) über die Zahl der Stellplätze, je Verteilung der Dauer;
    Fehlerbalken = Standardfehler. Bei k = 0 liegen alle auf der Null (Erlang B ist unempfindlich)."""
    fig = go.Figure()
    for kind in C.STUDY_KINDS:
        ys, errs = [], []
        for k in C.STUDY_K:
            cell = E.study_cell(pre, c, rho_pct, k, kind)
            ex = cell["blocking_exact"]
            ys.append(100 * (cell["blocking"] / ex - 1))
            errs.append(100 * (cell["blocking_se"] or 0.0) / ex)
        fig.add_trace(go.Scatter(x=list(C.STUDY_K), y=ys, mode="lines+markers", line=dict(color=KIND_COLORS[kind], width=2.5),
                                 error_y=dict(type="data", array=errs, visible=True), name=kind_label(kind)))
    fig.add_hline(y=0, line=dict(color="#9d9d9d", dash="dash"))
    fig.update_xaxes(title_text="Wartestellplätze k", tickvals=list(C.STUDY_K))
    fig.update_yaxes(title_text="Abweichung des Verlusts von der exponentiellen Rechnung", ticksuffix=" %")
    return _base(fig, 340)


def build_stellplatz_chart(c, a, pre):
    """Verlust (links) und mittlere Wartezeit der Angenommenen in Minuten (rechts) über die Zahl der Stellplätze, exponentielle Dauer exakt."""
    ks = list(range(0, 31))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ks, y=[100 * F.blocking(c, a, k) for k in ks], mode="lines", line=dict(color=EXACT_COLOR, width=2.5),
                             name="Verlust (links)"))
    fig.add_trace(go.Scatter(x=ks, y=[F.to_minutes(F.mean_wait_accepted(c, a, k)) for k in ks], mode="lines",
                             line=dict(color=SIM_COLOR, width=2.5, dash="dash"), name="Wartezeit der Angenommenen (rechts)", yaxis="y2"))
    fig.update_layout(yaxis2=dict(title="Wartezeit in Minuten", overlaying="y", side="right", rangemode="tozero", fixedrange=True))
    fig.update_xaxes(title_text="Wartestellplätze k")
    fig.update_yaxes(title_text="Verlust in %", ticksuffix=" %", rangemode="tozero")
    return _base(fig, 340)
