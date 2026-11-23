"""Optional: score systems that return text (extracted facts, summaries, graph paths)
instead of turn ids. An LLM checks which facts of each query's chain the text covers.

Run file, one line per query:

    {"query_id": "p01_q01", "context": "Sam is autistic ... plans his day in blocks ..."}

    pip install openai
    python -m bench.judge runs/my_system_text.jsonl --model <chat model name>

Uses any OpenAI-compatible API (set OPENAI_API_KEY, and OPENAI_BASE_URL for other providers).
Context is cut to --max-words (default 400, about what ten turns take) so that returning
the whole history does not win.

Metrics: fact_recall (share of chain facts covered) and chain (share of queries with every fact covered).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from bench.load import load_personas, load_queries

PROMPT = """You are grading the memory system of a therapy assistant.

The client just said:
"{query}"

The memory system retrieved this context about the client:
<context>
{context}
</context>

Below are facts about the client from earlier sessions. For each one, answer true if the
retrieved context states it or clearly implies it (paraphrase is fine), false if not.

{facts}

Reply with JSON only: {{"supported": [true or false for each fact, in order]}}"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-words", type=int, default=400)
    ap.add_argument("--json", help="write per-query results here")
    args = ap.parse_args()

    from openai import OpenAI

    client = OpenAI()
    contexts = {}
    with open(args.run) as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                contexts[row["query_id"]] = " ".join(row["context"].split()[: args.max_words])

    results, by_cat = {}, defaultdict(list)
    for q in load_queries(load_personas()):
        facts = [c["fact"] for c in q["chain"]]
        ctx = contexts.get(q["query_id"], "")
        if ctx:
            msg = PROMPT.format(
                query=q["query"], context=ctx, facts="\n".join(f"{i + 1}. {f}" for i, f in enumerate(facts))
            )
            resp = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "user", "content": msg}],
                response_format={"type": "json_object"},
            )
            supported = json.loads(resp.choices[0].message.content)["supported"][: len(facts)]
            supported += [False] * (len(facts) - len(supported))
        else:
            supported = [False] * len(facts)
        r = {"fact_recall": sum(map(bool, supported)) / len(facts), "chain": float(all(supported))}
        results[q["query_id"]] = r | {"supported": supported}
        by_cat[q["category"]].append(r)
        print(f"{q['query_id']:10s} facts {sum(map(bool, supported))}/{len(facts)}")

    def avg(rows, k):
        return sum(r[k] for r in rows) / len(rows)

    rows = [r for v in by_cat.values() for r in v]
    print(f"\n{'':22s}{'chain':>8}{'fact_recall':>13}{'n':>5}")
    print(f"{'all queries':22s}{avg(rows, 'chain'):>8.3f}{avg(rows, 'fact_recall'):>13.3f}{len(rows):>5}")
    for cat, v in sorted(by_cat.items()):
        print(f"{cat:22s}{avg(v, 'chain'):>8.3f}{avg(v, 'fact_recall'):>13.3f}{len(v):>5}")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
