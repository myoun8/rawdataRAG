# RAG Knowledge Pack Template

This repository template is for building RAG-ready knowledge packs for instrument support documentation. It is organized for CANDOR, VSANS, NSE, and shared/common resources such as NICE, data access, sample environment notes, and glossary terms.

A RAG-ready pack is more than a folder of PDFs. It contains:

- Original source files or source snapshots
- Normalized Markdown files with frontmatter metadata
- Chunked JSONL records for ingestion
- Source inventory tracking
- Manifest files
- Access-control labels
- Glossary and synonym files
- Evaluation questions
- Validation scripts

## Recommended workflow

1. Add sources to `source_inventory.csv`.
2. Save unmodified source files under `originals/`.
3. Convert each source to Markdown under `normalized/`.
4. Add YAML-style frontmatter to each Markdown file.
5. Run `python scripts/chunk_markdown.py candor` or the relevant pack name.
6. Run `python scripts/validate_pack.py candor`.
7. Review output with instrument owners.
8. Load the generated JSONL chunks into the RAG/vector index.

## Pack folders

```text
common/   Shared NCNR resources such as NICE, data access, sample environments, glossary terms
candor/   CANDOR-specific documentation and examples
vsans/    VSANS-specific documentation and examples
nse/      NSE-specific documentation and examples
```

## Source authority principle

Prefer current, reviewed, instrument-owner-approved documents over older tutorials, archived pages, or unreviewed notes. Mark old material as `legacy`, `deprecated`, or `needs_review` rather than deleting it immediately.

## Access-control principle

Every source, document, and chunk must have an access level. Do not rely on folder location alone.

Suggested levels:

- `public`
- `internal`
- `restricted`
