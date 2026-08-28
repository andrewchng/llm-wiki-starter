# LLM Wiki Starter

An empty, ready-to-fork starter kit for building a **personal LLM-powered knowledge base** — the "Karpathy wiki" pattern: *the LLM writes and maintains the wiki; the human reads and asks questions.*

You feed sources in, an LLM agent compiles them into wiki articles, and the knowledge base compounds over time.

## How it works

```
raw/          Immutable source material (transcripts, articles, notes)
wiki/         Compiled knowledge articles (OKF frontmatter + index + log)
.agents/      Agent skills that drive the workflow
tools/        Retrieval index over the wiki (SQLite FTS5 + embeddings)
```

- **`raw/<topic>/`** — sources you never modify after saving. One file per source.
- **`wiki/<topic>/`** — articles written and maintained by the agent, with machine-readable frontmatter, a global `wiki/index.md`, and an append-only `wiki/log.md`.
- **`tools/retrieval/okf.py`** — builds a hybrid retrieval index (`wiki.db`) from the frontmatter so the agent can query the wiki deterministically.

## Get started

### 1. Fork or clone this repo

```bash
# fork on GitHub, then:
git clone https://github.com/<you>/llm-wiki-starter.git my-wiki
cd my-wiki
```

Or use it as a template: click **Use this template** on GitHub.

### 2. Open it with your coding agent

Works with any agent that reads `.agents/skills/` (e.g. [pi](https://github.com/badlogic/pi-mono), Claude Code, etc.). The two bundled skills are picked up automatically:

- **`karpathy-llm-wiki`** — the core workflow: ingest sources → compile wiki articles → query → lint.
- **`baoyu-youtube-transcript`** — fetch YouTube transcripts/subtitles for ingestion.

### 3. Ingest your first source

Just tell your agent:

> "Ingest this article/video into my wiki: <url>"

On the first ingest the agent initializes the wiki scaffolding (`raw/`, `wiki/index.md`, `wiki/log.md`) and then keeps everything compounding from there.

### 4. (Optional) YouTube pipeline

To use the YouTube-to-wiki loop, install:

- [bun](https://bun.sh) — runs the transcript skill's scripts
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — fallback caption fetcher

Then maintain a queue in `to-transcribe-list.md` (pending URLs on top, done below) and say:

> "Ingest next"

The agent picks the next pending URL, transcribes it, ingests it, updates the list, and commits.

### 5. (Optional) Retrieval index

```bash
python3 tools/retrieval/okf.py reindex   # builds wiki.db
python3 tools/retrieval/okf.py query "your question"
```

Uses [Ollama](https://ollama.com) with `nomic-embed-text` if available; falls back to TF-IDF otherwise.

## Credits

- Workflow and structure based on Andrej Karpathy's "LLM wiki" idea.
- Skills: [`karpathy-llm-wiki`](https://github.com/astro-han/karpathy-llm-wiki) and [`baoyu-youtube-transcript`](https://github.com/jimliu/baoyu-skills) (pinned in `skills-lock.json`).
