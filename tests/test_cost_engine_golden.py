"""Golden tests for the CBAM cost engine and the remaining audit fixes.

Locks calculation-correctness fixes from the ECOSETU audit (04-Jul-2026)
section 3.A that were not already pinned elsewhere:

  C-06  free-allocation phase-in factor + gross/net cost + de minimis + Article 9
  C-10  hydrogen routes to `combustion_only` (0 process emissions)
  C-14  to_intensity refuses a non-positive production denominator
  C-08  removed regional grid EFs are truly gone from GRID_EF

Each assertion pins a number or contract that flows into a user-facing CBAM
statement; changing one requires a source citation in the same commit.

Run:  python -m pytest tests/ -q
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cost_engine import (  # noqa: E402
    cbam_factor,
    payable_see,
    net_certificate_price,
    is_below_de_minimis,
    cost_breakdown,
    phase_in_curve,
)
from emission_factors import (  # noqa: E402
    CBAM_FACTOR_SCHEDULE,
    CBAM_DE_MINIMIS_T,
    GRID_EF,
    INDIA_CARBON_PRICE,
)
from see_engine import calc_process_emissions, to_intensity, ProductionNotSetError  # noqa: E402
from cbam_meta import route_engine_key  # noqa: E402


# ---------------------------------------------------------------------------
# C-06 — CBAM free-allocation phase-in factor (IR (EU) 2025/2620).
# The official schedule: only this fraction of embedded emissions is payable in
# a given year; the rest is covered by free allocation being phased out.
# ---------------------------------------------------------------------------
def test_phase_in_schedule_matches_regulation():
    assert CBAM_FACTOR_SCHEDULE == {
        2026: 0.025,
        2027: 0.05,
        2028: 0.10,
        2029: 0.225,
        2030: 0.485,
        2031: 0.61,
        2032: 0.735,
        2033: 0.86,
        2034: 1.00,
    }


def test_cbam_factor_2026_is_2_5_percent():
    assert cbam_factor(2026) == 0.025


def test_cbam_factor_pre_2026_is_zero():
    assert cbam_factor(2025) == 0.0
    assert cbam_factor(2020) == 0.0


def test_cbam_factor_post_2034_fully_phased_in():
    assert cbam_factor(2035) == 1.0
    assert cbam_factor(2040) == 1.0


# ---------------------------------------------------------------------------
# C-06 — gross vs net cost under the fallback (whole-SEE-benchmark) model.
# 2026: net cost is 2.5% of gross; 2034: net == gross.
# ---------------------------------------------------------------------------
def test_2026_net_is_2_5_percent_of_gross():
    bd = cost_breakdown(see=2.0, year=2026, price=80.0, volume_t=10000.0)
    assert bd["gross_cost_per_t_eur"] == 160.0
    assert bd["net_cost_per_t_eur"] == 4.0  # 2.0 * 0.025 * 80
    assert bd["net_cost_per_t_eur"] == round(bd["gross_cost_per_t_eur"] * 0.025, 2)


def test_2034_net_equals_gross():
    bd = cost_breakdown(see=2.0, year=2034, price=80.0, volume_t=10000.0)
    assert bd["cbam_factor"] == 1.0
    assert bd["net_cost_per_t_eur"] == bd["gross_cost_per_t_eur"]


def test_benchmark_model_below_benchmark_is_near_zero_in_2026():
    # SEE 1.0 under a 1.5 benchmark: payable = max(1.0 - 1.5*(1-0.025), 0).
    assert payable_see(1.0, 2026, benchmark=1.5) == max(1.0 - 1.5 * 0.975, 0.0)


# ---------------------------------------------------------------------------
# C-06 — 50 t/importer/year de minimis (excludes hydrogen & electricity).
# Boundary is strict: exactly 50 t is NOT below.
# ---------------------------------------------------------------------------
def test_de_minimis_threshold_value():
    assert CBAM_DE_MINIMIS_T == 50.0


def test_de_minimis_boundary_is_strict():
    assert is_below_de_minimis(49.999) is True
    assert is_below_de_minimis(50.0) is False
    assert is_below_de_minimis(50.001) is False


def test_hydrogen_never_below_de_minimis():
    assert is_below_de_minimis(1.0, is_hydrogen=True) is False


# ---------------------------------------------------------------------------
# C-09 / C-06 — Article 9 carbon-price deduction. India's CCTS is not
# EU-recognised (July 2026), so the default deduction is EUR 0 (no discount).
# ---------------------------------------------------------------------------
def test_india_deduction_default_is_zero():
    assert INDIA_CARBON_PRICE.value == 0.0
    assert net_certificate_price(80.0) == 80.0


def test_article9_deduction_subtracts_and_clamps():
    assert net_certificate_price(80.0, india_deduction=10.0) == 70.0
    assert net_certificate_price(5.0, india_deduction=20.0) == 0.0


# ---------------------------------------------------------------------------
# C-06 — phase-in curve spans the whole 2026-2034 window, in order.
# ---------------------------------------------------------------------------
def test_phase_in_curve_covers_2026_to_2034():
    rows = phase_in_curve(see=2.0, net_price=80.0, volume_t=10000.0)
    assert [r["year"] for r in rows] == list(range(2026, 2035))
    assert rows[0]["cbam_factor"] == 0.025
    assert rows[-1]["cbam_factor"] == 1.0


# ---------------------------------------------------------------------------
# C-10 — hydrogen must route to `combustion_only` (0 process emissions); the
# SMR feedstock CO2 is captured through the combustion inputs, not a process
# term. Previously it borrowed `fertiliser_ammonia` by accident.
# ---------------------------------------------------------------------------
def test_hydrogen_routes_to_combustion_only():
    assert route_engine_key("Hydrogen", "Grey (SMR / coal gasification)") == "combustion_only"
    assert route_engine_key("Hydrogen", "Other") == "combustion_only"


def test_combustion_only_has_zero_process_emissions():
    assert calc_process_emissions("combustion_only") == 0.0


# ---------------------------------------------------------------------------
# C-14 — an annual total cannot be converted to per-tonne intensity without a
# positive production denominator. Before the fix this silently returned 0.0,
# hiding a missing-input error behind a plausible-looking zero.
# ---------------------------------------------------------------------------
def test_to_intensity_raises_on_zero_production():
    with pytest.raises(ProductionNotSetError):
        to_intensity(1000.0, 0.0)


def test_to_intensity_raises_on_negative_production():
    with pytest.raises(ProductionNotSetError):
        to_intensity(1000.0, -5.0)


def test_to_intensity_valid_denominator():
    assert to_intensity(1000.0, 500.0) == 2.0


# ---------------------------------------------------------------------------
# C-08 — the unsupported regional grid EFs (CEA V21.0 has no regional
# breakdown) were removed. They must not reappear in GRID_EF.
# ---------------------------------------------------------------------------
def test_regional_grid_efs_removed():
    assert "eastern_grid" not in GRID_EF
    assert "north_eastern_grid" not in GRID_EF


def test_national_grid_efs_present():
    assert "national_v21" in GRID_EF
    assert "national_v20" in GRID_EF
    assert "captive_renewable_zero" in GRID_EF
