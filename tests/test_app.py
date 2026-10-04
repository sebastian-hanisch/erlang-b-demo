"""AppTest-Rauchtests: Voreinstellung, jedes Preset, Randwerte, Würfel-Knopf, Permalink-Grenzen, Abschnitte, Footer."""

import random
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import erb_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(**state):
    at = AppTest.from_file(APP, default_timeout=600)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_default_run_has_no_exception_and_shows_the_reference_values():
    at = _run()
    _ok(at)
    assert _metric(at, "Verlust (exakt, exponentielle Dauer)") == "10.92 %"                  # B(20, 18) = Erlang B
    assert _metric(at, "Wartezeit der Angenommenen (Simulation)") == "0.00 min"               # ohne Stellplätze wartet niemand
    assert _metric(at, "Unbegrenzte Schlange (Erlang C, Stück 3)").endswith("min")
    assert float(_metric(at, "Abgewiesene Lkw je Stunde (Simulation)")) > 0


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_button_runs(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    assert (at.session_state["c_slider"], at.session_state["rho_slider"], at.session_state["k_select"], at.session_state["kind_select"]) == (
        p["c"], p["rho_pct"], p["k"], p["kind"])
    assert at.metric


def test_overload_has_no_stable_unbounded_queue():
    at = _run(rho_slider=120)
    _ok(at)
    assert _metric(at, "Unbegrenzte Schlange (Erlang C, Stück 3)") == "instabil"
    assert _metric(at, "Verlust (exakt, exponentielle Dauer)") == "25.71 %"


def test_stellplaetze_lower_the_exact_loss_in_the_app():
    loss = lambda at: float(_metric(at, "Verlust (exakt, exponentielle Dauer)").split()[0])
    assert loss(_run(k_select=0)) > loss(_run(k_select=2)) > loss(_run(k_select=10)) > loss(_run(k_select=20)) > 0


def test_warning_for_non_exponential_service_with_stellplaetze_and_hint_without():
    with_k = _run(kind_select="det", k_select=5)
    _ok(with_k)
    assert any("nur für **exponentielle** Dauer" in w.value for w in with_k.warning)
    without_k = _run(kind_select="logn", k_select=0)
    _ok(without_k)
    assert not without_k.warning and any("Erlang B auch bei" in s.value for s in without_k.success)
    assert not _run().warning and not _run().success


@pytest.mark.parametrize("kw", [dict(c_slider=5, rho_slider=130, k_select=20, kind_select="logn"), dict(c_slider=100, rho_slider=50, k_select=0),
                                 dict(c_slider=5, rho_slider=50, k_select=2, kind_select="unif"), dict(c_slider=60, rho_slider=100, k_select=10, kind_select="det"),
                                 dict(c_slider=15, rho_slider=70, k_select=5)])
def test_extreme_settings_run(kw):
    _ok(_run(**kw))


def test_dice_button_changes_the_seed_and_the_simulated_run(monkeypatch):
    """Der Würfel zieht sonst einen unseeded Zufalls-Seed; deshalb ist der gewürfelte Seed im Test fest, und verglichen werden die Daten
    des Diagramms der Zustandsverteilung (nicht eine gerundete Kennzahl)."""
    monkeypatch.setattr(random, "randint", lambda a, b: 508145)
    at = _run()
    old_seed, old = at.session_state["seed_input"], at.get("plotly_chart")[0].proto.spec
    next(b for b in at.button if b.label == "🎲 Neuen Lauf würfeln").click().run()
    _ok(at)
    assert at.session_state["seed_input"] == 508145 != old_seed and at.get("plotly_chart")[0].proto.spec != old


def test_permalink_values_are_clamped_and_snapped():
    at = AppTest.from_file(APP, default_timeout=600)
    at.query_params["c"] = "47"
    at.query_params["rho"] = "104"
    at.query_params["k"] = "7"
    at.query_params["kind"] = "det"
    at.run()
    _ok(at)
    assert at.session_state["c_slider"] == 45 and at.session_state["rho_slider"] == 100 and at.session_state["k_select"] == 5
    assert at.session_state["kind_select"] == "det"


def test_permalink_ignores_garbage_and_unknown_kinds():
    at = AppTest.from_file(APP, default_timeout=600)
    at.query_params["rho"] = "viel"
    at.query_params["kind"] = "zipf"
    at.query_params["k"] = "nan"
    at.run()
    _ok(at)
    assert at.session_state["rho_slider"] == C.DEFAULT_RHO_PCT and at.session_state["kind_select"] == C.DEFAULT_KIND
    assert at.session_state["k_select"] == C.DEFAULT_K


def test_charts_sections_and_limits_table_are_present():
    at = _run()
    _ok(at)
    assert len(at.get("plotly_chart")) == 5
    headers = [s.value for s in at.subheader]
    for part in ("Wie viele Spuren für ein Verlustziel", "Wie wichtig ist die Streuung", "Was bringen Stellplätze", "Wo die Annahmen enden"):
        assert any(part in h for h in headers), part
    table = next(m.value for m in at.markdown if "Wer setzt an" in m.value)
    for name in ("Splitting", "Kingman", "Prioritätsklassen", "Jackson-Netze", "Zeitvariable Ankünfte"):
        assert name in table
    assert "geplant" not in table      # die Linie wird erst vollständig veröffentlicht, kein Status-Zusatz


def test_sizing_and_insensitivity_tables_are_complete():
    at = _run()
    sizing = next(m.value for m in at.markdown if m.value.startswith("| Angebot a (Erlang) |"))
    assert "| 5 | 100 | 11 | 45 % | 14 | 36 % |" in sizing and "| 200 | 4.000 | 221 | 90 % | 238 | 84 % |" in sizing
    insens = next(m.value for m in at.markdown if m.value.startswith("| Verteilung |"))
    for label in ("exponentiell", "fest", "gleichverteilt (0 bis 2)", "lognormal (cv 2)"):
        assert f"| {label} |" in insens
    for k in C.STUDY_K:
        assert f"k = {k}" in insens


def test_seed_control_uses_the_portfolio_wording():
    at = _run()
    assert [n.label for n in at.number_input] == ["Zufalls-Seed"]


def test_related_demos_are_linked_and_footer_is_present():
    at = _run()
    text = " ".join(c.value for c in at.caption)
    for name in ("mmc-queue-demo", "erlang-a-demo", "mm1-queue-demo", "ems-demo", "truck-appointment-demo"):
        assert name in text
    assert "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in text


def test_no_sentence_wide_comma_replacement_in_the_app_source():
    """Regressionsschutz: `.replace(",", ".")` auf einem ganzen (verketteten) Satz macht aus Kommas im Fließtext Punkte; Tausender
    nur über `fmt_int`."""
    source = Path(APP).read_text(encoding="utf-8")
    assert '.replace(",", ".")' not in source
