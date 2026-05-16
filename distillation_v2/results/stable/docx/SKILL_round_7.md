```markdown
---
name: docx
description: "Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include: any mention of 'Word doc', 'word document', '.docx', or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx files, inserting or replacing images in documents, performing find-and-replace in Word files, working with tracked changes or comments, or converting content into a polished Word document. If the user asks for a 'report', 'memo', 'letter', 'template', or similar deliverable as a Word or .docx file, use this skill. Do NOT use for PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation."
license: Proprietary. LICENSE.txt has complete terms
---

# DOCX creation, editing, and analysis

## Overview

A .docx file is a ZIP archive containing XML files.

## Quick Reference

| Task | Approach |
|------|----------|
| Read/analyze content | `pandoc` or unpack for raw XML |
| Create new document | Use `docx-js` - see Creating New Documents below |
| Edit existing document | Unpack → edit XML → repack - see Editing Existing Documents below |

### Converting .doc to .docx

Legacy `.doc` files must be converted before editing:

```bash
python scripts/office/soffice.py --headless --convert-to docx document.doc
```

### Reading Content

```bash
# Text extraction with tracked changes
pandoc --track-changes=all document.docx -o output.md

# Raw XML access
python scripts/office/unpack.py document.docx unpacked/
```

### Converting to Images

```bash
python scripts/office/soffice.py --headless --convert-to pdf document.docx
pdftoppm -jpeg -r 150 document.pdf page
```

### Accepting Tracked Changes

To produce a clean document with all tracked changes accepted (requires LibreOffice):

```bash
python scripts/accept_changes.py input.docx output.docx
```

---

## Creating New Documents

Generate .docx files with JavaScript, then validate. Install: `npm install -g docx`

### Minimal Working Template

Copy and adapt this template for most document tasks:

```javascript
const { Document, Packer, Paragraph, TextRun } = require('docx');
const fs = require('fs');

const doc = new Document({
  sections: [{
    properties: {
      page: {
        size: {
          width: 12240,   // US Letter: 8.5 inches
          height: 15840   // US Letter: 11 inches
        },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } // 1 inch margins
      }
    },
    children: [
      new Paragraph({ children: [new TextRun("Your content here")] })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("output.docx", buffer);
  console.log("Document created: output.docx");
}).catch(err => {
  console.error("Error creating document:", err);
  process.exit(1);
});
```

**Always run this template and verify the file exists before adding complexity.**

### Setup

```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
        Header, Footer, AlignmentType, PageOrientation, LevelFormat, ExternalHyperlink,
        InternalHyperlink, Bookmark, FootnoteReferenceRun, PositionalTab,
        PositionalTabAlignment, PositionalTabRelativeTo, PositionalTabLeader,
        TabStopType, TabStopPosition, Column, SectionType,
        TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
        VerticalAlign, PageNumber, PageBreak } = require('docx');

const doc = new Document({ sections: [{ children: [/* content */] }] });
Packer.toBuffer(doc).then(buffer => fs.writeFileSync("doc.docx", buffer));
```

### Validation

After creating the file, validate it. If validation fails, unpack, fix the XML, and repack.

```bash
python scripts/office/validate.py doc.docx
```

If validation fails, the file was not written. Check:
1. Does `output.docx` exist in the current directory? Use `ls -la output.docx` to verify.
2. Did `Packer.toBuffer()` complete without errors? Add error handling: `.catch(err => console.error(err))`
3. Is the JavaScript syntax valid? Run `node script.js` directly to see errors.

### Page Size

```javascript
// CRITICAL: docx-js defaults to A4, not US Letter
// Always set page size explicitly for consistent results
sections: [{
  properties: {
    page: {
      size: {
        width: 12240,   // 8.5 inches in DXA
        height: 15840   // 11 inches in DXA
      },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } // 1 inch margins
    }
  },
  children: [/* content */]
}]
```

**Common page sizes (DXA units, 1440 DXA = 1 inch):**

| Paper | Width | Height | Content Width (1" margins) |
|-------|-------|--------|---------------------------|
| US Letter | 12,240 | 15,840 | 9,360 |
| A4 (default) | 11,906 | 16,838 | 9,026 |

**Landscape orientation:** docx-js swaps width/height internally, so pass portrait dimensions and let it handle the swap:

```javascript
size: {
  width: 12240,   // Pass SHORT edge as width
  height: 15840,  // Pass LONG edge as height
  orientation: PageOrientation.LANDSCAPE  // docx-js swaps them in the XML
},
// Content width = 15840 - left margin - right margin (uses the long edge)
```

### Styles (Override Built-in Headings)

Use Arial as the default font (universally supported). Keep titles black for readability.

```javascript
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } }, // 12pt default
    paragraphStyles: [
      // IMPORTANT: Use exact IDs to override built-in styles
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } }, // outlineLevel required for TOC
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    children: [
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Title")] }),
    ]
  }]
});
```

### Lists (NEVER use unicode bullets)

**Bulleted lists:**

```javascript
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    children: [
      new Paragraph({ numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Bullet item 1")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Bullet item 2")] }),
    ]
  }]
});
```

**Numbered lists (independent):**

```javascript
const doc = new Document({
  numbering: {
    config: [
      { reference: "numbers1",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers2",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    children: [
      new Paragraph({ numbering: { reference: "numbers1", level: 0 },
        children: [new TextRun("Installation Step 1")] }),
      new Paragraph({ numbering: { reference: "numbers1", level: 0 },
        children: [new TextRun("Installation Step 2")] }),
      new Paragraph({ children: [new TextRun("")] }), // Blank line between lists
      new Paragraph({ numbering: { reference: "numbers2", level: 0 },
        children: [new TextRun("Configuration Step 1")] }),
      new Paragraph({ numbering: { reference: "numbers2", level: 0 },
        children: [new TextRun("Configuration Step 2")] }),
    ]
  }]
});
```

**Key rule:** Each `reference` creates independent numbering. Use different references for lists that should restart at 1. If lists share numbering, they will continue from the previous list's last number.

### Tables

**CRITICAL: Tables need dual widths** - set both `columnWidths` on the table AND `width` on each cell. Without both, tables render incorrectly on some platforms.

```javascript
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

new Table({
  width: { size: 9360, type: WidthType.DXA }, // Always use DXA (percentages break in Google Docs)
  columnWidths: [4680, 4680], // Must sum to table width
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders,
          width: { size: 4680, type: WidthType.DXA }, // Also set on each cell
          shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, // CLEAR not SOLID
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun("Header")] })]
        })
      ]
    })
  ]
})
```

**Table width calculation:**

Always use `WidthType.DXA` — `WidthType.PERCENTAGE` breaks in Google Docs.

```javascript
// Table width = sum of columnWidths = content width
// US Letter with 1" margins: 12240 - 2880 = 9360 DXA
width: { size: 9360, type: WidthType.DXA },
columnWidths: [7000, 2360]  // Must sum to table width
```

**Width rules:**
- **Always use `WidthType.DXA`** — never `WidthType.PERCENTAGE`
- Table width must equal the sum of `columnWidths`
- Cell `width` must match corresponding `columnWidth`
- Cell `margins` are internal padding - they reduce content area, not add to cell width
- For full-width tables: use content width (page width minus left and right margins)

### Images

```javascript
// CRITICAL: type parameter is REQUIRED
new Paragraph({
  children: [new ImageRun({
    type: "png", // Required: png, jpg, jpeg, gif, bmp, svg
    data: fs.readFileSync("image.png"),
    transformation: { width: 200, height: 150 },
    altText: { title: "Title", description: "Desc", name: "Name" } // All three required
  })]
})
```

### Page Breaks

```javascript
// CRITICAL: PageBreak must be inside a Paragraph
new Paragraph({ children: [new PageBreak()] })

// Or use pageBreakBefore
new Paragraph({ pageBreakBefore: true, children: [new TextRun("New page")] })
```

### Hyperlinks

```javascript
// External link
new Paragraph({
  children: [new ExternalHyperlink({
    children: [new TextRun({ text: "Click here", style: "Hyperlink" })],
    link: "https://example.com",
  })]
})

// Internal link (bookmark + reference)
// 1. Create bookmark at destination
new Paragraph({ heading: HeadingLevel.HEADING_1, children: [
  new Bookmark({ id: "chapter1", children: [new TextRun("Chapter 1")] }),
]})
// 2. Link to it
new Paragraph({ children: [new InternalHyperlink({
  children: [new TextRun({ text: "See Chapter 1", style: "Hyperlink" })],
  anchor: "chapter1",
})]})
```

### Footnotes

**CRITICAL: Use `FootnoteReferenceRun` with superscript numbers, not inline citations. Use `docx-js` only — `python-docx` does not support footnotes.**

```javascript
const doc = new Document({
  footnotes: {
    1: { children: [new Paragraph("Source: Annual Report 2024")] },
    2: { children: [new Paragraph("See appendix for methodology")] },
  },
  sections: [{
    children: [new Paragraph({
      children: [
        new TextRun("Revenue grew 15%"),
        new FootnoteReferenceRun(1),
        new TextRun(" using adjusted metrics"),
        new FootnoteReferenceRun(2),
      ],
    })]
  }]
});
```

**Do NOT use inline citations like `[Smith et al. 2024]` or `[Footnote: ...]`.** Always use `FootnoteReferenceRun` for proper Word footnote objects with superscript references.

**If using `python-docx` instead of `docx-js`:** Use the unpack/edit/pack workflow to add footnotes via XML (see Editing Existing Documents). `python-docx` does not have native footnote support.

### Tab Stops (for footers with left/center/right alignment)

**Use tab stops instead of tables for footer alignment:**

```javascript
new Paragraph({
  children: [
    new TextRun("Left text"),
    new TextRun("\t"),
    new TextRun("Center text"),
    new TextRun("\t"),
    new TextRun("Right text"),
  ],
  tabStops: [
    { type: TabStopType.CENTER, position: 6120 },  // Center at 4.25 inches
    { type: TabStopType.RIGHT, position: 9360 },   // Right at 6.5 inches (content width)
  ],
})
```

**Do NOT use tables for footers.** Tables have minimum height and render as boxes. Use tab stops instead.

### Multi-Column Layouts

```javascript
// Equal-width columns
sections: [{
  properties: {
    column: {
      count: 2,          // number of columns
      space: 720,        // gap between columns in DXA (720 = 0.5 inch)
      equalWidth: true,
      separate: true,    // vertical line between columns
    },
  },
  children: [/* content flows naturally across columns */]
}]

// Custom-width columns (equalWidth must be false)
sections: [{
  properties: {
    column: {
      equalWidth: false,
      children: [
        new Column({ width: 5400, space: 720 }),
        new Column({ width: 3240 }),
      ],
    },
  },
  children: [/* content */]
}]
```

Force a column break with a new section using `type: SectionType.NEXT_COLUMN`.

### Table of Contents

**CRITICAL: TOC requires HeadingLevel on paragraphs AND must be updated in Word after opening.**

```javascript
// 1. Create headings with HeadingLevel (required for TOC to work)
new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Introduction")] }),
new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Background")] }),

// 2. Add TOC at the beginning
new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" })
```

**CRITICAL: After opening the document in Word, right-click the TOC and select "Update Field" to populate entries.** This is a Word limitation. The TOC will appear empty until updated in Word. Do not claim the TOC is complete until this step is performed by the user.

### Headers/Footers

```javascript
sections: [{
  properties: {
    page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } // 1440 = 1 inch
  },
  headers: {
    default: new Header({ children: [new Paragraph({ children: [new TextRun("Header")] })] })
  },
  footers: {
    default: new Footer({ children: [new Paragraph({
      children: [new TextRun("Page "), new TextRun({ children: [PageNumber.CURRENT] })]
    })] })
  },
  children: [/* content */]
}]
```

---

## Editing Existing Documents

**Follow all 3 steps in order.**

### Step 1: Unpack

```bash
python scripts/office/unpack.py document.docx unpacked/
```

Extracts XML, pretty-prints, merges adjacent runs, and converts smart quotes to XML entities (`&#x201C;` etc.) so they survive editing. Use `--merge-runs false` to skip run merging.

### Step 2: Edit XML

Edit files in `unpacked/word/`. See XML Reference below for patterns.

**Use "Claude" as the author** for tracked changes and comments, unless the user explicitly requests use of a different name.

**Use the Edit tool directly for string replacement. Do not write Python scripts.** Scripts introduce unnecessary complexity. The Edit tool shows exactly what is being replaced.

**CRITICAL: Use smart quotes for new content.** When adding text with apostrophes or quotes, use XML entities to produce smart quotes:

```xml
<!-- Use these entities for professional typography -->
<w:t>Here&#x2019;s a quote: &#x201C;Hello&#x201D;</w:t>
```

| Entity | Character |
|--------|-----------|
| `&#x2018;` | ' (left single) |
| `&#x2019;` | ' (right single / apostrophe) |
| `&#x201C;` | " (left double) |
| `&#x201D;` | " (right double) |

**Adding comments:** Use `comment.py` to handle boilerplate across multiple XML files (text must be pre-escaped XML):

```bash
python scripts/comment.py unpacked/ 0 "Comment text with &amp; and &#x2019;"
python scripts/comment.py unpacked/ 1 "Reply text" --parent 0  # reply to comment 0
python scripts/comment.py unpacked/ 0 "Text" --author "Custom Author"  # custom author name
```

Then add markers to document.xml (see Comments in XML Reference).

### Step 3: Pack

```bash
python scripts/office/pack.py unpacked/ output.docx --original document.docx
```

Validates with auto-repair, condenses XML, and creates DOCX. Use `--validate false` to skip.

**Auto-repair will fix:**
- `durableId` >= 0x7FFFFFFF (regenerates valid ID)
- Missing `xml:space="preserve"` on `<w:t>` with whitespace

**Auto-repair won't fix:**
- Malformed XML, invalid element nesting, missing relationships, schema violations

### Common Pitfalls

- **Replace entire `<w:r>` elements**: When adding tracked changes, replace the whole `<w:r>...</w:r>` block with `<w:del>...<w:ins>...` as siblings. Don't inject tracked change tags inside a run.
- **Preserve `<w:rPr>` formatting**: Copy the original run's `<w:rPr>` block into your tracked change runs to maintain bold, font size, etc.
- **For simple replacements without tracked changes**: Use the Edit tool to replace text directly. Only use tracked changes when the user explicitly requests them.

---

## XML Reference

### Schema Compliance

- **Element order in `<w:pPr>`**: `<w:pStyle>`, `<w:numPr>`, `<w:spacing>`, `<w:ind>`, `<w:jc>`, `<w:rPr>` last
- **Whitespace**: Add `xml:space="preserve"` to `<w:t>` with leading/trailing spaces
- **RSIDs**: Must be 8-digit hex (e.g., `00AB1234`)

### Tracked Changes

**Insertion:**

```xml
<w:ins w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:t>inserted text</w:t></w:r>
</w:ins>
```

**Deletion:**

```xml
<w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
```

**Inside `<w:del>`**: Use `<w:delText>` instead of `<w:t>`, and `<w:delInstrText>` instead of `<w:instrText>`.

**Minimal edits** - only mark what changes:

```xml
<!-- Change "30 days" to "60 days" -->
<w:r><w:t>The term is </w:t></w:r>
<w:del w:id="1" w:author="Claude" w:date="...">
  <w:r><w:delText>30</w:delText></w:r>
</w:del>
<w:ins w:id="2" w:author="Claude" w:date="...">
  <w:r><w:t>60</w:t></w:r>
</w:ins>
<w:r><w:t> days.</w:t></w:r>
```

**Deleting entire paragraphs/list items** - when removing ALL content from a paragraph, also mark the paragraph mark as deleted so it merges with the next paragraph. Add `<w:del/>` inside `<w:pPr><w:rPr>`:

```xml
<w:p>
  <w:pPr>
    <w:numPr>...</w:numPr>  <!-- list numbering if present -->
    <w:rPr>
      <w:del w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z"/>
    </w:rPr>
  </w:pPr>
  <w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
    <w:r><w:delText>Entire paragraph content being deleted...</w:delText></w:r>
  </w:del>
</w:p>
```

Without the `<w:del/>` in `<w:pPr><w:rPr>`, accepting changes leaves an empty paragraph/list item.

**Rejecting another author's insertion** - nest deletion inside their insertion:

```xml
<w:ins w:author="Jane" w:id="5">
  <w:del w:author="Claude" w:id="10">
    <w:r><w:delText>their inserted text</w:delText></w:r>
  </w:del>
</w:ins>
```

**Restoring another author's deletion** - add insertion after (don't modify their deletion):

```xml
<w:del w:author="Jane" w:id="5">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
<w:ins w:author="Claude" w:id="10">
  <w:r><w:t>deleted text</w:t></w:r>
</w:ins>
```

### Comments

After running `comment.py` (see Step 2), add markers to document.xml. For replies, use `--parent` flag and nest markers inside the parent's.

**CRITICAL: `<w:commentRangeStart>` and `<w:commentRangeEnd>` are siblings of `<w:r>`, never inside `<w:r>`.**

```xml
<!-- Comment markers are direct children of w:p, never inside w:r -->
<w:commentRangeStart w:id="0"/>
<w:del w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>deleted</w:delText></w:r>
</w:del>
<w:r><w:t> more text</w:t></w:r>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>

<!-- Comment 0 with reply 1 nested inside -->
<w:commentRangeStart w:id="0"/>
  <w:commentRangeStart w:id="1"/>
  <w:r><w:t>text</w:t></w:r>
  <w:commentRangeEnd w:id="1"/>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="1"/></w:r>
```

### Images

1. Add image file to `word/media/`
2. Add relationship to `word/_rels/document.xml.rels`:

```xml
<Relationship Id="rId5" Type=".../image" Target="media/image1.png"/>
```

3. Add content type to `[Content_Types].xml`:

```xml
<Default Extension="png" ContentType="image/png"/>
```

4. Reference in document.xml:

```xml
<w:drawing>
  <wp:inline>
    <wp:extent cx="914400" cy="914400"/>  <!-- EMUs: 914400 = 1 inch -->
    <a:graphic>
      <a:graphicData uri=".../picture">
        <pic:pic>
          <pic:blipFill><a:blip r:embed="rId5"/></pic:blipFill>
        </pic:pic>
      </a:graphicData>
    </a:graphic>
  </wp:inline>
</w:drawing>
```

---

## Common Mistakes

### Creation Failures

**Problem:** Agent claims document was created but no file exists.
- **Fix:** Always verify file creation with `ls -la output.docx` before claiming success.
- **Fallback:** If `Packer.toBuffer()` fails silently, add error handling: `.catch(err => console.error("Error:", err))`

**Problem:** Page size defaults to A4 instead of US Letter.
- **Fix:** Always explicitly set `size: { width: 12240, height: 15840 }` in page properties.
- **Fallback:** If unsure, copy the Minimal Working Template above and verify page size in Word.

**Problem:** Numbered lists continue from previous list instead of restarting.
- **Fix:** Use different `reference` names for each independent list: `"numbers1"`, `"numbers2"`, etc. Each reference creates independent numbering.
- **Fallback:** If lists are sharing numbering, unpack the document and check that each list has a unique `reference` in the numbering config.

**Problem:** Bullet points appear as plain text or unicode characters instead of formatted bullets.
- **Fix:** Use `numbering: { reference: "bullets", level: 0 }` with `LevelFormat.BULLET` in the numbering config.
- **Fallback:** Never manually insert `•` or `\u2022` characters.

**Problem:** Tables render with incorrect column widths or misaligned cells.
- **Fix:** Set both `columnWidths` array AND `width` on each cell. Ensure they match and sum correctly.
- **Fallback:** Use DXA units only; never use `WidthType.PERCENTAGE`.

**Problem:** Footer has table structure instead of tab stops.
- **Fix:** Replace table with tab stops: `tabStops: [{ type: TabStopType.CENTER, position: 6120 }, { type: TabStopType.RIGHT, position: 9360 }]`. Use `TextRun("\t")` to separate left/center/right elements.
- **Fallback:** If footer needs left/center/right alignment, always use tab stops, never tables.

**Problem:** Table of Contents appears empty or shows placeholder text.
- **Fix:** Ensure all headings use `heading: HeadingLevel.HEADING_1` (or HEADING_2, etc.), not custom styles. After opening in Word, right-click TOC and select "Update Field".
- **Fallback:** If TOC still doesn't populate after updating in Word, verify headings have `outlineLevel` in their style definition.

**Problem:** Footnotes appear as inline citations `[Author Year]` or `[Footnote: ...]` instead of superscript numbers.
- **Fix:** Use `FootnoteReferenceRun(n)` with a `footnotes` object in the Document. Do NOT use inline text citations. Use `docx-js` only—`python-docx` does not support footnotes.
- **Fallback:** If using `python-docx`, use the unpack/edit/pack workflow to add footnotes via XML.

### Editing Failures

**Problem:** Tracked changes not visible after editing.
- **Fix:** Ensure `<w:ins>` and `<w:del>` tags wrap complete `<w:r>` elements, not partial content. Replace entire `<w:r>...</w:r>` blocks with tracked change tags as siblings.
- **Fallback:** Use the Edit tool to replace entire `<w:r>...</w:r>` blocks, not just text inside them.

**Problem:** Smart quotes become garbled after editing.
- **Fix:** Use XML entities: `&#x2019;` for apostrophe, `&#x201C;` and `&#x201D;` for double quotes.
- **Fallback:** If editing plain text, use the unpack tool with default settings (it auto-converts quotes).

**Problem:** Document fails validation after editing.
- **Fix:** Check element order in `<w:pPr>`: must be `pStyle`, `numPr`, `spacing`, `ind`, `jc`, `rPr` (in that order).
- **Fallback:** Use `--validate false` to skip validation, then manually inspect the XML for malformed tags.

**Problem:** Simple text replacement was made but user expected tracked changes.
- **Fix:** If user explicitly requests tracked changes, use `<w:del>` and `<w:ins>` tags. Otherwise, direct replacement is acceptable.
- **Fallback:** Ask the user if tracked changes are required before editing.

**Problem:** Edited document shows no changes after packing.
- **Fix:** Verify edits were made to `unpacked/word/document.xml` (not other files). Use `ls -la unpacked/word/document.xml` and check file modification time.
- **Fallback:** Unpack again and manually verify your edits are present in the XML before p
