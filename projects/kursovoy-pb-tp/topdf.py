"""Конвертация docx -> pdf через LibreOffice (обёртка навыка docx)."""
import glob, os, sys
sys.path.insert(0, glob.glob("/root/.claude/skills/synced/*/docx/scripts")[0])
from office.soffice import run_soffice


def to_pdf(docx, outdir):
    r = run_soffice(["--headless", "--convert-to", "pdf", "--outdir", os.path.abspath(outdir),
                     os.path.abspath(docx)], capture_output=True, text=True)
    return r


if __name__ == "__main__":
    r = to_pdf(sys.argv[1], sys.argv[2])
    print(r.stdout[-300:], r.stderr[-300:])
