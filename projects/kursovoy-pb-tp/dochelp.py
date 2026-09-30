"""Помощники для сборки пояснительной записки в python-docx (ЕСКД/методичка ИвПСА)."""
import re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls
from docx.shared import Cm, Mm, Pt, RGBColor

FONT = "Times New Roman"
# сквозная нумерация таблиц: внутренний номер (раздел.№) -> номер в документе
TAB = {"1.1": "1", "1.2": "2", "2.1": "3", "2.2": "4", "3.1": "5", "3.2": "6", "3.3": "7",
       "4.1": "8", "6.1": "9", "7.1": "10", "7.2": "11", "8.1": "12", "8.2": "13", "9.1": "14"}
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def fmt(x, n=2):
    """Число с десятичной запятой."""
    s = f"{x:.{n}f}"
    return s.replace(".", ",").replace("-", "−")


# ---------------------------------------------------------------- runs -----
_TOKEN = re.compile(r"(_\{[^}]*\}|\^\{[^}]*\}|<b>.*?</b>|<i>.*?</i>)", re.S)


def add_runs(par, text, size=None, bold=False, italic=False):
    """Разметка: _{sub} ^{sup} <b>..</b> <i>..</i>."""
    for part in _TOKEN.split(text):
        if not part:
            continue
        b, i, sub, sup = bold, italic, False, False
        if part.startswith("_{"):
            part, sub = part[2:-1], True
        elif part.startswith("^{"):
            part, sup = part[2:-1], True
        elif part.startswith("<b>"):
            part, b = part[3:-4], True
        elif part.startswith("<i>"):
            part, i = part[3:-4], True
        r = par.add_run(part)
        r.font.name = FONT
        r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        if size:
            r.font.size = Pt(size)
        r.bold, r.italic = b or None, i or None
        if sub:
            r.font.subscript = True
        if sup:
            r.font.superscript = True
    return par


# ---------------------------------------------------------- OMML formulas ---
def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _mr(text, plain=False):
    sty = '<m:rPr><m:sty m:val="p"/></m:rPr>' if plain else ""
    rpr = f'<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
    return f"<m:r>{sty}{rpr}<m:t xml:space=\"preserve\">{_esc(text)}</m:t></m:r>"


GREEK = dict(rho="ρ", varepsilon="ε", tau="τ", varphi="φ", delta="δ", eta="η", mu="μ",
             beta="β", alpha="α", omega="ω", lam="λ", Sigma="Σ", Delta="Δ",
             theta="θ", gamma="γ", nu="ν", pi="π", phi="φ", sigma="σ")


class _P:
    """Мини-парсер LaTeX-подобной записи формулы в OMML."""
    FUNCS = ("ln", "lg", "min", "max", "exp")

    def __init__(self, s):
        self.s, self.i = s, 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else ""

    def group(self):
        assert self.peek() == "{", self.s[self.i:self.i + 15]
        self.i += 1
        out = self.seq(until="}")
        self.i += 1
        return out

    def seq(self, until=""):
        out = []
        while self.i < len(self.s) and self.peek() != until:
            out.append(self.script(self.atom()))
        return "".join(out)

    def atom(self):
        c = self.peek()
        if c == "{":
            return self.group()
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+)", self.s[self.i:])
            name = m.group(1)
            self.i += len(m.group(0))
            if name == "frac":
                n, d = self.group(), self.group()
                return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"
            if name == "sqrt":
                x = self.group()
                return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{x}</m:e></m:rad>'
            if name == "sum":
                return _mr("∑", True)
            if name == "cdot":
                return _mr("·", True)
            if name == "le":
                return _mr("≤", True)
            if name == "ge":
                return _mr("≥", True)
            if name == "lt":
                return _mr("<", True)
            if name == "gt":
                return _mr(">", True)
            if name == "ll":
                return _mr("≪", True)
            if name == "approx":
                return _mr("≈", True)
            if name == "q":
                return _mr(" ", True)
            if name in self.FUNCS:
                return _mr(name, True)
            if name == "lambda":
                return _mr("λ")
            if name in GREEK:
                return _mr(GREEK[name])
            raise ValueError(name)
        m = re.match(r"(ln|lg|min|max|exp)", self.s[self.i:])
        if m:
            self.i += len(m.group(0))
            return _mr(m.group(0), True)
        if c in "()[]":
            self.i += 1
            return _mr(c, True)
        if c.isdigit() or c in ",.":
            m = re.match(r"[0-9]+(?:[.,][0-9]+)?", self.s[self.i:])
            if m:
                self.i += len(m.group(0))
                return _mr(m.group(0), True)
        self.i += 1
        if c in "+-=<>·/*":
            return _mr({"-": "−", "*": "·"}.get(c, c), True)
        if c == " ":
            return _mr(" ", True)
        return _mr(c)

    def script(self, base):
        sub = sup = None
        while self.peek() in ("_", "^"):
            k = self.peek()
            self.i += 1
            g = self.group() if self.peek() == "{" else self.atom()
            if k == "_":
                sub = g
            else:
                sup = g
        if sub and sup:
            return f"<m:sSubSup><m:e>{base}</m:e><m:sub>{sub}</m:sub><m:sup>{sup}</m:sup></m:sSubSup>"
        if sub:
            return f"<m:sSub><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>"
        if sup:
            return f"<m:sSup><m:e>{base}</m:e><m:sup>{sup}</m:sup></m:sSup>"
        return base


def omml(latex):
    body = _P(latex).seq()
    xml = (f'<m:oMath xmlns:m="{M_NS}" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"{body}</m:oMath>")
    return parse_xml(xml)


# --------------------------------------------------------------- Document --
class Report:
    def __init__(self):
        d = self.d = Document()
        s = d.sections[0]
        s.page_width, s.page_height = Mm(210), Mm(297)
        s.top_margin, s.bottom_margin = Mm(20), Mm(20)
        s.left_margin, s.right_margin = Mm(20), Mm(10)
        s.header_distance = Mm(10)
        s.different_first_page_header_footer = True
        st = d.styles["Normal"]
        st.font.name, st.font.size = FONT, Pt(14)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        pf = st.paragraph_format
        pf.space_before = pf.space_after = Pt(0)
        pf.line_spacing = 1.5
        for hn, sz in (("Heading 1", 14), ("Heading 2", 14)):
            hs = d.styles[hn]
            hs.font.name, hs.font.size, hs.font.bold = FONT, Pt(sz), True
            hs.font.color.rgb = RGBColor(0, 0, 0)
            rf = hs.element.get_or_add_rPr().rFonts
            for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                rf.set(qn(a), FONT)
            for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
        self._page_number_header(s)
        self.tab_no = {}
        self.fig_no = {}

    # -- header with page number in the centre (title page: empty header)
    def _page_number_header(self, section):
        hp = section.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = hp.add_run()
        r.font.name, r.font.size = FONT, Pt(12)
        for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
            if kind:
                el = OxmlElement("w:fldChar")
                el.set(qn("w:fldCharType"), kind)
            else:
                el = OxmlElement("w:instrText")
                el.set(qn("xml:space"), "preserve")
                el.text = txt
            r._element.append(el)

    # -- basic blocks
    def p(self, text="", indent=True, align="justify", size=None, bold=False,
          italic=False, space_after=0, keep_next=False, line=None, left=None):
        par = self.d.add_paragraph()
        pf = par.paragraph_format
        pf.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                        "center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        if indent:
            pf.first_line_indent = Cm(1.25)
        if left is not None:
            pf.left_indent = Cm(left)
        pf.space_after = Pt(space_after)
        pf.keep_with_next = keep_next
        if line:
            pf.line_spacing = line
        add_runs(par, text, size, bold, italic)
        return par

    def h1(self, text, page_break=True, numbered=True):
        par = self.p("", indent=False, align="center", keep_next=True, space_after=6)
        if page_break:
            par.paragraph_format.page_break_before = True
        add_runs(par, text.upper(), bold=True)
        par.style = self.d.styles["Heading 1"]
        self._style_heading(par, 14)
        return par

    def h2(self, text):
        par = self.p("", indent=False, align="left", keep_next=True, space_after=3)
        par.paragraph_format.first_line_indent = Cm(1.25)
        par.paragraph_format.space_before = Pt(6)
        add_runs(par, text, bold=True)
        par.style = self.d.styles["Heading 2"]
        self._style_heading(par, 14)
        return par

    def _style_heading(self, par, size):
        # стиль заголовка меняет шрифт на Calibri — принудительно возвращаем Times, чёрный
        for r in par.runs:
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.color.rgb = None
            r.bold = True
            rpr = r._element.get_or_add_rPr()
            rpr.rFonts.set(qn("w:eastAsia"), FONT)
            rpr.rFonts.set(qn("w:ascii"), FONT)
            rpr.rFonts.set(qn("w:hAnsi"), FONT)
            for c in rpr.findall(qn("w:color")):
                rpr.remove(c)
        pf = par.paragraph_format
        pf.line_spacing = 1.5

    def bullets(self, items, size=None):
        for t in items:
            par = self.p("", indent=False, left=1.25)
            par.paragraph_format.first_line_indent = Cm(-0.5)
            par.paragraph_format.left_indent = Cm(1.75)
            add_runs(par, "– " + t, size)

    def formula(self, latex, number):
        """Формула по центру, номер справа в скобках (одна строка, табуляции)."""
        self._ref_formula(number)
        par = self.d.add_paragraph()
        pf = par.paragraph_format
        pf.line_spacing = 1.5
        pf.keep_together = True
        pf.tab_stops.add_tab_stop(Mm(90), WD_TAB_ALIGNMENT.CENTER)
        pf.tab_stops.add_tab_stop(Mm(180), WD_TAB_ALIGNMENT.RIGHT)
        r = par.add_run("\t")
        par._p.append(omml(latex))
        r2 = par.add_run("\t(" + number + ")")
        r2.font.name, r2.font.size = FONT, Pt(14)
        return par

    def _ref_formula(self, number):
        """Ссылка на формулу в тексте: дописываем «(N)» к предшествующему абзацу."""
        pars = self.d.paragraphs
        if not pars:
            return
        last = pars[-1]
        txt = last.text.rstrip()
        if not txt or last._p.findall(qn("m:oMath")) or f"({number})" in txt:
            return
        ref = f" ({number})"
        if txt.endswith(":"):
            last.runs[-1].text = last.runs[-1].text.rstrip()[:-1] + ref + ":"
        else:
            last.runs[-1].text = last.runs[-1].text.rstrip() + ref

    def where(self, items):
        """Блок «где ...» — каждая позиция с новой строки, без красной строки."""
        first = True
        for t in items:
            par = self.p("", indent=False)
            add_runs(par, ("где " if first else "       ") + t)
            first = False

    # -- tables
    def table_title(self, num, title):
        num = TAB.get(num, num)
        par = self.p("", indent=False, align="left", keep_next=True, line=1.15)
        add_runs(par, f"Таблица {num} {title}")
        return par

    def table(self, rows, widths_mm, header_rows=1, size=11, align=None, bold_first_col=False):
        t = self.d.add_table(rows=len(rows), cols=len(widths_mm))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        align = align or ["left"] * len(widths_mm)
        for ri, row in enumerate(rows):
            tr = t.rows[ri]
            trPr = tr._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")
            trPr.append(cs)
            if ri < header_rows:
                th = OxmlElement("w:tblHeader")
                trPr.append(th)
            for ci, val in enumerate(row):
                cell = tr.cells[ci]
                cell.width = Mm(widths_mm[ci])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                par = cell.paragraphs[0]
                pf = par.paragraph_format
                pf.line_spacing = 1.0
                pf.space_before = pf.space_after = Pt(1)
                pf.alignment = (WD_ALIGN_PARAGRAPH.CENTER if ri < header_rows
                                else {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER,
                                      "right": WD_ALIGN_PARAGRAPH.RIGHT}[align[ci]])
                lines = str(val).split("\n")
                for li, line in enumerate(lines):
                    if li:
                        par = cell.add_paragraph()
                        par.paragraph_format.line_spacing = 1.0
                        par.paragraph_format.space_before = par.paragraph_format.space_after = Pt(1)
                        par.paragraph_format.alignment = pf.alignment
                    add_runs(par, line, size, bold=(ri < header_rows) or (bold_first_col and ci == 0))
        # ширины колонок
        grid = t._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths_mm):
            gc.set(qn("w:w"), str(int(w * 56.7)))
        self.p("", indent=False, line=0.6)
        return t

    def image(self, path, width_mm, caption, page_break=False):
        par = self.p("", indent=False, align="center", keep_next=True, line=1.0)
        par.paragraph_format.page_break_before = page_break
        par.add_run().add_picture(path, width=Mm(width_mm))
        self.p(caption, indent=False, align="center", line=1.15, space_after=8)

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def save(self, path):
        z = self.d.settings.element.find(qn("w:zoom"))
        if z is not None and z.get(qn("w:percent")) is None:
            z.set(qn("w:percent"), "100")
        self.d.save(path)
