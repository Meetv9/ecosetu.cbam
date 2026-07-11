"""Module 2 — Fuel & Energy Inputs.

Fuel data is stored in the row dicts inside ss.fuels (a plain key, so it
persists across pages). Single inputs mirror into plain keys too.
"""

import streamlit as st

from state import (
    setup_page, add_fuel, remove_fuel, INPUT_BASES, GRID_CHOICES, GRID_LABELS,
)
from style import render_pagehead, render_footer
from emission_factors import FUELS, GRID_EF_FLAG

setup_page("Fuel & Energy")
ss = st.session_state

render_pagehead(
    "Step 2 of 5 · Fuel & Energy",
    "Fuel & Energy Inputs",
    "Add each combustion fuel and your electricity use. Defaults come from IPCC 2006 "
    "and CEA — edit any value you have better data for.",
)

ss.input_basis = st.radio(
    "How are you entering quantities?", INPUT_BASES,
    index=INPUT_BASES.index(ss.input_basis), key="w_basis", horizontal=True,
    help="Per-tonne values are used directly. Annual totals are divided by your "
         "annual production from Module 1.",
)
qty_unit = "t fuel / t product" if ss.input_basis == INPUT_BASES[0] else "t fuel / year"
elec_unit = "MWh / t product" if ss.input_basis == INPUT_BASES[0] else "MWh / year"

# ---------------------------------------------------------------------------
# Fuel table
# ---------------------------------------------------------------------------
st.subheader("Fuels (combustion)")
st.caption("NCV and EF auto-fill from IPCC 2006 when you pick a fuel — edit them "
           "if you have CEA parameters or lab analysis (recommended for Indian coal).")

# C-10: for hydrogen (SMR / coal gasification), the feedstock carbon leaves as CO2
# and there is no separate process term in the engine — so it is only counted if
# the user enters the TOTAL natural gas (feed + fuel). Make that explicit.
if ss.sector == "Hydrogen":
    st.info(
        "**Hydrogen (SMR / coal gasification):** enter your **total** natural gas "
        "or coal — the reforming/gasification **feedstock PLUS any process fuel** — "
        "as a combustion fuel below. The feedstock carbon is emitted as CO₂ and is "
        "captured here (there is no separate process-emission term), so leaving out "
        "the feedstock would under-count your SEE. Use the natural-gas or coal row "
        "and set the quantity to feed + fuel combined."
    )

_fuel_keys = list(FUELS.keys())
_fuel_labels = [FUELS[k].label for k in _fuel_keys]

if ss.fuels:
    h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 1])
    h1.markdown("**Fuel**")
    h2.markdown(f"**Qty** ({qty_unit})")
    h3.markdown("**NCV** (TJ/t)")
    h4.markdown("**EF** (kgCO₂/TJ)")
    h5.markdown("**​**")
else:
    st.info("No fuels added yet — click **Add fuel** below.")

for row in list(ss.fuels):
    fid = row["id"]
    sel_key, qty_key = f"fuel_sel_{fid}", f"fuel_qty_{fid}"
    ncv_key, ef_key = f"fuel_ncv_{fid}", f"fuel_ef_{fid}"

    # Seed widget state from the persistent row dict (first render, or after
    # Streamlit garbage-collects widget keys on page navigation).
    ss.setdefault(sel_key, FUELS[row["fuel_key"]].label)
    ss.setdefault(qty_key, float(row["quantity"]))
    ss.setdefault(ncv_key, float(row["ncv"]))
    ss.setdefault(ef_key, float(row["ef"]))

    # Detect a fuel change from the persisted selectbox value BEFORE any widget in
    # this row renders, so we can push the new fuel's defaults into the NCV/EF
    # widget state (setting a widget key before it renders DOES override it; the
    # `value=` parameter would be ignored once the key already exists).
    chosen_key = _fuel_keys[_fuel_labels.index(ss[sel_key])]
    if chosen_key != row["fuel_key"]:
        row["fuel_key"] = chosen_key
        row["ncv"] = FUELS[chosen_key].ncv_tj_per_t
        row["ef"] = FUELS[chosen_key].ef_kgco2_per_tj
        ss[ncv_key] = row["ncv"]
        ss[ef_key] = row["ef"]

    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
    c1.selectbox("Fuel", _fuel_labels, key=sel_key, label_visibility="collapsed")
    c2.number_input("Qty", min_value=0.0, step=0.01, format="%.4f",
                    key=qty_key, label_visibility="collapsed")
    c3.number_input("NCV", min_value=0.0, step=0.1, format="%.2f",
                    key=ncv_key, label_visibility="collapsed")
    c4.number_input("EF", min_value=0.0, step=0.1, format="%.1f",
                    key=ef_key, label_visibility="collapsed")
    if c5.button("✕", key=f"fuel_rm_{fid}", help="Remove this fuel"):
        remove_fuel(fid)
        st.rerun()

    # Mirror widget values back into the persistent row dict (source of truth).
    row["quantity"] = float(ss[qty_key])
    row["ncv"] = float(ss[ncv_key])
    row["ef"] = float(ss[ef_key])

    lib_ncv = FUELS[row["fuel_key"]].ncv_tj_per_t
    if abs(row["ncv"] - lib_ncv) > 1e-9:
        c3.caption(f"≠ IPCC default {lib_ncv}")

if st.button("➕ Add fuel"):
    add_fuel()
    st.rerun()

# ---------------------------------------------------------------------------
# C-15: biogenic zero-rating attestation. Biomass combustion CO2 is reported as
# net-zero ONLY if the biomass meets CBAM sustainability criteria (RED II). Keep
# the zero-rating, but require the producer to attest that they hold the evidence
# and record that attestation in the payload for the importer/verifier.
# ---------------------------------------------------------------------------
from emission_factors import BIOGENIC_FUELS  # noqa: E402

_has_biogenic = any(r["fuel_key"] in BIOGENIC_FUELS for r in ss.fuels)
if _has_biogenic:
    ss.biomass_sustainability_attested = st.checkbox(
        "I hold RED II-compliant sustainability documentation for the biomass "
        "claimed as zero-rated.",
        value=bool(ss.biomass_sustainability_attested), key="w_biomass_attest",
    )
    if not ss.biomass_sustainability_attested:
        st.warning(
            "Biomass is being zero-rated. CBAM only allows zero-rating of biogenic "
            "CO₂ where the biomass meets EU sustainability criteria (RED II) and you "
            "hold the evidence. Without it, a verifier may treat this biomass as "
            "fossil-equivalent. Your attestation is recorded in the exported payload."
        )

# ---------------------------------------------------------------------------
# Electricity
# ---------------------------------------------------------------------------
st.subheader("Electricity")
ss.electricity_value = st.number_input(
    f"Electricity consumed ({elec_unit})", min_value=0.0, step=0.01, format="%.4f",
    value=float(ss.electricity_value), key="w_elec",
)

# C-08/C-16: a restored save may hold a grid key that no longer exists (e.g. a
# retired regional factor). Fall back to the national default instead of raising.
if ss.grid_ef_choice not in GRID_CHOICES:
    ss.grid_ef_choice = "national_v21"
ss.grid_ef_choice = st.selectbox(
    "Grid emission factor", GRID_CHOICES,
    index=GRID_CHOICES.index(ss.grid_ef_choice), key="w_grid",
    format_func=lambda k: GRID_LABELS[k],
)
if ss.grid_ef_choice == "custom":
    cc1, cc2 = st.columns([1, 2])
    ss.grid_ef_custom = cc1.number_input(
        "Custom grid EF (tCO₂/MWh)", min_value=0.0, step=0.01, format="%.4f",
        value=float(ss.grid_ef_custom), key="w_gridcustom",
    )
    ss.grid_ef_source = cc2.text_input(
        "Source / documentation", value=ss.grid_ef_source, key="w_gridsrc",
        placeholder="e.g. PPA contract, captive meter reading",
    )

st.warning(GRID_EF_FLAG)

st.divider()
cprev, cnext = st.columns(2)
cprev.page_link("pages/1_Facility_Setup.py", label="← Back: Facility")
cnext.page_link("pages/3_Process_and_Results.py", label="Next: Process & Results →")

render_footer()
