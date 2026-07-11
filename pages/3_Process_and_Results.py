"""Module 3 — Process Emissions + live SEE results."""

import pandas as pd
import streamlit as st

from state import setup_page, build_see, annual_basis_missing_production
from style import render_pagehead, render_footer
from emission_factors import (
    REGULATION_SNAPSHOT, PROCESS_EF, GWP_SETS,
    EU_ETS_REFERENCE, INDIA_CARBON_PRICE, AL_SMELTER_TECH,
    CBAM_FACTOR_SCHEDULE, CBAM_DE_MINIMIS_T,
)
from cbam_meta import functional_unit, route_engine_key
from cbam_india_defaults import by_id, VINTAGE as CBAM_DEFAULTS_VINTAGE
from cost_engine import cost_breakdown, cbam_factor, net_certificate_price

setup_page("Process & Results")

sector = st.session_state.sector
route = st.session_state.route
unit = functional_unit(sector)

render_pagehead(
    "Step 3 of 5 · Process & Results",
    "Process Emissions & Results",
    "Process emissions complete your SEE. See it compared to the CBAM default and the "
    "indicative certificate cost below.",
)

# ---------------------------------------------------------------------------
# Sector-specific process inputs
# ---------------------------------------------------------------------------
st.subheader("Process emissions")

ss = st.session_state

if sector == "Iron & Steel":
    st.caption("Iron-ore reduction CO₂ (IPCC 2006: 0.18 tCO₂/t crude steel). Edit if "
               "you have route-specific data.")
    ss.steel_process_override = st.number_input(
        "Process EF (tCO₂ / t product)", min_value=0.0, step=0.01, format="%.3f",
        value=float(ss.steel_process_override), key="w_steel_proc")

elif sector == "Cement":
    st.caption("Clinker calcination = 0.5246 tCO₂/t clinker × your clinker fraction.")
    ss.clinker_fraction = st.number_input(
        "Clinker fraction (t clinker / t cement)", min_value=0.0, max_value=1.0,
        step=0.01, format="%.2f", value=float(ss.clinker_fraction), key="w_clinker")

elif sector == "Aluminium" and route_engine_key(sector, route) == "aluminium_primary":
    st.caption("Anode oxidation + PFC anode-effect emissions (GWP-applied). These "
               "arise ONLY in primary Hall-Héroult reduction.")

    # C-02: pick the cell technology → seeds Tier-1 CF₄/C₂F₆ from IPCC Table 4.15.
    tech_opts = list(AL_SMELTER_TECH.keys())
    if ss.al_smelter_tech not in tech_opts:  # guard restored/removed tech names
        ss.al_smelter_tech = tech_opts[0]
    prev_tech = ss.al_smelter_tech
    ss.al_smelter_tech = st.selectbox(
        "Smelter cell technology", tech_opts, index=tech_opts.index(ss.al_smelter_tech),
        key="w_al_tech",
        help="Sets IPCC 2006 Table 4.15 Tier-1 PFC defaults. Most Indian smelters "
             "are point-feed prebake (CWPB). Override the values below if you have "
             "measured (Tier-2/3) anode-effect data.")
    if ss.al_smelter_tech != prev_tech:
        t = AL_SMELTER_TECH[ss.al_smelter_tech]
        ss.al_cf4, ss.al_c2f6 = t["cf4"], t["c2f6"]
        for k in ("w_al_cf4", "w_al_c2f6"):
            ss.pop(k, None)
        st.rerun()

    a1, a2, a3 = st.columns(3)
    ss.al_anode = a1.number_input("Anode oxidation (tCO₂/t Al)", min_value=0.0, step=0.01,
                                  format="%.3f", value=float(ss.al_anode), key="w_al_anode")
    ss.al_cf4 = a2.number_input("CF₄ (kg/t Al)", min_value=0.0, step=0.01, format="%.3f",
                                value=float(ss.al_cf4), key="w_al_cf4")
    ss.al_c2f6 = a3.number_input("C₂F₆ (kg/t Al)", min_value=0.0, step=0.01, format="%.3f",
                                 value=float(ss.al_c2f6), key="w_al_c2f6")

elif sector == "Aluminium":
    st.caption("Secondary (scrap melting) and downstream processing have **no "
               "reduction-cell process emissions** — your SEE is combustion + "
               "electricity only. (Anode/PFC emissions apply to primary smelting.)")

elif sector == "Fertilisers" and route == "Nitric acid":
    st.caption("N₂O from catalytic oxidation (IPCC default 4.8 kg/t HNO₃; GWP-applied).")
    ss.fert_n2o = st.number_input(
        "N₂O (kg / t HNO₃)", min_value=0.0, step=0.1, format="%.2f",
        value=float(ss.fert_n2o), key="w_fert_n2o")
else:
    st.caption("No separate process-emission input for this route (combustion-only).")

ss.gwp_set = st.selectbox(
    "GWP set", list(GWP_SETS.keys()), index=list(GWP_SETS.keys()).index(ss.gwp_set),
    key="w_gwp", help="EU practice defaults to AR5; AR6 is an opt-in.")

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Specific Embedded Emissions (SEE)")

# C-14: annual-basis inputs need a production denominator; without it the SEE
# would silently read as zero. Block and point the user back to Facility Setup.
if annual_basis_missing_production():
    st.error(
        "You entered fuel/energy on an **annual total** basis, but annual "
        "production is 0. Enter your annual production in **Step 1 · Facility "
        "Setup** (or switch to a per-tonne basis in Step 2) to compute your SEE."
    )
    st.page_link("pages/1_Facility_Setup.py", label="← Go to Facility Setup")
    render_footer()
    st.stop()

result = build_see()

st.metric(f"TOTAL SEE  (tCO₂e per {unit})", f"{result.total_see:.3f}")

df = pd.DataFrame(result.as_rows(), columns=["Component", "tCO₂e / t"])
st.dataframe(df, hide_index=True, use_container_width=True)

if not result.indirect_included and result.informational_indirect > 0:
    st.caption(
        f"Note: for {sector}, electricity (Scope 2) is **not** part of CBAM SEE. "
        f"Your electricity emissions of {result.informational_indirect:.3f} tCO₂e/t "
        "are shown for your own tracking only."
    )

st.caption(
    f"GWP basis: {result.gwp_set} · "
    f"Regulation snapshot: {REGULATION_SNAPSHOT['snapshot_date']} · "
    f"Grid factor: {REGULATION_SNAPSHOT['cea_grid_version']} · "
    f"Verify current rules at {REGULATION_SNAPSHOT['verify_at']}"
)

st.info(
    "Self-calculated estimate — not verified data. Statutory CBAM verification "
    "requires an accredited third-party verifier (ISO 17029 + ISO 14065)."
)

# ---------------------------------------------------------------------------
# CBAM default-value comparison
# ---------------------------------------------------------------------------
st.divider()
st.subheader("CBAM default comparison")

year = int(ss.reporting_year)
d = by_id(ss.get("cbam_default_id", "")) if ss.get("cbam_default_id") else None
your_see = result.total_see

if d is None:
    st.info(
        "No official CBAM default value selected. Pick your exact CN product in "
        "**Step 1 · Facility Setup** to compare your SEE against the official "
        "EU default value."
    )
else:
    default_plain = d.total
    default_marked = d.marked(year)

    st.caption(f"Official default for **{d.cn_display} — {d.description}** "
               f"({d.section}). Source: {CBAM_DEFAULTS_VINTAGE}.")

    m1, m2, m3 = st.columns(3)
    m1.metric("Your SEE", f"{your_see:.3f}")
    m2.metric("CBAM default", f"{default_plain:.3f}")
    m3.metric(f"Default + {year} mark-up", f"{default_marked:.3f}")

    if year < 2026:
        st.caption(f"{year} is before the definitive period (2026); showing the "
                   "base default (mark-ups apply from 2026).")

    if your_see < default_marked:
        st.success(
            f"Your calculated SEE is **{default_marked - your_see:.3f} tCO₂e/t lower** "
            "than the marked-up default. Reporting actual emissions should reduce the "
            "importer's certificate obligation versus using the default value."
        )
    else:
        st.warning(
            f"Your calculated SEE is **{your_see - default_marked:.3f} tCO₂e/t higher** "
            "than the marked-up default. Double-check your inputs; if accurate, the "
            "default value would not help (actual emissions must be reported where known)."
        )

# -----------------------------------------------------------------------
# Importer certificate cost estimator (v2 — free-allocation aware, C-06)
# -----------------------------------------------------------------------
st.subheader("Importer certificate cost (indicative)")
st.caption("CBAM certificates are surrendered by the EU importer. During the "
           "phase-in, only part of the embedded emissions is payable — the "
           "**CBAM factor** (free-allocation adjustment, IR (EU) 2025/2620) — "
           "rising from 2.5% in 2026 to 100% in 2034. This shows both the gross "
           "(no adjustment) and the realistic net cost. Not a price quote.")

cc1, cc2 = st.columns(2)
price = cc1.number_input(
    "CBAM certificate price (EUR/tCO₂e)", min_value=0.0, step=1.0, format="%.2f",
    value=float(ss.get("cert_price", EU_ETS_REFERENCE.value)), key="w_cert_price",
    help="EU ETS-linked weekly average. Volatile — enter the current market price.")
ss.cert_price = price
prod = cc2.number_input(
    "Annual export volume (t)", min_value=0.0, step=1000.0, format="%.0f",
    value=float(ss.get("export_vol", ss.annual_production_t)), key="w_export_vol",
    help="Defaults to your annual production from Module 1.")
ss.export_vol = prod

bench = st.number_input(
    "EU-ETS product benchmark (tCO₂e/t) — optional, advanced", min_value=0.0,
    step=0.01, format="%.3f", value=float(ss.get("cbam_benchmark", 0.0)),
    key="w_cbam_bench",
    help="If you know the EU-ETS free-allocation benchmark for this good, enter "
         "it to sharpen the net figure (payable = SEE − benchmark × (1 − CBAM "
         "factor)). Leave 0 to use the conservative approximation "
         "(payable = SEE × CBAM factor).")
ss.cbam_benchmark = bench
benchmark = bench if bench > 0 else None

is_hydrogen = sector == "Hydrogen"
bd = cost_breakdown(
    see=your_see, year=year, price=price, volume_t=prod,
    benchmark=benchmark, is_hydrogen=is_hydrogen,
)
f = bd["cbam_factor"]

if year not in CBAM_FACTOR_SCHEDULE:
    st.caption(f"No CBAM factor defined for {year} "
               f"(schedule covers 2026–2034); using "
               f"{'0% (pre-definitive)' if year < 2026 else '100% (fully phased in)'}.")

st.markdown(f"**Reporting year {year} · CBAM factor = {f * 100:.1f}% payable**")
k1, k2, k3 = st.columns(3)
k1.metric("Payable SEE (tCO₂e/t)", f"{bd['payable_see_tco2e_per_t']:.3f}",
          help="Embedded emissions actually payable after the free-allocation "
               "adjustment for this year.")
k2.metric("Net cost / t", f"€{bd['net_cost_per_t_eur']:,.2f}",
          help="Realistic per-tonne cost at this year's CBAM factor.")
k3.metric("Gross cost / t", f"€{bd['gross_cost_per_t_eur']:,.2f}",
          help="Full SEE priced with no free-allocation adjustment (upper bound / "
               "phase-out endpoint).")

k4, k5 = st.columns(2)
k4.metric("Net annual cost", f"€{bd['net_annual_cost_eur']:,.0f}")
k5.metric("Gross annual cost", f"€{bd['gross_annual_cost_eur']:,.0f}")

if benchmark is None:
    st.caption("Net uses the conservative approximation (payable = SEE × CBAM "
               "factor). Enter your EU-ETS benchmark above to refine it.")

if bd["below_de_minimis"]:
    st.info(
        f"Your export volume ({prod:,.0f} t) is below the **{CBAM_DE_MINIMIS_T:.0f} "
        "t/importer/year de minimis**. If the EU importer's *total* CBAM-goods "
        "imports stay under 50 t for the year, those imports are **exempt** "
        "(does not apply to hydrogen or electricity). Confirm with your importer."
    )

if INDIA_CARBON_PRICE.value == 0.0:
    st.caption("No EU-recognised Indian carbon price (Jul 2026) → CBAM Article 9 "
               "deduction = €0. India's CCTS is not yet EU-recognised.")

st.markdown("**Phase-in — net annual cost using your SEE (2026 → 2034)**")
net_price = net_certificate_price(price)
curve = pd.DataFrame({
    "Year": [str(y) for y in sorted(CBAM_FACTOR_SCHEDULE)],
    "CBAM factor": [f"{CBAM_FACTOR_SCHEDULE[y] * 100:.1f}%"
                    for y in sorted(CBAM_FACTOR_SCHEDULE)],
    "Net cost / t": [
        f"€{cost_breakdown(see=your_see, year=y, price=price, volume_t=prod, benchmark=benchmark, is_hydrogen=is_hydrogen)['net_cost_per_t_eur']:,.2f}"
        for y in sorted(CBAM_FACTOR_SCHEDULE)],
    "Net annual cost": [
        f"€{cost_breakdown(see=your_see, year=y, price=price, volume_t=prod, benchmark=benchmark, is_hydrogen=is_hydrogen)['net_annual_cost_eur']:,.0f}"
        for y in sorted(CBAM_FACTOR_SCHEDULE)],
})
st.dataframe(curve, hide_index=True, use_container_width=True)

st.markdown("**Price sensitivity — net annual cost at this year's CBAM factor**")
scenarios = [40.0, 60.0, 75.0, 90.0, 100.0]
sens = pd.DataFrame({
    "Price (€/tCO₂e)": [f"{p:.0f}" for p in scenarios],
    "Net cost / t": [f"€{bd['payable_see_tco2e_per_t'] * p:,.2f}" for p in scenarios],
    "Net annual cost": [
        f"€{bd['payable_see_tco2e_per_t'] * p * prod:,.0f}" for p in scenarios],
})
st.dataframe(sens, hide_index=True, use_container_width=True)

st.caption(
    f"Certificate price is user-entered (reference {EU_ETS_REFERENCE.value} "
    f"{EU_ETS_REFERENCE.unit}, {EU_ETS_REFERENCE.vintage}); never hardcoded into "
    "your SEE. CBAM defaults: Reg. (EU) 2025/2621."
)

st.divider()
cprev, cnext = st.columns(2)
cprev.page_link("pages/2_Fuel_and_Energy.py", label="← Back: Fuel & Energy")
cnext.page_link("pages/4_Outputs.py", label="Next: Outputs →")

render_footer()
