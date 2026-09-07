# Research, evidence, and citations

Use this guide when the document needs online publication search or externally supported claims. Skip searching when the task is only formatting or translating fully supplied content.

## Frame and search

Define the smallest answerable question. For a clinical study, identify population, intervention/exposure or finding, comparator, outcome, setting, and time horizon. For an AI study, identify task, data domain, reference standard, model/intervention, comparator, evaluation setting, and metrics.

Choose a proportionate depth:

- **Targeted:** a narrow claim, usually 3–8 strong sources.
- **Focused:** a broader synthesis with disagreements and recent developments, usually 10–25 sources.
- **Protocol-driven:** predefined databases, queries, screening, and extraction. Call a search systematic only when those requirements were met.

Search with live tools rather than memory when evidence is requested or may have changed:

1. Expand synonyms, acronyms, controlled vocabulary, model/dataset names, and predecessor terms.
2. Search several focused queries, including recent and seminal searches when both matter.
3. For biomedical work, prioritize PubMed/MEDLINE, applicable guidelines/regulators, trial registries, and publisher records. For AI work, prioritize original papers, official repositories/model cards, dataset documentation, standards, and independent validations.
4. Open the source record or full text; never support a claim from a search snippet alone.
5. Follow backward references and forward citations for foundational work, updates, validation, corrections, and retractions.
6. Deduplicate by DOI, PMID, registry ID, or normalized title.
7. Record search date, main queries, sources searched, and access limitations when reproducibility matters.

Stop when central claims, credible disagreements, and material limitations are covered and new results are redundant.

## Select and extract evidence

Rank sources by:

1. direct relevance to the exact claim and population/data domain;
2. authority and study design;
3. methodological credibility;
4. applicability to the current setting, device, dataset, or model version;
5. external validation, replication, and reproducibility;
6. currency, correction, retraction, or supersession status;
7. influence or journal standing only as a tie-breaker.

Do not equate journal impact with evidential quality. Classify candidates as **essential**, **supporting**, **contextual**, or **excluded**. Preserve contradictory high-quality evidence.

For each essential source, capture only what the document needs:

| Claim | Source/location | Design and population/data | Main result | Applicability | Limitation |
|---|---|---|---|---|---|
| Exact proposed statement | DOI/PMID/URL and page/table/section | Study type and relevant sample | Result with uncertainty | Direct or indirect | Main constraint |

Use this working ledger to prevent citation drift; include it in the final document only when useful. Mark abstract-only evidence and avoid claims requiring unavailable methods or subgroup detail.

## Write supported claims

- Verify that each source directly supports the nearby wording.
- Use guidelines or syntheses for broad conclusions and primary studies for study-specific numbers or methods.
- Cite reporting guidance for reporting requirements, not efficacy.
- Label protocols, preprints, simulations, retrospective evidence, and project hypotheses.
- Do not turn association into causation, nonsignificance into equivalence, or model performance into clinical utility.
- Separate publications from local rules, unpublished results, and author interpretation.
- Never invent a publication, identifier, author, result, or citation count.

## Detection-style relative citations

Use bracketed numbers in Markdown, ordered by first appearance:

```text
The first supported claim ends here.[1] Several sources may support another claim.[2,3]
Consecutive sources are compressed.[4–6]
```

Reuse the same number for the same source. Put citations immediately after the supported claim and punctuation. Keep them out of headings, code/YAML/JSON, and Mermaid nodes; cite the explanatory sentence or figure note instead.

Place one numbered entry per source under `## References`, retaining a DOI, PMID, version, or stable URL when available. Never manufacture missing metadata. During web research, use normal source links in conversation; in the Markdown artifact, map the same verified sources to this numbered bibliography.

Before delivery, run the citation standardizer and strict validator listed in `SKILL.md`.

The standardizer renumbers existing citations and bibliography entries. It does not discover evidence, merge duplicate publications, or verify claim support.
