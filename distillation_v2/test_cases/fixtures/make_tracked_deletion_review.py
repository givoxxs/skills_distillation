#!/usr/bin/env python3
"""
Create tracked_deletion_review.docx for tc_c08.

Structure: a short document with 3 paragraphs where Jane has deleted text.
Each paragraph has a tracked deletion (<w:del w:author="Jane">) that the
agent should restore by inserting a corresponding <w:ins w:author="Claude">.
"""

import zipfile
from pathlib import Path

# ── Minimal valid OOXML document with 3 tracked deletions by Jane ──────────

DOCUMENT_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
  xmlns:cx="http://schemas.microsoft.com/office/drawing/2014/chartex"
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:o="urn:schemas-microsoft-com:office:office"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
  xmlns:v="urn:schemas-microsoft-com:vml"
  xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
  xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
  xmlns:w10="urn:schemas-microsoft-com:office:word"
  xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
  xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"
  xmlns:w16se="http://schemas.microsoft.com/office/word/2015/wordml/symex"
  xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
  xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
  xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml"
  xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
  mc:Ignorable="w14 w15 w16se wp14">
  <w:body>

    <!-- Paragraph 1: "The project deadline is [deleted: 'March 15th'] confirmed." -->
    <w:p>
      <w:pPr>
        <w:pStyle w:val="Normal"/>
      </w:pPr>
      <w:r>
        <w:t xml:space="preserve">The project deadline is </w:t>
      </w:r>
      <w:del w:id="1" w:author="Jane" w:date="2025-01-15T10:00:00Z">
        <w:r w:rsidDel="00AB1234">
          <w:delText>March 15th</w:delText>
        </w:r>
      </w:del>
      <w:r>
        <w:t xml:space="preserve"> confirmed.</w:t>
      </w:r>
    </w:p>

    <!-- Paragraph 2: "Please review the [deleted: 'attached budget proposal'] before the meeting." -->
    <w:p>
      <w:pPr>
        <w:pStyle w:val="Normal"/>
      </w:pPr>
      <w:r>
        <w:t xml:space="preserve">Please review the </w:t>
      </w:r>
      <w:del w:id="2" w:author="Jane" w:date="2025-01-15T10:01:00Z">
        <w:r w:rsidDel="00AB1235">
          <w:delText>attached budget proposal</w:delText>
        </w:r>
      </w:del>
      <w:r>
        <w:t xml:space="preserve"> before the meeting.</w:t>
      </w:r>
    </w:p>

    <!-- Paragraph 3: "All team members [deleted: 'are required to'] should attend." -->
    <w:p>
      <w:pPr>
        <w:pStyle w:val="Normal"/>
      </w:pPr>
      <w:r>
        <w:t xml:space="preserve">All team members </w:t>
      </w:r>
      <w:del w:id="3" w:author="Jane" w:date="2025-01-15T10:02:00Z">
        <w:r w:rsidDel="00AB1236">
          <w:delText>are required to</w:delText>
        </w:r>
      </w:del>
      <w:r>
        <w:t xml:space="preserve"> should attend.</w:t>
      </w:r>
    </w:p>

    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"
               w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

CONTENT_TYPES_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
</Types>
"""

RELS_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>
"""

WORD_RELS_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles"
    Target="styles.xml"/>
  <Relationship Id="rId2"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings"
    Target="settings.xml"/>
</Relationships>
"""

STYLES_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
    </w:rPr>
  </w:style>
</w:styles>
"""

SETTINGS_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:trackChanges/>
</w:settings>
"""


def build_docx(output_path: Path) -> None:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML.strip())
        zf.writestr("_rels/.rels", RELS_XML.strip())
        zf.writestr("word/_rels/document.xml.rels", WORD_RELS_XML.strip())
        zf.writestr("word/document.xml", DOCUMENT_XML.strip())
        zf.writestr("word/styles.xml", STYLES_XML.strip())
        zf.writestr("word/settings.xml", SETTINGS_XML.strip())
    print(f"Created: {output_path} ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    out = Path(__file__).parent / "tracked_deletion_review.docx"
    build_docx(out)

    # Verify: check XML contains the expected markers
    with zipfile.ZipFile(out) as zf:
        doc_xml = zf.read("word/document.xml").decode()

    assert doc_xml.count("<w:del w:id=") == 3, "Expected 3 <w:del> elements"
    assert 'w:author="Jane"' in doc_xml, "Expected Jane as author"
    print("Verification OK: 3 tracked deletions by Jane")
