import streamlit as st

from style import (
    inject_base_css, render_whatsapp_fab, render_footer, render_sidebar_footer,
)

st.set_page_config(
    page_title="Ecosetu CBAM — SEE Calculator",
    page_icon="assets/ecosetu_favicon.png",
    layout="centered",
    initial_sidebar_state="expanded",
)

try:
    st.logo("assets/ecosetu_logo_large.png", icon_image="assets/ecosetu_favicon.png")
except Exception:
    pass

inject_base_css()
render_whatsapp_fab()
render_sidebar_footer()

# ─────────────────────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="eco-hero">
        <div class="eco-eyebrow">
            <span class="eco-dot"></span>
            Ecosetu · CBAM for Indian Exporters
        </div>
        <div class="eco-h1">
            Know your CBAM number<br>
            <span class="grad">before your EU buyer asks.</span>
        </div>
        <div class="eco-sub">
            CBAM's definitive phase began 1 January 2026: imports of steel, aluminium,
            cement, fertiliser and hydrogen into the EU now carry an embedded-emissions
            obligation, with the first annual CBAM declaration due 30 September 2027.
            Ecosetu turns your fuel and electricity data into an EU-method SEE figure —
            with a CBAM-default comparison and an indicative certificate cost — in minutes.
        </div>
        <div class="eco-cta-row">
            <a class="eco-btn-primary" href="/Facility_Setup" target="_self">⚡ Start the calculator</a>
            <a class="eco-btn-ghost" href="#why-ecosetu-cbam">Why Ecosetu ↓</a>
        </div>
        <div class="eco-hero-note">
            A 50 t/importer/year de minimis applies (all CBAM goods combined; excludes
            hydrogen &amp; electricity). No account · no database · nothing stored on our servers.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Stat band
st.markdown(
    """
    <div class="eco-stats">
        <div class="eco-stat"><div class="num">5</div><div class="lbl">CBAM sectors</div></div>
        <div class="eco-stat"><div class="num">EU method</div><div class="lbl">SEE = DEE + IEE</div></div>
        <div class="eco-stat"><div class="num">~10 min</div><div class="lbl">to your number</div></div>
        <div class="eco-stat"><div class="num">No DB</div><div class="lbl">nothing stored on servers</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Feature cards
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
st.markdown('<a id="why-ecosetu-cbam"></a>', unsafe_allow_html=True)
st.markdown('<div class="eco-section-kicker">Why Ecosetu CBAM</div>', unsafe_allow_html=True)
st.markdown('<div class="eco-section-title">Built for the exporter, not the consultant</div>',
            unsafe_allow_html=True)
st.markdown(
    """
    <div class="eco-grid">
        <div class="eco-card">
            <div class="ic">🏭</div>
            <h4>Your real plant data</h4>
            <p>Enter fuels, NCV, emission factors and electricity. We default to IPCC 2006
               and CEA grid factors — edit any value when you have lab or CEA parameters.</p>
        </div>
        <div class="eco-card">
            <div class="ic">📊</div>
            <h4>SEE the EU way</h4>
            <p>Direct + indirect emissions per the CBAM method, with the right indirect
               treatment for each sector — cement &amp; fertilisers count electricity, steel
               &amp; aluminium don't.</p>
        </div>
        <div class="eco-card">
            <div class="ic">⚖️</div>
            <h4>Default comparison</h4>
            <p>See your SEE next to the CBAM default value — plus the annual mark-up penalty —
               so you know whether actual data saves you money.</p>
        </div>
        <div class="eco-card">
            <div class="ic">💶</div>
            <h4>Cost in euros</h4>
            <p>An indicative importer certificate cost at today's EU ETS price, with a
               price-sensitivity table from €40 to €100/tonne.</p>
        </div>
        <div class="eco-card">
            <div class="ic">📄</div>
            <h4>Audit-ready outputs</h4>
            <p>Download a structured JSON payload and a clean PDF SEE statement you can hand
               to your EU importer or verifier.</p>
        </div>
        <div class="eco-card">
            <div class="ic">🔒</div>
            <h4>No account, no database</h4>
            <p>No login and nothing is stored on our servers — your data lives only in your
               active session and in the progress file <b>you</b> download to your own device.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Save / Resume banner
st.markdown(
    """
    <a class="eco-save" href="/Save_and_Resume" target="_self">
        <div class="eco-save-ic">💾</div>
        <div class="eco-save-body">
            <span class="eco-save-pill">No login needed</span>
            <h4>Save your progress &amp; resume anytime</h4>
            <p>Download a single progress file, then upload it later — on any device — to pick
               up exactly where you left off.</p>
        </div>
        <span class="eco-save-cta">Save / Resume →</span>
    </a>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)

# Regulation + disclaimer
st.caption(
    "Regulation snapshot: CBAM definitive phase, researched June 2026 "
    "(Reg. 2025/2621, Omnibus 2025/2083). Always verify current rules at eur-lex.europa.eu."
)
st.info(
    "This tool **estimates and helps you prepare** your CBAM embedded-emissions data. "
    "It does **not** verify, assure, or certify emissions. Statutory CBAM verification "
    "requires an accredited third-party verifier (ISO 17029 + ISO 14065)."
)

st.page_link("pages/1_Facility_Setup.py", label="Start the calculator →")

render_footer()
