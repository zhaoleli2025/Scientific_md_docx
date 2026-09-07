---
name: scientific-md-docx
description: Create, translate, restructure, review, and render evidence-grounded scientific Markdown and DOCX documents. Use for clinical, biomedical, or AI study writing that needs publication search, source-backed claims, relative numeric citations, concise tables, readable workflows, audience-appropriate language, or reliable Markdown-to-Word conversion. Do not use it to invent evidence, replace domain-expert review, or treat formatting validation as scientific validation.
---

# Scientific Markdown and DOCX

Produce a clear Markdown source of truth and, when requested, a validated Word copy. Preserve the meaning and strength of the evidence while making the result concise enough for review, supervision, publication planning, or implementation.

## Route the request

Load only the guidance needed for the current deliverable:

- For online publication search, evidence selection, claim support, and citations, read [references/research-and-citations.md](references/research-and-citations.md).
- For language translation or technical-to-clinical/plain-language translation, read [references/scientific-translation.md](references/scientific-translation.md).
- For a rationale, evidence synthesis, protocol/rule, manuscript section, or supervisor brief, read [references/deliverables.md](references/deliverables.md).
- For tables, structured blocks, workflows, DOCX production, or conversion limits, read [references/document-production.md](references/document-production.md).

When the user supplies project rules, a protocol, reporting guideline, template, or house style, inspect it before drafting and treat it as project-specific authority. Link to the maintained source instead of copying a rulebook into this skill. Distinguish project rules from external scientific evidence.

## Authoring contract

1. Establish the deliverable, audience, language, intended use, evidence scope, and output files. Infer ordinary formatting preferences when they do not affect meaning.
2. Separate supplied facts/data, externally supported claims, derived results, interpretation, uncertainty, and recommendations. Never fill a gap with a plausible value or citation, and keep consequential conclusions subject to the appropriate expert review.
3. Search current evidence when the requested claims need external support. Use live online search rather than memory, prefer primary and authoritative sources, rank by relevance and evidential value rather than prestige alone, and keep a claim-to-source ledger while drafting.
4. Write the Markdown before rendering. Use prose for reasoning, tables for repeated fields or comparisons, code blocks for genuinely machine-readable material, and workflows for branching or ordered decisions. Put each table caption once, immediately above its table. Keep it to one concise sentence by default, and cite the direct source when the table is adapted or the caption makes an external claim.
5. Use the detection-rule citation convention by default: bracketed relative numbers in Markdown (`claim.[1–3]`), sources numbered by first appearance, and a static numbered bibliography. Keep bibliography numbering synchronized with the text.
6. Translate semantically before polishing style. Preserve numbers, units, direction, negation, temporality, uncertainty, source attribution, and citation attachment.
7. Make limitations and unresolved decisions visible. Provide an evidence-linked rationale suitable for expert review, not hidden chain-of-thought.
8. Standardize citations, validate the Markdown, and then render the DOCX. Report any unsupported feature or rendering fallback instead of silently losing content.

## Default output qualities

- Concise but not telegraphic: each sentence or table cell should perform one clear function.
- Scientifically calibrated: use association, prediction, diagnostic performance, and causation only when the evidence supports that wording.
- Understandable: define uncommon abbreviations once and explain the practical meaning after the technical result.
- Auditable: retain source locations, evidence limitations, document version, and unresolved questions when relevant.
- Portable: keep Markdown canonical; DOCX is a review or delivery artifact unless the user explicitly chooses another source of truth.

## Deterministic tools

Run these from the skill directory or by absolute path:

```bash
python scripts/standardize_citations.py report.md --in-place
python scripts/validate_markdown.py report.md --strict
python scripts/render_docx.py report.md --profile nature
```

This is the simplest detection-compatible path: readable bracketed citations remain in Markdown and become static Nature-style superscripts in DOCX. Rendering refuses to overwrite an existing DOCX unless `--force` is explicitly supplied. Use `--citation-style brackets` when brackets should also remain visible in Word.

The scripts validate document structure and rendering, not the truth of a clinical or scientific claim. Evidence review and human approval remain separate requirements.
