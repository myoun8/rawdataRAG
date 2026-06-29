# RAG Knowledge Pack Template

This repository is a set of RAG-ready knowledge packs for NIST NCNR neutron-scattering instrument documentation: `candor/`, `vsans/`, `nse/` (instrument-specific) and `common/` (shared NICE/NCNR-wide docs).

A RAG-ready pack is more than a folder of PDFs. It contains:

- Original source files or source snapshots (`originals/`)
- Normalized Markdown files with frontmatter metadata (`normalized/`)
- Chunked JSONL records for ingestion (`chunks/`)
- Source inventory tracking (`source_inventory.csv`)
- Manifest files (`manifest.jsonl`)
- Access-control labels (`access_policy.yaml`)
- Glossary and synonym files (`glossary.yaml`)
- Evaluation questions (`eval/`)
- Review artifacts (`review/`)

See `PACK_STRUCTURE.md` for the full folder layout and required metadata fields, and `schemas/` for the JSON schemas backing chunks, eval questions, and manifests.

## Recommended workflow

1. Add sources to `<pack>/source_inventory.csv`.
2. Save unmodified source files under `<pack>/originals/`.
3. Convert each source to Markdown under `<pack>/normalized/`, organized into the stage subfolders from `PACK_STRUCTURE.md`.
4. Add YAML frontmatter to each Markdown file (`doc_id`, `source_id`, `instrument`, `workflow_stage`, `source_type`, `access_level`, `status`, `owner`, `last_reviewed`, `source_url_or_path`, `citation_required`).
5. Run `python scripts/chunk_markdown.py <pack>` to split `normalized/**/*.md` into chunk JSONL.
6. Run `python scripts/validate_pack.py <pack>` to check structure, JSONL syntax, and cross-references against the source inventory.
7. Review output with instrument owners.
8. Run `python scripts/embed_and_ingest.py` to embed every pack's chunks and load them into the local Chroma vector store.
9. Use `python scripts/query_rag.py "<question>" [--pack <pack>]` for end-to-end RAG question answering.

## Scripts (`scripts/`)

- `chunk_markdown.py <pack>` — stdlib-only heading-based chunker; splits `normalized/**/*.md` by H2 headings into `<pack>_chunks.generated.jsonl`.
- `embed_and_ingest.py` — embeds every pack's `chunks/*_chunks.jsonl` with `nomic-ai/nomic-embed-text-v2-moe` and loads them into a Chroma `PersistentClient` at `./chroma_db` (collection `ncnr_rag`). Requires `sentence_transformers`, `chromadb`, `einops`.
- `validate_pack.py <pack>` — validates a pack's required files/dirs, JSONL syntax, chunk/metadata completeness, and cross-references chunk `source_id`s against `source_inventory.csv`.
- `test_retrieval.py` — stdlib-only TF-IDF retrieval/evaluation baseline (`<pack> "<query>"`, `<pack> --evaluate`, or `--evaluate-all`).
- `test_retrieval_embedding.py` — embedding-based counterpart to `test_retrieval.py`, evaluated against the Chroma collection from `embed_and_ingest.py`.
- `evaluate_retrieval_ragas.py` — embedding-based retrieval evaluation using RAGAS-standard Context Precision@K and Context Recall against each eval question's `expected_sources`.
- `query_rag.py "<question>"` — end-to-end RAG query: embeds the question, retrieves filtered chunks from Chroma, and calls an LLM (`--backend ollama|openai|ssh`) with the retrieved context.

Run any script with `--help` (where supported) or see `CLAUDE.md` for full per-script usage and flags.

`requirements.txt` pins `sentence_transformers`, `chromadb`, `paramiko`, and `einops`, needed before running `embed_and_ingest.py`, `query_rag.py`, `test_retrieval_embedding.py`, or `evaluate_retrieval_ragas.py`.

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
