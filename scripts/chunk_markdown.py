#!/usr/bin/env python3
"""Create simple heading-based JSONL chunks from normalized Markdown.

This is a starter utility. It intentionally avoids external dependencies.
For production, replace or extend it with your preferred parser and chunking policy.

Usage:
  python scripts/chunk_markdown.py candor
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)
HEADING_RE = re.compile(r'^(#{1,3})\s+(.+?)\s*$', re.MULTILINE)


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end():]
    meta: Dict[str, object] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        if value.lower() == 'true':
            meta[key] = True
        elif value.lower() == 'false':
            meta[key] = False
        else:
            meta[key] = value
    return meta, body


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r'[^a-z0-9]+', '_', value)
    return value.strip('_') or 'section'


def split_by_h2(body: str) -> List[Tuple[str, str]]:
    # Keep H1 title as context, split primarily on H2 headings.
    h1 = ''
    h1_match = re.search(r'^#\s+(.+?)\s*$', body, flags=re.MULTILINE)
    if h1_match:
        h1 = h1_match.group(1).strip()

    matches = list(re.finditer(r'^##\s+(.+?)\s*$', body, flags=re.MULTILINE))
    if not matches:
        return [(h1 or 'Document', body.strip())]

    chunks: List[Tuple[str, str]] = []
    intro = body[:matches[0].start()].strip()
    if intro:
        chunks.append(('Overview', intro))
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        section_title = match.group(1).strip()
        section_body = body[start:end].strip()
        if h1:
            section_body = f'# {h1}\n\n{section_body}'
        chunks.append((section_title, section_body))
    return chunks


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2
    root = Path.cwd()
    pack = sys.argv[1]
    pack_dir = root / pack
    norm_dir = pack_dir / 'normalized'
    if not norm_dir.is_dir():
        print(f'ERROR: normalized directory not found: {norm_dir}')
        return 1

    rows = []
    for md_path in sorted(norm_dir.rglob('*.md')):
        raw = md_path.read_text(encoding='utf-8')
        meta, body = parse_frontmatter(raw)
        doc_id = str(meta.get('doc_id') or slugify(md_path.stem))
        source_id = str(meta.get('source_id') or 'UNKNOWN')
        sections = split_by_h2(body)
        for i, (section, section_text) in enumerate(sections, start=1):
            metadata = {
                'instrument': str(meta.get('instrument') or pack.upper()),
                'workflow_stage': str(meta.get('workflow_stage') or md_path.parent.name),
                'source_type': str(meta.get('source_type') or 'unknown'),
                'software': str(meta.get('software') or 'none'),
                'access_level': str(meta.get('access_level') or 'internal'),
                'status': str(meta.get('status') or 'needs_review'),
                'owner': str(meta.get('owner') or 'unknown'),
                'last_reviewed': str(meta.get('last_reviewed') or ''),
                'source_url_or_path': str(meta.get('source_url_or_path') or str(md_path)),
                'section': section,
                'citation_required': bool(meta.get('citation_required', False)),
            }
            text = f'{doc_id} > {section}\n\n{section_text.strip()}'
            rows.append({
                'chunk_id': f'{doc_id}__{slugify(section)}__{i:03d}',
                'doc_id': doc_id,
                'source_id': source_id,
                'text': text,
                'metadata': metadata,
            })

    out_dir = pack_dir / 'chunks'
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f'{pack}_chunks.generated.jsonl'
    with out_path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(f'Wrote {len(rows)} chunks to {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
