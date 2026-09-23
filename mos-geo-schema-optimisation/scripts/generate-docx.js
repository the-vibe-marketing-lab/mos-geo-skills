#!/usr/bin/env node
// mos-geo-schema-optimisation: renders the schema optimisation brief as a
// landscape A4 DOCX from brief-data.json.
//
//   node generate-docx.js --data <brief-data.json> --out <folder>
//
// Defaults: --data ./brief-data.json, --out the current folder. Never writes
// into the skill folder unless you run it from there. If the output file
// already exists, " - v2", " - v3" ... is appended so nothing is overwritten.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, BorderStyle, ShadingType, HeadingLevel,
  PageOrientation, Footer,
  CommentRangeStart, CommentRangeEnd, CommentReference,
} = require("docx");

// ------- ARGS -------
function parseArgs(argv) {
  const args = { data: "brief-data.json", out: "." };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--data") args.data = argv[++i];
    else if (a === "--out") args.out = argv[++i];
    else if (a === "--help" || a === "-h") {
      console.log("Usage: node generate-docx.js --data <brief-data.json> --out <folder>\n" +
        "Defaults: --data ./brief-data.json, --out current folder. Existing files get ' - v2', ' - v3' ...");
      process.exit(0);
    } else {
      console.error(`Unknown argument: ${a}`);
      process.exit(2);
    }
  }
  if (!args.data || !args.out) {
    console.error("--data and --out need a value");
    process.exit(2);
  }
  return { data: path.resolve(args.data), out: path.resolve(args.out) };
}

const ARGS = parseArgs(process.argv);
if (!fs.existsSync(ARGS.data)) {
  console.error(`brief data not found: ${ARGS.data}`);
  process.exit(1);
}
const data = JSON.parse(fs.readFileSync(ARGS.data, "utf8"));
data.client = data.client || {};

// ------- COLOURS: MarketingOS Ember, paper (print) variant -------
// Ember is a dark web identity; this is its paper variant for print and
// documents. Ink on Ember is the AA pairing for the section banners.
const C = {
  ink: "0D0B0A",           // headings, code text, table header fill
  paper: "FAF7F2",         // label gutter, audit first column, header text
  ember: "C96442",         // the one accent: H1 banners, [Placeholder] tokens
  sun: "F4C24B",           // status highlight only: Not set, [REVIEW:]
  body: "2A2320",          // body copy
  muted: "5E544D",         // secondary text
  tableBorder: "D9D2C8",   // light neutral borders

  heading: "0D0B0A",
  subheading: "0D0B0A",
  tableHeaderBg: "0D0B0A",
  tableHeaderText: "FAF7F2",
  bannerBg: "C96442",
  bannerText: "0D0B0A",
  codeText: "0D0B0A",
  labelCellBg: "FAF7F2",
  placeholder: "C96442",
  flagBg: "F4C24B",
  flagText: "0D0B0A",
};

// Fonts: Bricolage Grotesque for display (cover title, H1, H2), Figtree for
// body. Ember has no monospace face, so JSON-LD uses Roboto Mono 9pt, which
// also renders in Google Docs.
const DISPLAY_FONT = "Bricolage Grotesque";
const BODY_FONT = "Figtree";
const CODE_FONT = "Roboto Mono";
const CODE_SIZE = 18; // 9pt

// ------- LANDSCAPE A4 DIMENSIONS -------
// Usable width after 1" margins in landscape A4 = 13958 DXA
const TOTAL_TABLE_WIDTH = 13950;
// 4-column schema table: Label | Current | Template | Recommended
const COL_LABEL = 1800;
const COL_CURRENT = 2700;
const COL_TEMPLATE = 4725;
const COL_RECOMMENDED = 4725;

// ------- COMMENT REGISTRY -------
// Comments are collected during cell rendering and passed to Document.comments.
const comments = [];
let nextCommentId = 0;
function initialsOf(name) {
  const words = String(name || "").split(/[^A-Za-z0-9]+/).filter(Boolean);
  if (!words.length) return "MO";
  return words.slice(0, 3).map(w => w[0].toUpperCase()).join("");
}
const COMMENT_AUTHOR = data.commentAuthor || data.client.preparedBy || "MarketingOS";
const COMMENT_INITIALS = data.commentInitials || initialsOf(COMMENT_AUTHOR);

// The docx library's Comments class wraps each child in new Comment(child),
// so we register raw option objects here, not constructed Comment instances.
function registerComment(text) {
  const id = nextCommentId++;
  comments.push({
    id,
    author: COMMENT_AUTHOR,
    initials: COMMENT_INITIALS,
    date: new Date(),
    children: [new Paragraph({
      children: [new TextRun({ text, font: BODY_FONT, size: 20, color: C.body })],
    })],
  });
  return id;
}

// ------- BORDER HELPERS -------
const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: C.tableBorder };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

// ------- HEADING / TEXT HELPERS -------
// H1 = Ember section banner (Ink text on Ember shading, the AA pairing).
function h1(text, pageBreakBefore = true) {
  return new Paragraph({
    children: [new TextRun({
      text: ` ${text} `,
      bold: true,
      font: DISPLAY_FONT,
      size: 46,
      color: C.bannerText,
      shading: { type: ShadingType.CLEAR, fill: C.bannerBg, color: "auto" },
    })],
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 280, after: 200 },
    pageBreakBefore,
  });
}

// H2 = ink subheading.
function h2(text) {
  return new Paragraph({
    children: [new TextRun({ text, bold: true, font: DISPLAY_FONT, size: 34, color: C.heading })],
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120 },
  });
}

function bodyText(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({
      text,
      font: BODY_FONT,
      size: 20,
      color: opts.color || C.body,
      italics: opts.italics || false,
      bold: opts.bold || false,
    })],
    spacing: { after: 100 },
  });
}

function bulletPoint(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({
      text,
      font: BODY_FONT,
      size: 20,
      color: opts.color || C.body,
      bold: opts.bold || false,
    })],
    bullet: { level: 0 },
    spacing: { before: 40, after: 40 },
  });
}

// ------- INLINE TOKEN PARSING -------
// Modes for codeLineParagraph:
//   "current"     → plain monospace
//   "template"    → [Placeholder] tokens render italic Ember
//   "recommended" → {{COMMENT:text}}anchor{{/COMMENT}} → real Word comments; [REVIEW:] gets a Sun highlight

// Tokenize a substring using a single regex, returning tokens of given type
// for matches and plain "text" tokens for the gaps.
function tokenizeWithRegex(line, regex, makeMatchToken) {
  const tokens = [];
  let lastIdx = 0;
  let m;
  while ((m = regex.exec(line)) !== null) {
    if (m.index > lastIdx) {
      tokens.push({ type: "text", text: line.slice(lastIdx, m.index) });
    }
    const tok = makeMatchToken(m);
    if (tok) tokens.push(tok);
    else tokens.push({ type: "text", text: m[0] });
    lastIdx = m.index + m[0].length;
  }
  if (lastIdx < line.length) {
    tokens.push({ type: "text", text: line.slice(lastIdx) });
  }
  return tokens.length ? tokens : [{ type: "text", text: line || " " }];
}

function tokenizeLine(line, mode) {
  if (!line) return [{ type: "text", text: " " }];

  if (mode === "recommended") {
    // {{COMMENT:text}}anchor{{/COMMENT}} → real Word comments
    // Also still honour [REVIEW:...] in the gaps so we have an inline TBD fallback
    const commentRe = /\{\{COMMENT:([\s\S]*?)\}\}([\s\S]*?)\{\{\/COMMENT\}\}/g;
    const passOne = tokenizeWithRegex(line, commentRe, m => ({
      type: "comment",
      commentText: m[1].trim(),
      anchor: m[2],
    }));
    // For each text-token in passOne, run a [REVIEW:] pass
    const result = [];
    for (const t of passOne) {
      if (t.type !== "text") { result.push(t); continue; }
      const reviewRe = /(\[REVIEW:[^\]]*\])/g;
      result.push(...tokenizeWithRegex(t.text, reviewRe, m => ({ type: "review", text: m[0] })));
    }
    return result;
  }

  if (mode === "template") {
    // [Placeholder] tokens in the template column render as italic Ember.
    // Skip [REVIEW:...]: templates shouldn't carry TBD notes.
    const placeholderRe = /(\[[A-Za-z][^\]\n]*\])/g;
    return tokenizeWithRegex(line, placeholderRe, m => {
      if (/^\[REVIEW:/i.test(m[0])) return null; // ignore review markers in template
      return { type: "placeholder", text: m[0] };
    });
  }

  // Default ("current" or anything else): only [REVIEW:...] gets highlighted.
  const reviewRe = /(\[REVIEW:[^\]]*\])/g;
  return tokenizeWithRegex(line, reviewRe, m => ({ type: "review", text: m[0] }));
}

function codeLineParagraph(line, mode = "current") {
  const tokens = tokenizeLine(line, mode);
  const children = [];

  for (const tok of tokens) {
    if (tok.type === "text") {
      children.push(new TextRun({
        text: tok.text || " ",
        font: CODE_FONT,
        size: CODE_SIZE,
        color: C.codeText,
      }));
    } else if (tok.type === "review") {
      children.push(new TextRun({
        text: tok.text,
        font: CODE_FONT,
        size: CODE_SIZE,
        color: C.flagText,
        bold: true,
        shading: { type: ShadingType.CLEAR, fill: C.flagBg, color: "auto" },
      }));
    } else if (tok.type === "placeholder") {
      children.push(new TextRun({
        text: tok.text,
        font: CODE_FONT,
        size: CODE_SIZE,
        color: C.placeholder,
        italics: true,
      }));
    } else if (tok.type === "comment") {
      const id = registerComment(tok.commentText);
      children.push(new CommentRangeStart(id));
      children.push(new TextRun({
        text: tok.anchor,
        font: CODE_FONT,
        size: CODE_SIZE,
        color: C.codeText,
        highlight: "yellow",
      }));
      children.push(new CommentRangeEnd(id));
      children.push(new TextRun({
        children: [new CommentReference(id)],
      }));
    }
  }

  return new Paragraph({
    children,
    spacing: { before: 0, after: 0 },
  });
}

// Accept either a string (raw) or an object (JSON-stringify on the fly).
function normalizeSchemaContent(content) {
  if (content === null || content === undefined || content === "") return null;
  if (typeof content === "string") return content;
  try {
    return JSON.stringify(content, null, 2);
  } catch {
    return String(content);
  }
}

// ------- TABLE CELLS -------
function labelCell(row, width) {
  const children = [
    new Paragraph({
      children: [new TextRun({
        text: row.label || "",
        bold: true,
        font: BODY_FONT,
        size: 20,
        color: C.subheading,
      })],
      spacing: { before: 60, after: 40 },
    }),
  ];
  if (row.examplePage) {
    children.push(new Paragraph({
      children: [new TextRun({
        text: "Example: ",
        font: BODY_FONT,
        size: 16,
        color: C.muted,
      }), new TextRun({
        text: row.examplePage,
        font: BODY_FONT,
        size: 16,
        color: C.muted,
        italics: true,
      })],
      spacing: { before: 0, after: 60 },
    }));
  }
  return new TableCell({
    children,
    width: { size: width, type: WidthType.DXA },
    borders: cellBorders,
    shading: { type: ShadingType.CLEAR, fill: C.labelCellBg },
    margins: { top: 100, bottom: 100, left: 140, right: 140 },
  });
}

function codeCell(content, width, mode = "current") {
  const normalized = normalizeSchemaContent(content);
  let paragraphs;
  if (normalized === null || /^not\s*set$/i.test(normalized.trim())) {
    paragraphs = [new Paragraph({
      children: [new TextRun({
        text: "Not set",
        font: BODY_FONT,
        size: 20,
        color: C.flagText,
        bold: true,
        italics: true,
        shading: { type: ShadingType.CLEAR, fill: C.flagBg, color: "auto" },
      })],
    })];
  } else {
    paragraphs = normalized.split(/\r?\n/).map(line => codeLineParagraph(line, mode));
  }
  return new TableCell({
    children: paragraphs,
    width: { size: width, type: WidthType.DXA },
    borders: cellBorders,
    // JSON-LD code columns sit on a plain white background.
    margins: { top: 160, bottom: 160, left: 200, right: 200 },
  });
}

function headerCell(text, width) {
  return new TableCell({
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, font: BODY_FONT, size: 22, color: C.tableHeaderText })],
      spacing: { before: 60, after: 60 },
    })],
    width: { size: width, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: C.tableHeaderBg },
    borders: cellBorders,
    margins: { top: 100, bottom: 100, left: 140, right: 140 },
  });
}

// Plain text data cell for audit tables
function textCell(text, width, opts = {}) {
  const cell = {
    children: [new Paragraph({
      children: [new TextRun({
        text: text == null ? "" : String(text),
        font: BODY_FONT,
        size: 20,
        color: opts.color || C.body,
        bold: opts.bold || false,
      })],
      spacing: { before: 40, after: 40 },
    })],
    width: { size: width, type: WidthType.DXA },
    borders: cellBorders,
    margins: { top: 80, bottom: 80, left: 140, right: 140 },
  };
  if (opts.fill) cell.shading = { type: ShadingType.CLEAR, fill: opts.fill };
  return new TableCell(cell);
}

// Build a simple header + rows table (DXA widths, full styling)
function buildAuditTable(headerTexts, rows, colWidths) {
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);
  const headerRow = new TableRow({
    tableHeader: true,
    children: headerTexts.map((t, i) => headerCell(t, colWidths[i])),
  });
  const dataRows = rows.map(row => new TableRow({
    children: row.map((cell, i) => textCell(cell, colWidths[i], {
      fill: i === 0 ? C.labelCellBg : undefined,
      bold: i === 0,
    })),
  }));
  return new Table({
    rows: [headerRow, ...dataRows],
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: colWidths,
  });
}

// ------- BUILD DOCUMENT -------
const children = [];

// ===== COVER PAGE =====
const coverLine = (text, size, color, after, opts = {}) => new Paragraph({
  children: [new TextRun({ text, font: opts.font || BODY_FONT, size, color, bold: opts.bold || false })],
  alignment: AlignmentType.CENTER,
  spacing: { after },
});
children.push(
  new Paragraph({ spacing: { before: 2400 } }),
  coverLine("Schema markup", 56, C.heading, 0, { font: DISPLAY_FONT, bold: true }),
  coverLine("optimisation brief", 56, C.heading, 200, { font: DISPLAY_FONT, bold: true }),
  // Ember rule: the one ornament
  new Paragraph({
    children: [new TextRun({ text: "\u00A0".repeat(14), size: 8, shading: { type: ShadingType.CLEAR, fill: C.ember, color: "auto" } })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 400 },
  }),
  coverLine(data.client.name || "", 36, C.subheading, 160),
  coverLine(data.client.url || "", 24, C.muted, 600),
);
if (data.client.preparedBy) children.push(coverLine(`Prepared by ${data.client.preparedBy}`, 22, C.muted, 0));
if (data.client.date) children.push(coverLine(data.client.date, 22, C.muted, 0));
children.push(coverLine("Built with MarketingOS", 16, C.muted, 0));

// ===== EXECUTIVE SUMMARY =====
if (data.executiveSummary && data.executiveSummary.length) {
  children.push(h1("Executive summary"));
  data.executiveSummary.forEach(para => children.push(bodyText(para)));
}

// ===== CURRENT STATE =====
const hasCrawlOverview = data.crawlOverview && Object.keys(data.crawlOverview).length;
const hasSchemaTypes = data.currentSchemaTypes && data.currentSchemaTypes.length;
const hasPageTemplates = data.pageTemplates && data.pageTemplates.length;

if (hasCrawlOverview || hasSchemaTypes || hasPageTemplates) {
  children.push(h1("Current state"));
}

if (hasCrawlOverview) {
  children.push(h2("Crawl overview"));
  const co = data.crawlOverview;
  const rows = [
    ["Total URLs Crawled", co.totalUrls],
    ["Indexable URLs", co.indexableUrls],
    ["Non-Indexable URLs", co.nonIndexableUrls],
    ["Pages with Schema Errors", co.pagesWithErrors],
    ["Pages with Schema Warnings", co.pagesWithWarnings],
    ["Rich Result Warnings", co.richResultWarnings],
    ["Rich Result Errors", co.richResultErrors],
    ["Pages Earning Rich Result Features", co.richResultFeaturesEarned],
    ["Unique Schema Types Found", co.uniqueSchemaTypes],
  ].filter(r => r[1] !== undefined && r[1] !== null);
  children.push(buildAuditTable(["Metric", "Value"], rows, [3000, 5000]));
  if (data.crawlOverviewAssessment) {
    children.push(new Paragraph({ spacing: { before: 120 } }));
    children.push(bodyText(data.crawlOverviewAssessment, { italics: true, color: C.muted }));
  }
}

if (hasSchemaTypes) {
  children.push(h2("Schema types currently deployed"));
  const rows = data.currentSchemaTypes.map(t => [t.type, t.pages, t.assessment]);
  children.push(buildAuditTable(
    ["Schema Type", "Pages", "Assessment"],
    rows,
    [2200, 1000, 8800],
  ));
}

if (hasPageTemplates) {
  children.push(h2("Page template breakdown"));
  const rows = data.pageTemplates.map(t => [t.template, t.pages, t.currentSchema, t.contentType]);
  children.push(buildAuditTable(
    ["Template", "Pages", "Current Schema", "Content Type"],
    rows,
    [2200, 900, 3500, 4400],
  ));
}

// ===== SCHEMA RECOMMENDATIONS TABLE (4 columns) =====
children.push(h1("Schema recommendations"));
children.push(bodyText("Template column uses [Placeholder] markers for fields the dev populates from the CMS. Recommended column shows the same schema filled in with the brand's real data. Yellow-highlighted values are anchored to margin comments the strategist should verify before delivery.", { italics: true, color: C.muted }));

const tableRows = [];
tableRows.push(new TableRow({
  tableHeader: true,
  children: [
    headerCell("Page / Schema Type", COL_LABEL),
    headerCell("Schema Implemented Currently", COL_CURRENT),
    headerCell("Schema Template Recommendation", COL_TEMPLATE),
    headerCell("Schema Recommendation / Example", COL_RECOMMENDED),
  ],
}));

(data.schemaRows || []).forEach(row => {
  tableRows.push(new TableRow({
    children: [
      labelCell(row, COL_LABEL),
      codeCell(row.current, COL_CURRENT, "current"),
      codeCell(row.template, COL_TEMPLATE, "template"),
      codeCell(row.recommended, COL_RECOMMENDED, "recommended"),
    ],
  }));
});

children.push(new Table({
  rows: tableRows,
  width: { size: TOTAL_TABLE_WIDTH, type: WidthType.DXA },
  columnWidths: [COL_LABEL, COL_CURRENT, COL_TEMPLATE, COL_RECOMMENDED],
}));

// ===== FOOTER NOTES =====
if (data.footerNotes && data.footerNotes.length) {
  children.push(h1("Notes"));
  data.footerNotes.forEach(note => children.push(bulletPoint(note)));
}

// ===== ASSEMBLE DOCUMENT (LANDSCAPE) =====
// NOTE: docx v9 swaps width/height when orientation=LANDSCAPE.
// Pass the *portrait* values here: the library outputs w:w=16838, w:h=11906,
// the wide-page representation Google Docs and Word both honour. Passing
// pre-swapped values renders portrait in Google Docs with content overflow.
const footerText = [data.client.name, "Schema optimisation brief", "Built with MarketingOS"].filter(Boolean).join("  \u00B7  ");
const doc = new Document({
  comments: { children: comments },
  sections: [{
    properties: {
      page: {
        size: {
          width: 11906,
          height: 16838,
          orientation: PageOrientation.LANDSCAPE,
        },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [new TextRun({ text: footerText, font: BODY_FONT, size: 16, color: C.muted })],
          alignment: AlignmentType.RIGHT,
        })],
      }),
    },
    children,
  }],
});

// ------- OUTPUT PATH (auto-version, never overwrite) -------
function versionedPath(dir, filename) {
  const ext = path.extname(filename) || ".docx";
  const stem = path.basename(filename, path.extname(filename));
  let candidate = path.join(dir, stem + ext);
  for (let v = 2; fs.existsSync(candidate); v++) {
    candidate = path.join(dir, `${stem} - v${v}${ext}`);
  }
  return candidate;
}

const today = new Date();
const pad = n => String(n).padStart(2, "0");
const defaultName = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}-schema-optimisation-brief.docx`;
const requested = path.basename(data.outputFilename || defaultName);
fs.mkdirSync(ARGS.out, { recursive: true });
const outputPath = versionedPath(ARGS.out, requested.endsWith(".docx") ? requested : `${requested}.docx`);

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log("DOCX generated:", outputPath);
}).catch(err => {
  console.error("Error generating DOCX:", err);
  process.exit(1);
});
