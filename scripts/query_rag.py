"""
Query the NCNR RAG knowledge pack with a self-hosted Ollama LLM.

Prerequisites:
  1. Ollama installed and running  (ollama serve)
  2. A model pulled               (ollama pull llama3.2)
  3. Chroma DB populated          (python scripts/embed_and_ingest.py)
  4. pip install sentence-transformers chromadb

Usage:
  python scripts/query_rag.py "<question>"
  python scripts/query_rag.py "<question>" --pack candor --top 6 --model llama3.2
  python scripts/query_rag.py "<question>" --access-level internal
"""

import argparse
import json
import urllib.request
import urllib.error
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
except ImportError as exc:
    raise SystemExit(
        f"Missing dependency: {exc}\n"
        "Run: pip install sentence-transformers chromadb"
    )

# ── Config ───────────────────────────────────────────────────────────────────
EMBED_MODEL   = "BAAI/bge-large-en-v1.5"
DEVICE        = "cpu"
CHROMA_PATH   = Path(__file__).parent.parent / "chroma_db"
COLLECTION    = "ncnr_rag"
OLLAMA_URL    = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.2"
DEFAULT_TOP   = 5

# BGE-large-en-v1.5: documents use no prefix; queries use this instruction prefix
# to align asymmetric retrieval (see BAAI/bge-large-en-v1.5 model card).
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# access_level cascade: each level includes all levels below it
ACCESS_LEVEL_MAP = {
    "public":     ["public"],
    "internal":   ["public", "internal"],
    "restricted": ["public", "internal", "restricted"],
}

SYSTEM_PROMPT = (
    "You are an expert assistant for NIST NCNR neutron-scattering instruments. "
    "Answer questions using ONLY the facts in the context provided below — do not invent "
    "facts that aren't there. The context may describe the relevant information using "
    "different terminology than the question (e.g. a question about \"beamline parameters\" "
    "may be answered by a \"Specifications / Capabilities\" section) — use your judgment to "
    "connect the question to relevant context even when exact wording differs. "
    "Only say the information isn't available if no context chunk is actually relevant. "
    "Cite your sources inline using [source_id] notation after relevant statements."
)
# ─────────────────────────────────────────────────────────────────────────────


def embed_query(model, query: str) -> list:
    return model.encode(
        BGE_QUERY_PREFIX + query,
        normalize_embeddings=True,
    ).tolist()


def build_chroma_filter(access_level: str, pack: str | None) -> dict:
    conditions = [
        {"status": {"$eq": "current"}},
        {"access_level": {"$in": ACCESS_LEVEL_MAP[access_level]}},
    ]
    if pack:
        conditions.append({"instrument": {"$eq": pack.upper()}})
    return {"$and": conditions}


def build_context(results: dict) -> tuple[str, list[dict]]:
    chunks = []
    for text, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({
            "source_id": meta.get("source_id", "unknown"),
            "section":   meta.get("section", ""),
            "url":       meta.get("source_url_or_path", ""),
            "text":      text,
        })
    context_str = "\n\n---\n\n".join(
        f"[{c['source_id']}] {c['section']}\n{c['text']}" for c in chunks
    )
    return context_str, chunks


def call_ollama(model_name: str, user_message: str) -> str:
    payload = json.dumps({
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())["message"]["content"]
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Cannot reach Ollama at {OLLAMA_URL}\n"
            f"Is it running? Try: ollama serve\n{exc}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Query the NCNR RAG knowledge pack via a local Ollama LLM."
    )
    parser.add_argument("query", help="Natural-language question")
    parser.add_argument(
        "--pack",
        metavar="PACK",
        help="Filter by instrument pack: candor, vsans, nse, common (default: all)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_TOP,
        metavar="N",
        help=f"Number of chunks to retrieve (default: {DEFAULT_TOP})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--access-level",
        choices=list(ACCESS_LEVEL_MAP),
        default="public",
        dest="access_level",
        help="Maximum access level to include (default: public)",
    )
    args = parser.parse_args()

    if not CHROMA_PATH.exists():
        raise SystemExit(
            f"Chroma DB not found at {CHROMA_PATH}\n"
            "Run: python scripts/embed_and_ingest.py"
        )

    print(f"Loading embedding model {EMBED_MODEL} ...")
    embed_model = SentenceTransformer(EMBED_MODEL, device=DEVICE)

    print("Connecting to Chroma ...")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        collection = client.get_collection(COLLECTION)
    except Exception:
        raise SystemExit(
            f"Collection '{COLLECTION}' not found in {CHROMA_PATH}\n"
            "Run: python scripts/embed_and_ingest.py"
        )

    where_filter = build_chroma_filter(args.access_level, args.pack)
    query_vec    = embed_query(embed_model, args.query)

    print(f"Retrieving top {args.top} chunks ...")
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=args.top,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    if not results["documents"][0]:
        raise SystemExit("No chunks matched the query and filters. Try relaxing --access-level or --pack.")

    context_str, chunks = build_context(results)
    user_message = f"Context:\n{context_str}\n\nQuestion: {args.query}"

    print(f"Calling Ollama ({args.model}) ...\n")
    answer = call_ollama(args.model, user_message)

    print("=" * 60)
    print(answer)
    print("=" * 60)
    print("\nSources:")
    for c in chunks:
        label = f"  [{c['source_id']}]"
        if c["section"]:
            label += f" {c['section']}"
        if c["url"]:
            label += f" — {c['url']}"
        print(label)


if __name__ == "__main__":
    main()
