#!/usr/bin/env python3
"""Simple retrieval test script for RAG knowledge pack chunks.

This script uses a lightweight TF-IDF style embedding and cosine similarity
vector search so the flow is:
  query -> embed query -> vector search -> return top chunks

Usage:
  python scripts/test_retrieval.py candor "How do I reduce CANDOR data?"
  python scripts/test_retrieval.py vsans "What is the VSANS Q-range?" --top 5
"""

from __future__ import annotations

import argparse
import math
import re
import time
from collections import Counter
from pathlib import Path

from _common import PACKS, load_eval_questions, load_jsonl_dir, write_csv

TOKEN_RE = re.compile(r"[a-z0-9']+")

EVAL_CSV_FIELDS = [
    'pack', 'top_n', 'queries', 'top1_accuracy', 'topk_accuracy',
    'mrr', 'avg_query_time', 'total_query_time', 'num_chunks', 'num_questions',
]


def load_chunks(pack_dir: Path) -> list[dict]:
    return load_jsonl_dir(pack_dir / 'chunks')


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if any(c.isalpha() for c in token)]


def build_vectors(chunks: list[dict]) -> tuple[list[dict], dict[str, float]]:
    doc_freq: dict[str, int] = {}
    tokenized_texts: list[list[str]] = []
    for chunk in chunks:
        tokens = tokenize(chunk.get('text', ''))
        tokenized_texts.append(tokens)
        unique_tokens = set(tokens)
        for token in unique_tokens:
            doc_freq[token] = doc_freq.get(token, 0) + 1

    num_docs = len(chunks)
    idf: dict[str, float] = {
        token: math.log((1 + num_docs) / (1 + count)) + 1.0 for token, count in doc_freq.items()
    }

    vectors: list[dict[str, float]] = []
    for tokens in tokenized_texts:
        tf = Counter(tokens)
        vector: dict[str, float] = {
            token: tf[token] * idf.get(token, 1.0) for token in tf
        }
        norm = math.sqrt(sum(value * value for value in vector.values()))
        if norm > 0:
            for token in vector:
                vector[token] /= norm
        vectors.append(vector)
    return vectors, idf


def embed_query(query: str, idf: dict[str, float]) -> dict[str, float]:
    tokens = tokenize(query)
    tf = Counter(tokens)
    vector: dict[str, float] = {}
    for token, count in tf.items():
        vector[token] = count * idf.get(token, 1.0)
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm > 0:
        for token in vector:
            vector[token] /= norm
    return vector


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(a[token] * b.get(token, 0.0) for token in a)


def query_chunk_vectors(chunks: list[dict], chunk_vectors: list[dict], idf: dict[str, float], query: str, top_n: int) -> list[tuple[float, dict]]:
    query_vector = embed_query(query, idf)
    if not query_vector:
        return []

    scored: list[tuple[float, dict]] = []
    for chunk, vector in zip(chunks, chunk_vectors):
        score = cosine_similarity(query_vector, vector)
        if score > 0.0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1].get('chunk_id', '')))
    return scored[:top_n]


def evaluate_retrieval(chunks: list[dict], questions: list[dict], top_n: int) -> dict[str, object]:
    chunk_vectors, idf = build_vectors(chunks)
    metrics = {
        'queries': 0,
        'top1_hits': 0,
        'topk_hits': 0,
        'mrr': 0.0,
        'total_query_time': 0.0,
        'details': [],
    }

    for question in questions:
        query_text = question.get('question', '')
        expected_sources = set(question.get('expected_sources', []))
        start = time.perf_counter()
        results = query_chunk_vectors(chunks, chunk_vectors, idf, query_text, top_n)
        elapsed = time.perf_counter() - start

        metrics['queries'] += 1
        metrics['total_query_time'] += elapsed

        hit_rank = 0
        for rank, (_, chunk) in enumerate(results, start=1):
            if chunk.get('source_id') in expected_sources:
                hit_rank = rank
                break

        if hit_rank:
            metrics['topk_hits'] += 1
            if hit_rank == 1:
                metrics['top1_hits'] += 1
            metrics['mrr'] += 1.0 / hit_rank

        metrics['details'].append({
            'question_id': question.get('question_id'),
            'query': query_text,
            'expected_sources': list(expected_sources),
            'top_hit_rank': hit_rank,
            'retrieved_source_ids': [chunk.get('source_id') for _, chunk in results],
            'elapsed_seconds': elapsed,
        })

    metrics['accuracy_topk'] = metrics['topk_hits'] / metrics['queries'] if metrics['queries'] else 0.0
    metrics['accuracy_top1'] = metrics['top1_hits'] / metrics['queries'] if metrics['queries'] else 0.0
    metrics['mrr'] = metrics['mrr'] / metrics['queries'] if metrics['queries'] else 0.0
    metrics['avg_query_time'] = metrics['total_query_time'] / metrics['queries'] if metrics['queries'] else 0.0
    return metrics


def print_eval_summary(metrics: dict[str, object], top_n: int) -> None:
    print(f"Evaluation results for top {top_n}")
    print(f"  queries: {metrics['queries']}")
    print(f"  top-1 accuracy: {metrics['accuracy_top1']:.3f}")
    print(f"  top-{top_n} accuracy: {metrics['accuracy_topk']:.3f}")
    print(f"  mean reciprocal rank: {metrics['mrr']:.3f}")
    print(f"  avg query time: {metrics['avg_query_time']:.4f}s")
    print(f"  total query time: {metrics['total_query_time']:.4f}s")


def evaluate_pack_to_row(pack_name: str, root: Path, top_n: int) -> dict[str, object]:
    pack_dir = root / pack_name
    chunks = load_chunks(pack_dir)
    questions = load_eval_questions(pack_dir)
    metrics = evaluate_retrieval(chunks, questions, top_n)
    return {
        'pack': pack_name,
        'top_n': top_n,
        'queries': metrics['queries'],
        'top1_accuracy': metrics['accuracy_top1'],
        'topk_accuracy': metrics['accuracy_topk'],
        'mrr': metrics['mrr'],
        'avg_query_time': metrics['avg_query_time'],
        'total_query_time': metrics['total_query_time'],
        'num_chunks': len(chunks),
        'num_questions': len(questions),
    }


def format_chunk(chunk: dict, score: float) -> str:
    metadata = chunk.get('metadata', {})
    return (
        f'chunk_id: {chunk.get("chunk_id")}\n'
        f'  score: {score:.4f}\n'
        f'  source_id: {chunk.get("source_id")}\n'
        f'  doc_id: {chunk.get("doc_id")}\n'
        f'  section: {metadata.get("section")}\n'
        f'  workflow_stage: {metadata.get("workflow_stage")}\n'
        f'  source_url_or_path: {metadata.get("source_url_or_path")}\n'
        f'  text_snippet: {chunk.get("text","").replace("\n", " ")[:320]}...\n'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='Test retrieval against a pack chunk set.')
    parser.add_argument('pack', nargs='?', help='Pack folder name (e.g. candor, common, nse, vsans)')
    parser.add_argument('query', nargs='?', help='Search query to test retrieval')
    parser.add_argument('--top', type=int, default=5, help='Number of top chunks to show')
    parser.add_argument('--evaluate', action='store_true', help='Run evaluation against pack eval questions')
    parser.add_argument('--evaluate-all', action='store_true', help='Run evaluation across candor, common, nse, vsans and save CSV')
    parser.add_argument('--output-csv', default='retrieval_results.csv', help='CSV path for evaluation results')
    parser.add_argument('--detail', action='store_true', help='Print per-question evaluation details')
    args = parser.parse_args()

    root = Path.cwd()
    if not args.evaluate_all and not args.pack:
        print('ERROR: pack is required unless --evaluate-all is used.')
        return 2

    pack_dir = None
    chunks = []
    if not args.evaluate_all:
        pack_dir = root / args.pack
        if not pack_dir.is_dir():
            print(f'ERROR: Pack directory not found: {pack_dir}')
            return 1

        chunks = load_chunks(pack_dir)
        if not chunks:
            print(f'No chunks loaded from {pack_dir / "chunks"}')
            return 1

    if args.evaluate_all:
        results: list[dict[str, object]] = []
        for pack_name in PACKS:
            row = evaluate_pack_to_row(pack_name, root, args.top)
            results.append(row)
        if not results:
            print('No evaluation results were generated.')
            return 1
        output_path = Path(args.output_csv)
        write_csv(results, EVAL_CSV_FIELDS, output_path)
        print(f'Wrote evaluation results for {len(results)} packs to {output_path}')
        return 0

    if args.evaluate:
        questions = load_eval_questions(pack_dir)
        if not questions:
            print(f'No eval questions found in {pack_dir / "eval"}')
            return 1

        metrics = evaluate_retrieval(chunks, questions, args.top)
        print_eval_summary(metrics, args.top)
        if args.detail:
            print('-' * 80)
            for detail in metrics['details']:
                print(f"question_id: {detail['question_id']}")
                print(f"  query: {detail['query']}")
                print(f"  expected_sources: {detail['expected_sources']}")
                print(f"  top_hit_rank: {detail['top_hit_rank']}")
                print(f"  retrieved_source_ids: {detail['retrieved_source_ids']}")
                print(f"  elapsed_seconds: {detail['elapsed_seconds']:.4f}")
                print('-' * 80)
        return 0

    if not args.query:
        print('ERROR: query is required unless --evaluate is used.')
        return 2

    print(f'[test_retrieval] query={args.query!r} top_n={args.top}')
    chunk_vectors, idf = build_vectors(chunks)
    start = time.perf_counter()
    results = query_chunk_vectors(chunks, chunk_vectors, idf, args.query, args.top)
    elapsed = time.perf_counter() - start

    if not results:
        print('No matching chunks found. Try a broader query or generate chunks first.')
        return 0

    print(f'Found {len(results)} matching chunks for query: {args.query!r}')
    print(f"[test_retrieval] timings=embed_query+score_chunks={elapsed:.4f}s")
    print('-' * 80)
    for score, chunk in results:
        print(format_chunk(chunk, score))
        print('-' * 80)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
