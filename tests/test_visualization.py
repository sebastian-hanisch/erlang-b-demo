"""Abbildungen: gesperrte Achsen, Zahl der Linien, Beschriftungen."""

import erb_constants as C
import erb_evaluation as E
import erb_formulas as F
import erb_visualization as V

PRE = E.load_precomputed()


def _locked(fig):
    return all(ax.fixedrange for ax in fig.select_xaxes()) and all(ax.fixedrange for ax in fig.select_yaxes())


def test_all_charts_lock_their_axes():
    live = E.live_report(10, 90, 3, "exp", seed=1, customers=5_000)
    figs = [V.build_state_chart(live["pi_exact"], live["pi_sim"], 10), V.build_load_chart(10, 3, 9.0), V.build_sizing_chart(0),
            V.build_insensitivity_chart(PRE, 20, 100), V.build_stellplatz_chart(10, 9.0, PRE)]
    assert all(_locked(f) for f in figs)
    assert figs[4].layout.yaxis2.fixedrange                         # auch die rechte Achse ist gesperrt


def test_kind_labels_cover_every_kind():
    assert [V.kind_label(k) for k in C.KINDS] == ["exponentiell", "fest", "gleichverteilt (0 bis 2)", "lognormal (cv 2)"]


def test_state_chart_marks_the_stellplaetze_in_a_lighter_colour():
    fig = V.build_state_chart([0.5, 0.3, 0.2], [0.5, 0.3, 0.2], 1)
    assert list(fig.data[0].marker.color) == [V.EXACT_COLOR, V.EXACT_COLOR, V.QUEUE_COLOR]


def test_load_chart_has_a_stellplatz_line_only_with_stellplaetzen():
    assert len(V.build_load_chart(10, 0, 9.0).data) == 2 and len(V.build_load_chart(10, 5, 9.0).data) == 3


def test_sizing_chart_has_one_line_per_target_and_rising_load():
    fig = V.build_sizing_chart(0)
    assert len(fig.data) == len(C.SIZING_TARGETS)
    ys = list(fig.data[0].y)
    assert all(a < b for a, b in zip(ys, ys[1:]))                    # große Anlagen tragen mehr Last (Skalenvorteil)


def test_insensitivity_chart_has_one_line_per_kind_and_zero_deviation_for_the_exact_kind():
    fig = V.build_insensitivity_chart(PRE, 20, 100)
    assert [t.name for t in fig.data] == [V.kind_label(k) for k in C.STUDY_KINDS]
    assert all(abs(y) < 5 for y in fig.data[0].y)


def test_stellplatz_chart_shows_falling_loss_and_rising_wait():
    fig = V.build_stellplatz_chart(10, 9.0, PRE)
    assert fig.data[0].y[0] == 100 * F.blocking(10, 9.0, 0) and fig.data[0].y[-1] < fig.data[0].y[0]
    assert fig.data[1].y[0] == 0.0 and fig.data[1].y[-1] > fig.data[1].y[1]


def test_state_chart_starts_at_zero_trucks_not_below():
    fig = V.build_state_chart([0.5, 0.3, 0.2], [0.5, 0.3, 0.2], 1)
    assert tuple(fig.layout.xaxis.range) == (-0.7, 2.7)
