"""Сборка пояснительной записки курсового проекта (двухпроходная: номера страниц содержания)."""
import os
import shutil
import calc
import sheets
import t_front, t_s1_2, t_s3_6, t_s7_8, t_s9_end
from dochelp import Report
from topdf import to_pdf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
RESULT = os.path.join(HERE, "result")
NAME = "Курсовой_проект_ПБТП_вариант73_Смолин"

# подстроки, по которым ищем страницы разделов в PDF (страницы 1–3 пропускаем)
FIND = {
    "intro": "ВВЕДЕНИЕ", "s1": "1. АНАЛИЗ ПОЖАРОВЗРЫВООПАСНЫХ", "s2": "2. КРАТКОЕ ОПИСАНИЕ",
    "s3": "3. АНАЛИЗ ВОЗМОЖНОСТИ ОБРАЗОВАНИЯ ГОРЮЧЕЙ", "s4": "4. АНАЛИЗ ВОЗМОЖНОСТИ ОБРАЗОВАНИЯ ХАРАКТЕРНЫХ",
    "s5": "5. АНАЛИЗ ПРИЧИН", "s6": "6. АНАЛИЗ ВОЗМОЖНЫХ", "s7": "7. РАСЧЁТ КРИТЕРИЕВ",
    "s8": "8. ОПРЕДЕЛЕНИЕ КАТЕГОРИЙ", "s9": "9. РАЗРАБОТКА МЕРОПРИЯТИЙ, НАПРАВЛЕННЫХ НА ОБЕСПЕЧЕНИЕ",
    "s91": "9.1 Разработка мероприятий, направленных на предотвращение",
    "s92": "9.2 Разработка мероприятий, направленных на противопожарную",
    "s93": "9.3 Расчёт инженерно-технических решений", "concl": "ЗАКЛЮЧЕНИЕ", "lit": "СПИСОК ЛИТЕРАТУРЫ",
    "appA": "ПРИЛОЖЕНИЕ А", "appB": "ПРИЛОЖЕНИЕ Б",
}


def build(pages, path):
    R = calc.run()
    rp = Report()
    t_front.title_page(rp, R)
    t_front.toc(rp, pages)
    t_front.initial_data(rp, R)
    t_front.intro(rp, R)
    t_front.__dict__  # noqa
    t_s1_2.s1(rp, R)
    t_s1_2.s2(rp, R)
    for fn in (t_s3_6.s3, t_s3_6.s4, t_s3_6.s5, t_s3_6.s6, t_s7_8.s7, t_s7_8.s8,
               t_s9_end.s9, t_s9_end.concl, t_s9_end.lit, t_s9_end.appendices):
        fn(rp, R)
    rp.save(path)


def find_pages(pdf):
    import pymupdf
    d = pymupdf.open(pdf)
    texts = [" ".join(p.get_text().split()) for p in d]
    pages = {}
    for key, s in FIND.items():
        for i in range(3, len(texts)):
            if s in texts[i]:
                pages[key] = i + 1
                break
    return pages, len(d)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(RESULT, exist_ok=True)
    sheets.build_all()
    tmp = os.path.join(OUT, "zapiska.docx")
    build({}, tmp)
    to_pdf(tmp, OUT)
    pages, n = find_pages(os.path.join(OUT, "zapiska.pdf"))
    build(pages, tmp)
    to_pdf(tmp, OUT)
    pages2, n2 = find_pages(os.path.join(OUT, "zapiska.pdf"))
    assert pages == pages2, (pages, pages2)
    shutil.copy(tmp, os.path.join(RESULT, NAME + ".docx"))
    shutil.copy(os.path.join(OUT, "zapiska.pdf"), os.path.join(RESULT, NAME + ".pdf"))
    shutil.copy(os.path.join(OUT, "sheet1.pdf"), os.path.join(RESULT, "Лист1_Технологическая_схема_A3.pdf"))
    shutil.copy(os.path.join(OUT, "sheet2.pdf"), os.path.join(RESULT, "Лист2_Пожарно-техническая_карта_A3.pdf"))
    print("страниц:", n2, pages)
