"""Ingest the official CBAM default-value dataset (C-05) — India sheet.

Source: Commission Implementing Reg. (EU) 2025/2621, "Default values for the
transitional... CBAM" workbook (one worksheet per country). We read the *India*
sheet and emit a static, versioned CSV that the runtime loads with the stdlib
`csv` module — so the app never needs pandas at runtime.

The Annex already contains the pre-computed *marked-up* columns (10/20/30% for
cement/aluminium/hydrogen/iron&steel; 1% for fertilisers). We copy those exact
published numbers; we DO NOT recompute a mark-up ourselves.

Sheet layout (India, no header offset — row 1 is the column banner):
    col 0  Product CN Code            (also carries section banners: "Cement", ...)
    col 1  Description
    col 2  Default Value (direct)
    col 3  Default Value (indirect)   (blank for steel/aluminium/hydrogen)
    col 4  Default Value (total = direct + indirect)
    col 5  2026 marked-up total
    col 6  2027 marked-up total
    col 7  2028-and-onwards marked-up total
    col 8  Underlying production route marker, e.g. "(A)"/"(B)"

Rows that are section banners, "see below" parents, or "–"/"_" (no value
published) are skipped. Same-CN variants (e.g. white vs grey clinker under
2523 10 00) are kept as separate rows, each with a stable `id`.

Usage
-----
    python scripts/ingest_cbam_defaults.py \
        --source "/path/to/DVs as adopted_v20260204 .xlsx"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data"
OUT_CSV = OUT_DIR / "india_cbam_defaults.csv"

VINTAGE = "IR (EU) 2025/2621 — DVs as adopted v2026-02-04 (India sheet)"

# Section banner text (col 0) -> tool sector name (cbam_meta.SECTORS keys).
SECTION_MAP = {
    "cement": "Cement",
    "fertilisers": "Fertilisers",
    "aluminium": "Aluminium",
    "hydrogen": "Hydrogen",
    "iron and steel": "Iron & Steel",
}

# Markup percentage applied at each section (for provenance/display only — the
# marked columns are already computed in the source).
SECTION_MARKUP_PCT = {
    "Cement": (10, 20, 30),
    "Aluminium": (10, 20, 30),
    "Hydrogen": (10, 20, 30),
    "Iron & Steel": (10, 20, 30),
    "Fertilisers": (1, 1, 1),
}

CSV_COLUMNS = [
    "id", "section", "cn_display", "cn_norm", "description",
    "direct", "indirect", "total",
    "marked_2026", "marked_2027", "marked_2028",
    "markup_2026_pct", "route_marker",
]

_NO_VALUE = {"", "–", "-", "_", "see below", "nan", "none"}


def _cn_norm(cn_display: str) -> str:
    """Digits-only CN key, e.g. '2523 10 00' -> '25231000'."""
    return re.sub(r"\D", "", cn_display)


def _num(cell) -> float | None:
    if cell is None:
        return None
    s = str(cell).strip().lower()
    if s in _NO_VALUE:
        return None
    try:
        return round(float(str(cell).strip()), 4)
    except ValueError:
        return None


def load_india_rows(source: Path) -> list[dict]:
    try:
        import pandas as pd
    except ImportError:
        sys.exit("pandas is required to ingest the dataset (pip install pandas).")

    if not source.exists():
        sys.exit(
            f"Source file not found: {source}\n"
            "Obtain the official IR (EU) 2025/2621 default-values workbook first — "
            "this script will not fabricate values."
        )
    try:
        df = pd.read_excel(source, sheet_name="India", header=None)
    except ImportError:
        sys.exit("openpyxl is required to read .xlsx (pip install openpyxl).")
    except ValueError:
        sys.exit("No 'India' sheet found in the workbook — check the source file.")

    rows: list[dict] = []
    section: str | None = None
    seq = 0

    for i in range(len(df)):
        c0 = df.iloc[i, 0]
        c0s = str(c0).strip()
        if c0s.lower() in ("nan", ""):
            continue

        # Section banner?
        if c0s.lower() in SECTION_MAP:
            section = SECTION_MAP[c0s.lower()]
            continue
        if section is None:
            continue  # skip the "India" title / column-banner rows

        # Data row candidate: col0 must look like a CN code (contains a digit).
        if not any(ch.isdigit() for ch in c0s):
            continue

        direct = _num(df.iloc[i, 2])
        indirect = _num(df.iloc[i, 3])
        total = _num(df.iloc[i, 4])
        m2026 = _num(df.iloc[i, 5])
        m2027 = _num(df.iloc[i, 6])
        m2028 = _num(df.iloc[i, 7])

        # Skip "see below" parents and "–"/"_" no-value rows (no total published).
        if total is None:
            continue

        desc = str(df.iloc[i, 1]).strip()
        route_marker = str(df.iloc[i, 8]).strip()
        if route_marker.lower() in ("nan", "\xa0"):
            route_marker = ""

        cn_display = c0s
        cn_norm = _cn_norm(cn_display)
        seq += 1
        pct = SECTION_MARKUP_PCT[section][0]
        rows.append({
            "id": f"{cn_norm}-{seq}",
            "section": section,
            "cn_display": cn_display,
            "cn_norm": cn_norm,
            "description": desc,
            "direct": direct if direct is not None else "",
            "indirect": indirect if indirect is not None else "",
            "total": total,
            "marked_2026": m2026 if m2026 is not None else "",
            "marked_2027": m2027 if m2027 is not None else "",
            "marked_2028": m2028 if m2028 is not None else "",
            "markup_2026_pct": pct,
            "route_marker": route_marker,
        })

    return rows


def _validate(rows: list[dict]) -> None:
    if not rows:
        sys.exit("No India data rows parsed — aborting (would ship an empty dataset).")
    # total must equal direct + indirect (indirect may be blank -> treated as 0).
    violations = 0
    for r in rows:
        d = r["direct"] if r["direct"] != "" else 0.0
        ind = r["indirect"] if r["indirect"] != "" else 0.0
        if abs(float(d) + float(ind) - float(r["total"])) > 0.011:
            violations += 1
            if violations <= 5:
                print(f"  WARN total!=direct+indirect: {r['cn_display']} {r['description']!r} "
                      f"{d}+{ind} != {r['total']}")
    if violations:
        print(f"WARNING: {violations} row(s) where total != direct+indirect (>0.011).")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest(source: Path) -> None:
    rows = load_india_rows(source)
    _validate(rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        fh.write(f"# {VINTAGE}\n")
        fh.write(f"# source: {source.name}\n")
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    checksum = _sha256(OUT_CSV)
    (OUT_CSV.parent / (OUT_CSV.name + ".sha256")).write_text(checksum + "\n")

    by_section: dict[str, int] = {}
    for r in rows:
        by_section[r["section"]] = by_section.get(r["section"], 0) + 1

    print(f"Wrote {len(rows)} rows -> {OUT_CSV.relative_to(REPO_ROOT)}")
    for s, n in by_section.items():
        print(f"  {s:14s} {n}")
    print(f"SHA-256: {checksum}")
    print("\nSpot-check a few India rows against the EUR-Lex PDF Annex before shipping.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest official CBAM India default values (C-05).")
    ap.add_argument("--source", required=True, type=Path,
                    help="Path to the official IR (EU) 2025/2621 default-values XLSX.")
    args = ap.parse_args()
    ingest(args.source)


if __name__ == "__main__":
    main()
