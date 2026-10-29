"""python-docx helpers for the final report: styles, headings, bullets, tables, callouts, figures, fields."""
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Pt, RGBColor

FONT = "Calibri"
NAVY = "1F2A44"
BLUE = "2A78D6"
DARK_BLUE = "0B49CB"
INK = "262626"
SECONDARY = "52514E"
MUTED = "898781"
TINT = "EEF4FD"
ZEBRA = "F4F4F1"
RULE = "C3C2B7"
WHITE = "FFFFFF"


def rgb(hex_color):
    return RGBColor.from_string(hex_color)


def new_document():
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.2)
    section.top_margin, section.bottom_margin = Cm(2.0), Cm(2.0)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = rgb(INK)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12
    for name, size, color, before, after in (("Heading 1", 17, NAVY, 18, 6), ("Heading 2", 13, DARK_BLUE, 12, 4), ("Heading 3", 11, NAVY, 8, 2)):
        st = styles[name]
        st.font.name = FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = rgb(color)
        rpr = st.element.get_or_add_rPr()
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.append(fonts)
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            fonts.set(qn(attr), FONT)
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            fonts.attrib.pop(qn(attr), None)
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.keep_with_next = True
    for name in ("List Bullet", "List Number"):
        st = styles[name]
        st.font.name = FONT
        st.font.size = Pt(10.5)
        st.paragraph_format.space_after = Pt(3)
    return doc


def add_runs(paragraph, runs, size=None, color=None):
    """runs: str or list of (text, {bold, italic, color, size})."""
    if isinstance(runs, str):
        runs = [(runs, {})]
    for text, opts in runs:
        r = paragraph.add_run(text)
        r.bold = opts.get("bold")
        r.italic = opts.get("italic")
        if opts.get("color") or color:
            r.font.color.rgb = rgb(opts.get("color") or color)
        if opts.get("size") or size:
            r.font.size = Pt(opts.get("size") or size)
    return paragraph


def para(doc_or_cell, runs, size=None, color=None, align=None, after=None, before=None, style=None, keep_next=False):
    p = doc_or_cell.add_paragraph(style=style) if style else doc_or_cell.add_paragraph()
    add_runs(p, runs, size, color)
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if before is not None:
        p.paragraph_format.space_before = Pt(before)
    if keep_next:
        p.paragraph_format.keep_with_next = True
    return p


def bullets(doc, items, style="List Bullet"):
    for item in items:
        para(doc, item, style=style)


def heading(doc, text, level=1):
    return doc.add_heading(text, level=level)


def _shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def _borders(table, color=RULE, inside=True, outer=False):
    tblPr = table._tbl.tblPr
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        show = (edge == "insideH" and inside) or (outer and edge in ("top", "bottom"))
        el.set(qn("w:val"), "single" if show else "nil")
        if show:
            el.set(qn("w:sz"), "4")
            el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def _cell_margins(table, left=90, right=90, top=40, bottom=40):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for edge, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def table(doc, rows, widths_cm, header=True, size=9.5, aligns=None, bold_first_col=False, highlight_rows=()):
    n_rows, n_cols = len(rows), len(rows[0])
    t = doc.add_table(rows=n_rows, cols=n_cols)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _borders(t)
    _cell_margins(t)
    aligns = aligns or [WD_ALIGN_PARAGRAPH.LEFT] * n_cols
    for i, row in enumerate(rows):
        is_header = header and i == 0
        if is_header:
            _repeat_header(t.rows[i])
        for j, value in enumerate(row):
            cell = t.cell(i, j)
            cell.width = Cm(widths_cm[j])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            fill = NAVY if is_header else (TINT if i in highlight_rows else (ZEBRA if i % 2 == 0 else WHITE))
            _shade(cell, fill)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            p.alignment = aligns[j]
            runs = value if isinstance(value, list) else [(str(value), {})]
            for text, opts in runs:
                r = p.add_run(text)
                r.font.size = Pt(size)
                r.bold = is_header or opts.get("bold") or (bold_first_col and j == 0) or (i in highlight_rows and j == 0)
                r.font.color.rgb = rgb(WHITE if is_header else opts.get("color", INK))
    for j, w in enumerate(widths_cm):
        t.columns[j].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def callout(doc, title, lines, fill=TINT, title_color=DARK_BLUE, width_cm=16.6):
    """A shaded one-cell box for key messages."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(t, inside=False)
    _cell_margins(t, 200, 200, 140, 140)
    cell = t.cell(0, 0)
    cell.width = Cm(width_cm)
    _shade(cell, fill)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(4)
    add_runs(p, [(title, {"bold": True, "color": title_color, "size": 11.5})])
    for line in lines:
        q = cell.add_paragraph(style="List Bullet")
        q.paragraph_format.space_after = Pt(2)
        add_runs(q, line)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def stat_row(doc, stats, width_cm=16.6):
    """Big-number tiles: stats = [(value, label), ...]."""
    t = doc.add_table(rows=1, cols=len(stats))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(t, inside=False)
    _cell_margins(t, 160, 160, 120, 120)
    for j, (value, label) in enumerate(stats):
        cell = t.cell(0, j)
        cell.width = Cm(width_cm / len(stats))
        _shade(cell, TINT)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        add_runs(p, [(value, {"bold": True, "color": DARK_BLUE, "size": 24})])
        q = cell.add_paragraph()
        q.paragraph_format.space_after = Pt(0)
        add_runs(q, [(label, {"color": SECONDARY, "size": 9.5})])
    # white gaps between tiles
    tblPr = t._tbl.tblPr
    spacing = OxmlElement("w:tblCellSpacing")
    spacing.set(qn("w:w"), "80")
    spacing.set(qn("w:type"), "dxa")
    tblPr.append(spacing)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figure(doc, path, caption, width_cm=16.6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    c = para(doc, [(caption, {"italic": True, "color": SECONDARY, "size": 9})], after=10)
    return c


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _field(paragraph, instruction, placeholder=""):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (begin, instr, sep, text, end):
        run._r.append(el)
    return run


def table_of_contents(doc):
    p = doc.add_paragraph()
    _field(p, 'TOC \\o "1-1" \\h \\z \\u', "Right-click and choose Update Field to build the table of contents.")


def footer(doc, text):
    for section in doc.sections:
        section.different_first_page_header_footer = True
        p = section.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        add_runs(p, [(f"{text}   |   page ", {"color": MUTED, "size": 8.5})])
        r = _field(p, "PAGE", "1")
        r.font.size = Pt(8.5)
        r.font.color.rgb = rgb(MUTED)
