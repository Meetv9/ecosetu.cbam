"""Ecosetu CBAM — SEE calculation engine.

PURE PYTHON. No Streamlit, no I/O. Every function is independently testable.

Implements the CBAM Specific Embedded Emissions (SEE) methodology:

    SEE = Direct Embedded Emissions (DEE) + Indirect Embedded Emissions (IEE)

    DEE  = combustion (Sigma fuel_i x NCV_i x EF_i x f_ox) + process emissions
    IEE  = electricity_consumed x grid_EF   (cement & fertilisers ONLY)
    +precursor contributions where applicable

All quantities are expressed PER TONNE OF PRODUCT (the SEE functional unit).
The UI layer converts annual totals -> per-tonne by dividing by annual
production before calling these functions. See `to_intensity`.
"""

from dataclasses import dataclass, field

from emission_factors import (
    FUELS,
    BIOGENIC_FUELS,
    PROCESS_EF,
    GWP_SETS,
    GWP_DEFAULT,
    DEFAULT_OXIDATION_FACTOR,
)


# Indirect (electricity) emissions count toward CBAM SEE ONLY for these sectors.
SECTORS_WITH_INDIRECT = {"Cement", "Fertilisers"}


# ---------------------------------------------------------------------------
# Inputs & outputs
# ---------------------------------------------------------------------------
@dataclass
class FuelInput:
    """One fuel line. `quantity_t` is tonnes of fuel per tonne of product."""
    fuel_key: str
    quantity_t: float
    ncv_tj_per_t: float | None = None      # override library NCV if set
    ef_kgco2_per_tj: float | None = None   # override library EF if set
    oxidation: float = DEFAULT_OXIDATION_FACTOR
    is_biogenic: bool | None = None        # override biogenic flag if set


@dataclass
class Precursor:
    """A CBAM-covered precursor consumed per tonne of product."""
    label: str
    see_per_t: float            # tCO2e per tonne of precursor
    quantity_t: float           # tonnes of precursor per tonne of product
    uses_default: bool = False  # True if see_per_t is a default (carries mark-up)


@dataclass
class SEEBreakdown:
    """Result of a SEE computation, all in tCO2e per tonne of product."""
    combustion: float
    process: float
    indirect: float                 # included in SEE (0 if sector excludes it)
    precursors: float
    total_see: float
    indirect_included: bool
    informational_indirect: float   # Scope-2 electricity NOT counted in SEE
    gwp_set: str

    def as_rows(self) -> list[tuple[str, float]]:
        """Display-ready breakdown rows (3-dp)."""
        rows = [
            ("Direct combustion", round(self.combustion, 3)),
            ("Process emissions", round(self.process, 3)),
        ]
        if self.indirect_included:
            rows.append(("Indirect (electricity)", round(self.indirect, 3)))
        if self.precursors:
            rows.append(("Precursors", round(self.precursors, 3)))
        rows.append(("TOTAL SEE", round(self.total_see, 3)))
        return rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class ProductionNotSetError(ValueError):
    """Raised when an annual total is converted to intensity without production.

    C-14: returning a silent 0.0 masked a missing annual-production input — the
    whole SEE would read as zero with no signal to the user. Annual-basis inputs
    MUST have production > 0; the UI validates this before computing.
    """


def to_intensity(annual_value: float, annual_production_t: float) -> float:
    """Convert an annual total to a per-tonne-of-product intensity.

    Raises ProductionNotSetError if production is not positive (C-14) — a zero or
    missing denominator cannot yield a meaningful per-tonne figure.
    """
    if annual_production_t <= 0:
        raise ProductionNotSetError(
            "Annual production must be greater than 0 to convert annual totals "
            "to per-tonne intensity. Enter annual production in Facility Setup."
        )
    return annual_value / annual_production_t


def _resolve_fuel(fi: FuelInput) -> tuple[float, float, bool]:
    """Return (ncv, ef, biogenic) for a fuel input, applying overrides."""
    lib = FUELS.get(fi.fuel_key)
    ncv = fi.ncv_tj_per_t if fi.ncv_tj_per_t is not None else (lib.ncv_tj_per_t if lib else 0.0)
    ef = fi.ef_kgco2_per_tj if fi.ef_kgco2_per_tj is not None else (lib.ef_kgco2_per_tj if lib else 0.0)
    if fi.is_biogenic is not None:
        biogenic = fi.is_biogenic
    else:
        biogenic = fi.fuel_key in BIOGENIC_FUELS
    return ncv, ef, biogenic


# ---------------------------------------------------------------------------
# 1. Combustion emissions
# ---------------------------------------------------------------------------
def fuel_emissions(fi: FuelInput) -> float:
    """tCO2 per tonne product from one fuel = qty x NCV x EF x f_ox / 1000.

    Biogenic fuels (e.g. sustainably-harvested biomass) are reported as net-zero.
    """
    ncv, ef, biogenic = _resolve_fuel(fi)
    if biogenic:
        return 0.0
    return fi.quantity_t * ncv * ef * fi.oxidation / 1000.0


def calc_combustion_emissions(fuels: list[FuelInput]) -> float:
    """Total combustion emissions across all fuel lines (tCO2e/t product)."""
    return round(sum(fuel_emissions(f) for f in fuels), 4)


# ---------------------------------------------------------------------------
# 2. Process emissions (sector/route specific)
# ---------------------------------------------------------------------------
def calc_process_emissions(route_key: str, gwp_set: str = GWP_DEFAULT, **kw) -> float:
    """Process (non-combustion) emissions, tCO2e per tonne of product.

    Recognised route keys and their kwargs:
      steel_bf_bof        : override (default 0.18 tCO2/t crude steel)
      steel_dri, steel_scrap_eaf : override (default 0.0)
      cement              : clinker_fraction (t clinker/t cement), override
      aluminium_primary   : anode_override, cf4_kg_per_t, c2f6_kg_per_t
      aluminium_secondary : 0 (scrap melting = combustion + electricity only)
      aluminium_downstream: 0 (semi-fabrication = combustion + electricity only)
      fertiliser_nitric_acid : n2o_kg_per_t
      fertiliser_ammonia  : 0 (SMR = combustion only)
      combustion_only     : 0 (e.g. hydrogen SMR — feedstock CO2 enters via fuel)
    An explicit `override` kwarg, when provided, replaces the computed value.

    C-01: secondary & downstream aluminium must NOT inherit primary-smelter
    anode-oxidation + PFC emissions; those arise only in Hall-Heroult reduction.
    """
    gwp = GWP_SETS.get(gwp_set, GWP_SETS[GWP_DEFAULT])

    if "override" in kw and kw["override"] is not None:
        return float(kw["override"])

    if route_key == "steel_bf_bof":
        return PROCESS_EF["steel_bf_bof_reduction"].value

    if route_key in ("steel_dri", "steel_scrap_eaf"):
        return 0.0

    if route_key == "cement":
        clinker_fraction = kw.get("clinker_fraction", 0.95)
        return PROCESS_EF["cement_calcination"].value * clinker_fraction

    if route_key == "aluminium_primary":
        anode = kw.get("anode_override", PROCESS_EF["aluminium_anode_oxidation"].value)
        cf4 = kw.get("cf4_kg_per_t", PROCESS_EF["aluminium_cf4_per_t"].value)
        c2f6 = kw.get("c2f6_kg_per_t", PROCESS_EF["aluminium_c2f6_per_t"].value)
        pfc = (cf4 * gwp["CF4"] + c2f6 * gwp["C2F6"]) / 1000.0  # kg -> t CO2e
        return anode + pfc

    if route_key in ("aluminium_secondary", "aluminium_downstream"):
        return 0.0  # C-01: no reduction-cell process emissions off the primary route

    if route_key == "fertiliser_nitric_acid":
        n2o = kw.get("n2o_kg_per_t", PROCESS_EF["fertiliser_nitric_acid_n2o"].value)
        return n2o * gwp["N2O"] / 1000.0

    if route_key == "fertiliser_ammonia":
        return 0.0

    if route_key == "combustion_only":
        # C-10: no separate process term — all CO2 (incl. SMR feedstock carbon)
        # is accounted for through the combustion inputs.
        return 0.0

    return 0.0


# ---------------------------------------------------------------------------
# 3. Indirect (electricity) emissions
# ---------------------------------------------------------------------------
def calc_indirect_emissions(electricity_mwh_per_t: float, grid_ef: float) -> float:
    """IEE = electricity consumed (MWh/t) x grid EF (tCO2/MWh)."""
    return electricity_mwh_per_t * grid_ef


# ---------------------------------------------------------------------------
# 4. Precursor contributions
# ---------------------------------------------------------------------------
def calc_precursor_contribution(precursors: list[Precursor] | None) -> float:
    """Sum of SEE_precursor x quantity for each CBAM-covered precursor."""
    if not precursors:
        return 0.0
    return round(sum(p.see_per_t * p.quantity_t for p in precursors), 4)


# ---------------------------------------------------------------------------
# 5. Orchestrator — full SEE
# ---------------------------------------------------------------------------
def compute_see(
    *,
    sector: str,
    fuels: list[FuelInput],
    process_route: str,
    process_kwargs: dict | None = None,
    electricity_mwh_per_t: float = 0.0,
    grid_ef: float = 0.0,
    precursors: list[Precursor] | None = None,
    gwp_set: str = GWP_DEFAULT,
) -> SEEBreakdown:
    """Compute the full SEE breakdown for one product at one installation."""
    process_kwargs = process_kwargs or {}

    combustion = calc_combustion_emissions(fuels)
    process = round(calc_process_emissions(process_route, gwp_set, **process_kwargs), 4)
    indirect_raw = round(calc_indirect_emissions(electricity_mwh_per_t, grid_ef), 4)
    precursor_total = calc_precursor_contribution(precursors)

    indirect_included = sector in SECTORS_WITH_INDIRECT
    indirect = indirect_raw if indirect_included else 0.0
    informational_indirect = 0.0 if indirect_included else indirect_raw

    total = round(combustion + process + indirect + precursor_total, 4)

    return SEEBreakdown(
        combustion=combustion,
        process=process,
        indirect=indirect,
        precursors=precursor_total,
        total_see=total,
        indirect_included=indirect_included,
        informational_indirect=informational_indirect,
        gwp_set=gwp_set,
    )


# ---------------------------------------------------------------------------
# Self-test: reproduces the two worked examples from the spec.
#   Run:  python see_engine.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Ecosetu CBAM SEE engine — worked-example checks ===\n")

    # --- Worked Example 1: Indian steel, BF-BOF -> HRC (expect 2.181) ---
    steel = compute_see(
        sector="Iron & Steel",
        fuels=[
            FuelInput("coke", 0.55),
            FuelInput("bituminous_coal_india", 0.15),  # NCV 22.0
            FuelInput("natural_gas", 0.011),
        ],
        process_route="steel_bf_bof",
        electricity_mwh_per_t=0.40,
        grid_ef=0.7117,  # informational only for steel
    )
    print("Steel BF-BOF -> HRC:")
    for label, val in steel.as_rows():
        print(f"  {label:24s} {val:.3f}")
    print(f"  (informational Scope-2 electricity: {steel.informational_indirect:.3f}, "
          f"not in SEE)\n")

    # --- Worked Example 2: Cement, Portland, wet kiln (expect 0.860) ---
    cement = compute_see(
        sector="Cement",
        fuels=[
            FuelInput("bituminous_coal_india", 0.16, ncv_tj_per_t=20.0),  # India wet kiln
        ],
        process_route="cement",
        process_kwargs={"clinker_fraction": 0.90},
        electricity_mwh_per_t=0.12,
        grid_ef=0.7117,
    )
    print("Cement (Portland, wet kiln):")
    for label, val in cement.as_rows():
        print(f"  {label:24s} {val:.3f}")
    print()

    assert round(steel.total_see, 3) == 2.181, steel.total_see
    assert round(steel.informational_indirect, 3) == 0.285, steel.informational_indirect
    assert round(cement.total_see, 3) == 0.860, cement.total_see
    assert cement.indirect_included and not steel.indirect_included
    print("All worked-example checks passed.")
