"""Write docs/data-dictionary.md from the model's TMDL files.

The dictionary is generated, never edited by hand, so it can't drift from the
model. tests/test_docs.py fails if the committed copy is out of date.

Run:  python scripts/build_data_dictionary.py
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODEL = REPO / "FjordvikEmissions.SemanticModel" / "definition"
OUT = REPO / "docs" / "data-dictionary.md"


def read_table(path):
    lines = path.read_text(encoding="utf-8").split("\n")
    info = {"description": "", "columns": [], "measures": []}
    pending = ""
    obj = None
    for line in lines:
        if line.startswith("///"):
            info["description"] = line[3:].strip()
        elif line.startswith("table "):
            info["name"] = line.split(" ", 1)[1].strip()
        elif line.startswith("\t///"):
            pending = line[4:].strip()
        elif line.startswith("\tcolumn "):
            obj = {"name": line.split(" ", 1)[1].strip().strip("'"), "description": pending,
                   "hidden": False, "dataType": "", "formatString": ""}
            info["columns"].append(obj)
            pending = ""
        elif line.startswith("\tmeasure "):
            m = re.match(r"\tmeasure '(.+?)' =(.*)$", line)
            obj = {"name": m.group(1), "description": pending, "dax": m.group(2).strip(),
                   "formatString": "", "displayFolder": ""}
            info["measures"].append(obj)
            pending = ""
        elif obj is not None and "dax" in obj and line.startswith("\t\t\t"):
            obj["dax"] += "\n" + line[3:]
        elif obj is not None and line.startswith("\t\t") and ":" in line:
            key, value = line.strip().split(":", 1)
            if key in obj:
                obj[key] = value.strip()
        elif obj is not None and line.strip() == "isHidden" and "hidden" in obj:
            obj["hidden"] = True
        elif line.startswith("\t") and not line.startswith("\t\t"):
            obj = None
    return info


def main():
    tables = {p.stem: read_table(p) for p in sorted((MODEL / "tables").glob("*.tmdl"))}
    out = ["# Data dictionary", "",
           "Generated from the model by `scripts/build_data_dictionary.py`. Do not edit by hand.",
           "Emission factors in this model are illustrative, not for real reporting.", ""]

    measures = tables.pop("_Measures")["measures"]
    out += ["## Measures", "",
            "Every measure lives in the `_Measures` table, grouped by display folder.", ""]
    for folder in dict.fromkeys(m["displayFolder"] for m in measures):
        out += [f"### {folder}", ""]
        for m in (m for m in measures if m["displayFolder"] == folder):
            out += [f"**{m['name']}**: {m['description']} Format: `{m['formatString']}`.", "",
                    "```dax", m["dax"].strip(), "```", ""]

    out += ["## Tables", ""]
    for t in tables.values():
        out += [f"### {t['name']}", "", t["description"], "",
                "| Column | Type | Format | Hidden | Description |", "| --- | --- | --- | --- | --- |"]
        for c in t["columns"]:
            out.append(f"| {c['name']} | {c['dataType']} | {c['formatString']} | "
                       f"{'yes' if c['hidden'] else ''} | {c['description']} |")
        out.append("")

    out += ["## Relationships", "", "All many-to-one, filtering from the dimension to the fact.", "",
            "| From (many) | To (one) |", "| --- | --- |"]
    rel = (MODEL / "relationships.tmdl").read_text(encoding="utf-8")
    for frm, to in re.findall(r"fromColumn: (\S+)\n\ttoColumn: (\S+)", rel):
        out.append(f"| {frm} | {to} |")
    out.append("")

    out += ["## Row-level security roles", "", "| Role | Filter |", "| --- | --- |"]
    for path in sorted((MODEL / "roles").glob("*.tmdl")):
        f = re.search(r"tablePermission (.+)", path.read_text(encoding="utf-8")).group(1)
        out.append(f"| {path.stem} | `{f}` |")
    out.append("")

    OUT.write_bytes(("\n".join(out)).encode("utf-8"))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
