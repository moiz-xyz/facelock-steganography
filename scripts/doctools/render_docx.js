/**
 * Generic academic DOCX renderer.
 *   node render_docx.js spec.json out.docx
 *
 * spec = { title, header, font, size, sections: [ { pageNumbers: "none"|"roman"|"decimal", blocks: [...] } ] }
 * block types: h, p, bullets, numbers, table, figure, code, pagebreak, toc, spacer, center
 * Inline markup in text: **bold**, *italic*, `code`.
 */
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, LineRuleType, TabStopType, LeaderType, Document, Footer, Header, HeadingLevel, ImageRun, LevelFormat, NumberFormat, Packer,
  PageBreak, PageNumber, Paragraph, PositionalTab, PositionalTabAlignment, PositionalTabLeader,
  PositionalTabRelativeTo, ShadingType, Table, TableCell, TableRow, TextRun, VerticalAlign, WidthType,
} = require("docx");

const [, , specPath, outPath] = process.argv;
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const FONT = spec.font || "Times New Roman";
const SIZE = (spec.size || 12) * 2;
const MONO = "Courier New";
// A4 with 1.5" binding margin on the left, 1" elsewhere
const PAGE = { width: 11906, height: 16838 };
const MARGIN = { top: 1440, bottom: 1440, left: 2160, right: 1440 };
const TEXT_W = PAGE.width - MARGIN.left - MARGIN.right; // DXA
const TEXT_W_IN = TEXT_W / 1440;

function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0;
  let m;
  const s = String(text);
  while ((m = re.exec(s))) {
    if (m.index > last) out.push(new TextRun({ text: s.slice(last, m.index), ...base }));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(new TextRun({ text: tok.slice(2, -2), bold: true, ...base }));
    else if (tok.startsWith("`")) out.push(new TextRun({ text: tok.slice(1, -1), font: MONO, size: Math.round(SIZE * 0.85), ...base }));
    else out.push(new TextRun({ text: tok.slice(1, -1), italics: true, ...base }));
    last = m.index + tok.length;
  }
  if (last < s.length) out.push(new TextRun({ text: s.slice(last), ...base }));
  return out;
}

const HEAD = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 };

function cellPara(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    spacing: { before: 40, after: 40, line: 260, lineRule: LineRuleType.AUTO },
    children: runs(text, { size: opts.size || 20, bold: opts.bold, font: FONT }),
  });
}

function table(b) {
  const n = b.header.length;
  const fr = b.widths || Array(n).fill(1 / n);
  const sum = fr.reduce((a, c) => a + c, 0);
  const widths = fr.map((f) => Math.floor((TEXT_W * f) / sum));
  widths[widths.length - 1] = TEXT_W - widths.slice(0, -1).reduce((a, c) => a + c, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const size = b.small ? 18 : 20;
  const mk = (cells, head, i) => new TableRow({
    tableHeader: head,
    cantSplit: true,
    children: cells.map((c, j) => new TableCell({
      width: { size: widths[j], type: WidthType.DXA },
      borders,
      verticalAlign: VerticalAlign.CENTER,
      margins: { top: 40, bottom: 40, left: 90, right: 90 },
      shading: head ? { type: ShadingType.CLEAR, fill: "D9E2F3", color: "auto" } : (i % 2 ? { type: ShadingType.CLEAR, fill: "F5F7FB", color: "auto" } : undefined),
      children: [cellPara(c, { bold: head, size, align: (b.align && b.align[j] === "r") ? AlignmentType.RIGHT : (b.align && b.align[j] === "c") ? AlignmentType.CENTER : AlignmentType.LEFT })],
    })),
  });
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA },
    columnWidths: widths,
    rows: [mk(b.header, true, 0), ...b.rows.map((r, i) => mk(r.map(String), false, i))],
  });
}

function caption(text, keepNext) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    keepNext: !!keepNext,
    spacing: { before: keepNext ? 200 : 100, after: keepNext ? 100 : 240, line: 276, lineRule: LineRuleType.AUTO },
    children: runs(text, { size: 20, bold: false, italics: false }).map((r) => r),
  });
}

function figure(b) {
  const buf = fs.readFileSync(b.path);
  // PNG size from IHDR
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  let wi = Math.min(b.width || TEXT_W_IN, TEXT_W_IN);
  let hi = (wi * h) / w;
  const maxH = b.maxHeight || 7.6;
  if (hi > maxH) { hi = maxH; wi = (hi * w) / h; }
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 160, after: 60, line: 240, lineRule: LineRuleType.AUTO },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: Math.round(wi * 96), height: Math.round(hi * 96) },
        altText: { title: b.caption || "figure", description: b.caption || "figure", name: path.basename(b.path) } })],
    }),
    caption(b.caption, false),
  ];
}

function code(b) {
  const out = [];
  if (b.caption) out.push(caption(b.caption, true));
  b.lines.forEach((ln, i) => out.push(new Paragraph({
    keepLines: true, keepNext: i < b.lines.length - 1,
    shading: { type: ShadingType.CLEAR, fill: "F3F4F6", color: "auto" },
    spacing: { before: i === 0 ? 80 : 0, after: i === b.lines.length - 1 ? 200 : 0, line: 240, lineRule: LineRuleType.AUTO },
    indent: { left: 120, right: 120 },
    children: [new TextRun({ text: ln.length ? ln : " ", font: MONO, size: 17 })],
  })));
  return out;
}

function tocLine(e) {
  return new Paragraph({
    spacing: { before: e.level === 1 ? 100 : 0, after: 30, line: 276, lineRule: LineRuleType.AUTO },
    indent: { left: (e.level - 1) * 400 },
    tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W, leader: LeaderType.DOT }],
    children: [new TextRun({ text: e.text, bold: e.level === 1 && !e.plain }), new TextRun({ text: "\t" + String(e.page) })],
  });
}

function block(b) {
  switch (b.t) {
    case "h":
      return [new Paragraph({ heading: HEAD[b.level], pageBreakBefore: !!b.newPage, alignment: b.center ? AlignmentType.CENTER : AlignmentType.LEFT,
        children: runs(b.text) })];
    case "p":
      return [new Paragraph({
        alignment: b.align === "center" ? AlignmentType.CENTER : b.align === "left" ? AlignmentType.LEFT : b.align === "right" ? AlignmentType.RIGHT : AlignmentType.JUSTIFIED,
        spacing: { before: b.before ?? 0, after: b.after ?? 160, line: b.line ?? 360, lineRule: LineRuleType.AUTO },
        keepNext: !!b.keepNext,
        children: runs(b.text, { size: b.size ? b.size * 2 : undefined, bold: b.bold, italics: b.italic }),
      })];
    case "center":
      return [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: b.before ?? 0, after: b.after ?? 120, line: 300, lineRule: LineRuleType.AUTO },
        children: runs(b.text, { size: (b.size || 12) * 2, bold: b.bold, italics: b.italic, color: b.color }) })];
    case "bullets":
    case "numbers":
      return b.items.map((it) => new Paragraph({
        numbering: { reference: b.t === "bullets" ? "bullets" : `num-${b.ref || "default"}`, level: 0 },
        alignment: AlignmentType.JUSTIFIED, spacing: { after: 80, line: 340, lineRule: LineRuleType.AUTO }, children: runs(it),
      }));
    case "table":
      return [caption(b.caption, true), table(b), new Paragraph({ spacing: { after: 120 }, children: [] })];
    case "figure":
      return figure(b);
    case "code":
      return code(b);
    case "pagebreak":
      return [new Paragraph({ children: [new PageBreak()] })];
    case "spacer":
      return [new Paragraph({ spacing: { before: (b.n || 1) * 240 }, children: [] })];
    case "toc":
      return b.entries.map(tocLine);
    default:
      throw new Error("unknown block " + b.t);
  }
}

// one numbering reference per numbered list so each restarts at 1
const numRefs = new Set(["default"]);
spec.sections.forEach((s) => s.blocks.forEach((b) => { if (b.t === "numbers" && b.ref) numRefs.add(b.ref); }));

const footer = (kind) => kind === "none" ? undefined : {
  default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] }),
};
const header = (kind) => (kind === "none" || !spec.header) ? undefined : {
  default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "A0A0A0", space: 4 } },
    children: [new TextRun({ text: spec.header, size: 18, italics: true, color: "555555" })] })] }),
};

const doc = new Document({
  creator: spec.author || "",
  title: spec.title,
  description: spec.title,
  styles: {
    default: { document: { run: { font: FONT, size: SIZE }, paragraph: { spacing: { line: 360, lineRule: LineRuleType.AUTO } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 32, bold: true, color: "1F2A44" }, paragraph: { spacing: { before: 240, after: 240, line: 300, lineRule: LineRuleType.AUTO }, keepNext: true, keepLines: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 28, bold: true, color: "1F2A44" }, paragraph: { spacing: { before: 280, after: 120, line: 300, lineRule: LineRuleType.AUTO }, keepNext: true, keepLines: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: "1F2A44" }, paragraph: { spacing: { before: 200, after: 80, line: 300, lineRule: LineRuleType.AUTO }, keepNext: true, keepLines: true, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
      ...[...numRefs].map((r) => ({ reference: `num-${r}`, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] })),
    ],
  },
  sections: spec.sections.map((s) => ({
    properties: {
      page: { size: PAGE, margin: MARGIN, pageNumbers: s.pageNumbers === "none" ? undefined : { start: 1, formatType: s.pageNumbers === "roman" ? NumberFormat.LOWER_ROMAN : NumberFormat.DECIMAL } },
    },
    headers: header(s.pageNumbers),
    footers: footer(s.pageNumbers),
    children: s.blocks.flatMap(block),
  })),
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log("wrote", outPath); });
