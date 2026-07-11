"""Module 5 — Save / Resume.

No accounts, no database: nothing is stored on our servers. Your data lives only
in your active session (server process memory while this tab is open) and in the
progress file you download. Re-upload it later, or on another device, to continue
exactly where you left off.
"""

import streamlit as st

from state import setup_page
from style import render_pagehead, render_footer
from cbam_progress import dump_progress, load_progress

setup_page("Save & Resume")
ss = st.session_state

render_pagehead(
    "Step 5 of 5 · Save & Resume",
    "Save & Resume",
    "No accounts, no database — nothing is stored on our servers. Your data lives only "
    "in this active session and in the progress file you download. Upload it later to "
    "pick up exactly where you left off.",
)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
st.subheader("Download progress")
_company = (ss.company_name or "producer").strip().replace(" ", "_") or "producer"
st.download_button(
    "⬇ Download progress file",
    data=dump_progress(ss),
    file_name=f"ecosetu_cbam_{_company}_progress.ecosetu",
    mime="text/plain",
    use_container_width=True,
)
st.caption("Keep this file safe — anyone who has it can see the data you entered.")

st.divider()

# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------
st.subheader("Resume from a file")
up = st.file_uploader("Upload a progress file", type=["ecosetu", "txt"],
                      key="progress_upload")
if up is not None:
    file_id = f"{up.name}:{up.size}"
    if ss.get("_last_loaded") != file_id:
        ok, msg = load_progress(up.getvalue().decode("utf-8", errors="ignore"), ss)
        if ok:
            ss["_last_loaded"] = file_id
            st.success(f"Progress restored (saved {msg}). Your inputs are back — "
                       "open any module from the sidebar.")
        else:
            st.error(msg)
    else:
        st.info("This file is already loaded. Edit any module, or upload a different "
                "file to switch.")

st.divider()
st.page_link("pages/1_Facility_Setup.py", label="Go to Facility Setup →")

render_footer()
