"""A small Excel (.xlsx) writer using only the standard library.

An .xlsx file is a zip of XML parts. This writes text and numbers with named cell styles
(fonts, fills, borders, alignment), merged cells, row heights, hidden gridlines, frozen
header rows and Excel tables in the blue "Table Style Medium 2" with banded rows: the
presentation of Fjordvik's data dictionary. Every zip entry carries a fixed date, so the
same content always gives the same bytes and a test can compare a fresh build with the
committed workbook byte for byte.
"""

import re
import zipfile
from xml.sax.saxutils import escape

FIXED = (1980, 1, 1, 0, 0, 0)
BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# Named styles: (font size, bold, font colour, fill colour, horizontal, vertical, wrap, indent, thin border)
STYLES = {
    "default": (11, False, None, None, None, None, False, 0, False),
    "head": (10, True, "FFFFFFFF", None, None, "center", True, 0, True),
    "cell": (9.5, False, None, None, None, "top", False, 0, True),
    "cell_wrap": (9.5, False, None, None, None, "top", True, 0, True),
    "cell_first": (9.5, True, None, None, None, "top", False, 0, True),
    "title": (20, True, "FFFFFFFF", "FF1F4E78", "left", "center", False, 0, False),
    "subtitle": (11, False, "FF1F4E78", "FFDDEBF7", "left", "center", False, 0, False),
}
# Read-me sections: (dark colour, light colour)
SECTIONS = {"green": ("FF548235", "FFE2EFDA"), "blue": ("FF2E75B6", "FFDDEBF7"), "orange": ("FFC55A11", "FFFCE4D6")}
for _name, (_dark, _light) in SECTIONS.items():
    STYLES[f"{_name}_section"] = (13, True, "FFFFFFFF", _dark, "left", "center", False, 0, False)
    STYLES[f"{_name}_number"] = (14, True, "FFFFFFFF", _dark, "center", "center", False, 0, False)
    STYLES[f"{_name}_item"] = (11, True, None, _light, "left", "center", False, 1, False)
    STYLES[f"{_name}_text"] = (10.5, False, None, _light, "left", "top", True, 1, False)
# The synthetic-data notice row above a sheet's table
STYLES["notice"] = (10, True, "FF1F4E78", "FFDDEBF7", "left", "center", False, 0, False)
ORDER = list(STYLES)


def _col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _styles_xml():
    fonts, fills, xfs = [], ["<fill><patternFill patternType=\"none\"/></fill>", "<fill><patternFill patternType=\"gray125\"/></fill>"], []
    for name in ORDER:
        size, bold, colour, fill, h, v, wrap, indent, border = STYLES[name]
        font = f"<font>{'<b/>' if bold else ''}<sz val=\"{size}\"/>{f'<color rgb=\"{colour}\"/>' if colour else ''}<name val=\"Calibri\"/><family val=\"2\"/></font>"
        if font not in fonts:
            fonts.append(font)
        fill_id = 0
        if fill:
            f = f"<fill><patternFill patternType=\"solid\"><fgColor rgb=\"{fill}\"/><bgColor indexed=\"64\"/></patternFill></fill>"
            if f not in fills:
                fills.append(f)
            fill_id = fills.index(f)
        align = "".join(f' {k}="{val}"' for k, val in (("horizontal", h), ("vertical", v), ("wrapText", "1" if wrap else None),
                                                       ("indent", indent or None)) if val)
        xfs.append(f'<xf numFmtId="0" fontId="{fonts.index(font)}" fillId="{fill_id}" borderId="{1 if border else 0}" xfId="0" '
                   f'applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment{align}/></xf>')
    thin = '<border><left style="thin"><color auto="1"/></left><right style="thin"><color auto="1"/></right><top style="thin"><color auto="1"/></top><bottom style="thin"><color auto="1"/></bottom><diagonal/></border>'
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<styleSheet xmlns="{NS}"><fonts count="{len(fonts)}">{"".join(fonts)}</fonts>'
            f'<fills count="{len(fills)}">{"".join(fills)}</fills>'
            f'<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>{thin}</borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            f'<cellXfs count="{len(xfs)}">{"".join(xfs)}</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            '<dxfs count="0"/><tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/></styleSheet>')


def _cell(ref, value, style):
    s = ORDER.index(style)
    if value is None or value == "":
        return f'<c r="{ref}" s="{s}"/>' if s else ""
    if isinstance(value, bool):
        value = "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return f'<c r="{ref}" s="{s}"><v>{repr(float(value)) if isinstance(value, float) else value}</v></c>'
    text = escape(BAD.sub("", str(value)))
    return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _top(sh):
    """1 when the sheet has a notice row above its rows, else 0."""
    return 1 if sh.get("notice") and sh.get("notice_row") else 0


def _sheet(sh, table_rid):
    rows, widths = sh["rows"], sh.get("widths") or []
    styles, heights, merges = sh.get("styles") or {}, sh.get("heights") or {}, sh.get("merges") or []
    freeze, zoom, notice, top = sh.get("freeze"), sh.get("zoom"), sh.get("notice"), _top(sh)
    view = f'<sheetView showGridLines="0"{f" zoomScale=\"{zoom}\" zoomScaleNormal=\"{zoom}\"" if zoom else ""} workbookViewId="0">'
    if freeze:
        col = re.match(r"[A-Z]+", freeze).group(0)
        row = int(freeze[len(col):]) + top
        freeze = f"{col}{row}"
        xs, ys = len(col) and (ord(col) - 64) - 1, row - 1
        attrs = (f' xSplit="{xs}"' if xs else "") + (f' ySplit="{ys}"' if ys else "")
        pane = "bottomRight" if xs and ys else ("bottomLeft" if ys else "topRight")
        view += f'<pane{attrs} topLeftCell="{freeze}" activePane="{pane}" state="frozen"/><selection pane="{pane}"/>'
    view += "</sheetView>"
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           f'<worksheet xmlns="{NS}" xmlns:r="{REL}">',
           f"<sheetViews>{view}</sheetViews>", '<sheetFormatPr defaultRowHeight="15"/>']
    if widths:
        out.append("<cols>" + "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths, 1)) + "</cols>")
    out.append("<sheetData>")
    if top:  # the notice row, styled across the sheet's width; everything else moves down one row
        width = max(len(r) for r in rows)
        cells = "".join(_cell(f"{_col(c)}1", notice if c == 1 else "", "notice") for c in range(1, width + 1))
        out.append(f'<row r="1" ht="20" customHeight="1">{cells}</row>')
    for r, row in enumerate(rows, 1):
        cells = "".join(_cell(f"{_col(c)}{r + top}", v, styles.get((r, c), sh["default_style"](r, c)))
                        for c, v in enumerate(row, 1))
        h = heights.get(r)
        out.append(f'<row r="{r + top}"{f" ht=\"{h}\" customHeight=\"1\"" if h else ""}>{cells}</row>')
    out.append("</sheetData>")
    if merges:
        moved = [re.sub(r"\d+", lambda m: str(int(m.group(0)) + top), m) for m in merges]
        out.append(f'<mergeCells count="{len(moved)}">' + "".join(f'<mergeCell ref="{m}"/>' for m in moved) + "</mergeCells>")
    out.append('<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>')
    if notice:  # printed at the top left of every page
        out.append(f"<headerFooter><oddHeader>{escape('&L' + notice.replace('&', '&&'))}</oddHeader></headerFooter>")
    if table_rid:
        out.append(f'<tableParts count="1"><tablePart r:id="{table_rid}"/></tableParts>')
    out.append("</worksheet>")
    return "".join(out)


def _table(tid, name, rows, top=0):
    ref = f"A{1 + top}:{_col(len(rows[0]))}{len(rows) + top}"
    cols = "".join(f'<tableColumn id="{i}" name="{escape(str(h))}"/>' for i, h in enumerate(rows[0], 1))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<table xmlns="{NS}" id="{tid}" name="{name}" displayName="{name}" ref="{ref}" totalsRowShown="0">'
            f'<autoFilter ref="{ref}"/><tableColumns count="{len(rows[0])}">{cols}</tableColumns>'
            '<tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/></table>')


def write(path, sheets):
    """sheets: list of dicts with name, rows and default_style(row, col), and optionally widths,
    styles {(row, col): name}, heights {row: points}, merges, freeze, zoom, table (a name) and
    notice (text printed as the page header). With notice_row, the notice also sits in row 1
    above the rows, and every row number given (styles, heights, merges, freeze, the table)
    counts from the row below it."""
    names = [s["name"] for s in sheets]
    assert len(set(names)) == len(names) and all(len(n) <= 31 and not set(n) & set('[]:*?/\\') for n in names), names
    tables = [s["table"] for s in sheets if s.get("table")]
    assert len(set(tables)) == len(tables) and all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t) for t in tables), tables
    parts, overrides, tid = {}, [], 0
    for i, sh in enumerate(sheets, 1):
        rid = None
        if sh.get("table"):
            headers = [str(h) for h in sh["rows"][0]]
            assert len({h.lower() for h in headers}) == len(headers) and all(headers), (sh["name"], headers)
            tid += 1
            rid = "rId1"
            parts[f"xl/tables/table{tid}.xml"] = _table(tid, sh["table"], sh["rows"], _top(sh))
            parts[f"xl/worksheets/_rels/sheet{i}.xml.rels"] = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rId1" Type="{REL}/table" Target="../tables/table{tid}.xml"/></Relationships>')
            overrides.append(f'<Override PartName="/xl/tables/table{tid}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>')
        parts[f"xl/worksheets/sheet{i}.xml"] = _sheet(sh, rid)
    head = {
        "[Content_Types].xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                                '<Default Extension="xml" ContentType="application/xml"/>'
                                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                                '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                                + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                                          for i in range(1, len(sheets) + 1)) + "".join(overrides) + "</Types>"),
        "_rels/.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                        f'<Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>'),
        "xl/workbook.xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                            f'<workbook xmlns="{NS}" xmlns:r="{REL}"><bookViews><workbookView activeTab="0"/></bookViews><sheets>'
                            + "".join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, 1))
                            + "</sheets></workbook>"),
        "xl/_rels/workbook.xml.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                       '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                                       + "".join(f'<Relationship Id="rId{i}" Type="{REL}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                                                 for i in range(1, len(sheets) + 1))
                                       + f'<Relationship Id="rId{len(sheets) + 1}" Type="{REL}/styles" Target="styles.xml"/></Relationships>'),
        "xl/styles.xml": _styles_xml(),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in {**head, **parts}.items():
            info = zipfile.ZipInfo(name, date_time=FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            z.writestr(info, text.encode("utf-8"))


def read(path):
    """The cell values of a workbook this module wrote: {sheet name: list of rows}."""
    out = {}
    with zipfile.ZipFile(path) as z:
        wb = z.read("xl/workbook.xml").decode("utf-8")
        names = re.findall(r'<sheet name="([^"]+)"', wb)
        for i, n in enumerate(names, 1):
            xml = z.read(f"xl/worksheets/sheet{i}.xml").decode("utf-8")
            rows = []
            for row in re.findall(r"<row [^>]*>(.*?)</row>", xml):
                vals = []
                for body in re.findall(r'<c r="[A-Z]+\d+"[^>]*?(?:/>|>(.*?)</c>)', row):
                    t = re.search(r"<t[^>]*>(.*?)</t>", body or "", re.S)
                    v = re.search(r"<v>(.*?)</v>", body or "")
                    vals.append(t.group(1) if t else (v.group(1) if v else ""))
                rows.append(vals)
            out[n.replace("&amp;", "&")] = rows
    return out
