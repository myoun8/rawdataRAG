# Pack Structure

Each instrument folder follows this layout:

```text
<pack>/
  glossary.yaml
  access_policy.yaml
  ingest_config.yaml
  originals/
    web_pages/
    pdfs/
    papers/
    manuals/
    notebooks/
    scripts/
    data_examples/
  normalized/
    overview/
    instrument_control/
    experiment_planning/
    sample_environment/
    raw_data/
    metadata/
    data_reduction/
    data_analysis/
    troubleshooting/
    examples/
    citations_publications/
    software_installation/
    developer_reference/
  chunks/
  eval/
  review/
```

## Required metadata fields

Every normalized Markdown document should have frontmatter with these fields:

```yaml
doc_id: unique_document_id
source_id: SOURCE-001
instrument: CANDOR | VSANS | NSE | COMMON
workflow_stage: data_reduction
source_type: manual | web_page | paper | notebook | code | video | example | faq
software: NICE | Reductus | Refl1D | Igor | SasView | DAVE | none
access_level: public | internal | restricted
status: current | legacy | deprecated | draft | needs_review | archived
owner: person_or_team
last_reviewed: YYYY-MM-DD
source_url_or_path: originals/path/or/source/url
citation_required: true | false
```

## Chunk record fields

Each JSONL chunk should contain:

```json
{
  "chunk_id": "stable_unique_id",
  "doc_id": "source_document_id",
  "source_id": "inventory_source_id",
  "text": "standalone chunk text",
  "metadata": {
    "instrument": "CANDOR",
    "workflow_stage": "data_reduction",
    "source_type": "manual",
    "software": "Reductus",
    "access_level": "internal",
    "status": "current",
    "owner": "CANDOR team",
    "last_reviewed": "2026-06-12",
    "source_url_or_path": "originals/manuals/example.pdf",
    "section": "Procedure",
    "citation_required": false
  }
}
```
