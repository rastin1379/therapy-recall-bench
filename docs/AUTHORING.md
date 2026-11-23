# How the data is written

Every client, session and query in this benchmark is fictional and was written for it. No real user or patient data is used anywhere.

## The idea

In therapy, the memory that matters most is often the one that shares no words with what the client just said:

- Session 1: *"I was diagnosed autistic at 19. Unpredictable noise and changes wreck me."*
- Session 3: *"I plan my whole day in fifteen-minute blocks. I love it."*
- New session: *"I snapped at my brother yesterday because he turned up forty minutes late."*

A good therapist links the anger to the broken plan, and the broken plan to the autism. A keyword or embedding search over "brother, late, snapped" finds the turns where the brother or anger come up, and misses both turns that explain it.

Each query in the benchmark is a client's opening message in a **new** session. The system gets the client's earlier sessions and has to retrieve the earlier turns a thoughtful therapist would bring to mind. The links follow how clinicians think about a case (the CBT case conceptualization: core belief → rule or coping strategy → trigger → automatic thought → emotion and behavior), not how the words match.

## File format

One JSON file per client: `data/personas/pNN.json`.

```json
{
  "persona_id": "p01",
  "name": "Sam",
  "case_formulation": "Hidden ground truth for humans: background, core beliefs, rules, patterns. Systems must not read this.",
  "sessions": [
    {
      "session_id": "p01_s1",
      "date": "2026-01-12",
      "turns": [
        {"turn_id": "p01_s1_t01", "speaker": "therapist", "text": "..."},
        {"turn_id": "p01_s1_t02", "speaker": "client", "text": "..."}
      ]
    }
  ],
  "queries": [
    {
      "query_id": "p01_q01",
      "category": "latent_trait",
      "date": "2026-04-20",
      "query": "The client's opening message in the new session.",
      "evidence": ["p01_s1_t06", "p01_s3_t14"],
      "chain": [
        {"turn_id": "p01_s3_t14", "fact": "Plans every day in fifteen-minute blocks and loves it."},
        {"turn_id": "p01_s1_t06", "fact": "Autistic; unpredictability and sensory overload are very hard for him."}
      ],
      "reasoning": "Lateness broke his plan; plans are how he manages autistic overload, so the anger is about losing predictability, not about the brother.",
      "distractors": ["p01_s2_t09", "p01_s4_t03"],
      "why_it_matters": "Without the link, the therapist treats it as an anger or sibling problem."
    }
  ]
}
```

Rules for ids: sessions are `pNN_sK` numbered from 1 in date order; turns are `pNN_sK_tMM` numbered from 01 within each session (three digits if a session passes 99 turns). Query ids are `pNN_qMM`.

Field meanings:

- `evidence`: every earlier turn needed for the full picture. All of them are required. Usually 1 to 3 turns, mostly client turns.
- `chain`: the same turns, each with the one-line fact it contributes, in reasoning order (closest to the query first). Used by the optional LLM judge for systems that return facts instead of turn ids.
- `reasoning`: one or two sentences on why these turns belong to this query.
- `distractors`: 2 to 4 earlier turns that **share surface words or topic with the query but are not relevant**. These are the traps for keyword and embedding search (the brother came up once to talk about his job; "late" appears in a turn about a late train that didn't bother him).
- `why_it_matters`: what a therapist would get wrong without the link.

## Query categories

| category | what it tests |
|---|---|
| `latent_trait` | A trait or diagnosis disclosed earlier explains what the client is doing now. |
| `relational_template` | A current relationship repeats the shape of an earlier one (an over-protective mother, then a girlfriend who "doesn't support me enough"). |
| `trigger_recurrence` | The same trigger and reaction appears in a new setting (a father's criticism at dinner, then a manager's code review). |
| `symbolic_reference` | An object, place, smell, song or metaphor points back to an earlier memory. |
| `temporal_anniversary` | A date, season or recurring event links to something that happened then. |
| `state_update` | An earlier fact was changed or reversed later; the system needs the latest state and what it replaced (stopped medication; moved out; started driving again). |
| `risk_signal` | A harmless-sounding message only looks worrying next to an earlier disclosure (giving things away, plus earlier passive thoughts of not being around). |
| `entity_resolution` | A nickname, role or pronoun refers to someone introduced earlier under another name. |
| `contradiction` | What the client says now conflicts with what they disclosed before ("Dad and I were always fine"). |
| `coping_resource` | Something that helped before is relevant now, even though the client says nothing helps. |

## Writing rules

1. **No shared words.** A query must not repeat the distinctive words of its evidence turns. If the evidence says "autism" and "schedule", the query talks about a brother and a late arrival. Generic words (feel, really, week) don't matter. Run the validator: it warns when an evidence turn shares 3 or more content words with its query, and when keyword search ranks every evidence turn in its top 5. Rewrite until those warnings are gone, unless the category truly needs a shared name (allowed only for `entity_resolution` and `state_update`, and then only one shared word).
2. **Plant the traps.** For every query, make sure the history contains turns that share the query's surface words or topic but don't help. List them as `distractors`.
3. **Evidence comes early and is spread out.** Most evidence lives in sessions 1 to 3, mentioned once, in passing, inside a turn about something else, the way real clients mention things. A multi-turn chain should span different sessions.
4. **Write real sessions, not a list of clues.** Sessions have small talk, tangents, work stress, TV shows, logistics, the therapist's reflections and questions. Most turns are not evidence for anything. Clients hedge, joke, contradict themselves and leave things half said. Therapist turns are short and natural.
5. **Clinically plausible.** Follow how these conditions and patterns really show up. No caricature, no diagnosis-by-numbers. Keep trauma and risk content non-graphic; risk content is passive or past, written with care.
6. **Self-contained queries.** The query reads like the first thing a client says in a new session, 1 to 4 sentences. It must not hint at the evidence ("like I told you about my diagnosis" is not allowed).
7. **Diversity.** Each client gets 10 queries covering at least 7 of the 10 categories; at least 4 queries need 2 or more evidence turns, and at least 1 needs 3.
8. **Size.** Each client has 6 sessions, about 2 weeks apart, each 20 to 30 turns, alternating therapist and client (start with the therapist). Client turns run 15 to 120 words. Query dates come 1 to 4 weeks after the last session.
9. **Fictional only.** Invented names, places and employers. No real brands where avoidable, no real people.
