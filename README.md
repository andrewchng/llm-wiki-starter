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

## Requirements

| Tool | Required? | Why |
|---|---|---|
| git | ✅ required | clone, commit history of your wiki |
| A coding agent | ✅ required | pi / Claude Code / etc. — writes and maintains the wiki |
| Python 3.8+ | ✅ required | retrieval tooling (`tools/retrieval/okf.py`) |
| bun | optional | runs the YouTube transcript scripts |
| yt-dlp | optional | fallback YouTube caption fetcher |
| Obsidian | optional | browse/read the wiki + Web Clipper for capturing articles |
| Ollama | optional | embeddings for smarter retrieval (`nomic-embed-text`) |

## Get started

### 1. Fork or clone this repo

```bash
# fork on GitHub, then:
git clone https://github.com/<you>/llm-wiki-starter.git my-wiki
cd my-wiki
```

Or use it as a template: click **Use this template** on GitHub.

### 2. Open it with your coding agent

Launch your agent **from inside this repo** — the bundled skills live in `.agents/skills/` and the agent picks them up automatically:

- **`karpathy-llm-wiki`** — the core workflow: ingest sources → compile wiki articles → query → lint.
- **`baoyu-youtube-transcript`** — fetch YouTube transcripts/subtitles for ingestion.
- **`wiki-ingest-next`** — the batch loop: process the queue in `to-transcribe-list.md` one item at a time.

Agent support:

- **[pi](https://github.com/badlogic/pi-mono)** — works out of the box. It reads `.agents/skills/` from the project root.
- **Claude Code** — it reads skills from `.claude/skills/`, so link them first:
  ```bash
  mkdir -p .claude && ln -s ../.agents/skills .claude/skills
  ```
- **Other agents** — any agent that can read a `SKILL.md` works; just copy or symlink `.agents/skills/` to wherever your agent looks for skills.

Verify it worked by asking your agent: *"What skills do you have available?"* — it should list the three above.

### 3. Ingest your first source

Just tell your agent:

> "Ingest this article/video into my wiki: <url>"

On the first ingest the agent initializes the wiki scaffolding (`raw/`, `wiki/index.md`, `wiki/log.md`) and then keeps everything compounding from there.

Each ingest produces a git commit (`docs(wiki): ingest <source>`), so your knowledge base has full history.

### 3b. Ask your wiki questions

Once you've ingested a few sources, the payoff:

> "What do I know about X?"
> "Summarize everything I've saved about topic Y"
> "Do my sources conflict on Z?"

The agent searches `wiki/` (and `raw/` if needed) and answers from your compiled knowledge — with links back to the source material.

### 4. (Optional) YouTube pipeline

To use the YouTube-to-wiki loop, install:

- [bun](https://bun.sh) — runs the transcript skill's scripts
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — fallback caption fetcher

Then maintain a queue in `to-transcribe-list.md` (pending URLs on top, done below) and say:

> "Ingest next"

The agent picks the next pending URL, transcribes it, ingests it, updates the list, and commits.

### 5. (Optional) Web articles — Obsidian Web Clipper

For articles, blogs, and essays, the easiest capture path is the [**Obsidian Web Clipper**](https://obsidian.md/clipper) browser extension (this is the flow Andrej Karpathy uses for his own LLM wiki):

1. Install the Obsidian Web Clipper in your browser (Chrome/Firefox/Safari).
2. Point it at this vault — set the default save location to `raw/<topic>/` inside this repo (create the topic folder if it doesn't exist).
3. On any article, hit the clipper — it saves a clean Markdown copy straight into `raw/`.

> 💡 Open this repo as an **Obsidian vault** too — then `wiki/` becomes a browsable, backlink-aware knowledge base you can read anytime.

Then just tell your agent:

> "Ingest the latest raw article into my wiki"

The `karpathy-llm-wiki` skill picks it up from `raw/` and compiles it into `wiki/` — same fetch → compile → index → log loop as everything else.

Don't use Obsidian? No problem — save any page as Markdown manually (or paste the text) into `raw/<topic>/` and ingest the same way. You can also queue article URLs in `to-transcribe-list.md` alongside YouTube videos and let the agent fetch them.

### 6. (Optional) Retrieval index

```bash
python3 tools/retrieval/okf.py reindex   # builds wiki.db
python3 tools/retrieval/okf.py query "your question"
```

Uses [Ollama](https://ollama.com) with `nomic-embed-text` if available; falls back to TF-IDF otherwise.

## Credits

- Workflow and structure based on Andrej Karpathy's "LLM wiki" idea.
- Skills: [`karpathy-llm-wiki`](https://github.com/astro-han/karpathy-llm-wiki) and [`baoyu-youtube-transcript`](https://github.com/jimliu/baoyu-skills) (pinned in `skills-lock.json`).
