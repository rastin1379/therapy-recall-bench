# TherapyRecall

**A small, hard retrieval benchmark for memory in therapy conversations.**

In therapy, the past turn that matters most often shares no words with what the client just said.

> **Session 1:** "I'm autistic, diagnosed at nineteen… If something changes without warning, or there's too much input at once, I go into a sort of static."
> **Session 3:** "My weekdays are honestly the best part of my life. I've got them in blocks on a whiteboard by the fridge… It's the closest I get to feeling free."
> **New session:** "I snapped at Danny on Saturday… He was coming round at ten to help me get the bookshelf up the stairs, and he rolled in forty-odd minutes late… and I just went cold."

A good therapist connects the anger to the broken plan, and the plan to how Sam copes with being autistic. A search for *Danny, late, snapped* finds the turns about Danny's carpentry, his birthday and a late train, and misses both turns that explain it.

> **Session 1:** "My mum, Shirin… When I went away to university she phoned me every single evening at nine, all five years… maybe too much, if I'm honest."
> **Session 2:** "In the morning it was finished on the kitchen table. Perfect. My mum had stayed up till three doing it. That happened with basically every school project."
> **New session:** "The Millbrook pitch was on Tuesday, the biggest thing I've ever led, and Noa didn't ask once how it went… I just don't feel like I get any help or support from her."

Is Noa unsupportive, or is Arash calibrated to a mother who never let him struggle? You can't even ask that question without retrieving the mother, and the new message never mentions her.

TherapyRecall measures whether a memory system can retrieve these links. Each query is a client's opening message in a new session. The system gets the client's earlier sessions and must return the earlier turns a thoughtful therapist would bring to mind. The gold links follow clinical reasoning (CBT case conceptualization: core belief → rule or coping strategy → trigger → reaction), not word overlap. Each query also lists **trap turns** that share the query's surface words but don't help.

## What's in it

- **8 fictional clients**, 6 sessions each: 48 sessions, 1,180 turns, about 31,000 words
- **80 queries** across 10 categories, 8 per category (relational_template 9, risk_signal 7)
- 64 of the 80 queries need 2 or more earlier turns for the full picture; 13 need 3
- 2 to 4 planted trap turns per query

| client | in brief |
|---|---|
| p01 Sam, 27 | Autistic QA tester; routines, sensory overload, a relaxed older brother, masking at work |
| p02 Arash, 31 | Architect; an over-supportive mother, a direct girlfriend, perfectionism |
| p03 Teresa, 61 | Widowed ten months; grief, guilt, the garden, passive thoughts of not waking up |
| p04 Dev, 34 | Engineer with ADHD; a critical father, shame and shutdown at work, medication changes |
| p05 Priya, 34 | New mother; postpartum anxiety with intrusive thoughts, a partner on night shifts |
| p06 Marcus, 46 | Two years sober; relapse patterns, a sponsor, an unpredictable father, a teenage son |
| p07 Jun, 20 | Student; social anxiety, perfectionism, food restriction, a sister cast as the family failure |
| p08 Tomás, 42 | Music teacher three years after a car crash; driving avoidance, startle, the dark months |

All clients, sessions and queries are fictional and were written for this benchmark (see [docs/AUTHORING.md](docs/AUTHORING.md)). There is no real user or patient data.

| category | what it tests |
|---|---|
| `latent_trait` | A trait or diagnosis disclosed earlier explains what the client is doing now. |
| `relational_template` | A current relationship repeats the shape of an earlier one. |
| `trigger_recurrence` | The same trigger and reaction show up in a new setting (a father's criticism, then a code review). |
| `symbolic_reference` | An object, place, smell or song points back to an earlier memory. |
| `temporal_anniversary` | A date or season links to something that happened then. |
| `state_update` | An earlier fact changed later; you need the latest state and what it replaced. |
| `risk_signal` | A harmless-sounding message only looks worrying next to an earlier disclosure. |
| `entity_resolution` | A nickname or role refers to someone introduced earlier under another name. |
| `contradiction` | What the client says now conflicts with what they said before. |
| `coping_resource` | Something that helped before is relevant now, though the client says nothing helps. |

## Quick start

No dependencies beyond Python 3.10+.

```bash
git clone https://github.com/rastin1379/therapy-recall-bench && cd therapy-recall-bench
python -m bench.baselines bm25          # writes runs/bm25.jsonl
python -m bench.evaluate runs/bm25.jsonl
```

## Testing your system

1. For each client in `data/personas/*.json`, ingest the `sessions` (every turn has a `turn_id`, a `speaker` and a session `date`). Don't read `case_formulation` or `queries`; they are the answer key.
2. For each query in that client's `queries`, give your system the `query` text (and its `date` if you use time) and retrieve from **that client's history only**.
3. Write one JSON line per query with the turn ids you retrieved, best first:

   ```json
   {"query_id": "p01_q01", "retrieved": ["p01_s3_t14", "p01_s1_t06", "p01_s2_t09"]}
   ```

   If your system stores extracted facts, chunks or graph nodes, keep the turn ids each one came from and list those. A chunk of five turns uses five slots.
4. `python -m bench.evaluate runs/your_system.jsonl`

If your system only returns text (synthesized facts, summaries), use the optional LLM judge instead: write `{"query_id": ..., "context": "..."}` lines and run `python -m bench.judge runs/your_text.jsonl --model <model>`. It checks which facts of each gold chain the text covers, capped at 400 words of context.

## Metrics

- **chain@10** (headline): share of queries where *every* evidence turn is in the top 10. Getting one hop of a chain is not enough.
- **recall@k**: share of evidence turns in the top k.
- **MRR**, **nDCG@10**: how high the evidence ranks.
- **trap@5**: share of the top 5 that are planted trap turns. Lower is better.

## Baselines

Each retriever searches only the queried client's history (about 150 turns).

| retriever | chain@10 | chain@20 | recall@10 | MRR | trap@5 |
|---|---:|---:|---:|---:|---:|
| random | 0.013 | 0.025 | 0.073 | 0.082 | 0.020 |
| recency (newest turns first) | 0.000 | 0.000 | 0.000 | 0.006 | 0.025 |
| BM25 keyword search\* | 0.000 | 0.025 | 0.019 | 0.032 | 0.328 |
| embeddings: all-MiniLM-L6-v2 | 0.150 | 0.325 | 0.321 | 0.247 | 0.175 |
| embeddings: bge-base-en-v1.5 | 0.237 | 0.412 | 0.429 | 0.276 | 0.258 |

\* The queries were rewritten during authoring until BM25 missed them, so BM25's score is low by construction. It shows the data has no keyword shortcuts. The embedding models were not used during authoring.

The best embedding baseline gets the full chain in its top 10 for under a quarter of queries. It scores 0 on `latent_trait` (the autism → routine → anger kind) and on every query that needs 3 turns, and a quarter of its top 5 are traps.

To reproduce the embedding rows:

```bash
pip install sentence-transformers
python -m bench.baselines dense --model sentence-transformers/all-MiniLM-L6-v2
python -m bench.baselines dense --model BAAI/bge-base-en-v1.5
python -m bench.evaluate runs/dense-bge-base-en-v1.5.jsonl
```

Baseline run files are in `runs/`.

## Related work

General long-term conversational memory benchmarks test multi-session recall, mostly of facts stated explicitly:

- **MSC**, *Beyond Goldfish Memory* (Xu et al., 2021) [arXiv:2107.07567](https://arxiv.org/abs/2107.07567)
- **LoCoMo** (Maharana et al., 2024) [arXiv:2402.17753](https://arxiv.org/abs/2402.17753)
- **LongMemEval** (Wu et al., ICLR 2025) [arXiv:2410.10813](https://arxiv.org/abs/2410.10813)
- **ConvoMem** (2025) [arXiv:2511.10523](https://arxiv.org/abs/2511.10523), which includes an implicit-connections category
- **BEAM** and the 2026 landscape, summarized in [this Mem0 overview](https://mem0.ai/blog/ai-memory-benchmarks-in-2026)

A newer line targets memories that matter logically but share little with the query, which is the closest to this benchmark:

- **Locomo-Plus** (ACL 2026) [arXiv:2602.10715](https://arxiv.org/abs/2602.10715): latent constraints with a cue-trigger semantic disconnect
- **IMLogic / RootMem** (2026) [arXiv:2606.23283](https://arxiv.org/abs/2606.23283): implicit logical memory retrieval for personalized LLMs
- **PersonaMem** [arXiv:2504.14225](https://arxiv.org/abs/2504.14225) and **PersonaMem-v2** [arXiv:2512.06688](https://arxiv.org/abs/2512.06688): implicit user personas
- **Explicit vs. Implicit Memory** (2025) [arXiv:2508.13250](https://arxiv.org/abs/2508.13250): multi-hop reasoning over personalized information
- **CUE-Mem** (2026) [arXiv:2609.32574](https://arxiv.org/abs/2609.32574): implicit cues in multi-session conversations

Therapy and counseling datasets exist, but they evaluate response quality or patient simulation, not retrieval:

- **PATIENT-Ψ** (Wang et al., 2024) [arXiv:2405.19660](https://arxiv.org/abs/2405.19660): simulated patients built from CBT cognitive conceptualization diagrams, the same structure TherapyRecall's chains follow
- **MusPsy** (ACL Findings 2026) [arXiv:2506.06626](https://arxiv.org/abs/2506.06626): synthetic multi-session CBT counseling
- **ESConv** (Liu et al., 2021) [arXiv:2106.01144](https://arxiv.org/abs/2106.01144): emotional support conversations

What TherapyRecall adds: retrieval gold labels at the turn level for clinical links (diagnosis to coping strategy to trigger, attachment templates, risk context, anniversaries), with planted lexical traps, small enough to read in an afternoon.

## Limitations

- It is small. It is meant as a sharp probe, not a leaderboard with tight confidence intervals. Look at the per-query results.
- The conversations were written with the help of an LLM and checked by a script (`python -m bench.validate`) for broken ids, keyword overlap and trivially easy queries. They have not been reviewed by clinicians.
- English only, written dialogue, six sessions per client. Real clients are messier and histories are longer.
- The gold chains reflect one reasonable clinical reading. A therapist might link other turns too, so treat retrieved non-gold turns as "not credited", not necessarily wrong.

## Contributing

New clients are welcome. Follow [docs/AUTHORING.md](docs/AUTHORING.md), run `python -m bench.validate`, and open a pull request.

## License

Code: MIT. Data (`data/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
