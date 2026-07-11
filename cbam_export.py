"""Importer-facing outputs — JSON payload + PDF SEE statement.

No Streamlit: functions take a session-state-like mapping (anything with .get)
and the SEEBreakdown from see_engine, so this module is unit-testable. Pulls all
factors/provenance from emission_factors so every output carries its vintages.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

from emission_factors import (
    REGULATION_SNAPSHOT, FUELS, GRID_EF,
    EU_ETS_REFERENCE, INDIA_CARBON_PRICE, BIOGENIC_FUELS,
)
from cbam_meta import functional_unit, route_engine_key
from cbam_india_defaults import by_id, VINTAGE as CBAM_DEFAULTS_VINTAGE
from cost_engine import cost_breakdown, phase_in_curve, payable_see

_ASSETS = Path(__file__).parent / "assets"
_LOGO = str(_ASSETS / "ecosetu_logo.png")


# ---------------------------------------------------------------------------
# JSON payload
# ---------------------------------------------------------------------------
def _resolved_cn(ss) -> str:
    override = (ss.get("cn_code") or "").strip()
    if override:
        return override
    d = by_id(ss.get("cbam_default_id", "")) if ss.get("cbam_default_id") else None
    return d.cn_display if d else ""


def _grid_value(ss):
    choice = ss.get("grid_ef_choice", "national_v21")
    if choice == "custom":
        return (float(ss.get("grid_ef_custom", 0.0)),
                "Custom (user-entered)", ss.get("grid_ef_source", ""))
    # A restored save may hold a grid key that has since been removed (e.g. the
    # retired regional factors, C-08). Fall back to the national default rather
    # than KeyError-ing when the export runs before resolve_grid_ef() repairs it.
    g = GRID_EF.get(choice) or GRID_EF["national_v21"]
    return g.value, g.source, g.vintage


def build_payload(ss, result) -> dict:
    sector = ss.get("sector", "")
    route = ss.get("route", "")
    year = int(ss.get("reporting_year", 2026))
    default = by_id(ss.get("cbam_default_id", "")) if ss.get("cbam_default_id") else None

    grid_val, grid_src, grid_vint = _grid_value(ss)

    fuels_out = []
    has_biogenic = False
    for row in ss.get("fuels", []):
        fk = row.get("fuel_key", "")
        is_bio = fk in BIOGENIC_FUELS
        has_biogenic = has_biogenic or is_bio
        fuels_out.append({
            "fuel_key": fk,
            "label": FUELS[fk].label if fk in FUELS else fk,
            "quantity": float(row.get("quantity", 0.0)),
            "ncv_tj_per_t": float(row.get("ncv", 0.0)),
            "ef_kgco2_per_tj": float(row.get("ef", 0.0)),
            "is_biogenic": is_bio,
        })

    payload = {
        "schema": "ecosetu-cbam-see/v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "regulation_snapshot": REGULATION_SNAPSHOT,
        "producer": {
            "company_name": ss.get("company_name", ""),
            "facility_name": ss.get("facility_name", ""),
            "state_ut": ss.get("state_ut", ""),
            "pin_code": ss.get("pin_code", ""),
            "reporting_year": year,
        },
        "product": {
            "sector": sector,
            "production_route": route,
            "engine_route_key": route_engine_key(sector, route),
            "cn_code": _resolved_cn(ss),
            "functional_unit": functional_unit(sector),
            "annual_production_t": float(ss.get("annual_production_t", 0.0)),
        },
        "inputs": {
            "input_basis": ss.get("input_basis", ""),
            "fuels": fuels_out,
            "electricity_value": float(ss.get("electricity_value", 0.0)),
            "grid_ef": {
                "choice": ss.get("grid_ef_choice", ""),
                "value_tco2_per_mwh": grid_val,
                "source": grid_src,
                "vintage": grid_vint,
            },
            # C-15: biogenic CO2 is zero-rated only with RED II sustainability
            # evidence. Record whether biomass was used and whether the producer
            # attested to holding that evidence, so the importer/verifier can see it.
            "biogenic": {
                "biomass_used": has_biogenic,
                "sustainability_documentation_attested":
                    bool(ss.get("biomass_sustainability_attested", False))
                    if has_biogenic else None,
                "basis": "CBAM zero-rating of biogenic CO2 requires RED II-compliant "
                         "sustainability criteria (Reg. (EU) 2018/2001).",
            },
        },
        "see_breakdown": {
            "combustion": result.combustion,
            "process": result.process,
            "indirect": result.indirect,
            "indirect_included_in_see": result.indirect_included,
            "informational_indirect": result.informational_indirect,
            "total_see_tco2e_per_t": result.total_see,
            "gwp_set": result.gwp_set,
        },
        "cbam_comparison": None,
        "cost_estimate": None,
        "disclaimers": [
            "Self-calculated estimate — NOT verified, assured, or certified.",
            "Statutory CBAM verification requires an accredited third-party verifier "
            "(ISO 17029 + ISO 14065).",
            f"Factors/defaults embedded at snapshot {REGULATION_SNAPSHOT['snapshot_date']}; "
            "confirm current values at https://eur-lex.europa.eu.",
        ],
    }

    if default is not None:
        payload["cbam_comparison"] = {
            "cn_code": default.cn_display,
            "description": default.description,
            "default_see": default.total,
            "markup_year": year,
            "default_with_markup": default.marked(year),
            "your_see": result.total_see,
            "delta_vs_marked_default": round(result.total_see - default.marked(year), 4),
            "source": CBAM_DEFAULTS_VINTAGE,
        }

    # Cost estimate v2 (C-06): free-allocation aware. Certificate price is
    # user-entered, never hardcoded into SEE. Shows gross vs net-of-free-allocation.
    price = float(ss.get("cert_price", EU_ETS_REFERENCE.value))
    export_vol = float(ss.get("export_vol", ss.get("annual_production_t", 0.0)))
    bench = float(ss.get("cbam_benchmark", 0.0))
    benchmark = bench if bench > 0 else None
    cost = cost_breakdown(
        see=result.total_see, year=year, price=price, volume_t=export_vol,
        benchmark=benchmark, is_hydrogen=(sector == "Hydrogen"),
    )
    # Whole-schedule phase-in so the importer sees the trajectory to 2034.
    cost["phase_in"] = phase_in_curve(
        result.total_see, cost["net_price_eur"], export_vol, benchmark)
    if default is not None:
        marked = default.marked(year)
        # Apply the same free-allocation factor to the default for a like-for-like line.
        default_payable = payable_see(marked, year, benchmark)
        cost["default_marked_see"] = marked
        cost["default_net_cost_per_t_eur"] = round(default_payable * cost["net_price_eur"], 2)
        cost["default_net_annual_cost_eur"] = round(
            default_payable * cost["net_price_eur"] * export_vol, 2)
    payload["cost_estimate"] = cost

    return payload


def payload_json(ss, result) -> str:
    return json.dumps(build_payload(ss, result), indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# PDF SEE statement
# ---------------------------------------------------------------------------
def _clean(t) -> str:
    """Strip characters core Helvetica cannot render."""
    if t is None or t == "":
        return "-"
    s = str(t)
    repl = {
        "–": "-", "—": "-", "\u2019": "'", "\u2018": "'", "\u201c": '"',
        "\u201d": '"', "₂": "2", "₃": "3", "₄": "4", "₆": "6", "€": "EUR ",
        "→": "->", "←": "<-", "≈": "~", "≠": "!=", "·": "-", "⚠": "",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


_INDIGO = (99, 102, 241)
_DGREEN = (15, 76, 44)   # brand dark green #0F4C2C


class _CBAMPdf(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*_INDIGO)
        self.rect(0, 0, 210, 12, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        self.set_y(3.5)
        self.cell(0, 5, "CBAM SPECIFIC EMBEDDED EMISSIONS (SEE) STATEMENT", align="C")
        self.set_text_color(0, 0, 0)
        self.ln(12)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(148, 163, 184)
        self.cell(0, 4,
                  "Generated by Ecosetu  |  Green compliance, bridged.  |  "
                  f"{datetime.now().strftime('%d %B %Y')}  |  Page {self.page_no()}",
                  align="C")

    def h2(self, text):
        self.ln(3)
        self.set_fill_color(*_DGREEN)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, f"  {_clean(text)}", fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def kv(self, label, value):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(90, 90, 90)
        self.cell(70, 7, f"  {_clean(label)}", border="B")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, f"  {_clean(value)}", border="B", ln=True)


def build_pdf(ss, result) -> bytes:
    p = build_payload(ss, result)
    pr, prod, b = p["product"], p["producer"], p["see_breakdown"]

    pdf = _CBAMPdf("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    try:
        pdf.image(_LOGO, x=14, y=12, w=50)
    except Exception:
        pass

    pdf.set_y(34)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*_DGREEN)
    pdf.cell(0, 10, "CBAM SEE Statement", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, "Specific Embedded Emissions - India Producer Edition", ln=True)
    pdf.set_text_color(0, 0, 0)

    # Headline SEE box
    pdf.ln(3)
    pdf.set_fill_color(240, 245, 242)
    pdf.set_draw_color(*_DGREEN)
    pdf.rect(14, pdf.get_y(), 182, 22, "FD")
    yb = pdf.get_y() + 6
    pdf.set_xy(20, yb)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_DGREEN)
    pdf.cell(120, 8, _clean(f"TOTAL SEE (tCO2e / {pr['functional_unit']})"))
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 8, f"{result.total_see:.3f}")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(22)

    pdf.h2("Producer & installation")
    pdf.kv("Company", prod["company_name"])
    pdf.kv("Facility", prod["facility_name"])
    pdf.kv("State / UT", prod["state_ut"])
    pdf.kv("Reporting year", prod["reporting_year"])

    pdf.h2("Product")
    pdf.kv("CBAM sector", pr["sector"])
    pdf.kv("Production route", pr["production_route"])
    pdf.kv("CN code", pr["cn_code"])
    pdf.kv("Annual production (t)", f"{pr['annual_production_t']:,.0f}")

    pdf.h2("SEE breakdown (tCO2e per t)")
    for comp, val in result.as_rows():
        pdf.kv(comp, f"{val:.4f}")
    if not b["indirect_included_in_see"] and b["informational_indirect"] > 0:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(0, 4, _clean(
            f"Note: electricity (Scope 2) is not part of CBAM SEE for {pr['sector']}. "
            f"Indirect {b['informational_indirect']:.4f} shown for tracking only."))
        pdf.set_text_color(0, 0, 0)

    if p["cbam_comparison"]:
        c = p["cbam_comparison"]
        pdf.h2("CBAM default comparison")
        pdf.kv("Official default (CN)", _clean(f"{c['cn_code']} - {c['description']}"))
        pdf.kv("CBAM default SEE", f"{c['default_see']:.3f}")
        pdf.kv(f"Default + {c['markup_year']} mark-up", f"{c['default_with_markup']:.3f}")
        pdf.kv("Your SEE", f"{c['your_see']:.3f}")
        pdf.kv("Delta vs marked default", f"{c['delta_vs_marked_default']:+.3f}")
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(0, 4, _clean(f"Source: {c['source']}"))
        pdf.set_text_color(0, 0, 0)

    if p["cost_estimate"]:
        ce = p["cost_estimate"]
        pdf.h2("Importer certificate cost (indicative)")
        pdf.kv("Reporting year", ce["reporting_year"])
        pdf.kv("CBAM factor (payable share)", f"{ce['cbam_factor'] * 100:.1f}%")
        pdf.kv("Certificate price (EUR/tCO2e)", f"{ce['certificate_price_eur']:,.2f}")
        if ce["india_carbon_deduction_eur"] > 0:
            pdf.kv("India carbon-price deduction", f"{ce['india_carbon_deduction_eur']:,.2f}")
            pdf.kv("Net price (EUR/tCO2e)", f"{ce['net_price_eur']:,.2f}")
        pdf.kv("Export volume (t)", f"{ce['export_volume_t']:,.0f}")
        pdf.kv("Payable SEE (tCO2e/t)", f"{ce['payable_see_tco2e_per_t']:.4f}")
        pdf.kv("Net cost / t (after free alloc.)", f"EUR {ce['net_cost_per_t_eur']:,.2f}")
        pdf.kv("Net annual cost", f"EUR {ce['net_annual_cost_eur']:,.0f}")
        pdf.kv("Gross cost / t (no adjustment)", f"EUR {ce['gross_cost_per_t_eur']:,.2f}")
        pdf.kv("Gross annual cost", f"EUR {ce['gross_annual_cost_eur']:,.0f}")
        if "default_net_cost_per_t_eur" in ce:
            pdf.kv("Net cost / t - default", f"EUR {ce['default_net_cost_per_t_eur']:,.2f}")
            pdf.kv("Net annual cost - default", f"EUR {ce['default_net_annual_cost_eur']:,.0f}")
        if ce["below_de_minimis"]:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(150, 90, 0)
            pdf.multi_cell(0, 4, _clean(
                f"Export volume is below the {ce['de_minimis_t']:.0f} t/importer/year "
                "de minimis - if the importer's total CBAM-goods imports stay under it, "
                "those imports are exempt (excludes hydrogen & electricity)."))
            pdf.set_text_color(0, 0, 0)

        # Phase-in table: net annual cost by year (using your SEE).
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_fill_color(*_DGREEN)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(30, 6, "  Year", border=1, fill=True)
        pdf.cell(38, 6, "  CBAM factor", border=1, fill=True)
        pdf.cell(48, 6, "  Net cost / t (EUR)", border=1, fill=True)
        pdf.cell(0, 6, "  Net annual cost (EUR)", border=1, fill=True, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8.5)
        for i, r in enumerate(ce.get("phase_in", [])):
            pdf.set_fill_color(245, 248, 246) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
            pdf.cell(30, 6, f"  {r['year']}", border=1, fill=True)
            pdf.cell(38, 6, f"  {r['cbam_factor'] * 100:.1f}%", border=1, fill=True)
            pdf.cell(48, 6, f"  {r['net_cost_per_t_eur']:,.2f}", border=1, fill=True)
            pdf.cell(0, 6, f"  {r['net_annual_cost_eur']:,.0f}", border=1, fill=True, ln=True)

        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(130, 130, 130)
        pdf.multi_cell(0, 4, _clean(
            "Indicative only - the CBAM certificate is surrendered by the EU importer. "
            "Gross ignores free allocation (upper bound); net applies the IR (EU) "
            "2025/2620 CBAM factor for the year. Certificate price is user-entered and "
            "volatile; never embedded in your SEE."))
        pdf.set_text_color(0, 0, 0)

    pdf.h2("Emission factor provenance")
    for f in p["inputs"]["fuels"]:
        pdf.kv(f["label"], f"qty {f['quantity']:.4f}  |  NCV {f['ncv_tj_per_t']:.2f}  "
                           f"|  EF {f['ef_kgco2_per_tj']:.1f}")
    g = p["inputs"]["grid_ef"]
    pdf.kv("Grid EF (tCO2/MWh)", f"{g['value_tco2_per_mwh']:.4f} - {g['source']}")
    pdf.kv("GWP basis", b["gwp_set"])
    pdf.kv("Regulation snapshot", p["regulation_snapshot"]["snapshot_date"])

    bio = p["inputs"]["biogenic"]
    if bio["biomass_used"]:
        attested = bio["sustainability_documentation_attested"]
        pdf.kv("Biomass zero-rated",
               "Yes - RED II sustainability documentation attested" if attested
               else "Yes - sustainability documentation NOT attested (verifier may "
                    "treat as fossil)")

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(0, 4, _clean(
        "Disclaimer: This statement is a self-calculated estimate prepared with the "
        "Ecosetu CBAM tool. It does NOT verify, assure, or certify emissions. Statutory "
        "CBAM verification requires an accredited third-party verifier (ISO 17029 + "
        "ISO 14065). Confirm current rules at https://eur-lex.europa.eu."), align="C")

    return bytes(pdf.output())
