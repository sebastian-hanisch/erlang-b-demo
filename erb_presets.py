"""SETTING_SPECS-Permalink-Muster, Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).
Alle Regler sind immer sichtbar - es gibt keinen ausblendbaren Regler (also auch kein KEPT-Muster)."""

import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import erb_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


SETTING_SPECS = {
    "c_slider": SettingSpec("c", int, C.DEFAULT_C, C.C_MIN, C.C_MAX),
    "rho_slider": SettingSpec("rho", int, C.DEFAULT_RHO_PCT, C.RHO_PCT_MIN, C.RHO_PCT_MAX),
    "k_select": SettingSpec("k", int, C.DEFAULT_K, C.K_OPTIONS[0], C.K_OPTIONS[-1]),
    "kind_select": SettingSpec("kind", str, C.DEFAULT_KIND),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
}
PRESET_KEYS = {"c": "c_slider", "rho_pct": "rho_slider", "k": "k_select", "kind": "kind_select", "seed": "seed_input"}
OPTIONS = {"k_select": C.K_OPTIONS}                       # Regler, die nur feste Stufen kennen


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def snap_to_option(state_key, value):
    """Regler mit festen Stufen: ein Permalink-Wert dazwischen rastet auf die nächste Stufe ein (bei Gleichstand auf die kleinere)."""
    return min(OPTIONS[state_key], key=lambda o: (abs(o - value), o))


def snap_step(value, lo, hi, step):
    """Wert rastet auf das nächste Vielfache der Schrittweite innerhalb der Grenzen ein."""
    snapped = round(value / step) * step
    return int(min(hi, max(lo, snapped)))


def snap_c(value):
    return snap_step(value, C.C_MIN, C.C_MAX, C.C_STEP)


def snap_rho(value):
    return snap_step(value, C.RHO_PCT_MIN, C.RHO_PCT_MAX, C.RHO_PCT_STEP)


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if value != value:                     # NaN
                    continue
                if state_key == "kind_select":
                    if value not in C.KINDS:
                        continue
                else:
                    if spec.lo is not None:
                        value = max(spec.lo, value)
                    if spec.hi is not None:
                        value = min(spec.hi, value)
                    if state_key in OPTIONS:
                        value = snap_to_option(state_key, value)
                    if state_key == "c_slider":
                        value = snap_c(value)
                    if state_key == "rho_slider":
                        value = snap_rho(value)
                st.session_state[state_key] = value
            except (ValueError, TypeError):
                pass
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][key]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
