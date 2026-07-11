"""Ecosetu design system for the CBAM tool.

inject_base_css() ports the Sora/Inter type system, eco color tokens, animated
mesh hero, feature cards, gradient buttons, section kickers, polished native
Streamlit widgets and footer. It is called once from setup_page() (state.py) so
every page inherits the look. Helper functions render the reusable hero / card /
section blocks.
"""

import streamlit as st

# Founder contact — shared with the BRSR tool.
WHATSAPP_NUMBER = "919409417490"
WHATSAPP_MESSAGE = ("Hi%20Meet%2C%20I%27m%20using%20Ecosetu%20CBAM%20and%20"
                    "have%20a%20question.")
FOUNDING_FORM_URL = "https://forms.gle/ZAvGwN25sCPT3gU3A"


_BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');

    :root {
        --eco-deep: #0F4C2C;
        --eco-green: #16A34A;
        --eco-mint: #DCFCE7;
        --eco-ink: #0B1F16;
        --eco-slate: #4B5D55;
        --eco-indigo: #6366F1;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Sora', sans-serif !important; letter-spacing: -0.02em; }

    .block-container { padding-top: 2.2rem; max-width: 1020px; margin-left: auto; margin-right: auto; }

    /* Page titles + captions a touch warmer/tighter */
    h1 { color: var(--eco-ink); }
    h2, h3 { color: var(--eco-ink); }

    /* ── Animated mesh hero (indigo + green for CBAM) ───── */
    .eco-hero {
        position: relative; overflow: hidden;
        border-radius: 24px; padding: 46px 38px 40px;
        margin: 6px 0 18px;
        background:
            radial-gradient(120% 120% at 0% 0%, rgba(99,102,241,0.32) 0%, rgba(99,102,241,0) 45%),
            radial-gradient(120% 120% at 100% 0%, rgba(22,163,74,0.28) 0%, rgba(22,163,74,0) 42%),
            radial-gradient(130% 130% at 80% 100%, rgba(16,124,67,0.30) 0%, rgba(16,124,67,0) 50%),
            linear-gradient(135deg, #0A1733 0%, #0F2E4A 45%, #0B3A22 100%);
        box-shadow: 0 24px 60px -28px rgba(15,76,44,0.65);
    }
    .eco-hero::after {
        content: ""; position: absolute; inset: -40%;
        background: conic-gradient(from 0deg at 50% 50%, transparent 0deg, rgba(199,210,254,0.08) 120deg, transparent 240deg);
        animation: ecospin 22s linear infinite; pointer-events: none;
    }
    @keyframes ecospin { to { transform: rotate(360deg); } }
    .eco-hero > * { position: relative; z-index: 1; }

    .eco-eyebrow {
        display: inline-flex; align-items: center; gap: 8px;
        font-size: 11.5px; font-weight: 600; letter-spacing: 2px;
        text-transform: uppercase; color: #C7D2FE;
        background: rgba(199,210,254,0.10); border: 1px solid rgba(199,210,254,0.22);
        padding: 6px 14px; border-radius: 999px; margin-bottom: 18px;
    }
    .eco-dot { width: 7px; height: 7px; border-radius: 50%; background: #818CF8;
               box-shadow: 0 0 0 0 rgba(129,140,248,0.7); animation: ecopulse 2s infinite; }
    @keyframes ecopulse {
        0% { box-shadow: 0 0 0 0 rgba(129,140,248,0.6); }
        70% { box-shadow: 0 0 0 8px rgba(129,140,248,0); }
        100% { box-shadow: 0 0 0 0 rgba(129,140,248,0); }
    }
    .eco-h1 {
        font-family: 'Sora', sans-serif; font-weight: 800;
        font-size: clamp(28px, 5vw, 46px); line-height: 1.06;
        color: #FFFFFF; margin: 0 0 16px;
    }
    .eco-h1 .grad {
        background: linear-gradient(90deg, #818CF8, #A7F3D0 60%, #C7D2FE);
        -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    }
    .eco-sub {
        font-size: clamp(14px, 2.2vw, 17px); line-height: 1.6;
        color: #D6E2F2; max-width: 640px; margin: 0 0 24px;
    }
    .eco-cta-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
    .eco-btn-primary {
        display: inline-flex; align-items: center; gap: 9px;
        padding: 14px 26px; border-radius: 12px; text-decoration: none;
        font-weight: 700; font-size: 15.5px; color: #07291A;
        background: linear-gradient(180deg, #6EE7A0, #22C55E);
        box-shadow: 0 12px 26px -10px rgba(34,197,94,0.8);
        transition: transform .18s ease, box-shadow .18s ease;
    }
    .eco-btn-primary:hover { transform: translateY(-2px); box-shadow: 0 18px 34px -10px rgba(34,197,94,0.9); }
    .eco-btn-ghost {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 13px 22px; border-radius: 12px; text-decoration: none;
        font-weight: 600; font-size: 15px; color: #EAF0FB;
        border: 1px solid rgba(199,210,254,0.32); background: rgba(199,210,254,0.06);
        transition: background .18s ease, border-color .18s ease;
    }
    .eco-btn-ghost:hover { background: rgba(199,210,254,0.14); border-color: rgba(199,210,254,0.55); }
    .eco-hero-note { font-size: 12.5px; color: #9FB3D3; margin-top: 14px; }

    /* ── Stat band ──────────────────────────────────────── */
    .eco-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0 8px; }
    .eco-stat {
        background: #FFFFFF; border: 1px solid #E6F0EA; border-radius: 16px;
        padding: 16px 14px; text-align: center;
        box-shadow: 0 8px 22px -18px rgba(15,76,44,0.5);
    }
    .eco-stat .num { font-family: 'Sora', sans-serif; font-weight: 800; font-size: 22px; color: var(--eco-deep); }
    .eco-stat .lbl { font-size: 11.5px; color: var(--eco-slate); margin-top: 3px; }
    @media (max-width: 640px) {
        .eco-stats { grid-template-columns: repeat(2, 1fr); }
        .eco-hero { padding: 34px 22px 30px; }
    }

    /* ── Feature cards ──────────────────────────────────── */
    .eco-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 8px 0; }
    @media (max-width: 760px) { .eco-grid { grid-template-columns: 1fr; } }
    .eco-card {
        background: #FFFFFF; border: 1px solid #E6F0EA; border-radius: 18px;
        padding: 20px 18px; transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    .eco-card:hover { transform: translateY(-3px); border-color: #C7D2FE;
                      box-shadow: 0 18px 40px -22px rgba(15,76,44,0.55); }
    .eco-card .ic {
        width: 42px; height: 42px; border-radius: 12px; display: flex;
        align-items: center; justify-content: center; font-size: 20px; margin-bottom: 12px;
        background: linear-gradient(135deg, var(--eco-mint), #E0E7FF);
    }
    .eco-card h4 { font-size: 16px; color: var(--eco-ink); margin: 0 0 6px; }
    .eco-card p { font-size: 13px; color: var(--eco-slate); line-height: 1.55; margin: 0; }

    .eco-section-title { font-family:'Sora',sans-serif; font-weight:700; font-size: 22px;
                         color: var(--eco-ink); margin: 6px 0 4px; }
    .eco-section-kicker { font-size:11.5px; font-weight:600; letter-spacing:2px; text-transform:uppercase;
                          color: var(--eco-indigo); margin-bottom: 2px; }

    /* ── Compact page header (inner pages) ──────────────── */
    .eco-pagehead {
        position: relative; overflow: hidden;
        border-radius: 18px; padding: 22px 26px; margin: 2px 0 16px;
        background:
            radial-gradient(120% 160% at 0% 0%, rgba(99,102,241,0.22) 0%, rgba(99,102,241,0) 55%),
            radial-gradient(130% 160% at 100% 100%, rgba(22,163,74,0.18) 0%, rgba(22,163,74,0) 55%),
            linear-gradient(135deg, #0C2240 0%, #103A26 100%);
        box-shadow: 0 16px 40px -26px rgba(15,76,44,0.6);
    }
    .eco-pagehead > * { position: relative; z-index: 1; }
    .eco-pagehead .step { font-size:11px; font-weight:700; letter-spacing:2px; text-transform:uppercase;
                          color:#C7D2FE; margin-bottom:6px; }
    .eco-pagehead h2 { font-family:'Sora',sans-serif; font-weight:800; font-size:24px;
                       color:#FFFFFF !important; margin:0 0 4px; letter-spacing:-0.02em; }
    .eco-pagehead p { font-size:13.5px; color:#CBD9EC; line-height:1.5; margin:0; }

    /* ── Polished native widgets ────────────────────────── */
    .stButton > button, .stDownloadButton > button {
        border-radius: 11px; font-weight: 600;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .stButton > button[kind="primary"], .stDownloadButton > button {
        background: linear-gradient(180deg, #6EE7A0, #22C55E);
        color: #07291A; border: none;
        box-shadow: 0 10px 22px -12px rgba(34,197,94,0.75);
    }
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button:hover {
        transform: translateY(-1px); box-shadow: 0 14px 28px -12px rgba(34,197,94,0.9);
        color: #07291A;
    }
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E6F0EA; border-radius: 14px;
        padding: 14px 16px; box-shadow: 0 8px 22px -20px rgba(15,76,44,0.5);
    }
    div[data-testid="stMetricValue"] { font-family:'Sora',sans-serif; color: var(--eco-deep); }
    section[data-testid="stSidebar"] { border-right: 1px solid #E6F0EA; }
    a[data-testid="stPageLink-NavLink"] {
        border: 1px solid #E6F0EA; border-radius: 10px; padding: 8px 12px;
        background: #F6FBF8; transition: border-color .15s ease, background .15s ease;
    }
    a[data-testid="stPageLink-NavLink"]:hover { border-color: #C7D2FE; background: #EEF2FF; }

    /* ── Save / Resume highlight banner ─────────────────── */
    .eco-save {
        position: relative; overflow: hidden;
        display: flex; align-items: center; gap: 20px;
        border-radius: 20px; padding: 22px 26px; margin: 20px 0 6px;
        text-decoration: none;
        background:
            radial-gradient(120% 150% at 0% 0%, rgba(99,102,241,0.24) 0%, rgba(99,102,241,0) 55%),
            radial-gradient(130% 150% at 100% 100%, rgba(74,222,128,0.18) 0%, rgba(74,222,128,0) 55%),
            linear-gradient(135deg, #0C2240 0%, #145236 60%, #10402A 100%);
        border: 1px solid rgba(199,210,254,0.25);
        box-shadow: 0 18px 44px -26px rgba(15,76,44,0.7);
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    .eco-save:hover { transform: translateY(-3px); border-color: rgba(199,210,254,0.55);
                      box-shadow: 0 24px 54px -24px rgba(15,76,44,0.85); }
    .eco-save::after {
        content:""; position:absolute; inset:-50%;
        background: conic-gradient(from 0deg at 50% 50%, transparent 0deg, rgba(199,210,254,0.10) 130deg, transparent 250deg);
        animation: ecospin 26s linear infinite; pointer-events:none;
    }
    .eco-save > * { position: relative; z-index: 1; }
    .eco-save-ic {
        flex: 0 0 auto; width: 58px; height: 58px; border-radius: 16px;
        display:flex; align-items:center; justify-content:center; font-size: 28px;
        background: linear-gradient(180deg, rgba(199,210,254,0.22), rgba(110,231,160,0.18));
        border: 1px solid rgba(220,252,231,0.3);
    }
    .eco-save-body { flex: 1 1 auto; min-width: 0; }
    .eco-save-pill {
        display:inline-block; font-size:10.5px; font-weight:700; letter-spacing:1.5px;
        text-transform:uppercase; color:#07291A;
        background: linear-gradient(90deg,#A7F3D0,#C7D2FE);
        padding:3px 10px; border-radius:999px; margin-bottom:9px;
    }
    .eco-save-body h4 { font-family:'Sora',sans-serif; font-weight:700; font-size:18px;
                        color:#FFFFFF !important; margin:0 0 5px; line-height:1.25; }
    .eco-save-body p { font-size:13.5px; color:#CDEAD9; line-height:1.55; margin:0; }
    .eco-save-cta {
        flex: 0 0 auto; display:inline-flex; align-items:center; gap:7px;
        font-weight:700; font-size:14px; color:#07291A;
        background: linear-gradient(180deg, #6EE7A0, #22C55E);
        padding:11px 18px; border-radius:11px; white-space:nowrap;
        box-shadow: 0 10px 22px -10px rgba(34,197,94,0.8);
    }
    @media (max-width: 640px) {
        .eco-save { flex-direction: column; align-items: flex-start; gap: 14px; padding: 20px; }
        .eco-save-cta { align-self: stretch; justify-content:center; }
    }

    /* ── Footer ─────────────────────────────────────────── */
    .eco-footer { text-align:center; color:#666; font-size:11.5px; line-height:1.6;
                  margin-top:34px; padding-top:18px; border-top:1px solid #EEF2F0; }
    .eco-footer b { color: var(--eco-deep); }
    .eco-footer a { color: #666; text-decoration:none; font-weight:600; }
    .eco-footer a[href^="https://ecosetu"] { color: var(--eco-deep); }
    .eco-footer a.founding {
        display:inline-block; padding:8px 16px; background:#0F4C2C; color:#fff !important;
        border-radius:8px; font-size:13px; font-weight:600;
    }
</style>
"""


def inject_base_css() -> None:
    """Inject the Ecosetu design system. Idempotent per page run."""
    st.markdown(_BASE_CSS, unsafe_allow_html=True)


def render_pagehead(step: str, title: str, subtitle: str = "") -> None:
    """Compact gradient header for an inner page (replaces a bare st.title)."""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="eco-pagehead">
            <div class="step">{step}</div>
            <h2>{title}</h2>
            {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_whatsapp_fab() -> None:
    """Floating WhatsApp contact button, fixed bottom-right. Call once per page."""
    st.markdown(
        f"""
        <a href="https://wa.me/{WHATSAPP_NUMBER}?text={WHATSAPP_MESSAGE}"
           target="_blank" rel="noopener"
           aria-label="Chat with us on WhatsApp"
           style="position:fixed; bottom:22px; right:22px; z-index:99999;
                  width:56px; height:56px; border-radius:50%;
                  background:#25D366; box-shadow:0 4px 14px rgba(0,0,0,0.25);
                  display:flex; align-items:center; justify-content:center;
                  text-decoration:none;">
            <svg viewBox="0 0 32 32" width="30" height="30" fill="#ffffff"
                 xmlns="http://www.w3.org/2000/svg">
                <path d="M16.04 3C9.4 3 4 8.4 4 15.04c0 2.12.55 4.18 1.6 6L4 29l8.13-1.55a12 12 0 0 0 3.9.65h.01C22.68 28.1 28 22.7 28 16.06 28 9.42 22.68 4 16.04 4zm0 22.06h-.01a10 10 0 0 1-5.1-1.4l-.36-.22-4.82.92.96-4.7-.24-.38a10 10 0 1 1 9.57 5.78zm5.49-7.5c-.3-.15-1.77-.87-2.04-.97-.27-.1-.47-.15-.67.15-.2.3-.77.96-.94 1.16-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.07-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51l-.57-.01c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48 0 1.46 1.07 2.87 1.22 3.07.15.2 2.1 3.2 5.08 4.49.71.3 1.26.49 1.69.63.71.22 1.36.19 1.87.12.57-.09 1.77-.72 2.02-1.42.25-.7.25-1.3.17-1.42-.07-.13-.27-.2-.57-.35z"/>
            </svg>
        </a>
        """,
        unsafe_allow_html=True,
    )


def render_save_resume_link() -> None:
    """Prominent 'Save / Resume progress' link in the sidebar (every page)."""
    try:
        with st.sidebar:
            st.page_link(
                "pages/5_Save_and_Resume.py",
                label="Save / Resume progress",
                icon="💾",
            )
    except Exception:
        # st.page_link unavailable or page not found — default nav still covers it.
        pass


def render_sidebar_footer() -> None:
    """Founding-100 CTA + built-by block in the sidebar. Matches the BRSR tool."""
    render_save_resume_link()
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            f"""
            <div style='text-align:center; padding: 4px 0;'>
                <a href='{FOUNDING_FORM_URL}' target='_blank'
                   style='display:inline-block; padding:8px 14px;
                          background:#0F4C2C; color:white;
                          border-radius:8px; text-decoration:none;
                          font-size:13px; font-weight:600;'>
                    🌱 Join the Founding 100
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style='font-size:11.5px; color:#666; text-align:center;
                        line-height:1.6; padding: 10px 4px 4px;'>
                Built by <b style='color:#0F4C2C;'>Meet Vaghani</b><br>
                Certified ESG Professional<br><br>
                <a href='mailto:meet.vaghani9909@gmail.com'
                   style='color:#666; text-decoration:none;'>
                   meet.vaghani9909@gmail.com
                </a><br>
                <a href='https://ecosetu.co.in'
                   style='color:#0F4C2C; text-decoration:none; font-weight:600;'>
                   ecosetu.co.in
                </a>
            </div>
            <div style='font-size:10.5px; color:#999; text-align:center;
                        margin-top:14px; padding-top:8px;
                        border-top:1px solid #eee;'>
                Made in India 🇮🇳<br>
                An initiative by Keprin Overseas Corporation<br>
                © 2026 Ecosetu
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_footer() -> None:
    """Main-page brand footer. Matches the BRSR built-by block."""
    st.markdown(
        f"""
        <div class="eco-footer">
            <a class="founding" href="{FOUNDING_FORM_URL}" target="_blank" rel="noopener">🌱 Join the Founding 100</a>
            <div style="margin-top:14px;">
                Built by <b>Meet Vaghani</b><br>
                Certified ESG Professional
            </div>
            <div style="margin-top:10px;">
                <a href="mailto:meet.vaghani9909@gmail.com">meet.vaghani9909@gmail.com</a><br>
                <a href="https://ecosetu.co.in">ecosetu.co.in</a>
            </div>
            <div style="margin-top:14px; color:#B6C2BC;">
                Made in India 🇮🇳<br>
                An initiative by Keprin Overseas Corporation<br>
                © 2026 Ecosetu
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
