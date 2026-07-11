"""Module 4 — Importer outputs: JSON payload + PDF SEE statement.

Both are generated in-memory and offered as downloads. Nothing is uploaded;
the certificate price and export volume entered on Module 3 carry through.
"""

import streamlit as st

from state import setup_page, build_see, annual_basis_missing_production
from style import render_pagehead, render_footer
from cbam_export import payload_json, build_pdf
from cbam_meta import functional_unit

setup_page("Outputs")
ss = st.session_state

render_pagehead(
    "Step 4 of 5 · Outputs",
    "Outputs for your importer",
    "Share these with your EU importer. Both are generated in your active session "
    "and offered as a download — no account, no database, nothing stored on our "
    "servers.",
)

# C-14: block export when annual-basis inputs have no production denominator.
if annual_basis_missing_production():
    st.error(
        "You entered fuel/energy on an **annual total** basis, but annual "
        "production is 0. Enter your annual production in **Step 1 · Facility "
        "Setup** (or switch to a per-tonne basis in Step 2) before exporting."
    )
    st.page_link("pages/1_Facility_Setup.py", label="← Go to Facility Setup")
    render_footer()
    st.stop()

result = build_see()

st.metric(f"TOTAL SEE (tCO₂e per {functional_unit(ss.sector)})", f"{result.total_see:.3f}")

_company = (ss.company_name or "producer").strip().replace(" ", "_") or "producer"
_base = f"ecosetu_cbam_{_company}_{int(ss.reporting_year)}"

c1, c2 = st.columns(2)
c1.download_button(
    "⬇ JSON payload (machine-readable)", data=payload_json(ss, result),
    file_name=f"{_base}.json", mime="application/json", use_container_width=True,
)
c2.download_button(
    "⬇ PDF SEE statement", data=build_pdf(ss, result),
    file_name=f"{_base}.pdf", mime="application/pdf", use_container_width=True,
)

st.caption("The JSON mirrors every input and factor vintage for the importer's own "
           "records; the PDF is a human-readable statement with provenance.")

st.divider()
st.info(
    "Self-calculated estimate — not verified data. Statutory CBAM verification "
    "requires an accredited third-party verifier (ISO 17029 + ISO 14065)."
)
st.page_link("pages/3_Process_and_Results.py", label="← Back: Process & Results")

render_footer()
