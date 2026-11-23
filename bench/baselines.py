"""Reference retrievers. Each searches only the queried client's own history.

    python -m bench.baselines bm25                 # standard library only
    python -m bench.baselines recency
    python -m bench.baselines random
    python -m bench.baselines dense --model sentence-transformers/all-MiniLM-L6-v2
    python -m bench.baselines dense --model BAAI/bge-base-en-v1.5
    python -m bench.baselines dense --model openai:text-embedding-3-small   # needs OPENAI_API_KEY

Writes runs/<name>.jsonl, which you then score with  python -m bench.evaluate.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from bench.bm25 import BM25
from bench.load import ROOT, iter_turns, load_personas

TOP_N = 50


def run_bm25(turns: list[dict], query: str) -> list[str]:
    bm = BM25([t["text"] for t in turns])
    return [turns[i]["turn_id"] for i in bm.rank(query)]


def run_recency(turns: list[dict], query: str) -> list[str]:
    return [t["turn_id"] for t in reversed(turns)]


def run_random(turns: list[dict], query: str, seed: int = 0) -> list[str]:
    ids = [t["turn_id"] for t in turns]
    random.Random(f"{seed}-{query}").shuffle(ids)
    return ids


class Dense:
    def __init__(self, model: str):
        self.model_name = model
        if model.startswith("openai:"):
            from openai import OpenAI

            client, name = OpenAI(), model.split(":", 1)[1]
            self.encode = lambda texts: [d.embedding for d in client.embeddings.create(model=name, input=texts).data]
            self.query_prefix = ""
        else:
            from sentence_transformers import SentenceTransformer

            st = SentenceTransformer(model)
            self.encode = lambda texts: st.encode(texts, normalize_embeddings=True).tolist()
            self.query_prefix = "Represent this sentence for searching relevant passages: " if "bge" in model.lower() else ""
        self.cache: dict[str, list[list[float]]] = {}

    def __call__(self, turns: list[dict], query: str) -> list[str]:
        key = turns[0]["persona_id"]
        if key not in self.cache:
            self.cache[key] = self.encode([t["text"] for t in turns])
        q = self.encode([self.query_prefix + query])[0]
        scores = [sum(a * b for a, b in zip(q, d)) for d in self.cache[key]]
        return [turns[i]["turn_id"] for i in sorted(range(len(turns)), key=lambda i: -scores[i])]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("method", choices=["bm25", "recency", "random", "dense"])
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--out", help="output path (default runs/<method>.jsonl)")
    args = ap.parse_args()

    if args.method == "dense":
        retrieve = Dense(args.model)
        name = "dense-" + args.model.split("/")[-1].replace(":", "-")
    else:
        retrieve = {"bm25": run_bm25, "recency": run_recency, "random": run_random}[args.method]
        name = args.method
    out = Path(args.out or ROOT / "runs" / f"{name}.jsonl")
    out.parent.mkdir(exist_ok=True)

    with out.open("w") as f:
        for persona in load_personas():
            turns = list(iter_turns(persona))
            for q in persona["queries"]:
                ranked = retrieve(turns, q["query"])[:TOP_N]
                f.write(json.dumps({"query_id": q["query_id"], "retrieved": ranked}) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
