"""Build docs/Proposal.{docx,pdf} and docs/Report.{docx,pdf} from the real results.

    python scripts/build_docs.py [--only report|proposal]

Personal details come from project.config.json. Requires: node (scripts/doctools
installed with `npm install`), LibreOffice (`soffice`) and poppler (`pdftotext`).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "docgen"))

from common import ROOT, _render, build, cfg, facts  # noqa: E402
from proposal import build_proposal  # noqa: E402
from report import build_report, lists  # noqa: E402
from short_report import build_short_report, short_lists  # noqa: E402

DOCS = ROOT / "docs"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["report", "full", "proposal"])
    a = ap.parse_args()
    C = cfg()
    base = {"title": f'{C["project_title"]}: {C["project_subtitle"]}', "header": f'{C["project_title"]} - {C["project_subtitle"]}',
            "author": ", ".join(m["name"] for m in C.get("group_members", [])) or C["student_name"], "font": "Times New Roman", "size": 12}
    if a.only in (None, "proposal"):
        p = build_proposal()
        pdf = _render(dict(base, sections=p.sections), DOCS / "Proposal.docx")
        print("proposal ->", pdf)
    if a.only in (None, "report", "full"):
        F = facts()
    if a.only in (None, "report"):                    # short report (~15 pages)
        d = build_short_report(F)
        res = build(d, lambda pages: short_lists(d, pages), base, DOCS / "Report.docx")
        print(f'report -> {res["pdf"]} ({res["n_pages"]} pages)')
    if a.only in (None, "full"):                      # full academic report
        d = build_report(F)
        for title in ("List of Figures", "List of Tables", "List of Abbreviations"):
            d.toc.insert([i for i, e in enumerate(d.toc) if e["kind"] == "front"][-1] + 1,
                         {"key": title.upper(), "text": title, "level": 1, "kind": "front", "plain": True})
        res = build(d, lambda pages: lists(d, pages), base, DOCS / "Report_Full.docx")
        print(f'full report -> {res["pdf"]} ({res["n_pages"]} pages)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
