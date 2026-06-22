# Document Review Checklist

Use this before marking a source or chunk set as production-ready.

## Source-level review

- [ ] Source has a stable `source_id`.
- [ ] Source owner is identified.
- [ ] Access level is correct.
- [ ] Current versus legacy status is correct.
- [ ] Version/date information is captured when available.
- [ ] Source is relevant to the instrument or shared common pack.

## Normalized-document review

- [ ] Markdown text is clean and readable.
- [ ] Tables, captions, equations, and code blocks are preserved.
- [ ] Procedures are complete and not split incorrectly.
- [ ] Safety, access, or operational warnings are preserved.
- [ ] YAML frontmatter is complete.

## Chunk review

- [ ] Each chunk can stand alone.
- [ ] Each chunk has source traceability.
- [ ] Chunk metadata is correct.
- [ ] No public chunk contains internal or restricted details.
- [ ] Legacy content is not marked as current.

## RAG-answer review

- [ ] Answers cite the expected source.
- [ ] Answers do not mix instruments incorrectly.
- [ ] Answers distinguish reduction from analysis.
- [ ] Answers distinguish current from legacy workflows.
- [ ] Answers do not invent procedures not present in sources.
