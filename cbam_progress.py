"""Save / resume — encode the calculator state into a downloadable token.

No accounts, no database — nothing is stored on our servers. The whole state is
base64-encoded JSON the user downloads and re-uploads later; it lives only in the
active session and in that file. Only persistent plain keys are saved; transient
widget keys (w_*, fuel_*_*) are cleared on load so they re-seed from restored values.
"""

import base64
import json
from datetime import datetime, timezone

SCHEMA = "ecosetu-cbam-progress/v1"

# Persistent plain keys that fully describe the calculator state.
SAVE_KEYS = [
    "company_name", "facility_name", "state_ut", "pin_code",
    "sector", "route", "cbam_default_id", "cn_code",
    "reporting_year", "annual_production_t",
    "input_basis", "fuels", "_fuel_seq",
    "electricity_value", "grid_ef_choice", "grid_ef_custom", "grid_ef_source",
    "biomass_sustainability_attested",
    "steel_process_override", "clinker_fraction",
    "al_smelter_tech", "al_anode", "al_cf4", "al_c2f6", "fert_n2o",
    "gwp_set", "cert_price", "export_vol", "cbam_benchmark",
]

# Prefixes of transient widget keys to drop on load (they re-seed from SAVE_KEYS).
_WIDGET_PREFIXES = ("w_", "fuel_sel_", "fuel_qty_", "fuel_ncv_", "fuel_ef_")


def dump_progress(ss) -> str:
    state = {k: ss[k] for k in SAVE_KEYS if k in ss}
    envelope = {
        "schema": SCHEMA,
        "saved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "state": state,
    }
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def load_progress(token: str, ss) -> tuple[bool, str]:
    """Decode a progress token into session_state. Returns (ok, message)."""
    try:
        raw = base64.b64decode(token.strip().encode("ascii"), validate=True)
        envelope = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        return False, f"Could not read this file — it may be corrupted ({exc})."

    if not isinstance(envelope, dict) or envelope.get("schema") != SCHEMA:
        return False, "This is not an Ecosetu CBAM progress file."

    state = envelope.get("state", {})
    for k in SAVE_KEYS:
        if k in state:
            ss[k] = state[k]

    # Clear transient widget keys so they re-seed from the restored values.
    for k in [k for k in ss.keys() if k.startswith(_WIDGET_PREFIXES)]:
        del ss[k]

    return True, envelope.get("saved_utc", "")
