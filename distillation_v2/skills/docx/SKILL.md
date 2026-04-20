# DOCX creation, editing, and analysis

## Overview

A .docx file is a ZIP archive containing XML files.

## Quick Reference

| Task | Approach |
|-------|----------|
| Read/analyze content | `pandoc` or unpack for raw XML |
| Create new document | Use Python `python-docx` (MANDATORY) |
| Edit existing document | Unpack → edit XML → repack — see Editing Existing Documents below |

---

## Creating New Documents

### ⚠️ CRITICAL REQUIREMENT: Save to workspace root BEFORE end_turn

**YOUR TASK FAILS IMMEDIATELY IF:**
1. The .docx file is NOT in the workspace root (not in a subdirectory)
2. The file does NOT exist after running your script
3. The file is empty (0 bytes)
4. You call end_turn without verifying the file exists and is valid
5. You do not run the validation script before end_turn
6. You get stuck in a loop repeating the same command — STOP and change approach
7. The filename in your script does NOT match the exact required filename from the task
8. You do NOT verify the file location with `ls -lh <filename>` before calling end_turn

---

## MANDATORY WORKFLOW (EXACT ORDER — DO NOT SKIP STEPS)

### Step 0: CRITICAL — Extract the Exact Output Filename
**BEFORE you write ANY code, you MUST do this:**

Read the entire task description and find the exact output filename. Write it down on paper or in a note.

Examples:
- If task says "Create a document named 'executive_summary.docx'", the filename is **executive_summary.docx**
- If task says "Save as 'contract_modified.docx'", the filename is **contract_modified.docx**
- If task does not specify, use **output.docx**

**CRITICAL:** The filename you use in the script MUST match exactly. Do NOT use a generic name if a specific name is required.

Test yourself: Can you state the exact output filename without looking at the task again? If NO, re-read the task until you can.

---

### Step 1: Read Task and Extract Requirements
**BEFORE writing any code:**
- Read the task description completely, twice
- Write down the **exact output filename** (this is CRITICAL — most failures are because the filename is wrong)
- Write down ALL required keywords, section names, and headings
- Write down ANY forbidden keywords to remove
- Note any special formatting (heading levels, tables, lists, numbered items, footers, headers, etc.)
- Note if footers or headers are required and what text/formatting they need
- Note if tracked changes (insertions/deletions) are required and with what author name
- Note if table of contents (TOC) is required
- **CRITICAL:** Count the exact number of items that must be numbered (e.g., "Step 1", "Step 2") — use this count to verify numbering refs later
- Verify you have the exact filename before proceeding to Step 2

### Step 2: Copy Template and Edit ONLY Content Section
Copy the template below exactly. Change **ONLY** the section marked `# ===== YOUR CONTENT HERE =====`. Do NOT modify initialization, save logic, or validation code.

### Step 3: Change Output Filename in Template — VERIFY THREE TIMES
Find this line in the template:
```python
output_file = os.path.join(os.getcwd(), 'output.docx')
```
Replace `'output.docx'` with the exact filename from Step 0:
```python
output_file = os.path.join(os.getcwd(), 'contract_modified.docx')
```

**CRITICAL VERIFICATION CHECKLIST:**
- [ ] I have written the exact filename from the task on paper
- [ ] I have changed the `output_file` line in the script to match that exact filename
- [ ] I have read the line in the script and confirmed it matches the task
- [ ] The filename has NO extra spaces, NO capitalization changes, NO typos
- If you cannot check all four boxes, re-read the task and fix the filename NOW before running the script

### Step 4: Run Script and Verify File Exists in Workspace Root
```bash
python script.py
```
Check for "SUCCESS" message. If "FATAL ERROR", STOP immediately and go to Common Mistakes.

```bash
ls -lh <filename>
```
Replace `<filename>` with the exact name from Step 0. **File MUST exist and show size > 0.**

**CRITICAL VERIFICATION:**
- Verify the filename shown in `ls -lh` output matches EXACTLY (no typos, no case changes)
- Verify the file size is > 0 bytes
- Run `pwd` to confirm you are in the workspace root
- If file does NOT exist after script SUCCESS, run `ls -la` to list all files

**CRITICAL:** If file does NOT exist, the task has FAILED. Do NOT run the script again. Instead:
1. Re-read Step 0 and Step 3 — did you use the correct filename in BOTH the script and the ls command?
2. Check the script output — does it say the file was saved? Copy the exact path from the output.
3. Run `pwd` to verify you are in the workspace root
4. Run `ls -la` to list all files in the current directory
5. If you see the file in a subdirectory, move it to the root: `mv subdir/filename.docx ./filename.docx`
6. If filename in script is WRONG, edit the script, change the filename to match exactly, and run again ONCE ONLY
7. If file is still not found after one more attempt, STOP and re-read the task from the beginning

### Step 5: Run Validation
```bash
python scripts/office/validate.py <filename>
```
Use the same filename from Step 0. **Validation MUST pass before calling end_turn.**

If validation fails, read the error message carefully. Go to Common Mistakes section for the specific error (e.g., "missing footer", "wrong numbering count", "missing keyword").

### Step 6: Call end_turn
Only after ALL of the following are confirmed:
- [ ] File exists at workspace root with correct filename
- [ ] `ls -lh <filename>` shows size > 0 bytes
- [ ] `python scripts/office/validate.py <filename>` PASSES (no error message)
- [ ] You have verified all three checks above

---

## Python — MANDATORY APPROACH

### Install (run once)
```bash
pip install python-docx
```

### Complete Minimal Working Template

**COPY THIS TEMPLATE EXACTLY. CHANGE ONLY THE `# ===== YOUR CONTENT HERE =====` SECTION. DO NOT MODIFY ANYTHING ELSE.**

```python
#!/usr/bin/env python3
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import sys
import os

# ===== INITIALIZE DOCUMENT =====
try:
    doc = Document()
    section = doc.sections[0]
    section.page_height = Inches(11)
    section.page_width = Inches(8.5)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
except Exception as e:
    print(f"ERROR during document initialization: {e}")
    sys.exit(1)

# ===== YOUR CONTENT HERE — MODIFY ONLY THIS SECTION =====
# Add all required headings, paragraphs, lists, and tables based on task description
# Add headers and footers if required by the task
# Add tracked changes (insertions/deletions) if required by the task
#
# REQUIRED PATTERNS:
# 1. ALL task-specified keywords MUST appear in the document as text
# 2. ALL required heading levels (e.g., Heading 1, Heading 2) MUST be present
# 3. Numbered lists (style='List Number') MUST be used ONLY for explicitly required numbered items
# 4. Table of Contents requires: (a) heading with level=1, (b) unpack/edit/repack to add TOC field
# 5. Footers require: section.footer with content
# 6. Tracked changes require: unpack/edit/repack workflow to add w:ins or w:del tags
# 7. Tables MUST use doc.add_table() with explicit row/col headers
#
# CRITICAL: The number of items with style='List Number' MUST match the task requirements exactly
#
# EXAMPLES:
#
# Example 1: Simple heading and paragraph with required keywords
# doc.add_heading('Document Title', level=1)
# doc.add_paragraph('This section introduces the Name, Department, and Salary information.')
#
# Example 2: Heading levels 1, 2, and 3 for outline structure
# doc.add_heading('Main Title', level=1)
# doc.add_heading('Section Heading', level=2)
# doc.add_paragraph('Section content here.')
# doc.add_heading('Subsection Heading', level=3)
# doc.add_paragraph('Subsection content here.')
#
# Example 3: Numbered items (ONLY if task explicitly requires exactly N numbered steps)
# doc.add_paragraph('Step 1: First action', style='List Number')
# doc.add_paragraph('Step 2: Second action', style='List Number')
# NOTE: If task requires 2 numbered steps, use EXACTLY 2 style='List Number' calls — not more, not less
#
# Example 4: Table with headers and data (ONLY if task requires a table)
# table = doc.add_table(rows=3, cols=3)
# table.style = 'Light Grid Accent 1'
# header_cells = table.rows[0].cells
# header_cells[0].text = 'Name'
# header_cells[1].text = 'Department'
# header_cells[2].text = 'Salary'
# row1_cells = table.rows[1].cells
# row1_cells[0].text = 'John'
# row1_cells[1].text = 'Engineering'
# row1_cells[2].text = '100000'
# row2_cells = table.rows[2].cells
# row2_cells[0].text = 'Jane'
# row2_cells[1].text = 'Marketing'
# row2_cells[2].text = '95000'
#
# Example 5: Footer with text (ONLY if task requires footer)
# section = doc.sections[0]
# footer = section.footer
# footer_para = footer.paragraphs[0]
# footer_para.text = 'PAGE'
#
# Example 6: Paragraph with specific formatting
# doc.add_heading('Section Title', level=2)
# para = doc.add_paragraph()
# run = para.add_run('Text with ')
# run.font.bold = True
# run = para.add_run('different ')
# run.font.italic = True
# run = para.add_run('formatting.')
#
# REPLACE THE ABOVE EXAMPLES WITH YOUR ACTUAL REQUIRED CONTENT
# DO NOT leave example code in place — write your own content based on task requirements

# ===== END YOUR CONTENT =====

# ===== SAVE FILE — DO NOT MODIFY THIS SECTION =====
output_file = os.path.join(os.getcwd(), 'output.docx')
try:
    doc.save(output_file)
except Exception as e:
    print(f"FATAL ERROR saving file: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ===== VERIFY FILE EXISTS AND IS NOT EMPTY =====
if not os.path.exists(output_file):
    print(f"FATAL ERROR: File not created at {output_file}")
    sys.exit(1)

file_size = os.path.getsize(output_file)
if file_size == 0:
    print(f"FATAL ERROR: File is empty (0 bytes)")
    sys.exit(1)

print(f"SUCCESS: {output_file} ({file_size} bytes)")
sys.exit(0)
```

---

## Common Code Patterns for Content Section

### Heading + Paragraph
```python
doc.add_heading('Section Title', level=2)
doc.add_paragraph('Paragraph text goes here.')
```

### Multiple Heading Levels (For Outline Structure)
```python
doc.add_heading('Main Title', level=1)
doc.add_heading('Section 1', level=2)
doc.add_paragraph('Content for section 1.')
doc.add_heading('Subsection 1.1', level=3)
doc.add_paragraph('Content for subsection 1.1.')
doc.add_heading('Section 2', level=2)
doc.add_paragraph('Content for section 2.')
```

### Bullet Points (ONLY if task requires)
```python
doc.add_paragraph('Bullet item 1', style='List Bullet')
doc.add_paragraph('Bullet item 2', style='List Bullet')
```

### Numbered List (ONLY if task explicitly requires numbering — count items carefully)
```python
# CRITICAL: Use style='List Number' ONLY for items that MUST be numbered
# CRITICAL: The count of items with style='List Number' MUST match task requirement exactly
# Example: If task says "Create 2 numbered steps", use style='List Number' EXACTLY 2 times
# Each use of style='List Number' creates ONE numbering reference in the XML
#
# CORRECT (for task requiring 2 numbered steps):
doc.add_paragraph('Step 1: First step', style='List Number')
doc.add_paragraph('Step 2: Second step', style='List Number')
doc.add_paragraph('Note: This is NOT numbered', style='List Bullet')
#
# WRONG (using too many numbering items):
# doc.add_paragraph('Item 1', style='List Number')
# doc.add_paragraph('Item 2', style='List Number')
# doc.add_paragraph('Item 3', style='List Number')
# ^ This creates 3 numbering refs, which will fail if task requires 2
```

### Simple Table (ONLY if task requires)
```python
table = doc.add_table(rows=2, cols=2)
table.style = 'Light Grid Accent 1'
header_cells = table.rows[0].cells
header_cells[0].text = 'Column 1'
header_cells[1].text = 'Column 2'
row_cells = table.rows[1].cells
row_cells[0].text = 'Data 1'
row_cells[1].text = 'Data 2'
```

### Table with Multiple Rows
```python
# Create table with correct row and column count
table = doc.add_table(rows=3, cols=3)  # 3 rows (1 header + 2 data), 3 columns
table.style = 'Light Grid Accent 1'
# Set header row
header_cells = table.rows[0].cells
header_cells[0].text = 'Name'
header_cells[1].text = 'Department'
header_cells[2].text = 'Salary'
# Set data rows
row1_cells = table.rows[1].cells
row1_cells[0].text = 'John Doe'
row1_cells[1].text = 'Engineering'
row1_cells[2].text = '100000'
row2_cells = table.rows[2].cells
row2_cells[0].text = 'Jane Smith'
row2_cells[1].text = 'Marketing'
row2_cells[2].text = '95000'
```

### Footer with Text
```python
section = doc.sections[0]
footer = section.footer
footer_para = footer.paragraphs[0]
footer_para.text = 'PAGE'
```

### Footer with Tab Element (If Required by Validation)
```python
section = doc.sections[0]
footer = section.footer
footer_para = footer.paragraphs[0]
footer_para.text = 'PAGE'
# Add tab element if validation requires w:type="clear"
run = footer_para.add_run()
tab_element = OxmlElement('w:tab')
tab_element.set(qn('w:type'), 'clear')
run._element.append(tab_element)
```

### Footer with Page Number Field
```python
section = doc.sections[0]
footer = section.footer
footer_para = footer.paragraphs[0]
# Add page number field (creates w:instrText with "PAGE")
run = footer_para.add_run()
fldChar1 = OxmlElement('w:fldChar')
fldChar1.set(qn('w:fldCharType'), 'begin')
run._element.append(fldChar1)

run = footer_para.add_run()
instrText = OxmlElement('w:instrText')
instrText.set(qn('xml:space'), 'preserve')
instrText.text = 'PAGE'
run._element.append(instrText)

run = footer_para.add_run()
fldChar2 = OxmlElement('w:fldChar')
fldChar2.set(qn('w:fldCharType'), 'end')
run._element.append(fldChar2)
```

### Paragraph with Specific Formatting
```python
para = doc.add_paragraph()
run = para.add_run('Bold text ')
run.font.bold = True
run = para.add_run('italic text ')
run.font.italic = True
run = para.add_run('normal text.')
```

---

## Common Code Patterns for Tracked Changes (Using Unpack/Edit/Repack)

**IMPORTANT:** If your task requires tracked changes with specific author names (e.g., `w:author="Jane"`) or deletion markup, you **MUST use the Unpack → Edit XML → Repack workflow**, not direct python-docx creation.

The workflow is:
1. Create document with python-docx (add all required content and keywords)
2. Save the .docx file
3. Verify file exists: `ls -lh output.docx`
4. Unpack the .docx: `python scripts/office/unpack.py output.docx unpacked/`
5. Edit `unpacked/word/document.xml` to add tracked change tags (`<w:ins>`, `<w:del>`) with correct author names
6. Repack: `python scripts/office/pack.py unpacked/ output.docx --original output.docx`
7. Verify file exists after repack: `ls -lh output.docx`
8. Validate: `python scripts/office/validate.py output.docx`

---

## Editing Existing Documents

### Complete Workflow: Unpack → Edit → Repack

**CRITICAL:** If you need to add tracked changes with author names, add table of contents (TOC), modify raw XML in any way, or add specific XML elements like `<w:instrText>` or `<w:clear>`, you MUST use this workflow instead of trying to modify with python-docx alone.

**Step-by-step:**

1. **Create base document with python-docx** (add all content and keywords)
   ```bash
   python script.py
   ```
   This creates `output.docx` (or your filename)

2. **Verify file exists immediately after script completes**
   ```bash
   ls -lh output.docx
   ```
   File MUST show size > 0 bytes. If file does not exist, STOP and debug using Mistake 9 section.

3. **Unpack the .docx into XML**
   ```bash
   python scripts/office/unpack.py output.docx unpacked/
   ```
   This creates folder `unpacked/` with extracted XML files

4. **Edit the XML file** — use the Edit tool to modify `unpacked/word/document.xml`
   - To add tracked insertion: wrap content with `<w:ins w:author="Claude">` ... `</w:ins>`
   - To add tracked deletion: wrap content with `<w:del w:author="Claude">` ... `</w:del>` (use `<w:delText>` instead of `<w:t>`)
   - To add table of contents: add `<w:instrText>TOC \o "1-1"</w:instrText>` inside a paragraph
   - To add page number field: add `<w:instrText>PAGE</w:instrText>` inside a paragraph
   - To add tab with clear type: add `<w:tab w:type="clear"/>` inside a paragraph
   - To remove forbidden keywords: find and delete the text or wrap in `<w:del>` tags
   - Example insertion:
     ```xml
     <w:ins w:author="Claude" w:date="2025-01-01T00:00:00Z">
       <w:r><w:t>This text was inserted</w:t></w:r>
     </w:ins>
     ```
   - Example deletion:
     ```xml
     <w:del w:author="Claude" w:date="2025-01-01T00:00:00Z">
       <w:r><w:delText>This text was deleted</w:delText></w:r>
     </w:del>
     ```
   - Example table of contents field:
     ```xml
     <w:p>
       <w:r>
         <w:fldChar w:fldCharType="begin"/>
       </w:r>
       <w:r>
         <w:instrText xml:space="preserve">TOC \o "1-1"</w:instrText>
       </w:r>
       <w:r>
         <w:fldChar w:fldCharType="end"/>
       </w:r>
     </w:p>
     ```
   - Example page number field:
     ```xml
     <w:p>
       <w:r>
         <w:fldChar w:fldCharType="begin"/>
       </w:r>
       <w:r>
         <w:instrText xml:space="preserve">PAGE</w:instrText>
       </w:r>
       <w:r>
         <w:fldChar w:fldCharType="end"/>
       </w:r>
     </w:p>
     ```
   - Example outline level (for heading outline structure):
     ```xml
     <w:pPr>
       <w:pStyle w:val="Heading2"/>
       <w:outlineLvl w:val="1"/>
     </w:pPr>
     ```

5. **Repack the edited XML back into .docx**
   ```bash
   python scripts/office/pack.py unpacked/ output.docx --original output.docx
   ```
   This recreates `output.docx` with your changes

6. **Verify the file immediately**
   ```bash
   ls -lh output.docx
   ```
   File must show size > 0 bytes. If file does not exist or is 0 bytes, STOP and re-run the repack command ONCE ONLY. If still fails, go to Mistake 9.

7. **Validate**
   ```bash
   python scripts/office/validate.py output.docx
   ```
   Must show PASS with no errors

---

## Common Mistakes & How to Fix Them

### Mistake 1: Wrong Output Filename (MOST COMMON — causes 100% of failures)
**Symptom:** File not found, or validation fails with "No .docx file found", or validation says file does not exist

**Root Cause:** Task specifies filename (e.g., "annual_report_2026.docx") but script saves as "output.docx" OR script has correct filename but you are checking for wrong name in validation

**How to fix:**
1. Re-read the task description. Find the EXACT required filename. Copy it character-for-character.
2. In the template, change THIS LINE ONLY:
   ```python
   output_file = os.path.join(os.getcwd(), 'output.docx')
   ```
   To (example):
   ```python
   output_file = os.path.join(os.getcwd(), 'annual_report_2026.docx')
   ```
3. Run: `python script.py`
4. Verify: `ls -lh annual_report_2026.docx` — use the EXACT filename
5. If file exists and shows size > 0, run validation: `python scripts/office/validate.py annual_report_2026.docx`
6. If file does not exist after script reports SUCCESS, run `ls -la` to see all files in current directory. Check if it was saved with a different name or in a subdirectory.
7. If validation passes, call end_turn.

### Mistake 2: Missing Required Keywords or Section Names
**Symptom:** File is created but validation fails because required content is missing (e.g., "Keyword not found: 'Name'", "Keyword not found: 'Steps to install'", "Keyword not found: 'Steps to configure'")

**Root Cause:** Task requires specific text (e.g., "Introduction", "Background Context", "Steps to install", "Steps to configure", "Name", "Department", "Salary", "Acme Corp") but it's not in the document content

**How to fix:**
1. Re-read the task description completely. Write down EVERY required keyword or phrase word-for-word.
2. For each keyword, ensure it appears as TEXT in the document:
   - Use `doc.add_paragraph('...')` to add text containing the keyword
   - Use `doc.add_heading('...')` if the keyword is a heading
   - Use table headers or cell text if keyword should appear in a table
   - Use footer text if keyword should appear in footer
3. Examples of adding keywords:
   ```python
   doc.add_heading('Steps to install', level=2)  # Adds "Steps to install" as heading
   doc.add_paragraph('Steps to configure the system are described below.')  # Adds "Steps to configure"
   doc.add_paragraph('Name and Department information follows.')  # Adds "Name" and "Department"
   ```
4. Verify each keyword appears in AT LEAST one `doc.add_*()` call by searching your script for the keyword text.
5. Run `python script.py` again.
6. Validate: `python scripts/office/validate.py <filename>`
7. If validation passes, call end_turn.

### Mistake 3: Using Numbered Lists When Not Required (or wrong count)
**Symptom:** Validation fails with "Expected 2 numbering refs, found 9" or "Expected 0 numbering refs, found 5" or XML missing `<w:numFmt>`, `<w:numId>`, `<w:numPr>`

**Root Cause:** Used `style='List Number'` the wrong number of times. EVERY use of `style='List Number'` creates exactly ONE numbering reference in the document XML. The validator counts these references and expects an exact match to the task requirement.

**How to fix:**
1. Re-read the task. Count the EXACT number of items that MUST be numbered:
   - Look for phrases like "Step 1", "Step 2", "numbered list", "procedure steps"
   - Count them carefully — if task shows "Step 1" and "Step 2" only, the count is 2
   - If task does NOT mention numbered items, the count is 0 (use NO `style='List Number'`)
2. In your script, use `style='List Number'` EXACTLY that many times:
   ```python
   # Correct example for task requiring 2 numbered steps:
   doc.add_paragraph('Step 1: First step', style='List Number')
   doc.add_paragraph('Step 2: Second step', style='List Number')
   doc.add_paragraph('Note: Additional information')  # NOT numbered

   # WRONG: Using too many or too few numbering items
   doc.add_paragraph('Item 1', style='List Number')  # Wrong if task requires 2
   doc.add_paragraph('Item 2', style='List Number')
   doc.add_paragraph('Item 3', style='List Number')  # Creates 3 refs, fails if expected 2
   ```
3. Count the number of `style='List Number'` calls in your script. This number MUST match the task requirement.
4. If task does NOT explicitly require numbered items, use NO `style='List Number'` calls at all (use normal paragraphs or bullets instead).
5. Run `python script.py` again.
6. Validate: `python scripts/office/validate.py <filename>`
7. If validation says "Expected X numbering refs", compare X to your count from step 3. They MUST match.
8. If validation passes, call end_turn.

### Mistake 4: Missing Footer (if task requires)
**Symptom:** Validation fails with "Footer XML missing: <w:tab/>", "Footer XML missing: PAGE", "XML missing: w:type=\"clear\"", or similar

**Root Cause:** Task requires a footer with specific content (e.g., "PAGE" or page numbers or tab element) but footer was not added to the document

**How to fix:**
1. Re-read the task. Look for words like "footer", "page", "page number", "bottom of page".
2. If task requires a footer, add one. Choose the appropriate pattern based on validation error:

   **Option A: Simple footer with text only**
   ```python
   section = doc.sections[0]
   footer = section.footer
   footer_para = footer.paragraphs[0]
   footer_para.text = 'PAGE'
   ```

   **Option B: Footer with tab element (if validation requires w:type="clear")**
   ```python
   section = doc.sections[0]
   footer = section.footer
   footer_para = footer.paragraphs[0]
   footer_para.text = 'PAGE'
   run = footer_para.add_run()
   tab_element = OxmlElement('w:tab')
   tab_element.set(qn('w:type'), 'clear')
   run._element.append(tab_element)
   ```

   **Option C: Footer with page number field (if validation requires w:instrText and PAGE)**
   ```python
   section = doc.sections[0]
   footer = section.footer
   footer_para = footer.paragraphs[0]
   run = footer_para.add_run()
   fldChar1 = OxmlElement('w:fldChar')
   fldChar1.set(qn('w:fldCharType'), 'begin')
   run._element.append(fldChar1)
   run = footer_para.add_run()
   instrText = OxmlElement('w:instrText')
   instrText.set(qn('xml:space'), 'preserve')
   instrText.text = 'PAGE'
   run._element.append(instrText)
   run = footer_para.add_run()
   fldChar2 = OxmlElement('w:fldChar')
   fldChar2.set(qn('w:fldCharType'), 'end')
   run._element.append(fldChar2)
   ```

3. Run `python script.py` again.
4. Validate: `python scripts/office/validate.py <filename>`
5. If validation passes, call end_turn.

### Mistake 5: Missing Heading Levels (causes w:outlineLvl error)
**Symptom:** Validation fails with "XML missing in word/document.xml: w:val='Heading2'" or "w:outlineLvl" or similar

**Root Cause:** Task requires specific heading levels (e.g., Heading2, Heading3) but they are not in the document. Heading levels create outline structure in the document.

**How to fix:**
1. Re-read the task. Look for words like "heading", "section", "subsection", "outline", "structure", or numbered section names like "1. Introduction", "1.1 Background".
2. Add headings with the correct levels:
   ```python
   doc.add_heading('Main Title', level=1)  # Creates Heading1, outline level 0
   doc.add_heading('Section Title', level=2)  # Creates Heading2, outline level 1
   doc.add_heading('Subsection Title', level=3)  # Creates Heading3, outline level 2
   ```
3. Each call to `doc.add_heading(..., level=N)` creates a heading at that level and sets outline level in the XML.
4. If validation requires "w:val='Heading2'", use at least one `doc.add_heading(..., level=2)` call.
5. Run `python script.py` again.
6. Validate: `python scripts/office/validate.py <filename>`
7. If validation passes, call end_turn.

### Mistake 6: Tracked Changes Missing Author Name (MOST COMMON FOR TRACKED CHANGES)
**Symptom:** Validation fails with "XML missing in word/document.xml: w:author=\"Claude\"" or "w:author=\"Jane\"" or "XML missing:
