"""Чертежи графической части (2 листа А3) и рисунки для пояснительной записки.

Координаты — миллиметры на листе, ось y направлена вниз.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, Ellipse, FancyArrowPatch

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["pdf.fonttype"] = 42
RED = "#e00000"
BLK = "#000000"
LW = 0.9          # основная линия, pt (≈0,32 мм)
LW_THIN = 0.45


class Canvas:
    def __init__(self, w_mm, h_mm):
        self.w, self.h = w_mm, h_mm
        self.fig = plt.figure(figsize=(w_mm / 25.4, h_mm / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w_mm)
        self.ax.set_ylim(h_mm, 0)
        self.ax.axis("off")

    # -- примитивы
    def line(self, pts, lw=LW, c=BLK, ls="-", z=2):
        xs, ys = zip(*pts)
        self.ax.plot(xs, ys, color=c, lw=lw, ls=ls, solid_capstyle="butt", zorder=z)

    def rect(self, x, y, w, h, lw=LW, c=BLK, fc="none", z=2):
        self.ax.add_patch(Rectangle((x, y), w, h, fill=fc != "none", fc=fc, ec=c, lw=lw, zorder=z))

    def circle(self, x, y, r, lw=LW, c=BLK, fc="none", z=2):
        self.ax.add_patch(Circle((x, y), r, fill=fc != "none", fc=fc, ec=c, lw=lw, zorder=z))

    def poly(self, pts, lw=LW, c=BLK, fc="none", z=2, closed=True):
        self.ax.add_patch(Polygon(pts, closed=closed, fill=fc != "none", fc=fc, ec=c, lw=lw, zorder=z))

    def text(self, x, y, s, size=9, ha="left", va="center", c=BLK, bold=False, rot=0,
             italic=False, z=5, wrap=None):
        self.ax.text(x, y, s, fontsize=size, ha=ha, va=va, color=c, rotation=rot, zorder=z,
                     fontweight="bold" if bold else "normal",
                     fontstyle="italic" if italic else "normal", linespacing=1.15)

    def arrow(self, p0, p1, lw=LW, c=BLK, ms=7):
        self.ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                                          lw=lw, color=c, shrinkA=0, shrinkB=0, zorder=3))

    def save(self, path, dpi=200):
        """path без расширения — сохраняем PDF (вектор) и PNG."""
        if path.endswith((".png", ".pdf")):
            self.fig.savefig(path, dpi=dpi)
        else:
            self.fig.savefig(path + ".pdf")
            self.fig.savefig(path + ".png", dpi=dpi)
        plt.close(self.fig)


# ---------------------------------------------------------- символы -------
def pump(cv, x, y, r=6.5, c=BLK, lw=LW):
    """Центробежный насос: круг + треугольник."""
    cv.circle(x, y, r, lw=lw, c=c)
    cv.poly([(x - r * 0.55, y - r * 0.75), (x - r * 0.55, y + r * 0.75), (x + r * 0.9, y)],
            lw=lw * 0.8, c=c)


def valve(cv, x, y, s=2.6, horizontal=True, lw=LW * 0.8):
    if horizontal:
        cv.poly([(x - s, y - s), (x - s, y + s), (x + s, y - s), (x + s, y + s)], lw=lw)
    else:
        cv.poly([(x - s, y - s), (x + s, y - s), (x - s, y + s), (x + s, y + s)], lw=lw)


def vessel(cv, x, y, w, h, c=BLK, lw=LW, dome=True):
    """Вертикальный цилиндрический аппарат со скруглёнными днищами (x, y — левый верх)."""
    e = min(w * 0.25, 4)
    cv.line([(x, y + e), (x, y + h - e)], lw=lw, c=c)
    cv.line([(x + w, y + e), (x + w, y + h - e)], lw=lw, c=c)
    cv.ax.add_patch(matplotlib.patches.Arc((x + w / 2, y + e), w, 2 * e, theta1=180, theta2=360,
                                           ec=c, lw=lw, zorder=2))
    cv.ax.add_patch(matplotlib.patches.Arc((x + w / 2, y + h - e), w, 2 * e, theta1=0, theta2=180,
                                           ec=c, lw=lw, zorder=2))


def tag(cv, x, y, s, size=8, c=BLK):
    """Позиционный номер в кружке."""
    cv.circle(x, y, 3.6, lw=LW_THIN, c=c, fc="white", z=4)
    cv.text(x, y, s, size=size - 1.5 if len(s) > 2 else size, ha="center", c=c, z=6)


class View:
    """Обёртка над Canvas: локальные координаты → лист (смещение ox, oy и масштаб k)."""
    def __init__(self, cv, ox, oy, k=1.0, fs=None):
        self.cv, self.ox, self.oy, self.k = cv, ox, oy, k
        self.fs = fs if fs is not None else max(k, 0.72)

    def P(self, x, y):
        return (self.ox + self.k * x, self.oy + self.k * y)

    def line(self, pts, **kw):
        self.cv.line([self.P(*p) for p in pts], **kw)

    def rect(self, x, y, w, h, **kw):
        px, py = self.P(x, y)
        self.cv.rect(px, py, w * self.k, h * self.k, **kw)

    def circle(self, x, y, r, **kw):
        px, py = self.P(x, y)
        self.cv.circle(px, py, r * self.k, **kw)

    def poly(self, pts, **kw):
        self.cv.poly([self.P(*p) for p in pts], **kw)

    def text(self, x, y, s, size=9, **kw):
        px, py = self.P(x, y)
        self.cv.text(px, py, s, size=size * self.fs, **kw)

    def arrow(self, p0, p1, **kw):
        self.cv.arrow(self.P(*p0), self.P(*p1), **kw)

    def pump(self, x, y, r=6.5, **kw):
        px, py = self.P(x, y)
        pump(self.cv, px, py, r * self.k, **kw)

    def valve(self, x, y, horizontal=True):
        px, py = self.P(x, y)
        valve(self.cv, px, py, 2.6 * self.k, horizontal)

    def vessel(self, x, y, w, h, **kw):
        px, py = self.P(x, y)
        vessel(self.cv, px, py, w * self.k, h * self.k, **kw)

    def tag(self, x, y, s, **kw):
        px, py = self.P(x, y)
        tag(self.cv, px, py, s, **kw)


def draw_scheme(v, marks=False):
    """Принципиальная технологическая схема краскоприготовления и окраски (≈ 350 × 125 мм)."""
    # --- линии (основные, потоки)
    # растворитель: вход -> насос 1 -> мерник 2
    v.arrow((0, 78), (13.5, 78))
    v.text(0, 86, "Растворитель Р-4", size=8)
    v.line([(26.5, 78), (45, 78), (45, 38), (60, 38)])
    v.valve(36, 78)
    v.pump(20, 78, 6.5)
    # мерник 2
    v.vessel(60, 26, 16, 24)
    v.line([(68, 50), (68, 58), (100, 58), (100, 64)])
    v.valve(68, 55, horizontal=False)
    # бункер 4
    v.vessel(135, 22, 30, 28)
    v.arrow((150, 8), (150, 22))
    v.text(150, 4, "Полуфабрикат краски\n(70 % смолы + 30 % растворителя)", size=7, ha="center")
    v.line([(150, 50), (150, 58), (120, 58), (120, 64)])
    v.valve(150, 55, horizontal=False)
    # смеситель 3 — красный контур (основной аппарат)
    R = dict(c=RED, lw=LW * 1.8)
    v.line([(90, 64), (90, 106), (100, 118), (120, 118), (130, 106), (130, 64)], **R)
    v.line([(90, 64), (130, 64)], **R)
    # мешалка
    v.line([(110, 52), (110, 112)], c=RED, lw=LW)
    v.rect(104, 46, 12, 6, c=RED, lw=LW)
    for yy in (96, 106):
        v.line([(98, yy), (122, yy)], c=RED, lw=LW)
    v.text(108, 79, "смеситель\nV = 0,7 м³", size=7, ha="right", c=RED)
    # рубашка / горячая вода
    v.arrow((78, 100), (90, 100), c=BLK)
    v.text(66, 106, "Горячая вода\n40…60 °C", size=7, ha="center")
    v.arrow((130, 82), (142, 82))
    v.text(143, 82, "Конденсат / вода", size=7)
    # выход смесителя -> насос 5 -> фильтр 6 -> баки 7
    v.line([(110, 118), (110, 126), (128, 126)])
    v.pump(135, 126, 6.5)
    v.line([(141.5, 126), (158, 126)])
    v.rect(158, 119, 14, 14)
    v.line([(158, 119), (172, 133)], lw=LW_THIN)
    v.line([(172, 126), (182, 126), (182, 62), (199, 62), (199, 70)])
    v.line([(199, 62), (225, 62), (225, 70)])
    v.valve(182, 100, horizontal=False)
    # баки 7
    v.vessel(190, 70, 18, 42)
    v.vessel(216, 70, 18, 42)
    # насос 8 и кольцевая линия 9
    v.line([(199, 112), (199, 124), (243, 124)])
    v.line([(225, 112), (225, 124)])
    v.pump(250, 124, 6.5)
    v.line([(256.5, 124), (330, 124)])
    v.line([(330, 124), (330, 140), (205, 140), (205, 112)], ls="--", lw=LW_THIN)
    v.text(260, 134, "кольцевая линия", size=7)
    # окрасочная камера 17, шланги 18
    v.rect(292, 84, 50, 30)
    for xx in (305, 328):
        v.line([(xx, 124), (xx, 104)], lw=LW_THIN)
        v.circle(xx, 100, 2.4, lw=LW_THIN)
    v.text(317, 92, "окрасочная\nкамера", size=7, ha="center")
    v.arrow((342, 99), (356, 99))
    v.text(342, 78, "Вытяжка", size=7)
    v.arrow((317, 84), (317, 70))
    # позиции
    lab = {"1": (20, 68), "2": (68, 22), "3": (84, 116), "4": (150, 27), "5": (135, 137),
           "6": (165, 113), "7": (212, 64), "8": (250, 137), "9": (285, 120), "17": (297, 80),
           "18": (336, 108)}
    for n, (x, y) in lab.items():
        if n in ("4",):
            continue
        v.tag(x, y, n)
    v.tag(150, 36, "4")
    if marks:
        draw_marks(v)


def draw_marks(v):
    """Индексы пожарной опасности на схеме ПТК (1.1, 2.1 …) — красные."""
    M = [("1.1", 40, 68), ("1.1", 200, 56), ("2.1", 84, 34), ("2.2", 100, 92), ("3.1", 96, 52),
         ("3.2", 122, 52), ("3.3", 96, 124), ("4.1", 118, 40), ("4.2", 135, 114), ("4.3", 98, 40),
         ("4.4", 172, 112), ("5.1", 75, 58), ("5.2", 300, 68), ("5.3", 122, 134)]
    for s, x, y in M:
        v.circle(x, y, 4.6, lw=LW_THIN, c=RED, fc="white", z=6)
        v.text(x, y, s, size=6.2, ha="center", c=RED, z=7)


def draw_plan(v, W=13.0, D=9.2, marks=True):
    """План помещения цеха мерников и растворителей (координаты в метрах, v.k = мм/м)."""
    # стены (кирпич/бетон, 0,4 м): серая заливка снаружи, белый интерьер
    v.rect(-0.4, -0.4, W + 0.8, D + 0.8, fc="#cfcfcf", lw=LW, z=0.5)
    v.rect(0, 0, W, D, fc="white", lw=LW, z=1)
    # ЛСК (остеклённые проёмы) в верхней стене
    for x0 in (2.6, 5.4, 8.2):
        v.rect(x0, -0.4, 1.8, 0.4, fc="#bfe3ff", lw=LW_THIN, z=4)
    v.text(2.6, -0.85, "ЛСК (остекление)", size=6.5)
    # дверь с тамбур-шлюзом (низ, справа)
    v.rect(11.0, D - 0.05, 1.3, 0.5, fc="white", lw=LW, z=4)
    v.line([(11.0, D + 0.02), (11.0, D + 0.85)], lw=LW_THIN, z=5)
    v.line([(12.3, D + 0.02), (12.3, D + 0.85)], lw=LW_THIN, z=5)
    v.line([(11.0, D + 0.85), (12.3, D + 0.85)], lw=LW_THIN, z=5)
    v.text(9.3, D + 1.35, "дверь EI 60, тамбур-шлюз", size=6.5)
    v.line([(11.0, D - 0.9), (11.0, D - 0.05)], lw=LW_THIN, ls="--")   # порог
    # мерники 2
    for x in (1.2, 2.3):
        v.circle(x, 1.5, 0.32, lw=LW)
    v.tag(1.75, 0.55, "2")
    # смесители 3 (левый — расчётный аппарат, красный)
    v.circle(4.6, 4.0, 0.60, c=RED, lw=LW * 2)
    v.circle(6.9, 4.0, 0.60, lw=LW)
    v.line([(4.0, 4.0), (5.2, 4.0)], c=RED, lw=LW_THIN)
    v.line([(4.6, 3.4), (4.6, 4.6)], c=RED, lw=LW_THIN)
    v.tag(4.6, 2.85, "3")
    v.tag(6.9, 2.85, "3")
    # бункеры 4
    for x in (10.2, 11.5):
        v.circle(x, 1.5, 0.38, lw=LW)
    v.tag(10.85, 0.55, "4")
    # трубопроводы: растворитель (пунктир), готовая краска
    v.line([(0, 1.5), (0.88, 1.5)], lw=LW * 1.2)
    v.arrow((-0.6, 1.5), (0, 1.5), ms=6)
    v.text(-1.0, 1.15, "Р-4", size=6.5, ha="right")
    v.line([(1.5, 1.82), (1.5, 2.6), (4.6, 2.6), (4.6, 3.4)], lw=LW_THIN)
    v.line([(2.6, 1.82), (2.6, 2.4), (6.9, 2.4), (6.9, 3.4)], lw=LW_THIN)
    v.line([(10.2, 1.88), (10.2, 2.7), (4.9, 2.7), (4.9, 3.42)], lw=LW_THIN)
    v.line([(4.6, 4.6), (4.6, 6.9), (W, 6.9)], lw=LW * 1.2)
    v.arrow((W, 6.9), (W + 0.7, 6.9), ms=6)
    v.text(W + 0.85, 6.9, "к насосу 5", size=6.5)
    # аварийный слив
    v.line([(6.9, 4.6), (6.9, 8.1), (W, 8.1)], lw=LW * 1.2, ls="--")
    v.rect(W + 0.8, 7.75, 1.0, 0.7, lw=LW)
    v.text(W + 1.0, 8.1, "АЕ", size=6.5)
    v.circle(9.0, 8.1, 0.14, lw=LW_THIN, fc="white")
    v.text(9.0, 8.55, "задвижка", size=6, ha="center")
    # вытяжка / местный отсос
    v.rect(5.2, 5.2, 0.9, 0.5, fc="#e8e8e8", lw=LW_THIN)
    v.text(5.65, 5.45, "В1", size=6.5, ha="center")
    v.line([(5.65, 5.2), (5.65, 4.55)], lw=LW_THIN, ls=":")
    v.text(0.5, 6.1, "МО — местные отсосы\nот люков смесителей", size=6, ha="left")
    # сигнализаторы довзрывных концентраций и огнетушители
    for x, y in ((3.3, 3.1), (8.3, 3.1), (12.2, 5.0)):
        v.rect(x - 0.15, y - 0.15, 0.3, 0.3, fc="#ffe9a8", lw=LW_THIN)
    v.text(12.2, 4.6, "СДК", size=6, ha="center")
    v.poly([(10.4, D - 0.35), (10.8, D - 0.35), (10.6, D - 0.75)], lw=LW_THIN, fc=RED)
    v.text(9.9, D - 0.75, "ОП", size=6, ha="center")
    # категория / зона
    v.rect(0.4, 7.8, 1.7, 1.0, lw=LW, z=4, fc="white")
    v.text(1.25, 8.3, "А\nВ-Iа", size=8, ha="center", bold=True)
    # размеры
    v.line([(0, -1.35), (W, -1.35)], lw=LW_THIN)
    v.text(W / 2, -1.15, f"{W:.0f}".replace(".", ",") + "000", size=7, ha="center", va="bottom")
    v.line([(-1.6, 0), (-1.6, D)], lw=LW_THIN)
    v.text(-1.85, D / 2, "9200", size=7, ha="center", rot=90)
    if marks:
        for s, x, y in [("2.1", 1.75, 2.1), ("2.2", 4.6, 4.3), ("3.1", 5.5, 3.3), ("3.2", 3.7, 3.3),
                        ("3.3", 4.0, 5.0), ("4.1", 7.9, 4.6), ("4.3", 10.5, 3.6), ("5.1", 8.4, 6.9),
                        ("5.2", 5.65, 6.1), ("5.3", 9.0, 7.5), ("5.4", 11.7, D - 0.6)]:
            v.circle(x, y, 0.36, lw=LW_THIN, c=RED, fc="white", z=7)
            v.text(x, y, s, size=5.6, ha="center", c=RED, z=8)


def draw_section(v, W=13.0, H=3.5):
    """Разрез 1–1 (метры)."""
    v.rect(-0.4, -0.3, W + 0.8, 0.3, fc="#cfcfcf")           # перекрытие
    v.rect(-0.4, H, W + 0.8, 0.3, fc="#cfcfcf")               # пол
    v.line([(0, 0), (0, H)], lw=LW * 1.6)
    v.line([(W, 0), (W, H)], lw=LW * 1.6)
    # ЛСК в торцевой стене
    v.rect(-0.12, 0.7, 0.12, 1.3, fc="#bfe3ff", lw=LW_THIN, z=4)
    # смеситель на опорах
    v.rect(4.18, H - 0.5 - 1.26, 0.84, 1.26, c=RED, lw=LW * 1.8)
    v.line([(4.35, H - 0.5), (4.35, H)], c=RED)
    v.line([(4.85, H - 0.5), (4.85, H)], c=RED)
    v.line([(4.6, H - 1.9), (4.6, H - 0.8)], c=RED, lw=LW_THIN)
    v.rect(4.42, H - 2.08, 0.36, 0.18, c=RED, lw=LW_THIN)
    v.rect(6.48, H - 0.5 - 1.26, 0.84, 1.26)
    v.line([(6.65, H - 0.5), (6.65, H)])
    v.line([(7.15, H - 0.5), (7.15, H)])
    # мерник и бункер на площадке
    v.rect(0.95, 0.7, 0.5, 0.9)
    v.rect(2.0, 0.7, 0.5, 0.9)
    v.rect(9.9, 0.6, 0.7, 1.0)
    v.rect(11.2, 0.6, 0.7, 1.0)
    # вытяжной воздуховод под потолком
    v.rect(3.0, 0.15, 6.0, 0.35, fc="#e8e8e8", lw=LW_THIN)
    v.text(6.0, 0.33, "воздуховод В1 (верхняя зона)", size=6, ha="center")
    # дверь
    v.rect(11.0, H - 2.1, 1.3, 2.1, fc="white", lw=LW_THIN, z=3)
    v.text(11.65, H - 1.05, "EI 60", size=6, ha="center")
    v.line([(0, H - 0.15), (W, H - 0.15)], lw=LW_THIN, ls="--")
    # отметки
    v.text(W + 0.3, H, "±0,000", size=6.5)
    v.text(W + 0.3, 0, "+3,500", size=6.5)
    v.line([(-1.2, 0), (-1.2, H)], lw=LW_THIN)
    v.text(-1.5, H / 2, "3500", size=7, ha="center", rot=90)


# ------------------------------------------------- рамка, штамп, таблицы ---
import textwrap

PT = 0.3528      # мм в одном пункте


def wrap(s, width_mm, size):
    n = max(4, int(width_mm / (0.205 * size)))
    out = []
    for para in str(s).split("\n"):
        out += textwrap.wrap(para, n) or [""]
    return out


def table(cv, x, y, cols, rows, size=8, head=1, pad=1.2, bold_head=True, max_h=None):
    """Таблица с переносом текста. Возвращает y нижней границы."""
    lh = size * PT * 1.22
    cy = y
    for ri, row in enumerate(rows):
        cells = [wrap(c, w - 2 * pad, size) for c, w in zip(row, cols)]
        h = max(len(c) for c in cells) * lh + 2 * pad
        cx = x
        for ci, (lines, w) in enumerate(zip(cells, cols)):
            cv.rect(cx, cy, w, h, lw=LW_THIN)
            hb = ri < head
            for li, ln in enumerate(lines):
                if hb:
                    cv.text(cx + w / 2, cy + pad + lh * (li + 0.5), ln, size=size, ha="center", bold=bold_head)
                else:
                    cv.text(cx + pad, cy + pad + lh * (li + 0.5), ln, size=size)
            cx += w
        cy += h
    return cy


def frame(cv):
    cv.rect(0.3, 0.3, cv.w - 0.6, cv.h - 0.6, lw=0.3)                # кромка листа
    cv.rect(20, 5, cv.w - 25, cv.h - 10, lw=1.6)                    # рамка чертежа


def stamp(cv, code, title, sheet, sheets, author="Смолин", scale="—"):
    """Основная надпись по форме 1 ГОСТ 2.104 (185 × 55 мм, упрощённо)."""
    x0, y0 = cv.w - 5 - 185, cv.h - 5 - 55
    cv.rect(x0, y0, 185, 55, lw=1.6)
    # горизонтальные линии слева (строки по 5 мм)
    for i in range(1, 11):
        yy = y0 + 5 * i
        if yy < y0 + 55:
            cv.line([(x0, yy), (x0 + 65, yy)], lw=LW_THIN)
    for dx in (17, 40, 55):
        cv.line([(x0 + dx, y0 + 20), (x0 + dx, y0 + 55)], lw=LW_THIN)
    cv.line([(x0 + 7, y0 + 50), (x0 + 7, y0 + 55)], lw=LW_THIN)
    cv.line([(x0 + 65, y0), (x0 + 65, y0 + 55)], lw=1.6)
    cv.line([(x0, y0 + 20), (x0 + 65, y0 + 20)], lw=1.6)
    cv.line([(x0, y0 + 40), (x0 + 65, y0 + 40)], lw=LW_THIN)
    # шапки левого блока
    for dx, s in ((3.5, "Изм."), (12, "Лист"), (28.5, "№ докум."), (47.5, "Подп."), (60, "Дата")):
        cv.text(x0 + dx, y0 + 47.5 + 5, s, size=6, ha="center")
        cv.text(x0 + dx, y0 + 47.5 - 5 + 0, "", size=6)
    roles = [("Разраб.", author), ("Пров.", ""), ("Т. контр.", ""), ("Н. контр.", ""), ("Утв.", "")]
    for i, (r, n) in enumerate(roles):
        yy = y0 + 22.5 + 5 * i
        if yy + 2.5 <= y0 + 47:
            cv.text(x0 + 1, yy, r, size=6)
            cv.text(x0 + 18, yy, n, size=6.5)
    # правая часть
    cv.line([(x0 + 65, y0 + 15), (x0 + 185, y0 + 15)], lw=1.6)
    cv.text(x0 + 125, y0 + 7.5, code, size=15, ha="center", bold=True)
    cv.line([(x0 + 65, y0 + 40), (x0 + 135, y0 + 40)], lw=LW_THIN)
    lines = wrap(title, 68, 10)
    for i, ln in enumerate(lines[:5]):
        cv.text(x0 + 100, y0 + 17.5 + i * 4.6, ln, size=10, ha="center")
    cv.line([(x0 + 135, y0 + 15), (x0 + 135, y0 + 55)], lw=1.6)
    for dx in (150, 165):
        cv.line([(x0 + dx, y0 + 15), (x0 + dx, y0 + 30)], lw=LW_THIN)
    cv.line([(x0 + 135, y0 + 22), (x0 + 185, y0 + 22)], lw=LW_THIN)
    cv.line([(x0 + 135, y0 + 30), (x0 + 185, y0 + 30)], lw=LW_THIN)
    for dx, s, v in ((142.5, "Лит.", "У"), (157.5, "Масса", "—"), (175, "Масштаб", scale)):
        cv.text(x0 + dx, y0 + 18.5, s, size=6, ha="center")
        cv.text(x0 + dx, y0 + 26, v, size=8, ha="center")
    cv.text(x0 + 137, y0 + 34, f"Лист {sheet}", size=8)
    cv.text(x0 + 162, y0 + 34, f"Листов {sheets}", size=8)
    cv.text(x0 + 160, y0 + 43, "ИвПСА ГПС МЧС России", size=8, ha="center")
    cv.text(x0 + 160, y0 + 49, "гр. ________", size=8, ha="center")
    return x0, y0
