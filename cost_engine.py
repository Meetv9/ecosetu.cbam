"""Ecosetu CBAM — importer certificate-cost engine v2 (C-06).

PURE PYTHON. No Streamlit, no I/O. Independently testable.

The naive estimate (SEE x price x volume) overstates the 2026 cost by roughly
an order of magnitude because it ignores the EU-ETS free-allocation adjustment
(IR (EU) 2025/2620). During the phase-in, only a fraction of embedded emissions
is actually payable — the "CBAM factor" — rising from 2.5% (2026) to 100% (2034).

This module produces BOTH lines so the producer can talk realistically with an
EU buyer:
  * gross  = full SEE priced at the certificate price (upper bound, phase-out end)
  * net    = payable emissions after the free-allocation adjustment for the year

Payable-emissions model
-----------------------
The EU reduces the obligation to reflect free allocation an equivalent EU
installation still receives. With a route benchmark B (tCO2e/t) and CBAM factor
f for the year:

    payable_per_t = max(SEE - B * (1 - f), 0)

When no verified benchmark is supplied we fall back to the audit's own framing
("CBAM factor 2.5% in 2026 -> ~97.5% of benchmark-covered emissions effectively
not payable"), i.e. treat the whole SEE as benchmark-covered:

    payable_per_t = SEE * f

The fallback is clearly labelled as an approximation in outputs; a user who
knows their EU-ETS product benchmark can pass it to sharpen the estimate.

Article 9 carbon-price deduction is applied to the price (net_price), never to
the SEE.
"""

from emission_factors import (
    CBAM_FACTOR_SCHEDULE, CBAM_FACTOR_SOURCE, CBAM_DE_MINIMIS_T,
    INDIA_CARBON_PRICE,
)

_MIN_YEAR = min(CBAM_FACTOR_SCHEDULE)
_MAX_YEAR = max(CBAM_FACTOR_SCHEDULE)


def cbam_factor(year: int) -> float:
    """Payable share of embedded emissions for a reporting year (0..1).

    Before the definitive period (pre-2026) there is no financial obligation -> 0.
    After the schedule ends (post-2034) the factor is fully phased in -> 1.0.
    """
    y = int(year)
    if y < _MIN_YEAR:
        return 0.0
    if y > _MAX_YEAR:
        return 1.0
    return CBAM_FACTOR_SCHEDULE[y]


def payable_see(see: float, year: int, benchmark: float | None = None) -> float:
    """Payable emissions per tonne after the free-allocation adjustment.

    With a benchmark: max(SEE - benchmark * (1 - factor), 0).
    Without one: SEE * factor  (whole-SEE-benchmark-covered approximation).
    """
    f = cbam_factor(year)
    if benchmark is not None and benchmark > 0:
        return max(see - benchmark * (1.0 - f), 0.0)
    return see * f


def net_certificate_price(price: float,
                          india_deduction: float | None = None) -> float:
    """Certificate price after the Article 9 carbon-price deduction (>= 0)."""
    ded = INDIA_CARBON_PRICE.value if india_deduction is None else india_deduction
    return max(float(price) - float(ded), 0.0)


def is_below_de_minimis(annual_volume_t: float,
                        is_hydrogen: bool = False) -> bool:
    """True if the annual import volume is under the 50 t/yr de minimis.

    Hydrogen (and electricity) are excluded from the de minimis, so it never
    applies to them.
    """
    if is_hydrogen:
        return False
    return float(annual_volume_t) < CBAM_DE_MINIMIS_T


def cost_breakdown(
    *,
    see: float,
    year: int,
    price: float,
    volume_t: float,
    benchmark: float | None = None,
    india_deduction: float | None = None,
    is_hydrogen: bool = False,
) -> dict:
    """Full indicative cost breakdown (gross vs net-of-free-allocation).

    All monetary figures use the net (post-Article-9) certificate price. The SEE
    is never adjusted by price. Returns a plain dict for JSON/PDF payloads.
    """
    f = cbam_factor(year)
    net_price = net_certificate_price(price, india_deduction)
    pay_see = payable_see(see, year, benchmark)

    gross_per_t = see * net_price
    net_per_t = pay_see * net_price

    return {
        "reporting_year": int(year),
        "cbam_factor": f,
        "cbam_factor_source": CBAM_FACTOR_SOURCE,
        "benchmark_tco2e_per_t": benchmark,
        "benchmark_basis": (
            "user-supplied EU-ETS product benchmark"
            if benchmark else
            "approximation: whole SEE treated as benchmark-covered (payable = SEE x factor)"
        ),
        "certificate_price_eur": float(price),
        "india_carbon_deduction_eur": (
            INDIA_CARBON_PRICE.value if india_deduction is None else float(india_deduction)
        ),
        "net_price_eur": net_price,
        "export_volume_t": float(volume_t),
        "see_tco2e_per_t": float(see),
        "payable_see_tco2e_per_t": round(pay_see, 4),
        # Gross = no free-allocation adjustment (phase-out endpoint / upper bound).
        "gross_cost_per_t_eur": round(gross_per_t, 2),
        "gross_annual_cost_eur": round(gross_per_t * float(volume_t), 2),
        # Net = after the year's free-allocation adjustment (the realistic figure).
        "net_cost_per_t_eur": round(net_per_t, 2),
        "net_annual_cost_eur": round(net_per_t * float(volume_t), 2),
        "de_minimis_t": CBAM_DE_MINIMIS_T,
        "below_de_minimis": is_below_de_minimis(volume_t, is_hydrogen),
        "note": "Indicative only. The CBAM certificate is surrendered by the EU "
                "importer. Gross ignores free allocation (upper bound); net applies "
                "the IR (EU) 2025/2620 CBAM factor for the year. Certificate price is "
                "user-entered and volatile; never embedded in your SEE.",
    }


def phase_in_curve(see: float, net_price: float, volume_t: float,
                   benchmark: float | None = None) -> list[dict]:
    """Per-year net annual cost across the whole 2026-2034 phase-in."""
    rows = []
    for y in sorted(CBAM_FACTOR_SCHEDULE):
        pay = payable_see(see, y, benchmark)
        rows.append({
            "year": y,
            "cbam_factor": CBAM_FACTOR_SCHEDULE[y],
            "payable_see": round(pay, 4),
            "net_cost_per_t_eur": round(pay * net_price, 2),
            "net_annual_cost_eur": round(pay * net_price * volume_t, 2),
        })
    return rows


if __name__ == "__main__":
    # Sanity: 2026 net cost is ~2.5% of gross under the fallback model.
    bd = cost_breakdown(see=2.0, year=2026, price=80.0, volume_t=10000.0)
    print("2026 gross/t:", bd["gross_cost_per_t_eur"],
          "net/t:", bd["net_cost_per_t_eur"], "factor:", bd["cbam_factor"])
    assert bd["cbam_factor"] == 0.025
    assert bd["net_cost_per_t_eur"] == round(2.0 * 0.025 * 80.0, 2)
    assert bd["gross_cost_per_t_eur"] == round(2.0 * 80.0, 2)
    # 2034 is fully phased in: net == gross under the fallback model.
    bd34 = cost_breakdown(see=2.0, year=2034, price=80.0, volume_t=10000.0)
    assert bd34["cbam_factor"] == 1.0
    assert bd34["net_cost_per_t_eur"] == bd34["gross_cost_per_t_eur"]
    # Benchmark model: SEE below benchmark in 2026 -> ~0 payable.
    assert payable_see(1.0, 2026, benchmark=1.5) == max(1.0 - 1.5 * 0.975, 0.0)
    # De minimis.
    assert is_below_de_minimis(49.0) and not is_below_de_minimis(50.0)
    assert not is_below_de_minimis(10.0, is_hydrogen=True)
    print("cost_engine self-checks passed.")
