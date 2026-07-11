"""Sector / production-route metadata for the CBAM UI.

Maps each user-facing sector + route to the engine's process-route key and
records whether indirect (electricity) emissions count toward CBAM SEE for that
sector. Official per-CN default values live in `cbam_india_defaults` (ingested
from the EU Annex); this module no longer carries illustrative CN codes or a
route-level default proxy — the user selects the exact official default row.
"""

SECTORS = {
    "Iron & Steel": {
        "routes": {
            "BF-BOF": "steel_bf_bof",
            "Coal-DRI + EAF": "steel_dri",
            "Gas-DRI + EAF": "steel_dri",
            "Scrap EAF": "steel_scrap_eaf",
            "Other": "steel_bf_bof",
        },
        "indirect": False,
        "functional_unit": "tonne of steel product",
    },
    "Aluminium": {
        "routes": {
            "Primary (Hall-Heroult)": "aluminium_primary",
            "Secondary (scrap melting)": "aluminium_secondary",
            "Downstream processing": "aluminium_downstream",
        },
        "indirect": False,
        "functional_unit": "tonne of aluminium",
    },
    "Cement": {
        "routes": {
            "Wet kiln": "cement",
            "Dry kiln": "cement",
            "Pre-calciner": "cement",
            "Other": "cement",
        },
        "indirect": True,
        "functional_unit": "tonne of cement",
    },
    "Fertilisers": {
        "routes": {
            "Ammonia (SMR)": "fertiliser_ammonia",
            "Ammonia (coal gasification)": "fertiliser_ammonia",
            "Nitric acid": "fertiliser_nitric_acid",
            "Urea": "fertiliser_ammonia",
            "Mixed N": "fertiliser_ammonia",
        },
        "indirect": True,
        "functional_unit": "tonne of product",
    },
    "Hydrogen": {
        # C-10: hydrogen used the fertiliser_ammonia key by accident (both return
        # 0 process emissions). Use a semantically honest `combustion_only` key so
        # payloads read correctly. The SMR feedstock CO2 is captured only if the
        # user enters TOTAL natural gas (feed + fuel) as combusted — the UI must
        # say so (see the Hydrogen explainer in the Fuel & Energy step).
        "routes": {
            "Grey (SMR / coal gasification)": "combustion_only",
            "Other": "combustion_only",
        },
        "indirect": False,
        "functional_unit": "tonne of hydrogen",
    },
}


def sector_names() -> list[str]:
    return list(SECTORS.keys())


def routes_for(sector: str) -> list[str]:
    return list(SECTORS.get(sector, {}).get("routes", {}).keys())


def route_engine_key(sector: str, route: str) -> str:
    return SECTORS.get(sector, {}).get("routes", {}).get(route, "")


def functional_unit(sector: str) -> str:
    return SECTORS.get(sector, {}).get("functional_unit", "tonne of product")
