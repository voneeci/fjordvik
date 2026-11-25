"""Build docs/architecture-drawings.html from the Mermaid drawings in the architecture docs.

The page is published on GitHub Pages from main. It is generated, never edited by hand:
data/tests/test_drawings_page.py fails if it differs from a fresh build.

    python docs/site/drawings/build.py            # write the page
    python docs/site/drawings/build.py --check    # exit 1 if the page is out of date

Standard library only. The output depends only on the docs and the template (no build
date or commit), so a fresh build matches the committed page byte for byte.
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = Path(__file__).resolve().with_name("template.html")
OUT = ROOT / "docs" / "architecture-drawings.html"
GITHUB = "https://github.com/voneeci/fjordvik/blob/main/"

DOCS = [
    ("docs/architecture.md", "Solution architecture",
     "C4 levels 1 to 3: who uses the platform, its containers, and the service AI pipeline."),
    ("docs/data-model.md", "Data model",
     "The business things the data describes, where each table's data comes from and who owns it, "
     "and the tables in three subject areas."),
    ("docs/requirements.md", "Requirements", "Who supplies the data and who uses the results."),
    ("docs/threat-model.md", "Threat model", "Where data or control changes hands, boundary by boundary."),
]
LEGEND_TITLE = 'title: "How status is shown'
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def github_link(target, doc_path):
    """A relative Markdown link in a doc, as a link to the file on GitHub."""
    if target.startswith(("http://", "https://", "#")):
        return target
    path, _, anchor = target.partition("#")
    parts = []
    for p in (Path(doc_path).parent / path).as_posix().split("/"):
        if p == "..":
            parts.pop()
        elif p not in ("", "."):
            parts.append(p)
    return GITHUB + "/".join(parts) + (f"#{anchor}" if anchor else "")


def inline(s, doc_path):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: f'<a href="{html.escape(github_link(m.group(2), doc_path))}">{m.group(1)}</a>', s)


def table(rows, doc_path, cls="key wide"):
    head = "".join(f"<th scope='col'>{inline(c, doc_path)}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{inline(c, doc_path)}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f"<div class='tablewrap'><table class='{cls}'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def read_table(lines, i):
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if not set("".join(cells)) <= set("-: "):
            rows.append(cells)
        i += 1
    return rows, i


def markdown(md, doc_path):
    """Enough Markdown for the concepts section: headings, paragraphs, tables, lists, the legend."""
    out, lines, i = [], md.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("### "):
            out.append(f"<h3>{inline(line[4:], doc_path)}</h3>")
            i += 1
        elif line.strip() == "```mermaid":
            j = i + 1
            while lines[j].strip() != "```":
                j += 1
            code = "\n".join(lines[i + 1:j])
            out.append(f'<div class="sheet legend"><pre class="mermaid">{html.escape(code)}</pre></div>')
            i = j + 1
        elif line.startswith("|"):
            rows, i = read_table(lines, i)
            out.append(table(rows, doc_path, "key wide concept"))
        elif line.startswith("- "):
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("  ")):
                if lines[i].startswith("- "):
                    items.append(lines[i][2:].strip())
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x, doc_path)}</li>" for x in items) + "</ul>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("|", "### ", "- ", "```")):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(para), doc_path)}</p>")
    return "\n".join(out)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def latest_update(texts):
    """The latest "Last updated: D Month YYYY" date across the docs."""
    found = []
    for text in texts:
        for d, m, y in re.findall(r"Last updated: (\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})", text):
            found.append((int(y), MONTHS.index(m), int(d)))
    if not found:
        return "not recorded"
    y, m, d = max(found)
    return f"{d} {MONTHS[m]} {y}"


def drawings(path, lines):
    """Each Mermaid drawing in a doc, with its key table and the notes under it."""
    heading, i, out = None, 0, []
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^#{2,3}\s+(.*)", line)
        if m:
            heading = m.group(1).replace("`", "")
        if line.strip() != "```mermaid":
            i += 1
            continue
        start = j = i + 1
        while lines[j].strip() != "```":
            j += 1
        code = "\n".join(lines[start:j])
        i = j + 1
        if LEGEND_TITLE in code:  # the legend belongs to the concepts section
            continue
        t = re.search(r'title:\s*"([^"]+)"', code)
        title = t.group(1) if t else heading
        k = i
        while k < len(lines) and not lines[k].strip():
            k += 1
        tables = ""
        while k < len(lines) and lines[k].startswith("|"):
            rows, k = read_table(lines, k)
            if rows and rows[0][0] == "Key":
                body = "".join(f"<tr><th scope='row'>{inline(r[0], path)}</th><td>{inline(r[1], path)}</td></tr>"
                               for r in rows[1:])
                tables += f"<details class='keybox'><summary>Key</summary><table class='key'>{body}</table></details>"
            else:
                tables += table(rows, path)
            while k < len(lines) and not lines[k].strip():
                k += 1
        paras, cur = [], []
        while k < len(lines) and not lines[k].startswith(("#", "|", "```", "<")) and len(paras) < 2:
            if lines[k].strip():
                cur.append(lines[k].strip())
            elif cur:
                paras.append(" ".join(cur))
                cur = []
            k += 1
        if cur and len(paras) < 2:
            paras.append(" ".join(cur))
        out.append(dict(title=title, code=code, heading=heading, line=start, tables=tables,
                        notes=[inline(p, path) for p in paras]))
    return out


def build():
    arch = read("docs/architecture.md")
    c0 = arch.index("## Concepts and methods")
    c1 = arch.index("\n## ", c0 + 5)
    concepts = markdown(arch[c0 + len("## Concepts and methods"):c1].strip(), "docs/architecture.md")
    src = f'<a class="path" href="{GITHUB}docs/architecture.md">docs/architecture.md</a>'
    sections = [f"""
    <section class="doc concepts" id="concepts">
      <header class="dochead">
        <h2>Concepts and methods</h2>
        <p>The ideas behind the drawings and how they were made. {src}</p>
      </header>
      <div class="prose">{concepts}</div>
    </section>"""]
    toc = ['<li><a href="#concepts"><span class="tn">i</span>Concepts and methods</a></li>']
    texts, n = [], 0
    for path, name, blurb in DOCS:
        text = read(path)
        texts.append(text)
        figs = []
        for d in drawings(path, text.split("\n")):
            n += 1
            notes = "".join(f'<p class="note">{p}</p>' for p in d["notes"])
            link = f'{GITHUB}{path}?plain=1#L{d["line"]}'  # GitHub jumps to a line only in plain view
            figs.append(f"""
      <figure class="fig" id="d{n}">
        <figcaption>
          <span class="num">Drawing {n}</span>
          <h3>{html.escape(d["title"])}</h3>
          <p class="src"><a href="{link}">{html.escape(path)}, line {d["line"]}</a>, under "{html.escape(d["heading"] or name)}"</p>
        </figcaption>
        <div class="sheet"><pre class="mermaid">{html.escape(d["code"])}</pre></div>
        {d["tables"]}
        {notes}
      </figure>""")
            toc.append(f'<li><a href="#d{n}"><span class="tn">{n}</span>{html.escape(d["title"])}</a></li>')
        sections.append(f"""
    <section class="doc">
      <header class="dochead">
        <h2>{html.escape(name)}</h2>
        <p>{html.escape(blurb)} <a class="path" href="{GITHUB}{path}">{html.escape(path)}</a></p>
      </header>
      {''.join(figs)}
    </section>""")
    page = TEMPLATE.read_text(encoding="utf-8")
    return (page.replace("{{COUNT}}", str(n)).replace("{{UPDATED}}", latest_update(texts))
            .replace("{{TOC}}", "\n".join(toc)).replace("{{SECTIONS}}", "\n".join(sections)))


def main(argv):
    page = build()
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != page:
            print(f"{OUT.relative_to(ROOT).as_posix()} is out of date: run python docs/site/drawings/build.py")
            return 1
        print("drawings page is up to date")
        return 0
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}: {page.count('class=\"fig\"')} drawings")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
