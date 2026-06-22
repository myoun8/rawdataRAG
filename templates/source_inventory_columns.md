# Source Inventory Columns

Use these columns in each `source_inventory.csv` file.

| Column | Meaning |
|---|---|
| source_id | Stable unique ID, for example `CANDOR-001` |
| instrument | `CANDOR`, `VSANS`, `NSE`, or `COMMON` |
| workflow_stage | Controlled workflow category |
| title | Human-readable source title |
| source_type | Manual, web page, paper, notebook, code, video, example, FAQ |
| url_or_path | URL or relative path to original source |
| format | PDF, HTML, DOCX, Markdown, notebook, script, dataset, video |
| access_level | `public`, `internal`, or `restricted` |
| owner | Person or team responsible for accuracy |
| status | `current`, `legacy`, `deprecated`, `draft`, `needs_review`, or `archived` |
| version | Document version if known |
| last_updated | Source's own update date if known |
| last_reviewed | Review date by pack owner |
| priority | `high`, `medium`, or `low` |
| ingestion_status | `not_started`, `collected`, `normalized`, `chunked`, `validated`, `ingested`, `excluded` |
| notes | Free text notes |
