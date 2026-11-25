"""Shared helpers for the proposal and report generators.

* ``Doc`` collects blocks, auto-numbers figures/tables per chapter and records
  table-of-contents entries.
* ``facts()`` reads every benchmark/test output so prose and tables quote real numbers.
* ``build()`` renders DOCX (Node docx renderer) -> PDF (LibreOffice) and runs a
  pagination pass: it finds each heading/caption in the PDF and writes the real
  page numbers into the TOC / list of figures / list of tables, repeating until stable.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import statistics as st
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "dataset" / "results"
FIG = ROOT / "docs" / "figures"
DIAG = FIG / "diagrams"
SHOT = FIG / "screenshots"
TOOLS = ROOT / "scripts" / "doctools"


def cfg() -> dict:
    return json.loads((ROOT / "project.config.json").read_text())


def roman(n: int) -> str:
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


class Doc:
    def __init__(self):
        self.sections: list[dict] = []
        self.toc: list[dict] = []      # {key, text, level, kind: front|body}
        self.figs: list[dict] = []
        self.tabs: list[dict] = []
        self.order: list[tuple[str, str]] = []   # body headings + captions in document order
        self.chapter = 0
        self.fig_n = 0
        self.tab_n = 0

    def section(self, page_numbers: str) -> None:
        self.sections.append({"pageNumbers": page_numbers, "blocks": []})

    def add(self, **b) -> None:
        self.sections[-1]["blocks"].append(b)

    # --- structure ---------------------------------------------------------
    def front_heading(self, title: str, toc=True) -> None:
        self.add(t="h", level=1, text=title.upper(), center=True, newPage=True)
        if toc:
            self.toc.append({"key": title.upper(), "text": title, "level": 1, "kind": "front", "plain": True})

    def chapter_heading(self, title: str, toc_title: str | None = None) -> None:
        self.chapter += 1
        self.fig_n = self.tab_n = 0
        text = f"CHAPTER {self.chapter}: {title.upper()}"
        self.add(t="h", level=1, text=text, newPage=True)
        self.toc.append({"key": text, "text": f"{self.chapter}  {toc_title or title}", "level": 1, "kind": "body"})
        self.order.append(("toc", text))

    def unnumbered_heading(self, title: str) -> None:
        self.add(t="h", level=1, text=title.upper(), newPage=True)
        self.toc.append({"key": title.upper(), "text": title, "level": 1, "kind": "body"})
        self.order.append(("toc", title.upper()))

    def h2(self, num: str, title: str) -> None:
        text = f"{num} {title}"
        self.add(t="h", level=2, text=text)
        self.toc.append({"key": text, "text": text, "level": 2, "kind": "body"})
        self.order.append(("toc", text))

    def h3(self, num: str, title: str, toc=False) -> None:
        text = f"{num} {title}"
        self.add(t="h", level=3, text=text)
        if toc:
            self.toc.append({"key": text, "text": text, "level": 3, "kind": "body"})
            self.order.append(("toc", text))

    # --- content -----------------------------------------------------------
    def p(self, *texts: str, **kw) -> None:
        for t in texts:
            self.add(t="p", text=t, **kw)

    def bullets(self, items) -> None:
        self.add(t="bullets", items=list(items))

    def numbers(self, items, ref: str) -> None:
        self.add(t="numbers", items=list(items), ref=ref)

    def figure(self, path: Path, caption: str, width: float = 6.0, max_height: float = 7.6) -> str:
        self.fig_n += 1
        num = f"{self.chapter}.{self.fig_n}" if self.chapter else str(len(self.figs) + 1)
        cap = f"Figure {num}: {caption}"
        self.add(t="figure", path=str(path), caption=cap, width=width, maxHeight=max_height)
        self.figs.append({"key": f"Figure {num}:", "text": cap})
        if self.chapter:
            self.order.append(("fig", f"Figure {num}:"))
        return f"Figure {num}"

    def table(self, caption: str, header, rows, widths=None, align=None, small=False) -> str:
        self.tab_n += 1
        num = f"{self.chapter}.{self.tab_n}" if self.chapter else str(len(self.tabs) + 1)
        cap = f"Table {num}: {caption}"
        self.add(t="table", caption=cap, header=list(header), rows=[[str(c) for c in r] for r in rows],
                 widths=widths, align=align, small=small)
        self.tabs.append({"key": f"Table {num}:", "text": cap})
        if self.chapter:
            self.order.append(("tab", f"Table {num}:"))
        return f"Table {num}"

    def code(self, lines: str, caption: str | None = None) -> None:
        self.add(t="code", lines=lines.strip("\n").split("\n"), caption=caption)

    def next_fig(self) -> str:
        return f"Figure {self.chapter}.{self.fig_n + 1}"

    def next_tab(self) -> str:
        return f"Table {self.chapter}.{self.tab_n + 1}"


# ------------------------------------------------------------------------ facts
def _rows(name):
    with open(RES / name) as fh:
        return list(csv.DictReader(fh))


def _pytest_summary() -> dict:
    xml = RES / "pytest.xml"
    if not xml.exists():
        subprocess.run([str(ROOT / "app/backend/.venv/bin/python"), "-m", "pytest", "-q", "-p", "no:warnings",
                        f"--junitxml={xml}", "tests"], cwd=ROOT / "app/backend", capture_output=True)
    root = ET.parse(xml).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    per_file: dict[str, int] = {}
    for tc in suite.iter("testcase"):
        f = tc.get("classname", "").split(".")[-1]
        per_file[f] = per_file.get(f, 0) + 1
    return {"tests": int(suite.get("tests")), "failures": int(suite.get("failures")), "errors": int(suite.get("errors")),
            "skipped": int(suite.get("skipped", 0)), "time": float(suite.get("time")), "per_file": per_file}


def facts() -> dict:
    F: dict = {}
    r = _rows("results.csv")
    ok = [x for x in r if x["success"] == "True"]
    F["runs"], F["ok_runs"] = len(r), len(ok)
    F["cap_fail"] = [x for x in r if x["note"]]
    F["images"] = len({x["image"] for x in r})
    man = _rows("../manifest.csv") if (RES / "../manifest.csv").exists() else []
    F["manifest"] = man
    F["by_source"] = {s: sum(1 for m in man if m["source"].startswith(s)) for s in ("Kodak", "USC-SIPI", "Generated")}
    pay = {}
    for p in ("100B", "1KB", "10KB", "PDF", "50KB"):
        s = [x for x in ok if x["payload"] == p]
        f = lambda k: [float(x[k]) for x in s]  # noqa: E731
        pay[p] = {"n": len(s), "bytes": int(s[0]["payload_bytes"]), "psnr_mean": st.mean(f("psnr_db")), "psnr_min": min(f("psnr_db")),
                  "psnr_max": max(f("psnr_db")), "ssim_mean": st.mean(f("ssim")), "ssim_min": min(f("ssim")),
                  "mse_mean": st.mean(f("mse")), "util_mean": st.mean(f("utilization_pct")), "util_max": max(f("utilization_pct")),
                  "embed_med": st.median(f("embed_ms")), "extract_med": st.median(f("extract_ms")),
                  "changed_mean": st.mean(f("changed_pixels_pct"))}
    F["pay"] = pay
    F["min_psnr_all"] = min(float(x["psnr_db"]) for x in ok)
    F["min_ssim_all"] = min(float(x["ssim"]) for x in ok)
    kod = [x for x in ok if x["source"] == "Kodak PhotoCD" and x["payload"] == "10KB"]
    F["kodak10_embed"] = st.median(float(x["embed_ms"]) for x in kod)
    F["kodak10_extract"] = st.median(float(x["extract_ms"]) for x in kod)
    hd = [x for x in ok if x["resolution"] == "1920x1080" and x["payload"] == "10KB"][0]
    F["hd_embed"], F["hd_extract"] = float(hd["embed_ms"]), float(hd["extract_ms"])
    F["per_image_10k"] = [x for x in ok if x["payload"] == "10KB"]
    F["results_rows"] = r

    sa = _rows("steganalysis_results.csv")
    F["stega"] = {f: {"seq": st.mean(float(x["sequential_flagged_pct"]) for x in sa if x["fill_pct"] == f),
                      "rnd": st.mean(float(x["random_flagged_pct"]) for x in sa if x["fill_pct"] == f),
                      "seq_p": st.mean(float(x["sequential_mean_p"]) for x in sa if x["fill_pct"] == f),
                      "rnd_p": st.mean(float(x["random_mean_p"]) for x in sa if x["fill_pct"] == f),
                      "rnd_any": sum(x["random_any_flag"] == "True" for x in sa if x["fill_pct"] == f),
                      "clean": st.mean(float(x["clean_flagged_pct"]) for x in sa if x["fill_pct"] == f),
                      "n": sum(1 for x in sa if x["fill_pct"] == f)}
                  for f in ("10", "25", "50", "100")}
    rob = _rows("robustness_results.csv")
    ops = []
    for x in rob:
        if x["operation"] not in ops:
            ops.append(x["operation"])
    F["robust"] = [(o, sum(x["extracted"] == "True" for x in rob if x["operation"] == o),
                    sum(1 for x in rob if x["operation"] == o),
                    next((x["error"] for x in rob if x["operation"] == o and x["error"]), "")) for o in ops]
    F["face"] = json.loads((RES / "face_summary.json").read_text())
    F["farfrr"] = _rows("face_far_frr.csv")
    lv = _rows("liveness_results.csv")
    sc = []
    for x in lv:
        if x["scenario"] not in sc:
            sc.append(x["scenario"])
    F["live"] = [(s, sum(1 for x in lv if x["scenario"] == s), sum(x["correct"] == "True" for x in lv if x["scenario"] == s),
                  sorted({x["reason"] for x in lv if x["scenario"] == s})) for s in sc]
    F["live_summary"] = json.loads((RES / "liveness_summary.json").read_text())
    F["ui"] = json.loads((RES / "ui_e2e_results.json").read_text())
    F["machine"] = json.loads((RES / "machine.json").read_text())
    F["pytest"] = _pytest_summary()
    return F


# ---------------------------------------------------------------------- render
def _render(spec: dict, out_docx: Path) -> Path:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(spec, fh)
        sp = fh.name
    subprocess.run(["node", str(TOOLS / "render_docx.js"), sp, str(out_docx)], check=True, cwd=TOOLS,
                   capture_output=True)
    _fix_package(out_docx)
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["soffice", f"-env:UserInstallation=file://{tmp}/profile", "--headless", "--convert-to", "pdf",
                    "--outdir", str(out_docx.parent), str(out_docx)], check=True, capture_output=True, timeout=300)
    shutil.rmtree(tmp, ignore_errors=True)
    return out_docx.with_suffix(".pdf")


def _fix_package(docx: Path) -> None:
    """docx 9.0.2 writes word/fontTable.xml without a relationship; reference it (and drop folder entries)."""
    import zipfile
    zin = zipfile.ZipFile(docx)
    items = {i.filename: zin.read(i.filename) for i in zin.infolist() if not i.filename.endswith("/")}
    zin.close()
    rels = items["word/_rels/document.xml.rels"].decode()
    if "word/fontTable.xml" in items and "fontTable.xml" not in rels:
        rels = rels.replace("</Relationships>", '<Relationship Id="rIdFontTable1" Type="http://schemas.openxmlformats.org/'
                            'officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/></Relationships>')
        items["word/_rels/document.xml.rels"] = rels.encode()
    ct = items["[Content_Types].xml"].decode()
    if "/word/fontTable.xml" not in ct:
        ct = ct.replace("</Types>", '<Override PartName="/word/fontTable.xml" ContentType="application/'
                        'vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/></Types>')
        items["[Content_Types].xml"] = ct.encode()
    with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", items.pop("[Content_Types].xml"))
        for n, data in items.items():
            z.writestr(n, data)


def _pages(pdf: Path) -> list[str]:
    txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    return [re.sub(r"\s+", " ", p) for p in txt.split("\f")]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def build(doc: Doc, make_lists, spec_base: dict, out_docx: Path, max_iter: int = 4) -> dict:
    """make_lists(pages) inserts TOC/LOF/LOT blocks given {key: page_label}; returns final page map."""
    pages_map: dict[str, str] = {}
    prev = None
    pdf = None
    for _ in range(max_iter):
        spec = dict(spec_base, sections=make_lists(pages_map))
        pdf = _render(spec, out_docx)
        pages = _pages(pdf)
        # locate body start: first page containing the first body TOC key
        front_keys = [e for e in doc.toc if e["kind"] == "front"]
        ptr = 1
        new: dict[str, str] = {}
        for e in front_keys:
            k = _norm(e["key"])
            while ptr < len(pages) and k not in pages[ptr]:
                ptr += 1
            new[e["key"]] = roman(ptr) if ptr < len(pages) else "?"
        start = None
        # body entries in document order interleaved with figure/table captions
        order = doc.order
        for kind, key in order:
            k = _norm(key)
            while ptr < len(pages) and k not in pages[ptr]:
                ptr += 1
            if ptr >= len(pages):
                new[key] = "?"
                ptr = len(pages) - 1
                continue
            if start is None:
                start = ptr
            new[key] = str(ptr - start + 1)
        pages_map = new
        if new == prev:
            break
        prev = new
    return {"pages": pages_map, "pdf": pdf, "n_pages": len(_pages(pdf))}
