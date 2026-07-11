"""Session-state setup and the glue between the Streamlit UI and the SEE engine.

ZERO server storage: everything lives in st.session_state for the browser
session only. Nothing is written to a server-side database or disk.
"""

import streamlit as st

from emission_factors import (
    FUELS, GRID_EF, PROCESS_EF, GWP_DEFAULT, AL_SMELTER_TECH_DEFAULT,
)
from cbam_meta import sector_names, routes_for, route_engine_key
from see_engine import FuelInput, compute_see, to_intensity, ProductionNotSetError
from style import inject_base_css, render_whatsapp_fab, render_sidebar_footer


# Friendly labels for the grid-EF selector.
GRID_CHOICES = list(GRID_EF.keys()) + ["custom"]
GRID_LABELS = {
    "national_v21": "National average — CEA V21.0, FY24-25 (0.7117)",
    "national_v20": "National average — CEA V20.0, FY23-24 (0.7270)",
    "captive_renewable_zero": "Captive renewable — documented (0.0)",
    "custom": "Custom (enter value + source)",
}

INPUT_BASES = ["Per tonne of product", "Annual total"]


# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------
def init_state() -> None:
    defaults = {
        # Module 1 — facility & product
        "company_name": "",
        "facility_name": "",
        "state_ut": "",
        "pin_code": "",
        "sector": sector_names()[0],
        "route": routes_for(sector_names()[0])[0],
        # Official CBAM default row id (from cbam_india_defaults); "" = none picked.
        "cbam_default_id": "",
        "cn_code": "",
        "reporting_year": 2026,
        "annual_production_t": 0.0,
        # Module 2 — fuel & energy
        "input_basis": INPUT_BASES[0],
        "fuels": [],          # list of {"id": int, "fuel_key": str}
        "_fuel_seq": 0,
        "electricity_value": 0.0,
        # C-15: biomass is zero-rated only with RED-II sustainability evidence.
        "biomass_sustainability_attested": False,
        "grid_ef_choice": "national_v21",
        "grid_ef_custom": 0.7117,
        "grid_ef_source": "",
        # Module 3 — process
        "steel_process_override": PROCESS_EF["steel_bf_bof_reduction"].value,
        "clinker_fraction": 0.90,
        "al_smelter_tech": AL_SMELTER_TECH_DEFAULT,
        "al_anode": PROCESS_EF["aluminium_anode_oxidation"].value,
        "al_cf4": PROCESS_EF["aluminium_cf4_per_t"].value,
        "al_c2f6": PROCESS_EF["aluminium_c2f6_per_t"].value,
        "fert_n2o": PROCESS_EF["fertiliser_nitric_acid_n2o"].value,
        "gwp_set": GWP_DEFAULT,
        # Module 3 — importer cost estimator (C-06). cert_price / export_vol keep
        # their ss.get() fallbacks (ETS reference / annual production) so they are
        # intentionally NOT seeded here.
        "cbam_benchmark": 0.0,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def setup_page(title: str) -> None:
    """Standard page header: config + logo + state init. Call first on each page."""
    st.set_page_config(
        page_title=f"Ecosetu CBAM — {title}",
        page_icon="assets/ecosetu_favicon.png",
        layout="centered",
    )
    try:
        st.logo("assets/ecosetu_logo_large.png", icon_image="assets/ecosetu_favicon.png")
    except Exception:
        pass
    inject_base_css()
    render_whatsapp_fab()
    render_sidebar_footer()
    init_state()


# ---------------------------------------------------------------------------
# Fuel-row management (stable ids so removals don't shift widget keys)
# ---------------------------------------------------------------------------
def add_fuel(fuel_key: str = "coke") -> None:
    # Data lives in the row dict (a plain session_state key) so it survives page
    # navigation. Widget keys (fuel_*_{id}) are transient and may be GC'd.
    st.session_state._fuel_seq += 1
    fid = st.session_state._fuel_seq
    f = FUELS[fuel_key]
    st.session_state.fuels.append({
        "id": fid,
        "fuel_key": fuel_key,
        "quantity": 0.0,
        "ncv": f.ncv_tj_per_t,
        "ef": f.ef_kgco2_per_tj,
    })


def remove_fuel(fid: int) -> None:
    st.session_state.fuels = [r for r in st.session_state.fuels if r["id"] != fid]
    for k in (f"fuel_sel_{fid}", f"fuel_qty_{fid}", f"fuel_ncv_{fid}", f"fuel_ef_{fid}"):
        st.session_state.pop(k, None)


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------
def resolve_grid_ef() -> float:
    choice = st.session_state.grid_ef_choice
    if choice == "custom":
        return float(st.session_state.get("grid_ef_custom", 0.0))
    # C-08: a restored save may hold a grid key that has since been removed
    # (e.g. the retired regional factors). Fall back to the national default
    # rather than KeyError-ing on resume.
    if choice not in GRID_EF:
        st.session_state.grid_ef_choice = "national_v21"
        choice = "national_v21"
    return GRID_EF[choice].value


def _process_kwargs() -> dict:
    s = st.session_state
    sector = s.sector
    if sector == "Iron & Steel":
        return {"override": s.steel_process_override}
    if sector == "Cement":
        return {"clinker_fraction": s.clinker_fraction}
    if sector == "Aluminium":
        # C-01: only the primary (Hall-Heroult) route has anode + PFC process
        # emissions. Secondary/downstream are combustion + electricity only.
        if route_engine_key(sector, s.route) == "aluminium_primary":
            return {
                "anode_override": s.al_anode,
                "cf4_kg_per_t": s.al_cf4,
                "c2f6_kg_per_t": s.al_c2f6,
            }
        return {}
    if sector == "Fertilisers" and s.route == "Nitric acid":
        return {"n2o_kg_per_t": s.fert_n2o}
    return {}


# ---------------------------------------------------------------------------
# Build engine inputs from session state and compute SEE
# ---------------------------------------------------------------------------
def annual_basis_missing_production() -> bool:
    """C-14: True when inputs are on an annual basis but production is not set.

    Callers should surface a validation message and skip computing rather than
    letting build_see() raise (or, previously, silently produce all-zero SEE).
    """
    s = st.session_state
    return s.input_basis == "Annual total" and float(s.annual_production_t) <= 0


def build_see():
    s = st.session_state
    basis_annual = s.input_basis == "Annual total"
    prod = s.annual_production_t

    fuels = []
    for row in s.fuels:
        qty = float(row.get("quantity", 0.0))
        if basis_annual:
            qty = to_intensity(qty, prod)
        fuels.append(
            FuelInput(
                row["fuel_key"],
                qty,
                ncv_tj_per_t=float(row.get("ncv", 0.0)),
                ef_kgco2_per_tj=float(row.get("ef", 0.0)),
            )
        )

    elec = float(s.electricity_value)
    if basis_annual:
        elec = to_intensity(elec, prod)

    return compute_see(
        sector=s.sector,
        fuels=fuels,
        process_route=route_engine_key(s.sector, s.route),
        process_kwargs=_process_kwargs(),
        electricity_mwh_per_t=elec,
        grid_ef=resolve_grid_ef(),
        gwp_set=s.gwp_set,
    )
