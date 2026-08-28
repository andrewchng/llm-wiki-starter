# LLM Wiki Starter

An empty, ready-to-fork starter kit for building a **personal LLM-powered knowledge base** — the "Karpathy wiki" pattern: *the LLM writes and maintains the wiki; the human reads and asks questions.*

You feed sources in, an LLM agent compiles them into wiki articles, and the knowledge base compounds over time.

## 🚀 Quick start: one prompt

Open your coding agent in an **empty directory** and paste this. The prompt handles everything: getting your own copy of the repo, verifying the setup, initializing the wiki, and teaching you how to use it.

```text
I want to set up my personal LLM wiki using the template at
https://github.com/andrewchng/llm-wiki-starter (the "karpathy-llm-wiki" pattern).

STEP A — Get my own copy:
- Check if the current directory already is a wiki repo (it has
  .agents/skills/karpathy-llm-wiki). If so, skip this step.
- Otherwise: if the `gh` CLI is available and authenticated, create my own
  repo from the template (gh repo create llm-wiki --template
  andrewchng/llm-wiki-starter --clone --private, ask me first about the name
  and visibility), then work inside it.
- If `gh` is not available: tell me to click "Use this template" on the
  template page, wait for me to confirm, then git clone my new repo and
  work inside it.

STEP B — Verify the setup, inside the repo:
- Check that you can see the bundled skills: karpathy-llm-wiki,
  baoyu-youtube-transcript, and wiki-ingest-next. If you can't find them,
  tell me how to fix it (hint: they live in .agents/skills/, and
  .claude/skills should be a symlink there — run ./setup.sh if missing).

STEP C — Initialize:
- wiki/index.md and wiki/log.md should exist. Create them only if missing;
  never overwrite existing content.

STEP D — Teach me:
- Give me a 60-second tour of this repo: what raw/ and wiki/ are for,
  and what you will do on each ingest (fetch -> compile -> index -> log -> commit).
- Teach me the 4 ways I'll use you from now on, with example prompts:
  - Ingest a source: "Ingest this article/video into my wiki: <url>"
  - Batch process my YouTube queue in to-transcribe-list.md: "Ingest next"
  - Ask my own knowledge: "What do I know about <topic>?"
  - Keep it healthy: "Lint my wiki"

Then confirm everything is ready and wait for my first source.
```

That's it. Everything below is reference material — read it if you want to understand what just happened.

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
| `gh` CLI | optional | lets the one-prompt setup create your repo from the template automatically |
| bun | optional | runs the YouTube transcript scripts |
| yt-dlp | optional | fallback YouTube caption fetcher |
| Obsidian | optional | browse/read the wiki + Web Clipper for capturing articles |
| Ollama | optional | embeddings for smarter retrieval (`nomic-embed-text`) |

## Day-to-day usage

### Ingest your first source

Just tell your agent:

> "Ingest this article/video into my wiki: <url>"

The agent fetches it into `raw/`, compiles it into `wiki/`, updates the index and log, and commits (`docs(wiki): ingest <source>`) — so your knowledge base has full history.

### Ask your wiki questions

Once you've ingested a few sources, the payoff:

> "What do I know about X?"
> "Summarize everything I've saved about topic Y"
> "Do my sources conflict on Z?"

The agent searches `wiki/` (and `raw/` if needed) and answers from your compiled knowledge — with links back to the source material.

### (Optional) YouTube pipeline

Install [bun](https://bun.sh) (runs the transcript skill's scripts) and [yt-dlp](https://github.com/yt-dlp/yt-dlp) (fallback caption fetcher). Then maintain a queue in `to-transcribe-list.md` (pending URLs on top, done below) and say:

> "Ingest next"

The agent picks the next pending URL, transcribes it, ingests it, updates the list, and commits.

### (Optional) Web articles — Obsidian Web Clipper

For articles, blogs, and essays, the easiest capture path is the [**Obsidian Web Clipper**](https://obsidian.md/clipper) browser extension (this is the flow Andrej Karpathy uses for his own LLM wiki):

1. Install the Obsidian Web Clipper in your browser (Chrome/Firefox/Safari).
2. Point it at this vault — set the default save location to `raw/<topic>/` inside this repo (create the topic folder if it doesn't exist).
3. On any article, hit the clipper — it saves a clean Markdown copy straight into `raw/`.

> 💡 Open this repo as an **Obsidian vault** too — then `wiki/` becomes a browsable, backlink-aware knowledge base you can read anytime.

Then just tell your agent:

> "Ingest the latest raw article into my wiki"

The `karpathy-llm-wiki` skill picks it up from `raw/` and compiles it into `wiki/` — same fetch → compile → index → log loop as everything else.

Don't use Obsidian? No problem — save any page as Markdown manually (or paste the text) into `raw/<topic>/` and ingest the same way. You can also queue article URLs in `to-transcribe-list.md` alongside YouTube videos and let the agent fetch them.

### (Optional) Retrieval index

```bash
python3 tools/retrieval/okf.py reindex   # builds wiki.db
python3 tools/retrieval/okf.py query "your question"
```

Uses [Ollama](https://ollama.com) with `nomic-embed-text` if available; falls back to TF-IDF otherwise.

## Manual setup (if you skipped the prompt)

<details>
<summary>Step-by-step without the one-prompt setup</summary>

1. Click **Use this template** on GitHub to create your own copy under your account, then `git clone` it and `cd` inside.
2. Launch your agent **from inside the repo** — skills live in `.agents/skills/` and are picked up automatically:
   - **[pi](https://github.com/badlogic/pi-mono)** — works out of the box (reads `.agents/skills/`).
   - **Claude Code** — works out of the box (`.claude/skills` is a symlink to `.agents/skills`). If your platform doesn't preserve symlinks (e.g. Windows without developer mode), run `./setup.sh` once.
   - **Other agents** — any agent that can read a `SKILL.md` works; copy or symlink `.agents/skills/` to wherever your agent looks for skills.
3. Verify by asking your agent: *"What skills do you have available?"* — it should list `karpathy-llm-wiki`, `baoyu-youtube-transcript`, and `wiki-ingest-next`.

</details>

## Credits

- Workflow and structure based on Andrej Karpathy's "LLM wiki" idea.
- Skills: [`karpathy-llm-wiki`](https://github.com/astro-han/karpathy-llm-wiki) and [`baoyu-youtube-transcript`](https://github.com/jimliu/baoyu-skills) (pinned in `skills-lock.json`).
