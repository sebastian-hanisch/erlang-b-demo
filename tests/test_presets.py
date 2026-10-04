"""Presets: Vollständigkeit, gültige Werte, Permalink-Konstanten."""

import pytest

import erb_constants as C
import erb_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) == set(C.PRESET_ORDER) and len(C.PRESETS) == 4
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS) and C.PRESET_HELP[name]


def test_preset_values_are_valid_and_match_the_setting_specs():
    for preset in C.PRESETS.values():
        assert C.C_MIN <= preset["c"] <= C.C_MAX and P.snap_c(preset["c"]) == preset["c"]
        assert C.RHO_PCT_MIN <= preset["rho_pct"] <= C.RHO_PCT_MAX and P.snap_rho(preset["rho_pct"]) == preset["rho_pct"]
        assert preset["k"] in C.K_OPTIONS and preset["kind"] in C.KINDS
        for key, state_key in P.PRESET_KEYS.items():
            P.SETTING_SPECS[state_key].caster(preset[key])


def test_preset_names_state_the_values_they_set():
    assert C.PRESETS["Mit 10 Stellplätzen"]["k"] == 10 and C.PRESETS["Überlast (120 %)"]["rho_pct"] == 120
    p = C.PRESETS["Feste Abfertigung, 5 Stellplätze"]
    assert (p["kind"], p["k"], p["c"], p["rho_pct"]) == ("det", 5, 10, 100)
    assert C.PRESETS["Gate ohne Warteraum (Erlang B)"]["k"] == 0


def test_default_preset_equals_the_default_settings():
    p = C.PRESETS["Gate ohne Warteraum (Erlang B)"]
    assert (p["c"], p["rho_pct"], p["k"], p["kind"], p["seed"]) == (C.DEFAULT_C, C.DEFAULT_RHO_PCT, C.DEFAULT_K, C.DEFAULT_KIND, C.DEFAULT_SEED)


def test_bounds_and_url_params():
    assert P.bounds("seed_input") == (0, C.SEED_MAX) and P.bounds("c_slider") == (5, 100) and P.bounds("rho_slider") == (50, 130)
    assert len({spec.url_param for spec in P.SETTING_SPECS.values()}) == len(P.SETTING_SPECS)


@pytest.mark.parametrize("value,expected", [(3, 2), (7, 5), (30, 20), (6, 5), (8, 10)])
def test_k_snaps_to_the_nearest_option(value, expected):
    assert P.snap_to_option("k_select", value) == expected                       # Optionen 0, 2, 5, 10, 20


@pytest.mark.parametrize("value,expected", [(0, 5), (7, 5), (8, 10), (52, 50), (99, 100), (150, 100)])
def test_spuren_snap_to_the_step_inside_the_bounds(value, expected):
    assert P.snap_c(value) == expected


@pytest.mark.parametrize("value,expected", [(0, 50), (54, 50), (56, 60), (94, 90), (96, 100), (200, 130)])
def test_load_snaps_to_the_step_inside_the_bounds(value, expected):
    assert P.snap_rho(value) == expected


def test_formatters():
    assert C.fmt_int(150000) == "150.000" and C.fmt_pct(0.2) == "20 %" and C.fmt_pct(0.0898, 1) == "9.0 %"
