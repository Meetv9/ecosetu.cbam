"""Golden tests for the SEE engine's process-emission routing.

Locks the calculation-correctness fixes from the ECOSETU audit (04-Jul-2026)
section 3.A. Each assertion pins a number that flows into a user-facing CBAM
statement; changing one requires a source citation in the same commit.

Run:  python -m pytest tests/ -q   (or)   python tests/test_see_engine_golden.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from see_engine import calc_process_emissions, compute_see, FuelInput  # noqa: E402
from emission_factors import AL_SMELTER_TECH, GWP_AR5  # noqa: E402


# ---------------------------------------------------------------------------
# C-01 — secondary & downstream aluminium must NOT inherit the primary
# smelter's anode-oxidation + PFC (CF4/C2F6) process emissions. Those arise
# ONLY in Hall-Heroult reduction. Before the fix these routes silently carried
# ~+11.5 tCO2e/t of phantom process emissions.
# ---------------------------------------------------------------------------
def test_secondary_aluminium_has_zero_process_emissions():
    assert calc_process_emissions("aluminium_secondary") == 0.0


def test_downstream_aluminium_has_zero_process_emissions():
    assert calc_process_emissions("aluminium_downstream") == 0.0


def test_primary_aluminium_still_carries_pfc():
    # Sanity: the primary route DOES include anode + PFC, so it must be > 0
    # even with zero fuel input.
    val = calc_process_emissions("aluminium_primary")
    assert val > 0.0


def test_secondary_aluminium_see_is_combustion_only():
    # A secondary (scrap-melting) installation's SEE should equal its
    # combustion only — no process, and electricity is not in SEE for Al.
    res = compute_see(
        sector="Aluminium",
        fuels=[FuelInput("natural_gas", 0.05)],
        process_route="aluminium_secondary",
        electricity_mwh_per_t=1.0,
        grid_ef=0.7117,
    )
    assert res.process == 0.0
    assert not res.indirect_included
    assert round(res.total_see, 4) == round(res.combustion, 4)


# ---------------------------------------------------------------------------
# C-02 — smelter-technology PFC factors must match IPCC 2006 Table 4.15 exactly,
# and the default (CWPB) must replace the old technology-agnostic 1.5/0.15 pair
# that inflated PFCs to ~11.6 tCO2e/t.
# ---------------------------------------------------------------------------
def test_table_4_15_tier1_factors():
    assert AL_SMELTER_TECH["CWPB / PFPB (point-feed prebake)"] == {"cf4": 0.4, "c2f6": 0.04}
    assert AL_SMELTER_TECH["SWPB (side-worked prebake)"] == {"cf4": 1.6, "c2f6": 0.4}
    assert AL_SMELTER_TECH["VSS (vertical-stud Soderberg)"] == {"cf4": 0.8, "c2f6": 0.04}
    assert AL_SMELTER_TECH["HSS (horizontal-stud Soderberg)"] == {"cf4": 0.4, "c2f6": 0.03}


def test_primary_al_cwpb_process_is_realistic():
    # CWPB Tier-1: anode 0.04 + PFC (0.4*GWP_CF4 + 0.04*GWP_C2F6)/1000, AR5 basis.
    expected_pfc = (0.4 * GWP_AR5["CF4"] + 0.04 * GWP_AR5["C2F6"]) / 1000.0
    expected = 0.04 + expected_pfc
    got = calc_process_emissions(
        "aluminium_primary", gwp_set="AR5",
        anode_override=0.04, cf4_kg_per_t=0.4, c2f6_kg_per_t=0.04,
    )
    assert round(got, 4) == round(expected, 4)
    # And it must be far below the old ~11.6 phantom figure.
    assert got < 4.0


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
