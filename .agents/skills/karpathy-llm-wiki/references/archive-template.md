---
type: Archived
title: {Title}
description: {One sentence}
tags: [{topic}]
sources:
  - id: {cited article slug}
    resource: {article1.md or ../other-topic/article2.md}
  - id: {cited article slug}
    resource: {article2.md}
generated: { by: process:wiki-ingest, at: YYYY-MM-DDTHH:MM:SSZ }
---

# {Title}

> Sources: [{Cited Article 1}](article1.md); [{Cited Article 2}](../other-topic/article2.md)
{Paths must be relative to this file: same-topic = filename only, cross-topic = ../other-topic/filename.md}
> Archived: {YYYY-MM-DD}

## Overview

{One paragraph summarizing the query and key findings.}

## {Body Sections}

{The synthesized answer, lightly edited for wiki context. This page is a point-in-time snapshot; it will not be cascade-updated when source articles change.}

{OPTIONAL — include this section only when cross-references exist:}

## See Also

{Cross-references to related wiki articles. Use relative links:
- Same topic: [Other Article](other-article.md)
- Different topic: [Other Article](../other-topic/other-article.md)}

## Frontmatter rules

- `type: Archived` distinguishes point-in-time snapshots from compiled articles.
- `sources`: one entry per cited wiki article, using the same file-relative paths as the body Sources links.
- `generated.at`: the archive date (the moment the snapshot was taken). Never refreshed — the page is a point-in-time record.
