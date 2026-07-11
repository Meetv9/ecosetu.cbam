"""Golden tests for the two-lane fuel registry (C-04).

Locks the fuel NCV/EF corrections from the ECOSETU audit (04-Jul-2026)
section 3.A / §2.7. IPCC-exact fuels must carry the published IPCC 2006
Vol.2 Ch.1 Table 1.2 (NCV) / Table 1.4 (CO2 EF) values; the one
India-adjusted entry must be flagged as such and NOT claim IPCC's NCV.
Changing any pinned number requires a source citation in the same commit.

Run:  python -m pytest tests/ -q   (or)   python tests/test_fuels_golden.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emission_factors import FUELS  # noqa: E402


# ---------------------------------------------------------------------------
# C-04 — IPCC-exact NCV (Table 1.2) and CO2 EF (Table 1.4). Each tuple is
# (ncv_tj_per_t, ef_kgco2_per_tj, derived_tco2_per_t).
# ---------------------------------------------------------------------------
IPCC_EXACT = {
    "coke":                    (28.2, 107.0, 3.0174),
    "bituminous_coal_global":  (25.8,  94.6, 2.4407),
    "sub_bituminous_coal":     (18.9,  96.1, 1.8163),
    "lignite":                 (11.9, 101.0, 1.2019),
    "natural_gas":             (48.0,  56.1, 2.6928),
    "petroleum_coke":          (32.5,  97.5, 3.1688),
    "heavy_fuel_oil":          (40.4,  77.4, 3.1270),
    "diesel":                  (43.0,  74.1, 3.1863),
    "biomass":                 (15.6, 112.0, 1.7472),
}


def test_ipcc_exact_fuel_ncv_ef_match_published():
    for key, (ncv, ef, tco2) in IPCC_EXACT.items():
        f = FUELS[key]
        assert f.ncv_tj_per_t == ncv, f"{key} NCV"
        assert f.ef_kgco2_per_tj == ef, f"{key} EF"
        assert f.tco2_per_t == tco2, f"{key} tCO2/t = {f.tco2_per_t}"


def test_ipcc_exact_fuels_are_flagged_ipcc_basis():
    for key in IPCC_EXACT:
        assert FUELS[key].basis == "IPCC 2006 (exact)", key


def test_ipcc_exact_fuels_cite_ipcc_source():
    for key in IPCC_EXACT:
        assert "IPCC 2006" in FUELS[key].source, key


# ---------------------------------------------------------------------------
# C-04 — the India-adjusted lane must NOT masquerade as IPCC. Its NCV is a
# deliberate deviation (high-ash Indian coal), so it is flagged and its source
# must not claim IPCC's NCV. CO2 EF still comes from IPCC Table 1.4 (chemistry).
# ---------------------------------------------------------------------------
def test_india_adjusted_bituminous_is_flagged_not_ipcc_exact():
    f = FUELS["bituminous_coal_india"]
    assert f.basis == "India-adjusted"
    assert f.ncv_tj_per_t == 22.0
    assert f.ef_kgco2_per_tj == 94.6
    assert f.tco2_per_t == 2.0812
    # Source must be honest: it is NOT the IPCC NCV.
    assert "India-adjusted" in f.source
    assert f.basis != "IPCC 2006 (exact)"


def test_india_ncv_is_below_ipcc_global_default():
    # High-ash Indian coal must sit below the IPCC global bituminous NCV, else
    # the India lane provides no correction.
    assert (FUELS["bituminous_coal_india"].ncv_tj_per_t
            < FUELS["bituminous_coal_global"].ncv_tj_per_t)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
