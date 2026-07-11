"""Golden tests — every factor must equal its published, cited value.

These lock the numbers that go into user-facing CBAM statements. If a factor
changes, this test must change WITH a source citation in the same commit.
Sources are the ECOSETU audit (04-Jul-2026) §2.6 and the primary refs in §10.

Run:  python -m pytest tests/ -q      (or)   python tests/test_factors_golden.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emission_factors import GWP_AR5, GWP_AR6  # noqa: E402


# ---------------------------------------------------------------------------
# C-03 — Global Warming Potentials (GWP-100), IPCC AR5 (2013) & AR6 (2021).
# Published values per audit §2.6.
# ---------------------------------------------------------------------------
def test_gwp_ar5_published_values():
    assert GWP_AR5["CO2"] == 1
    assert GWP_AR5["CH4"] == 28
    assert GWP_AR5["N2O"] == 265
    assert GWP_AR5["CF4"] == 6630      # was 6500 (wrong) before C-03 fix
    assert GWP_AR5["C2F6"] == 11100
    assert GWP_AR5["SF6"] == 23500


def test_gwp_ar6_published_values():
    assert GWP_AR6["CO2"] == 1
    assert GWP_AR6["N2O"] == 273
    assert GWP_AR6["CF4"] == 7380      # AR6 row previously held AR5 values
    assert GWP_AR6["C2F6"] == 12400
    assert GWP_AR6["SF6"] == 25200


def test_gwp_ar6_ch4_split():
    # AR6 splits CH4 into biogenic / fossil-fugitive (GHG Protocol AR6 guidance).
    assert GWP_AR6["CH4"] == 27.9          # CH4-only scalar (back-compat)
    assert GWP_AR6["CH4_biogenic"] == 27.0
    assert GWP_AR6["CH4_fossil"] == 29.8


def test_ar6_pfc_higher_than_ar5():
    # Sanity: AR6 PFC/SF6 GWPs are all higher than AR5.
    for gas in ("CF4", "C2F6", "SF6"):
        assert GWP_AR6[gas] > GWP_AR5[gas]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
