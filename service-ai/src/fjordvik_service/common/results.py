"""The results writer: stamped tables, a summary, a results note and a manifest of checksums."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .checks import check_frame
from .stamps import STAMP_FIELDS, sha256_file, sha256_json


def tidy(df):
    """Months as YYYY-MM and dates as YYYY-MM-DD, for stable CSV files."""
    out = df.copy()
    for col in out.columns:
        if isinstance(out[col].dtype, pd.PeriodDtype):
            out[col] = out[col].astype(str)
        elif pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
    return out


def stamp_id(stamps):
    """A short name for a stamp, so row-level files need not repeat four long columns."""
    return sha256_json({k: stamps[k] for k in STAMP_FIELDS})[:12]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=_json) + "\n", encoding="utf-8", newline="\n")


def write_results(out_dir, tables, summary, stamps, readme, environment, *, row_level=(), extra_json=None):
    """Write each table with the stamp columns, the summary, the note and a manifest of checksums.

    Tables named in `row_level` carry one short `stamp_id` column instead of the four stamp
    columns; the manifest resolves it. `extra_json` maps file names to further JSON values.
    Every file is written with Unix line endings, the bytes git keeps for results/ and eval/
    (service-ai/.gitattributes), so its checksum holds in any checkout.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    sid = stamp_id(stamps)
    for name, table in tables.items():
        if name in row_level:
            stamped = tidy(table).assign(stamp_id=sid)
            check_frame(stamped, f"write {name}", [], required=["stamp_id"])
        else:
            stamped = tidy(table).assign(**{k: stamps[k] for k in STAMP_FIELDS})
            check_frame(stamped, f"write {name}", [], required=STAMP_FIELDS)
        target = out_dir / f"{name}.csv"
        stamped.to_csv(target, index=False, lineterminator="\n")
        files[target.name] = {"rows": len(stamped)}
    for fname, value in {"summary.json": summary, **(extra_json or {})}.items():
        write_json(out_dir / fname, value)
        files[fname] = {}
    note_target = out_dir / "README.md"
    note_target.write_text(readme, encoding="utf-8", newline="\n")
    files[note_target.name] = {}
    for fname in files:
        files[fname]["sha256"] = sha256_file(out_dir / fname)
    manifest = {**stamps, "environment": environment, "files": files}
    if row_level:
        manifest["stamp_ids"] = {sid: {k: stamps[k] for k in STAMP_FIELDS}}
    write_json(out_dir / "manifest.json", manifest)
    return manifest


def _json(value):
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.bool_):
        return bool(value)
    return str(value)
