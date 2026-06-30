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
3. Add your Groq API key to a `.env` file in the repo root: `GROQ_API_KEY=gsk_...`
4. Run `python scripts/run_pipeline.py [--pack <pack>]` — this chains all four steps automatically:
   - Converts originals to normalized Markdown via the Groq API (interactive: confirms stage per file)
   - Chunks `normalized/**/*.md` into JSONL
   - Validates pack structure, JSONL syntax, and metadata
   - Embeds all chunks and loads them into the local Chroma vector store
5. Use `python scripts/query_rag.py "<question>" [--pack <pack>]` for end-to-end RAG question answering.

Individual steps can also be run directly — see **Scripts** below.

## Scripts (`scripts/`)

- `run_pipeline.py` — **main entry point**; chains all four ingestion steps in order. Reads `GROQ_API_KEY` from `.env` or the environment. Flags: `--pack`, `--model` (default: `moonshotai/kimi-k2-instruct`), `--skip-normalize`, `--skip-validate`, `--dry-run`.
- `full_document_ingestion.py` — converts files in `originals/` to normalized Markdown using the Groq API. Interactive: streams each file's output and asks you to confirm the workflow stage before writing. Args: `--model NAME` (required), `[--api-key KEY]`, `[--pack PACK]`, `[--dry-run]`. API key falls back to `GROQ_API_KEY` env var.
- `chunk_markdown.py <pack>` — stdlib-only heading-based chunker; splits `normalized/**/*.md` by H2 headings into `<pack>_chunks.generated.jsonl`.
- `validate_pack.py <pack>` — validates a pack's required files/dirs, JSONL syntax, chunk/metadata completeness, and cross-references chunk `source_id`s against `source_inventory.csv`.
- `embed_and_ingest.py` — embeds every pack's `chunks/*_chunks.jsonl` with `nomic-embed-text` via Ollama and loads them into a Chroma `PersistentClient` at `./chroma_db` (collection `ncnr_rag`). Requires Ollama running with `nomic-embed-text` pulled.
- `test_retrieval_embedding.py` — embedding-based retrieval evaluation against the Chroma collection from `embed_and_ingest.py`; reports top-1/top-k accuracy and MRR.
- `evaluate_retrieval_ragas.py` — embedding-based retrieval evaluation using RAGAS-standard Context Precision@K and Context Recall against each eval question's `expected_sources`.
- `query_rag.py "<question>"` — end-to-end RAG query: embeds the question, retrieves filtered chunks from Chroma, and calls an LLM (`--backend ollama|openai|ssh`) with the retrieved context.

Run any script with `--help` or see `CLAUDE.md` for full per-script usage and flags.

`requirements.txt` pins `chromadb`, `paramiko`, `groq`, `pypdf`, and the LangChain integration packages needed for embedding, vectorstore, and chat-model access.

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
