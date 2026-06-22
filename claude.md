# rag-knowledge-pack-template

A RAG knowledge-pack template for NIST NCNR neutron-scattering instrument documentation. Four packs: `candor/`, `vsans/`, `nse/` (instrument-specific) and `common/` (shared NICE/NCNR-wide docs).

## Pack structure (per `PACK_STRUCTURE.md`)

Each pack (`<pack>/`) contains:
- `README.md`, `source_inventory.csv`, `manifest.jsonl`, `glossary.yaml`, `access_policy.yaml`, `ingest_config.yaml`
- `originals/` — unmodified source material (web_pages, pdfs, papers, manuals, notebooks, scripts, data_examples)
- `normalized/` — Markdown docs with YAML frontmatter (doc_id, source_id, instrument, workflow_stage, source_type, access_level, status, owner, last_reviewed, source_url_or_path, citation_required), organized into stage subfolders (overview, instrument_control, experiment_planning, data_access/raw_data, metadata, sample_environment, troubleshooting, citations_publications, etc.)
- `chunks/` — JSONL chunk records (chunk_id, doc_id, source_id, text, metadata) generated from `normalized/`
- `eval/` — JSONL evaluation questions for retrieval testing
- `review/` — review artifacts

Schemas for these record types live in `schemas/`.

## Scripts (`scripts/`)

- `chunk_markdown.py` — splits `normalized/**/*.md` by H2 headings into `<pack>_chunks.generated.jsonl`. Stdlib only.
- `embed_and_ingest.py` — embeds every pack's `chunks/*_chunks.jsonl` with `BAAI/bge-large-en-v1.5` (via `sentence_transformers`) and loads them into a Chroma `PersistentClient` at `./chroma_db` (collection `ncnr_rag`). Requires `sentence_transformers` and `chromadb` (not pinned anywhere — install manually).
- `test_retrieval.py` — stdlib-only TF-IDF retrieval/evaluation tool.
  - `python scripts/test_retrieval.py <pack> "<query>" [--top N]` — single query
  - `python scripts/test_retrieval.py <pack> --evaluate [--detail]` — evaluate one pack against its eval questions
  - `python scripts/test_retrieval.py --evaluate-all [--output-csv file.csv]` — evaluate all packs, writes `retrieval_results.csv`
  - Loads ALL `*.jsonl` files under a pack's `chunks/` dir, so a pack must not contain duplicate/derived chunk files alongside the canonical one.
- `validate_pack.py` — validates a pack's required files/dirs, JSONL syntax, chunk/metadata field completeness, and cross-references chunk `source_id`s against `source_inventory.csv`. Run as `python scripts/validate_pack.py <pack>`.
- `query_rag.py` — end-to-end RAG query against a self-hosted Ollama LLM. Embeds the query with `BAAI/bge-large-en-v1.5`, retrieves from the Chroma `ncnr_rag` collection (filtered by `status=current`, `access_level` cascade, optional `instrument`/pack), then calls a local Ollama model (`ollama serve`) with the retrieved chunks as context. Requires `embed_and_ingest.py` to have been run first, plus `sentence_transformers` and `chromadb`. Run as `python scripts/query_rag.py "<question>" [--pack candor] [--top N] [--model llama3.2] [--access-level public|internal|restricted]`.
- `test_retrieval_embedding.py` — embedding-based counterpart to `test_retrieval.py`'s TF-IDF evaluation: runs each pack's `eval/*.jsonl` questions against the Chroma `ncnr_rag` collection (via `embed_and_ingest.py` output) and reports top-1/top-k accuracy and MRR, for apples-to-apples comparison with the TF-IDF baseline. Requires `chromadb` and `sentence_transformers`. Run as `python scripts/test_retrieval_embedding.py <pack> --evaluate [--detail]` or `--evaluate-all [--output-csv file.csv]`.
- `evaluate_retrieval_ragas.py` — embedding-based retrieval evaluation using RAGAS-standard Context Precision@K and Context Recall, computed directly from each eval question's `expected_sources` ground truth (no fuzzy text-similarity approximation). Requires `embed_and_ingest.py` to have been run first. Run as `python scripts/evaluate_retrieval_ragas.py <pack> [--top N] [--detail]` or `--evaluate-all [--output-csv file.csv]`.

No `requirements.txt` exists; `sentence_transformers` and `chromadb` must be installed manually before running `embed_and_ingest.py`, `query_rag.py`, `test_retrieval_embedding.py`, or `evaluate_retrieval_ragas.py`. `query_rag.py` additionally requires a running Ollama instance with a pulled model.
