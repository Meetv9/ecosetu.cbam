"""Golden tests for the official CBAM India default values (C-05) and the
sector/route metadata that drives the SEE engine.

The route-level placeholder defaults and the (sector, route) proxy mapping were
RETIRED. Binding defaults now come from the official EU Annex (IR (EU) 2025/2621,
India sheet), ingested to data/india_cbam_defaults.csv and loaded by
cbam_india_defaults. Each assertion pins an official number or a contract that
flows into a user-facing CBAM default comparison; changing one requires a source
citation in the same commit.

Run:  python -m pytest tests/ -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cbam_meta  # noqa: E402
import cbam_india_defaults as cd  # noqa: E402


# ---------------------------------------------------------------------------
# C-05 — the retired route-based proxy machinery must be gone. A resurrected
# cbam_default_key / is_proxy_default would re-introduce the mis-mappings the
# official per-CN dataset was brought in to fix.
# ---------------------------------------------------------------------------
def test_route_based_default_machinery_removed():
    assert not hasattr(cbam_meta, "cbam_default_key")
    assert not hasattr(cbam_meta, "is_proxy_default")
    assert not hasattr(cbam_meta, "ROUTE_CBAM_DEFAULT")
    assert not hasattr(cbam_meta, "cn_codes_for")


# ---------------------------------------------------------------------------
# Dataset shape — 256 India rows across the five CBAM goods sectors.
# ---------------------------------------------------------------------------
def test_dataset_row_counts_by_section():
    counts = {}
    for d in cd.DEFAULTS:
        counts[d.section] = counts.get(d.section, 0) + 1
    assert counts == {
        "Cement": 5,
        "Fertilisers": 27,
        "Aluminium": 24,
        "Hydrogen": 1,
        "Iron & Steel": 199,
    }
    assert len(cd.DEFAULTS) == 256


# ---------------------------------------------------------------------------
# Pinned official India default values (direct+indirect total) and the Annex's
# pre-computed marked-up columns. These are copied verbatim from the source XLS.
# ---------------------------------------------------------------------------
def test_hydrogen_official_value_and_markup():
    h = cd.by_id([d.id for d in cd.DEFAULTS if d.cn_norm == "28041000"][0])
    assert h.total == 14.03            # tCO2e per TONNE H2 (not per kg)
    assert h.marked(2026) == 15.433    # +10%
    assert h.marked(2027) == 16.836    # +20%
    assert h.marked(2028) == 18.239    # +30%
    assert h.marked(2025) == 14.03     # pre-definitive: base default


def test_steel_hrc_official_value():
    hrc = [d for d in cd.DEFAULTS if d.cn_norm == "7208"][0]
    assert hrc.total == 4.28
    assert hrc.marked(2026) == 4.708


def test_grey_portland_cement_official_value():
    c = [d for d in cd.DEFAULTS if d.cn_norm == "25232900"][0]
    assert c.total == 1.48


# ---------------------------------------------------------------------------
# C-11 — nitric acid is a distinct N2O-driven good. It now has its OWN official
# default (2.01) and must never borrow the ammonia value again.
# ---------------------------------------------------------------------------
def test_nitric_acid_has_its_own_official_default():
    n = [d for d in cd.DEFAULTS if d.cn_norm == "28080000"][0]
    assert n.section == "Fertilisers"
    assert n.total == 2.01
    # Fertiliser mark-up is 1% and flat across all years.
    assert n.marked(2026) == n.marked(2028) == 2.0301


# ---------------------------------------------------------------------------
# Same-CN variants must stay distinct (white vs grey clinker share CN
# 2523 10 00 but carry different values). A CN-only key would collide them.
# ---------------------------------------------------------------------------
def test_same_cn_variants_are_distinct_rows():
    clinker = [d for d in cd.DEFAULTS if d.cn_norm == "25231000"]
    by_desc = {d.description: d.total for d in clinker}
    assert by_desc == {"White clinker": 1.41, "Grey clinker": 1.44}


# ---------------------------------------------------------------------------
# Loader contract — total == direct + indirect (indirect blank -> treated 0),
# and by_id round-trips.
# ---------------------------------------------------------------------------
def test_total_equals_direct_plus_indirect():
    for d in cd.DEFAULTS:
        direct = d.direct or 0.0
        indirect = d.indirect or 0.0
        assert abs(direct + indirect - d.total) <= 0.011, d


def test_by_id_round_trips():
    sample = cd.DEFAULTS[0]
    assert cd.by_id(sample.id) is sample
    assert cd.by_id("no-such-id") is None


def test_option_labels_are_scoped_to_section():
    labels = cd.option_labels("Hydrogen")
    assert len(labels) == 1
    assert labels[0][0] == cd.defaults_for_section("Hydrogen")[0].id


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
