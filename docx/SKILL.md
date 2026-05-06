---
name: docx
description: "Use when creating, reading, editing, or producing Word documents (.docx) — including reports, memos, letters, templates with TOCs, headings, page numbers, or letterheads; extracting or reorganizing .docx content; find-and-replace; inserting/replacing images; accepting, rejecting, or authoring tracked changes and redlines; adding comments; validating docx structure; fixing 'invalid docx' or content-type / schema errors; converting .doc→.docx. Do NOT use for PDFs, spreadsheets, Google Docs, or coding tasks unrelated to Word documents."
---

# DOCX creation, editing, and analysis

## Where to look

| Task | Go to |
|------|-------|
| **Create a new `.docx`** (reports, memos, letters, formatted output) | `references/docx-js.md` |
| **Edit an existing `.docx`** (find-replace, tweak XML, add tracked changes) | `## Editing Existing Documents` below |
| **Raw OOXML / schema** (tracked changes, comments, images at XML level) | `references/ooxml.md` |
| **Accept all tracked changes** | `scripts/accept_changes.py` |
| **Add a comment** | `scripts/comment.py` |
| **Unpack / repack / validate** | `scripts/office/{unpack,pack,validate}.py` |


## Overview

A `.docx` file is a ZIP archive containing XML. Read it with pandoc, edit it
by unpacking the XML and repacking, or create a new one with the `docx` npm
package.

## Common Operations

```bash
# Extract text as markdown (accepts tracked changes by default)
pandoc document.docx -o out.md

# Extract preserving tracked changes as markup
pandoc --track-changes=all document.docx -o out.md

# Convert legacy .doc → .docx (required before editing)
python scripts/office/soffice.py --headless --convert-to docx document.doc

# Convert to images (via PDF)
python scripts/office/soffice.py --headless --convert-to pdf document.docx
pdftoppm -jpeg -r 150 document.pdf page

# Accept all tracked changes
python scripts/accept_changes.py input.docx output.docx

# Unpack for raw XML editing
python scripts/office/unpack.py document.docx unpacked/
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

Edit files in `unpacked/word/`. See `references/ooxml.md` for element patterns
(tracked changes, comments, images, schema rules).

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
Then add markers to `document.xml` (see the Comments section in `references/ooxml.md`).

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


---

## Dependencies

- **pandoc** — text extraction (`brew install pandoc`)
- **docx** npm package — creating new documents (`bun install -g docx`)
- **LibreOffice** — PDF conversion and accepting tracked changes; `scripts/office/soffice.py` auto-configures it for sandboxed environments (`brew install --cask libreoffice`)
- **Poppler** — `pdftoppm` for image conversion (`brew install poppler`)
- **defusedxml** — used by `unpack.py`, `pack.py`, `comment.py`, and the run/redline helpers. Declared inline via `uv` script metadata — `uv run scripts/...` installs on first run.

---

## Scripts & Templates

The helpers referenced throughout this skill live under `scripts/` next to
`SKILL.md` — not embedded in this document.

**Python scripts** (`scripts/`):

| Path | Purpose |
|------|---------|
| `accept_changes.py` | Accept all tracked changes via LibreOffice |
| `comment.py` | Add comments to a DOCX |
| `office/unpack.py` | Unpack DOCX/PPTX/XLSX for XML editing |
| `office/pack.py` | Repack an unpacked directory into a valid DOCX/PPTX/XLSX |
| `office/soffice.py` | LibreOffice wrapper with sandbox-friendly env setup |
| `office/validate.py` | Validate DOCX structure and content |
| `office/helpers/merge_runs.py` | Merge adjacent runs with identical formatting |
| `office/helpers/simplify_redlines.py` | Collapse adjacent `w:ins` / `w:del` |
| `office/validators/base.py` | Shared `BaseSchemaValidator` (XML, namespace, ID-uniqueness, XSD, relationship checks) |
| `office/validators/docx.py` | `DOCXSchemaValidator` — full WordprocessingML schema + tracked-change + relationship validation |
| `office/validators/pptx.py` | `PPTXSchemaValidator` — PresentationML schema validation (shared code used by the pptx/xlsx skills too) |
| `office/validators/redlining.py` | `RedliningValidator` — tracked-change integrity (accept-all round-trip test) |

**XML templates** (`scripts/templates/`): `comments.xml`, `commentsExtended.xml`,
`commentsExtensible.xml`, `commentsIds.xml`, `people.xml` — minimal valid root
documents used when bootstrapping a new comments payload.

Invoke scripts with `uv run scripts/<path>` (deps auto-install from each
script's inline metadata) or `python scripts/<path>` if you've pre-installed
`defusedxml`. Scripts add their parent dir to `sys.path` at import time, so
running from the skill root, the `scripts/` dir, or any other cwd all work.

