"""Ecosetu CBAM — Emission Factor Library (versioned).

Every factor carries: value, unit, source, vintage, and (where relevant) a note.
This module is PURE DATA — no Streamlit, no I/O — so it can be unit-tested and
imported by the SEE calculation engine.

OVERCLAIM / CURRENCY GUARD:
- These factors are embedded at the vintages shown below. CEA updates annually;
  CBAM defaults update annually. Always confirm current values before relying on
  any output. CBAM regulation: verify at https://eur-lex.europa.eu.
- The EU ETS / CBAM certificate price is NEVER hardcoded into calculations.
  EU_ETS_REFERENCE below is a placeholder for UI display only; the user must
  enter the current market price.

Regulation snapshot for this build: see REGULATION_SNAPSHOT.
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Snapshot metadata — embedded in every tool output
# ---------------------------------------------------------------------------
REGULATION_SNAPSHOT = {
    "snapshot_date": "2026-06",
    "cbam_phase": "Definitive phase (from 1 January 2026)",
    "key_regulations": [
        "Regulation (EU) 2023/956 (core CBAM)",
        "Implementing Reg. (EU) 2023/1773 (transitional rules)",
        "Implementing Reg. (EU) 2025/2621 (definitive-phase default values)",
        "Omnibus Reg. (EU) 2025/2083 (deadline extensions)",
    ],
    "verify_at": "https://eur-lex.europa.eu",
    "cea_grid_version": "V21.0 (FY 2024-25, published Nov 2025)",
    "gwp_basis": "IPCC AR5 GWP-100 (2013); AR6 available as opt-in",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Factor:
    """A single scalar emission factor / constant with provenance."""
    value: float
    unit: str
    source: str
    vintage: str
    url: str = ""
    note: str = ""


@dataclass(frozen=True)
class FuelFactor:
    """Fuel combustion factor. CO2 per tonne fuel is derived from NCV x EF."""
    key: str
    label: str
    ncv_tj_per_t: float        # Net Calorific Value, TJ per tonne of fuel
    ef_kgco2_per_tj: float     # CO2 emission factor, kgCO2 per TJ
    source: str
    vintage: str
    url: str = ""
    note: str = ""
    basis: str = "IPCC 2006 (exact)"   # C-04: "IPCC 2006 (exact)" | "India-adjusted"

    @property
    def tco2_per_t(self) -> float:
        """CO2 emitted per tonne of fuel burned = NCV(TJ/t) * EF(kgCO2/TJ) / 1000."""
        return round(self.ncv_tj_per_t * self.ef_kgco2_per_tj / 1000.0, 4)


# ---------------------------------------------------------------------------
# 1. Fuel combustion factors — TWO LANES (C-04):
#    (a) IPCC-exact: NCV = IPCC 2006 Vol.2 Ch.1 Table 1.2, CO2 EF = Table 1.4.
#        These carry basis="IPCC 2006 (exact)" and cite IPCC truthfully.
#    (b) India-adjusted: NCV deviates from IPCC to reflect Indian coal chemistry;
#        basis="India-adjusted" and the source names the real basis (NOT IPCC's
#        NCV). CO2 EF stays IPCC (fuel-chemistry based).
#    NCV in TJ/tonne (TJ/Mg); EF in kgCO2/TJ.
#    India note: the IPCC global bituminous NCV (25.8 TJ/t) OVERSTATES Indian
#    coal due to high ash (~30-35%). Prefer CEA params or lab NCV.
# ---------------------------------------------------------------------------
_IPCC = "IPCC 2006 Guidelines Vol.2 (Energy) Ch.1 Table 1.2 (NCV) / Table 1.4 (CO2 EF)"
_IPCC_URL = "https://www.ipcc-nggip.iges.or.jp/public/2006gl"

FUELS = {
    "coke": FuelFactor(
        "coke", "Coke (metallurgical / coke-oven coke)", 28.2, 107.0, _IPCC, "2006",
        _IPCC_URL, "IPCC coke-oven coke. ~3.017 tCO2/t.",
    ),
    "bituminous_coal_global": FuelFactor(
        "bituminous_coal_global", "Bituminous coal (IPCC other-bituminous default)",
        25.8, 94.6, _IPCC, "2006", _IPCC_URL,
        "IPCC 'other bituminous coal' default. Overstates high-ash Indian coal "
        "(~2.441 tCO2/t) — prefer the India-adjusted entry or lab NCV.",
    ),
    "bituminous_coal_india": FuelFactor(
        "bituminous_coal_india", "Bituminous coal (India-adjusted)",
        22.0, 94.6,
        "India-adjusted NCV (high-ash coal); CO2 EF from IPCC 2006 Table 1.4",
        "2006", _IPCC_URL,
        "Indian NCV ~18-22 TJ/t (high ash 30-35%) — below IPCC 25.8. Editable — "
        "use CEA params or lab analysis. 22.0 -> ~2.081 tCO2/t.",
        basis="India-adjusted",
    ),
    "sub_bituminous_coal": FuelFactor(
        "sub_bituminous_coal", "Sub-bituminous coal", 18.9, 96.1, _IPCC, "2006",
        _IPCC_URL, "IPCC default; a match for some Indian grades (~1.816 tCO2/t).",
    ),
    "lignite": FuelFactor(
        "lignite", "Lignite / tertiary coal", 11.9, 101.0, _IPCC, "2006", _IPCC_URL,
        "IPCC default; eastern India lignite mines (~1.202 tCO2/t).",
    ),
    "natural_gas": FuelFactor(
        "natural_gas", "Natural gas", 48.0, 56.1, _IPCC, "2006", _IPCC_URL,
        "IPCC default; consistent globally (~2.693 tCO2/t).",
    ),
    "petroleum_coke": FuelFactor(
        "petroleum_coke", "Petroleum coke", 32.5, 97.5, _IPCC, "2006", _IPCC_URL,
        "IPCC default; common in Indian cement (~3.169 tCO2/t).",
    ),
    "heavy_fuel_oil": FuelFactor(
        "heavy_fuel_oil", "Heavy fuel oil / furnace oil (residual fuel oil)", 40.4,
        77.4, _IPCC, "2006", _IPCC_URL,
        "IPCC residual fuel oil; pre-heat chambers, ship fuel (~3.127 tCO2/t).",
    ),
    "diesel": FuelFactor(
        "diesel", "Diesel / gas oil", 43.0, 74.1, _IPCC, "2006", _IPCC_URL,
        "IPCC gas/diesel oil; logistics, generator sets (~3.186 tCO2/t).",
    ),
    "biomass": FuelFactor(
        "biomass", "Biomass (wood / wood waste, dry)", 15.6, 112.0, _IPCC, "2006",
        _IPCC_URL,
        "IPCC wood/wood-waste. Carbon-neutral if sustainably harvested; treated as "
        "zero net CO2 for reporting. Gross factor ~1.747 tCO2/t shown for reference.",
    ),
}

# Fuels whose biogenic CO2 is reported as net-zero (combustion CO2 excluded).
BIOGENIC_FUELS = {"biomass"}


# ---------------------------------------------------------------------------
# 2. India grid emission factors — CEA CO2 Baseline Database
#    Source: Central Electricity Authority, Ministry of Power, GoI.
# ---------------------------------------------------------------------------
_CEA = "CEA CO2 Baseline Database for the Indian Power Sector"
_CEA_URL = "https://cea.nic.in"

GRID_EF = {
    "national_v21": Factor(
        0.7117, "tCO2/MWh", _CEA + " V21.0", "FY 2024-25", _CEA_URL,
        "All-India weighted-average grid EF. Default choice for national use.",
    ),
    "national_v20": Factor(
        0.727, "tCO2/MWh", _CEA + " V20.0", "FY 2023-24", _CEA_URL,
        "Prior-year national figure (for comparison only).",
    ),
    # C-08: regional (eastern / north-eastern) rows were removed. They cited
    # "CEA V21.0 (regional)", but CEA V21.0 publishes ONLY an all-India weighted
    # factor — no verifiable regional breakdown exists at that vintage. Rather than
    # print an unverifiable citation in user outputs, we drop them. If a regional
    # figure is ever needed, re-add it with a real, checkable derivation.
    "captive_renewable_zero": Factor(
        0.0, "tCO2/MWh", "User-declared captive renewable", "n/a", "",
        "Use 0 only with documentation (PPA / captive solar-wind metering).",
    ),
}

# FLAG: CEA factors are not formally pre-approved by the EU Commission for CBAM
# indirect emissions (EU uses IEA 5-yr national averages for defaults). Surface
# this distinction in the UI; allow the producer to document their electricity
# source when claiming CEA values.
GRID_EF_FLAG = (
    "CEA grid factors are the most current Indian values but are NOT yet formally "
    "accepted by the EU Commission for CBAM indirect-emission calculations "
    "(rules under consultation as of June 2026). Document your electricity source."
)


# ---------------------------------------------------------------------------
# 3. CBAM definitive-phase default values — Implementing Reg. (EU) 2025/2621
#    Effective 1 Jan 2026. The binding country×CN-code figures now live in
#    `cbam_india_defaults` (the India sheet of the official Annex, ingested to a
#    versioned CSV via scripts/ingest_cbam_defaults.py). The Annex already
#    contains the pre-computed marked-up columns, so no mark-up schedule is
#    carried here anymore.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 4. Global Warming Potentials (GWP-100). AR5 is primary; AR6 opt-in.
#    Values verified against IPCC AR5 (2013) WG1 Table 8.A.1 and IPCC AR6 (2021)
#    WG1 Ch.7 / WGIII Annex II GWP-100 tables. See ECOSETU audit §2.6 (C-03).
#    CH4 AR6 has a biogenic/fossil split (GHG Protocol AR6 guidance); the scalar
#    "CH4" key keeps the CH4-only value for back-compat. The engine currently
#    applies CF4/C2F6/N2O only; the rest are encoded for completeness + tests.
# ---------------------------------------------------------------------------
GWP_AR5 = {"CO2": 1, "CH4": 28, "N2O": 265, "CF4": 6630, "C2F6": 11100, "SF6": 23500}
GWP_AR6 = {
    "CO2": 1,
    "CH4": 27.9, "CH4_biogenic": 27.0, "CH4_fossil": 29.8,
    "N2O": 273, "CF4": 7380, "C2F6": 12400, "SF6": 25200,
}

GWP_SETS = {"AR5": GWP_AR5, "AR6": GWP_AR6}
GWP_DEFAULT = "AR5"  # EU practice defaults to AR5 until formal AR6 adoption (~2027-28)


# ---------------------------------------------------------------------------
# 5. Process emission factors by sector — IPCC 2006 Vol.3
# ---------------------------------------------------------------------------
_IPCC_V3 = "IPCC 2006 Guidelines Vol.3 (Industrial Processes)"

PROCESS_EF = {
    "steel_bf_bof_reduction": Factor(
        0.18, "tCO2/t crude steel", _IPCC_V3 + " Ch.4; GHG Protocol Steel Guidance",
        "2006", _IPCC_URL, "Iron ore reduction (limestone, coke), fixed chemistry.",
    ),
    "cement_calcination": Factor(
        0.5246, "tCO2/t clinker", _IPCC_V3 + " Ch.3.1; WBCSD CSI = 0.525",
        "2006/2011", _IPCC_URL,
        "Limestone calcination (CaCO3 -> CaO + CO2). Multiply by clinker fraction.",
    ),
    "aluminium_anode_oxidation": Factor(
        0.04, "tCO2/t Al", _IPCC_V3 + " Ch.4.4", "2006", _IPCC_URL,
        "Hall-Heroult anode oxidation; IPCC range 0.03-0.05.",
    ),
    # C-02: default to CWPB / point-feed prebake — the modern technology used by
    # essentially all Indian smelters. The prior 1.5 / 0.15 pair matched NO cell
    # technology and inflated PFCs to ~11.6 tCO2e/t. See AL_SMELTER_TECH below for
    # the full IPCC 2006 Table 4.15 Tier-1 set; these two hold the default tech.
    "aluminium_cf4_per_t": Factor(
        0.4, "kg CF4/t Al", _IPCC_V3 + " Ch.4.4 Table 4.15 (CWPB)", "2006", _IPCC_URL,
        "Anode-effect PFC, Tier-1 CWPB default. Apply GWP(CF4).",
    ),
    "aluminium_c2f6_per_t": Factor(
        0.04, "kg C2F6/t Al", _IPCC_V3 + " Ch.4.4 Table 4.15 (CWPB)", "2006", _IPCC_URL,
        "Anode-effect PFC, Tier-1 CWPB default. Apply GWP(C2F6).",
    ),
    "fertiliser_nitric_acid_n2o": Factor(
        4.8, "kg N2O/t HNO3", _IPCC_V3 + " Ch.3.2 Table 3.1", "2006", _IPCC_URL,
        "Catalytic oxidation; IPCC range 2-9 kg/t. Apply GWP(N2O).",
    ),
}


# ---------------------------------------------------------------------------
# C-02: IPCC 2006 Vol.3 Ch.4 Table 4.15 — Tier-1 PFC emission factors by
# aluminium cell technology (kg gas / tonne Al). Tier-1 is a conservative
# fallback; smelters with anode-effect data should use Tier-2 (Table 4.16).
# CWPB includes Point-Feed and Bar-Broken Prebake per the table's footnotes.
# ---------------------------------------------------------------------------
AL_SMELTER_TECH = {
    "CWPB / PFPB (point-feed prebake)": {"cf4": 0.4, "c2f6": 0.04},
    "SWPB (side-worked prebake)":       {"cf4": 1.6, "c2f6": 0.4},
    "VSS (vertical-stud Soderberg)":    {"cf4": 0.8, "c2f6": 0.04},
    "HSS (horizontal-stud Soderberg)":  {"cf4": 0.4, "c2f6": 0.03},
}
AL_SMELTER_TECH_DEFAULT = "CWPB / PFPB (point-feed prebake)"


# ---------------------------------------------------------------------------
# C-06: CBAM factor phase-in (free-allocation adjustment) — IR (EU) 2025/2620.
# The CBAM factor is the share of embedded emissions that is PAYABLE each year;
# the remainder mirrors the free allocation still granted to EU producers and is
# NOT payable. It ramps 2.5% (2026) -> 100% (2034). Applying it is what turns the
# naive "SEE x price" (gross) into the realistic net-of-free-allocation cost.
# ---------------------------------------------------------------------------
CBAM_FACTOR_SCHEDULE = {
    2026: 0.025, 2027: 0.05, 2028: 0.10, 2029: 0.225, 2030: 0.485,
    2031: 0.61, 2032: 0.735, 2033: 0.86, 2034: 1.00,
}
CBAM_FACTOR_SOURCE = "Implementing Reg. (EU) 2025/2620 (CBAM free-allocation factor)"

# De minimis: imports up to this aggregate mass per importer per year are exempt
# (all CBAM goods combined; NOT applicable to hydrogen & electricity). Reg (EU)
# 2023/956 as amended by Omnibus Reg. (EU) 2025/2083.
CBAM_DE_MINIMIS_T = 50.0


# ---------------------------------------------------------------------------
# 6. EU ETS / CBAM certificate price — REFERENCE ONLY (never hardcode)
# ---------------------------------------------------------------------------
EU_ETS_REFERENCE = Factor(
    75.36, "EUR/tCO2e", "EU ETS Q1 2026 actual", "2026-Q1",
    "https://www.eex.com",
    "REFERENCE ONLY. Certificate prices are volatile (EUR 40-100+). The tool must "
    "let the user enter the current price and show a sensitivity table. Never "
    "hardcode this value into calculations.",
)

# India carbon price recognised by EU for the CBAM Article 9 deduction (as of Jul 2026).
# (Art. 9 is the carbon-price-paid-in-country-of-origin deduction; Art. 10 covers
# authorised-declarant registration — an earlier comment mis-cited Article 10.)
INDIA_CARBON_PRICE = Factor(
    0.0, "EUR/tCO2e", "No EU-recognised Indian carbon price (July 2026)", "2026-07",
    "", "India's CCTS (Carbon Credit Trading Scheme) exists domestically but is NOT "
    "yet recognised by the EU Commission for CBAM Article 9 deductions (Jul 2026). "
    "Deduction = 0 unless and until a scheme is recognised.",
)

# Default oxidation factor for complete industrial combustion (IPCC allows 0.99 for coal).
DEFAULT_OXIDATION_FACTOR = 1.0


# ---------------------------------------------------------------------------
# Self-test: run `python emission_factors.py` to eyeball values vs the spec.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Ecosetu CBAM emission factors — sanity check ===\n")
    print(f"Regulation snapshot: {REGULATION_SNAPSHOT['snapshot_date']} | "
          f"CEA {REGULATION_SNAPSHOT['cea_grid_version']}\n")

    print("Fuel combustion (tCO2 per tonne fuel):")
    for f in FUELS.values():
        print(f"  {f.label:38s} NCV {f.ncv_tj_per_t:5.1f}  EF {f.ef_kgco2_per_tj:6.1f}"
              f"  -> {f.tco2_per_t:.4f} tCO2/t")

    print("\nCBAM defaults now live in cbam_india_defaults (official India Annex CSV).")

    print("\nGrid EF (tCO2/MWh):")
    for k, g in GRID_EF.items():
        print(f"  {k:24s} {g.value:.4f}  [{g.vintage}]")

    # Spot checks against the spec's worked example numbers.
    assert FUELS["coke"].tco2_per_t == 3.0174, FUELS["coke"].tco2_per_t
    assert FUELS["natural_gas"].tco2_per_t == 2.6928, FUELS["natural_gas"].tco2_per_t
    assert FUELS["bituminous_coal_india"].tco2_per_t == 2.0812
    print("\nAll spot checks passed.")
