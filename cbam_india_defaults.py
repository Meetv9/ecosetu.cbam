"""Runtime loader for the official CBAM India default values (C-05).

Reads the static CSV produced by `scripts/ingest_cbam_defaults.py` using ONLY
the Python standard library (no pandas at runtime). Each row is one official
default-value entry from IR (EU) 2025/2621 (India sheet), keyed per product row
so same-CN variants (e.g. white vs grey clinker under 2523 10 00) stay distinct.

Public API
----------
    VINTAGE                       provenance string for the dataset
    DEFAULTS                      list[IndiaDefault] in sheet order
    by_id(row_id)                 -> IndiaDefault | None
    defaults_for_section(sec)     -> list[IndiaDefault]
    option_labels(sec)            -> list[(row_id, label)] for a UI dropdown
    IndiaDefault.marked(year)     -> official marked-up total for a CBAM year
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

_DATA = Path(__file__).resolve().parent / "data" / "india_cbam_defaults.csv"


@dataclass(frozen=True)
class IndiaDefault:
    id: str
    section: str
    cn_display: str
    cn_norm: str
    description: str
    direct: float | None
    indirect: float | None
    total: float
    marked_2026: float | None
    marked_2027: float | None
    marked_2028: float | None
    markup_2026_pct: int
    route_marker: str

    @property
    def label(self) -> str:
        return f"{self.cn_display} — {self.description}"

    def marked(self, year: int) -> float:
        """Official marked-up total for a CBAM compliance year.

        The Annex publishes marked-up defaults for 2026, 2027 and 2028-onwards.
        Falls back to the plain total if a marked column is blank or the year is
        before the definitive period (2026)."""
        if year <= 2025:
            return self.total
        if year == 2026:
            val = self.marked_2026
        elif year == 2027:
            val = self.marked_2027
        else:
            val = self.marked_2028
        return val if val is not None else self.total


def _f(s: str) -> float | None:
    s = (s or "").strip()
    if s == "":
        return None
    return float(s)


def _load() -> list[IndiaDefault]:
    if not _DATA.exists():
        raise FileNotFoundError(
            f"CBAM India default-values CSV not found: {_DATA}\n"
            "Generate it with: python scripts/ingest_cbam_defaults.py --source <official.xlsx>"
        )
    rows: list[IndiaDefault] = []
    with _DATA.open(newline="", encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    reader = csv.DictReader(lines)
    for r in reader:
        rows.append(IndiaDefault(
            id=r["id"],
            section=r["section"],
            cn_display=r["cn_display"],
            cn_norm=r["cn_norm"],
            description=r["description"],
            direct=_f(r["direct"]),
            indirect=_f(r["indirect"]),
            total=float(r["total"]),
            marked_2026=_f(r["marked_2026"]),
            marked_2027=_f(r["marked_2027"]),
            marked_2028=_f(r["marked_2028"]),
            markup_2026_pct=int(r["markup_2026_pct"]),
            route_marker=r["route_marker"],
        ))
    return rows


VINTAGE = "Official EU CBAM default values — IR (EU) 2025/2621 (India), adopted 2026-02-04"

DEFAULTS: list[IndiaDefault] = _load()
_BY_ID: dict[str, IndiaDefault] = {d.id: d for d in DEFAULTS}


def by_id(row_id: str) -> IndiaDefault | None:
    return _BY_ID.get(row_id)


def defaults_for_section(section: str) -> list[IndiaDefault]:
    return [d for d in DEFAULTS if d.section == section]


def option_labels(section: str) -> list[tuple[str, str]]:
    return [(d.id, d.label) for d in defaults_for_section(section)]


if __name__ == "__main__":  # simple self-test / summary
    from collections import Counter
    c = Counter(d.section for d in DEFAULTS)
    print(f"{len(DEFAULTS)} India defaults loaded:", dict(c))
    h = [d for d in DEFAULTS if d.section == "Hydrogen"][0]
    assert h.total == 14.03, h.total
    assert h.marked(2026) == 15.433, h.marked(2026)
    grey = [d for d in DEFAULTS if d.description == "Grey clinker"][0]
    assert grey.total == 1.44 and grey.marked(2026) == 1.584, grey
    nitric = [d for d in DEFAULTS if d.cn_norm == "28080000"][0]
    assert nitric.total == 2.01, nitric.total
    print("self-test OK")
