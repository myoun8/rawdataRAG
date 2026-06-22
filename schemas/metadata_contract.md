# Metadata Contract

This contract defines the fields that should be carried from source inventory to normalized Markdown to JSONL chunks.

## Required fields

- `source_id`
- `doc_id`
- `instrument`
- `workflow_stage`
- `source_type`
- `access_level`
- `status`
- `source_url_or_path`

## Strongly recommended fields

- `software`
- `owner`
- `last_reviewed`
- `version`
- `section`
- `citation_required`

## Controlled values

### instrument

- `COMMON`
- `CANDOR`
- `VSANS`
- `NSE`

### access_level

- `public`
- `internal`
- `restricted`

### status

- `current`
- `legacy`
- `deprecated`
- `draft`
- `needs_review`
- `archived`

### ingestion_status

- `not_started`
- `collected`
- `normalized`
- `chunked`
- `validated`
- `ingested`
- `excluded`
