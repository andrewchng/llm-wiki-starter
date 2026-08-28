---
type: Article
title: {Title}
description: {One sentence}
tags: [{topic}]
sources:
  - id: {raw filename slug, date prefix removed}
    resource: ../../raw/{topic1}/{filename1}.md
    author: {Author1, YYYY-MM-DD}
    last_modified: YYYY-MM-DD
  - id: {raw filename slug, date prefix removed}
    resource: ../../raw/{topic2}/{filename2}.md
    author: {Author2, YYYY-MM-DD}
    last_modified: YYYY-MM-DD
generated: { by: process:wiki-ingest, at: YYYY-MM-DDTHH:MM:SSZ }
---

# {Title}

> Sources: {Author1, YYYY-MM-DD; Author2, YYYY-MM-DD}
> Raw: [{source1}](../../raw/{topic1}/{filename1}.md); [{source2}](../../raw/{topic2}/{filename2}.md)

## Overview

{One paragraph summarizing the key points of this article.}

## {Body Sections}

{Synthesize a coherent structure from the source material. Do not copy source text verbatim; distill and reorganize. Use blockquotes sparingly for particularly important original phrasing.}

{OPTIONAL — include this section only when cross-references exist:}

## See Also

{Cross-references to related wiki articles. Maintained during lint. Use relative links:
- Same topic: [Other Article](other-article.md)
- Different topic: [Other Article](../other-topic/other-article.md)}

## Frontmatter rules

The frontmatter is the machine-readable layer (OKF v0.2); the Sources/Raw lines in the body are the human-readable layer. Keep both in sync.

- `id`: slug of the raw filename with the `YYYY-MM-DD-` prefix removed, kebab-case. For `transcript.md` files, use the parent directory name.
- `author`: the matching entry from the Sources line, when sources and raw files correspond one-to-one in order. Omit the key when they do not.
- `last_modified`: the source's own date (from the filename or the Sources entry). Omit when unknown.
- `generated.at`: ISO 8601 timestamp of the last content change. Refresh it on every merge or update, not just creation.
- `verified`: add `verified: { by: human:{name}, at: YYYY-MM-DDTHH:MM:SSZ }` only when the user explicitly confirms the content. Ingest never adds it.
- `stale_after`: optional `YYYY-MM-DD` for fast-moving topics (earnings, news, prices). Omit for stable content.
- Paths in frontmatter use the same file-relative convention as body links (`../../raw/...`).
