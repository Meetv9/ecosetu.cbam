"""Module 1 — Facility & Product Setup.

Every input mirrors its value into a plain session_state key (e.g. `sector`)
that persists across pages; the widget itself uses a transient `w_*` key.
"""

import streamlit as st

from state import setup_page
from style import render_pagehead, render_footer
from cbam_meta import sector_names, routes_for, functional_unit
from cbam_india_defaults import option_labels, by_id

setup_page("Facility Setup")
ss = st.session_state

render_pagehead(
    "Step 1 of 5 · Facility & Product",
    "Facility & Product Setup",
    "Tell us about the installation and the CBAM good you produce.",
)

st.subheader("Producer details")
c1, c2 = st.columns(2)
ss.company_name = c1.text_input("Company name", value=ss.company_name, key="w_company")
ss.facility_name = c2.text_input("Facility / installation name",
                                 value=ss.facility_name, key="w_facility")
c3, c4 = st.columns(2)
ss.state_ut = c3.text_input("State / UT", value=ss.state_ut, key="w_state")
ss.pin_code = c4.text_input("PIN code", value=ss.pin_code, max_chars=6, key="w_pin",
                            help="Used only to suggest a regional grid factor — "
                                 "never stored on a server.")

st.subheader("Product")

# C-16: a restored save may hold a sector that has since been removed from the
# list; fall back to the first option instead of raising (same guard pattern the
# route and CN selectors already use below).
_sectors = sector_names()
if ss.sector not in _sectors:
    ss.sector = _sectors[0]
ss.sector = st.selectbox("CBAM sector", _sectors,
                         index=_sectors.index(ss.sector), key="w_sector")

routes = routes_for(ss.sector)
if ss.route not in routes:
    ss.route = routes[0]
ss.route = st.selectbox("Production route", routes,
                        index=routes.index(ss.route), key="w_route")

# Official CBAM default value, keyed to the exact product CN row from the EU
# Annex (IR (EU) 2025/2621, India sheet). Picking one enables an exact
# like-for-like comparison against your calculated SEE later; "— none —" skips it.
_opts = [("", "— none / my product isn't listed —")] + option_labels(ss.sector)
_ids = [o[0] for o in _opts]
_labels = {o[0]: o[1] for o in _opts}
if ss.cbam_default_id not in _ids:
    ss.cbam_default_id = ""
ss.cbam_default_id = st.selectbox(
    "Product & official CBAM default value (CN code)",
    _ids, index=_ids.index(ss.cbam_default_id),
    format_func=lambda i: _labels[i], key="w_cbam_default",
    help="Official India default from the EU Annex, keyed to your exact CN "
         "product. Used only for the default-value comparison — your SEE is "
         "always computed from your own inputs.",
)

_picked = by_id(ss.cbam_default_id) if ss.cbam_default_id else None
ss.cn_code = st.text_input(
    "CN code (for your report)", value=ss.cn_code, key="w_cn_code",
    placeholder=(_picked.cn_display if _picked else "e.g. 7208 00 00"),
    help="Must match the CN codes in CBAM Annex I. Leave blank to use the CN "
         "code of the default you selected above.",
)

c5, c6 = st.columns(2)
ss.reporting_year = c5.number_input("Reporting year", min_value=2024, max_value=2035,
                                    step=1, value=int(ss.reporting_year), key="w_year")
ss.annual_production_t = c6.number_input(
    f"Annual production ({functional_unit(ss.sector)}s/year)",
    min_value=0.0, step=1000.0, format="%.0f",
    value=float(ss.annual_production_t), key="w_prod",
)

st.divider()
st.info(
    "This tool **estimates and helps you prepare** your CBAM data. It does **not** "
    "verify, assure, or certify emissions. Statutory CBAM verification requires an "
    "accredited third-party verifier (ISO 17029 + ISO 14065)."
)
st.page_link("pages/2_Fuel_and_Energy.py", label="Next: Fuel & Energy →")

render_footer()
