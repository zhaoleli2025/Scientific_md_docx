# Document production

Use this guide to turn approved scientific content into concise Markdown structures and a validated DOCX. Keep Markdown as the canonical editable source.

## Choose the clearest form

- Use prose for a short explanation or integrated reasoning.
- Use a table for repeated fields, comparisons, thresholds/actions, evidence matrices, or timelines.
- Use a workflow for three or more dependent steps, decisions, retries, or state changes.
- Use fenced blocks only when literal structure matters: code, commands, equations, pseudocode, JSON, YAML, schemas, or report examples.

## Tables

Build each table around one question. Use informative headers, parallel grammar, and consistent vocabulary. One cell should normally contain one result plus one essential qualifier; move extended methods, exceptions, and interpretation into a note.

Useful patterns include:

| Purpose | Useful columns |
|---|---|
| Evidence summary | Claim; source; main finding; applicability; limitation |
| Clinical/technical rationale | Domain; evidence; interpretation; uncertainty; action/review |
| Model comparison | Model/data; comparator; metric; result; validation; limitation |
| Decision rule | Condition; interpretation; action; exception/review |

State shared units in headers, explain abbreviations below the table, and cite the claim-bearing cell or introductory sentence. Preserve `not available`, `not assessed`, `not detected`, and `not applicable` as distinct states. Split a table rather than filling it with paragraph-length cells.

## Structured blocks and workflows

Add a language label to every fenced block. Make placeholders visibly different from actual study or case values. Do not use code blocks merely to place a border around prose.

Use Mermaid for branching workflows:

```mermaid
flowchart TD
    A[Verified inputs] --> B{Evidence sufficient?}
    B -->|Yes| C[Synthesize]
    B -->|No| D[State limitation]
    C --> E[Expert review or output]
    D --> E
```

Use actions for process nodes, questions for decisions, and labels for every branch. Show meaningful failure, unavailable-data, stop, and review routes. Put citations in the accompanying sentence or figure note, not inside Mermaid nodes. Confirm that prose, tables, structured blocks, and workflows express the same states and outcomes.

## Render to DOCX

The bundled renderer supports headings, paragraphs, blockquotes, basic lists, inline emphasis/code/simple mathematics, links, numeric citations, pipe tables with escaped pipes, fenced blocks, Mermaid, local PNG/JPEG images, and numbered references.

It does not create live Zotero fields, tracked changes, footnotes/endnotes, complex Word equations, merged Markdown table cells, or remote-image downloads. Use a specialized pipeline when those features are essential.

Run the detection-compatible path:

```bash
python scripts/standardize_citations.py report.md --in-place
python scripts/validate_markdown.py report.md --strict
python scripts/render_docx.py report.md --profile nature
```

Profiles:

- `nature`: Times New Roman, static superscript citations, three-line tables; default.
- `scientific`: Times New Roman, bracketed citations, three-line tables.
- `clinical`: Arial with compact grid tables.
- `supervisor`: Aptos with a presentation-oriented layout.

Options can override font, size, citation/table style, orientation, or a clean DOCX template. Mermaid `auto` renders when possible and otherwise preserves the source as code with a warning; use `--mermaid render` to fail instead. Existing outputs require explicit `--force` to replace.

## Final check

Verify that headings, tables, figures, code, citations, and references are present; wide tables are legible; citation markers still support the same claims; code indentation is preserved; diagram branches match the source; no fallback warning was missed; and Word or LibreOffice opens the file. Structural validation cannot establish scientific truth or translation fidelity.
