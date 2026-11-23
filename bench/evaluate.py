"""Score a run file.

A run file is JSON Lines, one line per query, with the earlier turns your system
retrieved for it, best first:

    {"query_id": "p01_q01", "retrieved": ["p01_s3_t14", "p01_s1_t06", ...]}

    python -m bench.evaluate runs/bm25.jsonl
    python -m bench.evaluate runs/my_system.jsonl --by category --json results.json

Metrics (all averaged over queries; a missing query scores 0):
  chain@k   share of queries where EVERY evidence turn is in the top k  (headline)
  recall@k  share of evidence turns found in the top k
  mrr       1 / rank of the first evidence turn
  trap@5    share of the top 5 that are planted distractor turns (lower is better)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict

from bench.load import iter_turns, load_personas, load_queries

KS = (5, 10, 20)


def score_query(q: dict, retrieved: list[str]) -> dict:
    ev = set(q["evidence"])
    seen, ranked = set(), []
    for tid in retrieved:  # drop duplicates, keep order
        if tid not in seen:
            seen.add(tid)
            ranked.append(tid)
    out = {}
    for k in KS:
        hits = ev & set(ranked[:k])
        out[f"recall@{k}"] = len(hits) / len(ev)
        out[f"chain@{k}"] = float(hits == ev)
    first = next((i for i, tid in enumerate(ranked) if tid in ev), None)
    out["mrr"] = 0.0 if first is None else 1.0 / (first + 1)
    dcg = sum(1 / math.log2(i + 2) for i, tid in enumerate(ranked[:10]) if tid in ev)
    idcg = sum(1 / math.log2(i + 2) for i in range(min(len(ev), 10)))
    out["ndcg@10"] = dcg / idcg
    traps = set(q["distractors"])
    out["trap@5"] = sum(tid in traps for tid in ranked[:5]) / 5
    return out


def aggregate(rows: list[dict]) -> dict:
    keys = rows[0].keys() if rows else []
    return {k: sum(r[k] for r in rows) / len(rows) for k in keys} | {"n": len(rows)}


def evaluate(run: dict[str, list[str]], queries: list[dict], valid_ids: set[str]) -> dict:
    per_query, unknown = {}, 0
    for q in queries:
        retrieved = run.get(q["query_id"], [])
        unknown += sum(tid not in valid_ids for tid in retrieved)
        per_query[q["query_id"]] = score_query(q, retrieved)
    groups: dict[str, dict[str, list]] = {"category": defaultdict(list), "hops": defaultdict(list)}
    for q in queries:
        s = per_query[q["query_id"]]
        groups["category"][q["category"]].append(s)
        n = len(q["evidence"])
        groups["hops"][f"{n} evidence turn{'s' if n > 1 else ''}"].append(s)
    return {
        "overall": aggregate(list(per_query.values())),
        "by_category": {k: aggregate(v) for k, v in sorted(groups["category"].items())},
        "by_hops": {k: aggregate(v) for k, v in sorted(groups["hops"].items())},
        "per_query": per_query,
        "missing_queries": sorted(set(per_query) - set(run)),
        "unknown_turn_ids": unknown,
    }


def read_run(path: str) -> dict[str, list[str]]:
    run = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                run[row["query_id"]] = row["retrieved"]
    return run


COLS = ("chain@10", "chain@20", "recall@5", "recall@10", "mrr", "ndcg@10", "trap@5")


def print_table(title: str, groups: dict[str, dict]) -> None:
    width = max([len(title)] + [len(g) for g in groups]) + 2
    print(f"\n{title:<{width}}" + "".join(f"{c:>10}" for c in COLS) + f"{'n':>5}")
    for name, m in groups.items():
        print(f"{name:<{width}}" + "".join(f"{m[c]:>10.3f}" for c in COLS) + f"{m['n']:>5}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--by", choices=["category", "hops", "both", "none"], default="both")
    ap.add_argument("--json", help="write the full results here")
    args = ap.parse_args()

    personas = load_personas()
    queries = load_queries(personas)
    valid = {t["turn_id"] for p in personas for t in iter_turns(p)}
    res = evaluate(read_run(args.run), queries, valid)

    print_table("overall", {"all queries": res["overall"]})
    if args.by in ("category", "both"):
        print_table("by category", res["by_category"])
    if args.by in ("hops", "both"):
        print_table("by evidence turns", res["by_hops"])
    if res["missing_queries"]:
        print(f"\n{len(res['missing_queries'])} queries missing from the run (scored 0)")
    if res["unknown_turn_ids"]:
        print(f"{res['unknown_turn_ids']} retrieved ids are not turns in the benchmark")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(res, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
