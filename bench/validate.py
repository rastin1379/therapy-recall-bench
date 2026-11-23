"""Check the data files and report how hard each query is for keyword search.

    python -m bench.validate                # all personas
    python -m bench.validate data/personas/p01.json --verbose

Errors (broken ids, wrong dates, missing fields) make the exit code 1.
Warnings flag queries that keyword search finds too easily.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from bench.bm25 import BM25
from bench.load import CATEGORIES, DATA_DIR, content_terms, iter_turns

TURN_ID = re.compile(r"^(p\d{2})_s(\d+)_t(\d{2,3})$")
REQUIRED_QUERY = ("query_id", "category", "date", "query", "evidence", "chain", "reasoning", "distractors")


def check_persona(p: dict, verbose: bool) -> tuple[list[str], list[str], list[dict]]:
    errors, warnings, stats = [], [], []
    pid = p.get("persona_id", "?")
    for key in ("persona_id", "name", "case_formulation", "sessions", "queries"):
        if key not in p:
            errors.append(f"{pid}: missing top-level field '{key}'")
    if errors:
        return errors, warnings, stats

    turns = list(iter_turns(p))
    ids = [t["turn_id"] for t in turns]
    if len(ids) != len(set(ids)):
        errors.append(f"{pid}: duplicate turn ids")
    by_id = {t["turn_id"]: t for t in turns}
    last_date = ""
    for s_idx, session in enumerate(p["sessions"], 1):
        if session["session_id"] != f"{pid}_s{s_idx}":
            errors.append(f"{pid}: session {s_idx} has id {session['session_id']}")
        if session["date"] <= last_date:
            errors.append(f"{pid}: session dates not increasing at {session['session_id']}")
        last_date = session["date"]
        for t_idx, turn in enumerate(session["turns"], 1):
            want = f"{pid}_s{s_idx}_t{t_idx:02d}"
            if turn.get("turn_id") != want:
                errors.append(f"{pid}: expected {want}, found {turn.get('turn_id')}")
            if turn.get("speaker") not in ("client", "therapist"):
                errors.append(f"{pid}: bad speaker in {turn.get('turn_id')}")
            if not turn.get("text", "").strip():
                errors.append(f"{pid}: empty text in {turn.get('turn_id')}")

    bm25 = BM25([t["text"] for t in turns])
    seen_q = set()
    for q in p["queries"]:
        qid = q.get("query_id", "?")
        missing = [k for k in REQUIRED_QUERY if k not in q]
        if missing:
            errors.append(f"{qid}: missing {missing}")
            continue
        if qid in seen_q or not qid.startswith(pid + "_q"):
            errors.append(f"{qid}: duplicate or badly named query id")
        seen_q.add(qid)
        if q["category"] not in CATEGORIES:
            errors.append(f"{qid}: unknown category {q['category']}")
        if q["date"] <= last_date:
            errors.append(f"{qid}: query date must come after the last session ({last_date})")
        ev = q["evidence"]
        if not ev:
            errors.append(f"{qid}: no evidence")
        for tid in ev + q["distractors"]:
            if tid not in by_id:
                errors.append(f"{qid}: unknown turn id {tid}")
        if set(ev) & set(q["distractors"]):
            errors.append(f"{qid}: a turn is both evidence and distractor")
        chain_ids = {c.get("turn_id") for c in q["chain"]}
        if chain_ids != set(ev):
            errors.append(f"{qid}: chain turn ids {sorted(chain_ids)} != evidence {sorted(ev)}")
        if len(q["distractors"]) < 2:
            warnings.append(f"{qid}: fewer than 2 distractors")
        if any(tid not in by_id for tid in ev + q["distractors"]):
            continue

        q_terms = set(content_terms(q["query"]))
        ranking = [ids[i] for i in bm25.rank(q["query"])]
        ranks = {tid: ranking.index(tid) + 1 for tid in ev}
        overlaps = {tid: sorted(q_terms & set(content_terms(by_id[tid]["text"]))) for tid in ev}
        d_overlap = [len(q_terms & set(content_terms(by_id[d]["text"]))) for d in q["distractors"]]
        stats.append({"qid": qid, "ranks": ranks, "chain10": all(r <= 10 for r in ranks.values())})

        if all(r <= 5 for r in ranks.values()):
            warnings.append(f"{qid}: TOO EASY, keyword search puts all evidence in its top 5 {ranks}")
        for tid, words in overlaps.items():
            if len(words) >= 3:
                warnings.append(f"{qid}: evidence {tid} shares {len(words)} keywords with the query {words}")
        if d_overlap and max(d_overlap) == 0:
            warnings.append(f"{qid}: distractors share no keywords with the query, so they don't lure keyword search")
        if verbose:
            print(f"  {qid:10s} {q['category']:20s} bm25 ranks {ranks}  shared words {overlaps}")
    return errors, warnings, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="persona files (default: all)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    files = [Path(f) for f in args.files] or sorted(DATA_DIR.glob("*.json"))

    all_err, all_warn, all_stats = [], [], []
    totals = {"sessions": 0, "turns": 0, "words": 0, "queries": 0}
    cats: dict[str, int] = {}
    for f in files:
        try:
            p = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            all_err.append(f"{f.name}: invalid JSON: {e}")
            continue
        if args.verbose:
            print(f"{f.name}")
        e, w, s = check_persona(p, args.verbose)
        all_err += e
        all_warn += w
        all_stats += s
        if not e:
            turns = list(iter_turns(p))
            totals["sessions"] += len(p["sessions"])
            totals["turns"] += len(turns)
            totals["words"] += sum(len(t["text"].split()) for t in turns)
            totals["queries"] += len(p["queries"])
            for q in p["queries"]:
                cats[q["category"]] = cats.get(q["category"], 0) + 1

    print(f"\n{len(files)} personas, {totals['sessions']} sessions, {totals['turns']} turns, "
          f"{totals['words']} words, {totals['queries']} queries")
    print("categories:", ", ".join(f"{k} {v}" for k, v in sorted(cats.items())))
    if all_stats:
        c10 = sum(s["chain10"] for s in all_stats) / len(all_stats)
        print(f"keyword search (BM25) finds the full chain in its top 10 for {c10:.0%} of queries")
    for w in all_warn:
        print("WARN ", w)
    for e in all_err:
        print("ERROR", e)
    print(f"\n{len(all_err)} errors, {len(all_warn)} warnings")
    return 1 if all_err else 0


if __name__ == "__main__":
    sys.exit(main())
