#!/usr/bin/env python3
"""OKF retrieval prototype for the llm-wiki bundle.

Deterministic retrieval over OKF frontmatter (no LLM calls at query time):

  reindex   -> build wiki.db (concepts, concepts_fts, embeddings)
  query     -> context_for(question): hybrid seed matching + trust/staleness filtering
  evaluate  -> regression gate: auto-seeded cases + out-of-bundle canaries

Follows the "OKF Graph Wiki" spec (VivianBalakrishnan gist) §5–§7:
- SQLite index compiled from frontmatter; markdown is the only source of truth.
- Hybrid seed matching fused with reciprocal rank fusion:
  exact-title match (2x), FTS5 BM25, vector cosine (nomic-embed-text via Ollama,
  TF-IDF fallback when the model is unavailable).
- Confidence gating per spec §10: BM25 trusted only on word coverage (>0.5),
  vector trusted only above a threshold, never on raw scores alone.
- Trust tier (verified) and staleness (stale_after) are ranking inputs.

Usage:
  python3 tools/retrieval/okf.py reindex [--no-evaluate]
  python3 tools/retrieval/okf.py query "question" [--budget 3000] [--top 5]
  python3 tools/retrieval/okf.py evaluate
"""
import argparse
import datetime
import json
import math
import os
import re
import sqlite3
import sys
import urllib.request
import zlib
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


def json_safe(obj):
    """Recursively convert YAML-native date/datetime objects to ISO strings.
    Unquoted date scalars in frontmatter parse as datetime.date under many
    YAML parsers (gist §10.2) and break plain JSON serialization."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(v) for v in obj]
    return obj

ROOT = Path(__file__).resolve().parent.parent.parent   # repo root
WIKI = ROOT / "wiki"
DB_PATH = WIKI / "wiki.db"
EVAL_PATH = WIKI / "evaluate.json"
K = 60                      # RRF constant (spec §6.1)
VEC_THRESHOLD = float(os.environ.get("OKF_VEC_THRESHOLD", "0.65"))
TRUST_MULT = {"human-reviewed": 1.0, "machine-confirmed": 0.8, "unverified": 0.6}
STALE_MULT = 0.5            # down-rank, don't exclude, stale concepts
STOPWORDS = frozenset("""a an the and or but of to in on for with at by from is are
was were be been being how what when where why who which do does did i you we they it
this that these those as if than then so can will would should may might about into out
up down over under not no
make get use help fix go know think want need find give tell take see like try feel
put look show work mean say learn build create run come done doing much many more most
some any all both each few such only own same too very just also still even""".split())

CANARIES = [
    ("How do I fix a flat bicycle tire?", True),
    ("Best sourdough bread recipe?", True),
    ("How to make pasta sauce?", True),
    ("What is the airspeed velocity of an unladen swallow?", True),
    ("How do I center a div in CSS?", True),
]

MODEL = "nomic-embed-text"


# ---------------------------------------------------------------- frontmatter

def parse_frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        fm = {}
    return fm or {}, text[m.end():]


def body_to_plain(body: str) -> str:
    # drop the legacy human-readable provenance header lines — they are
    # duplicated in frontmatter and only add noise to FTS/embeddings.
    body = re.sub(r"^\s*(?:>\s*)?(?:\*\*)?(Sources|Raw|Updated|Archived)[^\n]*\n?",
                  "", body, flags=re.IGNORECASE | re.MULTILINE)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)     # images
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)  # links -> label
    body = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    body = re.sub(r"[#>*`|]", " ", body)
    body = re.sub(r"\s+", " ", body)
    return body.strip()


def trust_tier(verified) -> str:
    if not verified:
        return "unverified"
    if isinstance(verified, dict):
        verified = [verified]
    if any(str(v.get("by", "")).startswith("human:") for v in verified):
        return "human-reviewed"
    return "machine-confirmed"


def collect_concepts():
    concepts = []
    for topic in sorted(p for p in WIKI.iterdir() if p.is_dir()):
        for f in sorted(topic.glob("*.md")):
            if f.name in ("index.md", "log.md"):
                continue
            text = f.read_text()
            fm, body = parse_frontmatter(text)
            fm = json_safe(fm)
            m = re.search(r"^# (.+)$", body, re.MULTILINE)
            concepts.append({
                "path": str(f.relative_to(ROOT)),
                "type": fm.get("type", ""),
                "title": fm.get("title") or (m.group(1).strip() if m else f.stem),
                "description": fm.get("description", ""),
                "tags": fm.get("tags", []) or [],
                "sources": fm.get("sources", []) or [],
                "generated_at": (fm.get("generated") or {}).get("at", ""),
                "verified": trust_tier(fm.get("verified")),
                "status": fm.get("status", "stable"),
                "stale_after": fm.get("stale_after", ""),
                "body": body_to_plain(body),
            })
    return concepts


# ---------------------------------------------------------------- embeddings

def tokenize(text: str):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())
            if t not in STOPWORDS and len(t) > 1]


def ollama_available(model: str = MODEL) -> bool:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            models = json.load(r).get("models", [])
        return any(m.get("name", "").startswith(model) for m in models)
    except Exception:
        return False


def ollama_embed(texts, prefix):
    body = json.dumps({"model": MODEL,
                       "input": [f"{prefix} {t}" for t in texts]}).encode()
    req = urllib.request.Request("http://localhost:11434/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["embeddings"]


class TFIDFEmbedder:
    """Deterministic fallback (spec §9.2's prototype stand-in): hashed TF-IDF.
    Stable across runs (crc32 keys) so retrieval stays reproducible."""

    DIM = 512

    def __init__(self):
        self.idf = {}

    def fit(self, texts):
        n = len(texts)
        df = {}
        for t in texts:
            for tok in set(tokenize(t)):
                df[tok] = df.get(tok, 0) + 1
        self.idf = {tok: math.log((n + 1) / (d + 1)) + 1 for tok, d in df.items()}

    def _vec(self, text):
        v = [0.0] * self.DIM
        toks = tokenize(text)
        for tok in set(toks):
            h = zlib.crc32(tok.encode()) % self.DIM
            v[h] += self.idf.get(tok, 1.0) * toks.count(tok) * (1 if h % 2 else -1)
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed(self, texts):
        return [self._vec(t) for t in texts]


def make_doc_embedder(concepts, force=None):
    """Return (name, doc_embed, idf_or_None) for building the index."""
    def tfidf():
        e = TFIDFEmbedder()
        e.fit([c["body"] for c in concepts])
        print("embedder: TF-IDF fallback (nomic-embed-text not on Ollama)",
              file=sys.stderr)
        return "tfidf", e.embed, e.idf
    if force == "tfidf":
        return tfidf()
    if not ollama_available():
        if force == "ollama":
            sys.exit(f"--force-embedder ollama but {MODEL} is not on localhost:11434")
        return tfidf()
    print("embedder: nomic-embed-text via Ollama", file=sys.stderr)
    return "ollama", lambda ts: ollama_embed(ts, "search_document:"), None


def query_embedder(name, idf):
    """Embedder for question vectors, matching however the index was built."""
    if name == "tfidf":
        e = TFIDFEmbedder()
        e.idf = idf
        return e.embed
    return lambda ts: ollama_embed(ts, "search_query:")


# ---------------------------------------------------------------- reindex

def build_db(concepts, doc_embed, name, idf):
    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=OFF")
    con.executescript("""
      CREATE TABLE concepts(
        path TEXT PRIMARY KEY, type TEXT, title TEXT, description TEXT,
        tags TEXT, sources TEXT, generated_at TEXT, verified TEXT,
        status TEXT, stale_after TEXT, body TEXT);
      CREATE VIRTUAL TABLE concepts_fts USING fts5(
        path UNINDEXED, title, description, tags, body);
      CREATE TABLE embeddings(path TEXT PRIMARY KEY, vector TEXT);
      CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    docs = [" ".join([c["title"], c["description"], " ".join(c["tags"]),
                      c["body"]]) for c in concepts]
    vectors = doc_embed(docs) if docs else []
    for c, v in zip(concepts, vectors):
        con.execute("INSERT INTO concepts VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            c["path"], c["type"], c["title"], c["description"],
            json.dumps(c["tags"]), json.dumps(c["sources"]),
            c["generated_at"], c["verified"], c["status"],
            c["stale_after"], c["body"]))
        con.execute("INSERT INTO concepts_fts(path,title,description,tags,body) "
                    "VALUES (?,?,?,?,?)",
                    (c["path"], c["title"], c["description"],
                     " ".join(c["tags"]), c["body"]))
        con.execute("INSERT INTO embeddings VALUES (?,?)",
                    (c["path"], json.dumps(v)))
    con.execute("INSERT INTO meta VALUES ('embedder', ?)", (name,))
    con.execute("INSERT INTO meta VALUES ('idf', ?)", (json.dumps(idf or {}),))
    con.commit()
    con.close()


def load_meta():
    con = sqlite3.connect(DB_PATH)
    meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    con.close()
    return meta.get("embedder", "tfidf"), json.loads(meta.get("idf", "{}"))


# ---------------------------------------------------------------- query

def exact_match_rank(question: str, concepts) -> dict:
    """Concept paths containing the full title at word boundaries, in order."""
    q = question.lower()
    hits = []
    for c in concepts:
        t = c["title"].lower()
        if not t:
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", q):
            hits.append(c["path"])
    return {p: i for i, p in enumerate(hits)}


def bm25_hits(question: str):
    toks = tokenize(question)
    if not toks:
        return []
    q = " OR ".join('"' + t.replace('"', '""') + '"' for t in toks)
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT path, bm25(concepts_fts) FROM concepts_fts "
            "WHERE concepts_fts MATCH ? ORDER BY 2 LIMIT 25", (q,)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    return rows


def vec_hits(question_vec, con):
    rows = con.execute("SELECT path, vector FROM embeddings").fetchall()
    scored = [(p, sum(a * b for a, b in zip(question_vec, json.loads(v))))
              for p, v in rows]
    scored.sort(key=lambda x: -x[1])
    return scored


def coverage(question: str, doc_text: str) -> float:
    qtoks = tokenize(question)
    if not qtoks:
        return 0.0
    d = doc_text.lower()
    present = sum(1 for t in qtoks
                  if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", d))
    return present / len(qtoks)


def load_index():
    con = sqlite3.connect(DB_PATH)
    concepts = {r[0]: {"path": r[0], "type": r[1], "title": r[2],
                       "description": r[3], "tags": json.loads(r[4]),
                       "sources": json.loads(r[5]),
                       "generated_at": r[6], "verified": r[7],
                       "status": r[8], "stale_after": r[9], "body": r[10]}
                for r in con.execute("SELECT * FROM concepts")}
    return con, concepts


def context_for(question: str, embed_q, top: int = 5):
    con, concepts = load_index()
    if not concepts:
        con.close()
        return None
    exact = exact_match_rank(question, list(concepts.values()))
    bm = {p: i for i, (p, _s) in enumerate(bm25_hits(question))}
    vq = embed_q([question])[0]
    vrank = {p: i for i, (p, _s) in enumerate(vec_hits(vq, con))}
    vsim = {p: s for p, s in vec_hits(vq, con)}

    today = datetime.date.today().isoformat()
    cands = []
    for p, c in concepts.items():
        rrf, sig = 0.0, []
        if p in exact:
            rrf += 2.0 / (K + exact[p] + 1)     # exact-title counted 2x (§6.1)
            sig.append("exact")
        if p in bm:
            rrf += 1.0 / (K + bm[p] + 1)
            sig.append("bm25")
        if p in vrank:
            rrf += 1.0 / (K + vrank[p] + 1)
            sig.append("vec")
        if not sig:
            continue
        mult = TRUST_MULT[c["verified"]]
        stale = bool(c["stale_after"]) and today >= c["stale_after"]
        if stale:
            mult *= STALE_MULT
            sig.append("STALE")
        cands.append({"path": p, "rrf": rrf * mult, "signals": sig,
                      "stale": stale, "vec_sim": vsim.get(p, 0.0)})
    cands.sort(key=lambda x: -x["rrf"])
    top_cands = cands[:top]

    verdicts = []
    for c in top_cands:
        k = concepts[c["path"]]
        doc_text = " ".join([k["title"], k["description"],
                             " ".join(k["tags"]), k["body"]])
        cov = coverage(question, doc_text)
        # Confidence gate (spec §10.4–10.5). BM25 coverage alone over-trusts
        # when the question's words coincide with an unrelated doc (gist §10.4's
        # validated failure); require the vector signal not to contradict.
        if "exact" in c["signals"]:
            verdicts.append("confident")
        elif cov > 0.5 and c["vec_sim"] >= 0.5:
            verdicts.append("confident")
        elif c["vec_sim"] >= VEC_THRESHOLD:
            verdicts.append("confident")
        else:
            verdicts.append("low")
    con.close()
    return {"candidates": top_cands, "verdicts": verdicts,
            "concepts": concepts}


# ---------------------------------------------------------------- serialization

def serialize(result, budget_tokens: int):
    chars = budget_tokens * 4
    overall = "confident" if result["verdicts"] and \
        result["verdicts"][0] == "confident" else "no confident match"
    out, used = [], 0
    for c, verdict in zip(result["candidates"], result["verdicts"]):
        k = result["concepts"][c["path"]]
        block = [
            f"## {k['title']}  [{k['type']}] — {verdict}",
            f"tier: {k['verified']}" + (f" | STALE (stale_after {k['stale_after']})"
                                        if c["stale"] else ""),
            f"tags: {', '.join(k['tags']) if k['tags'] else '-'} | "
            f"sources: {len(k['sources']) if k['sources'] else 0} | "
            f"generated: {k['generated_at']}",
        ]
        if k["description"]:
            block.append(k["description"])
        block.append(k["body"][:600])
        text = "\n".join(block) + "\n"
        if out and used + len(text) > chars:
            break
        out.append(text)
        used += len(text)
    return overall, "\n".join(out)


# ---------------------------------------------------------------- evaluate

def run_evaluate(concepts=None):
    if not DB_PATH.exists():
        return False, [("evaluate", "wiki.db missing — run reindex first",
                        "FAIL", "")]
    name, idf = load_meta()
    embed_q = query_embedder(name, idf)
    results = []
    if EVAL_PATH.exists():
        cases = json.loads(EVAL_PATH.read_text())
    else:
        cases = [{"q": c["title"], "expect": c["path"]} for c in
                 (concepts or collect_concepts())]
        EVAL_PATH.write_text(json.dumps(cases, indent=2) + "\n")
        results.append(("auto-seeded", "evaluate.json created", "INFO", ""))
    for q, expect_no_match in CANARIES:
        cases.append({"q": q, "expectNoMatch": expect_no_match})
    for case in cases:
        res = context_for(case["q"], embed_q, top=1)
        if res is None or not res["candidates"]:
            results.append((case["q"], "no candidates", "FAIL", ""))
            continue
        top = res["candidates"][0]
        if case.get("expectNoMatch"):
            ok = res["verdicts"][0] != "confident"
        else:
            ok = top["path"] == case["expect"]
        results.append((case["q"], top["path"], "PASS" if ok else "FAIL",
                        res["verdicts"][0]))
    return all(r[2] in ("PASS", "INFO") for r in results), results


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("reindex", help="rebuild wiki.db from wiki/ frontmatter")
    p.add_argument("--no-evaluate", action="store_true",
                   help="skip the evaluate gate after reindex")
    p.add_argument("--force-embedder", choices=["ollama", "tfidf"])

    p = sub.add_parser("query", help="context_for(question)")
    p.add_argument("question")
    p.add_argument("--budget", type=int, default=3000)
    p.add_argument("--top", type=int, default=5)

    sub.add_parser("evaluate", help="run the regression gate")

    args = ap.parse_args()

    if args.cmd == "reindex":
        concepts = collect_concepts()
        name, doc_embed, idf = make_doc_embedder(concepts, args.force_embedder)
        build_db(concepts, doc_embed, name, idf)
        print(f"reindexed {len(concepts)} concepts -> {DB_PATH.relative_to(ROOT)}")
        if not args.no_evaluate:
            ok, results = run_evaluate(concepts)
            print(f"\nevaluate gate: {'PASS' if ok else 'FAIL'}")
            for q, matched, status, verdict in results:
                print(f"  [{status:4}] {q[:58]:58} -> {matched[:38]:38} {verdict}")
            sys.exit(0 if ok else 1)
        return

    if args.cmd == "evaluate":
        ok, results = run_evaluate()
        print(f"evaluate gate: {'PASS' if ok else 'FAIL'}")
        for q, matched, status, verdict in results:
            print(f"  [{status:4}] {q[:58]:58} -> {matched[:38]:38} {verdict}")
        sys.exit(0 if ok else 1)

    if args.cmd == "query":
        if not DB_PATH.exists():
            sys.exit("wiki.db missing — run: python3 tools/retrieval/okf.py reindex")
        name, idf = load_meta()
        embed_q = query_embedder(name, idf)
        result = context_for(args.question, embed_q, top=args.top)
        if result is None:
            sys.exit("index is empty — run reindex")
        overall, block = serialize(result, args.budget)
        print(f"verdict: {overall}")
        print("-" * 70)
        for c, v in zip(result["candidates"], result["verdicts"]):
            print(f"  {c['rrf']:7.4f} {v:9} {c['path']}  [{','.join(c['signals'])}]")
        print("-" * 70)
        print(block)
        if overall != "confident":
            print("\nNOTE: no confident match — the wiki likely does not cover this "
                  "question. Showing nearest candidates at low confidence.")


if __name__ == "__main__":
    main()
