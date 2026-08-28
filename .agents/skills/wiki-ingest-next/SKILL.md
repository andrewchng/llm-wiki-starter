---
name: wiki-ingest-next
description: Process the next pending YouTube transcript end-to-end — pick one URL from to-transcribe-list.md, transcribe it (baoyu-youtube-transcript), ingest into the wiki (karpathy-llm-wiki), move it to done, and commit. Then ask whether to continue with the next pending item. Use when the user says "ingest next", "process next transcript", "continue transcribing", or wants to work down to-transcribe-list.md one item at a time.
---

# Ingest Next Transcript

Process ONE pending item from `to-transcribe-list.md` end-to-end, then ask if the user wants to continue to the next. This chains the existing skills: **baoyu-youtube-transcript** (fetch) → **karpathy-llm-wiki** (ingest) → **git commit**.

## Loop structure

1. **Pick** the first URL under `## pending` in `to-transcribe-list.md`. If pending is empty, report "list is done" and stop.
2. **Transcribe** the video.
3. **Ingest** it into the wiki.
4. **Move** the URL from `pending` to `done` in the list file.
5. **Commit** the changes.
6. **Ask** "Continue with the next one?" — if yes, repeat from step 1; if no, stop.

## Step 2 — Transcribe

Use the baoyu-youtube-transcript script (run with bun; single-quote the URL — zsh treats `?` as a glob):

```bash
bun .agents/skills/baoyu-youtube-transcript/scripts/main.ts '<url>' --chapters
```

- The script saves to `youtube-transcript/{channel-slug}/{title-slug}/transcript.md` and prints the path. Note it.
- If the direct API path fails, the script auto-falls back to `yt-dlp` — that's fine.
- **Speakers decision:** for a 2-speaker host+guest format, skip speaker identification (the compile step re-derives attribution; it's not worth the cost — see the earlier decision). For a 3+ speaker panel, run the `--speakers` flag and follow the speaker post-processing workflow in the baoyu skill. When in doubt, match how similar episodes in `raw/` were handled.

## Step 3 — Ingest

Follow the karpathy-llm-wiki **Ingest** workflow (`.agents/skills/karpathy-llm-wiki/SKILL.md`):

1. **Fetch → raw/**: copy the transcript to `raw/<topic>/YYYY-MM-DD-descriptive-slug.md` (date = published date from the frontmatter; slug ≤ 60 chars). Reuse an existing topic dir if close enough; create only for genuinely distinct topics.
2. **Compile → wiki/**: new concept → new article named after the concept; same core thesis → merge into the existing article. Check `wiki/index.md` for related articles first.
3. **Cascade updates**: scan same-topic articles for content affected by the new source; update `wiki/index.md` entries (refresh Updated date for touched articles); append to `wiki/log.md` per the Post-Ingest format.

## Step 4 — Update the list

Edit `to-transcribe-list.md`: remove the URL from `## pending` and add it under `## done` (keep the existing header comment at the top).

## Step 5 — Commit

Stage and commit using Conventional Commits. Scope `wiki`, type `docs`:

```
docs(wiki): ingest <title-slug> transcript
```

Include the raw file, the new/updated article(s), index.md, log.md, and to-transcribe-list.md in the same commit (they're one logical change). **Leave unrelated untracked files alone.** If the commit message contains apostrophes, write it to a temp file and use `git commit -F`.

## Step 6 — Continue?

Report what was ingested (channel, title, article path, commit hash), then ask whether to continue with the next pending item. One item per trigger unless the user says to keep going.

## Notes

- Never skip a step: transcribe → ingest → list → commit is the full loop.
- If the transcript fetch fails for a URL (deleted/private video, no captions), report the error, move that URL to `done` with a `(failed)` note or ask the user, then offer the next item.
- The raw/ ingest must be committed together with the wiki changes — raw/ is source material and the log references it.
