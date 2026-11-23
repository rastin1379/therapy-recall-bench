"""Load personas, the retrieval corpus, and the queries. Standard library only."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "personas"

CATEGORIES = {
    "latent_trait": "A trait or diagnosis disclosed earlier explains what the client is doing now.",
    "relational_template": "A current relationship repeats the shape of an earlier one.",
    "trigger_recurrence": "The same trigger and reaction shows up again in a different setting.",
    "symbolic_reference": "An object, place, smell, song or metaphor points back to an earlier memory.",
    "temporal_anniversary": "A date, season or recurring event links to something that happened then.",
    "state_update": "An earlier fact was later changed or reversed; you need the latest state and what it replaced.",
    "risk_signal": "A harmless-sounding message only looks worrying next to an earlier disclosure.",
    "entity_resolution": "A nickname, role or pronoun refers to someone introduced earlier under another name.",
    "contradiction": "What the client says now conflicts with what they disclosed before.",
    "coping_resource": "Something that helped before is relevant now, even though the client says nothing helps.",
}


def load_personas(data_dir: Path | str = DATA_DIR) -> list[dict]:
    paths = sorted(Path(data_dir).glob("*.json"))
    return [json.loads(p.read_text()) for p in paths]


def iter_turns(persona: dict) -> Iterator[dict]:
    """Yield every history turn with its session id and date attached."""
    for session in persona["sessions"]:
        for turn in session["turns"]:
            yield {
                "persona_id": persona["persona_id"],
                "session_id": session["session_id"],
                "date": session["date"],
                **turn,
            }


def load_queries(personas: list[dict]) -> list[dict]:
    out = []
    for persona in personas:
        for q in persona["queries"]:
            out.append({"persona_id": persona["persona_id"], **q})
    return out


# --- light text processing shared by the validator and the BM25 baseline ---

STOPWORDS = set(
    """
a about above after again against all almost also am an and any are aren't as at be because been before being
below between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each
few for from further had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him
himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more most mustn't my
myself no nor not of off on once only or other ought our ours ourselves out over own same shan't she she'd she'll
she's should shouldn't so some such than that that's the their theirs them themselves then there there's these
they they'd they'll they're they've this those through to too under until up very was wasn't we we'd we'll we're
we've were weren't what what's when when's where where's which while who who's whom why why's with won't would
wouldn't you you'd you'll you're you've your yours yourself yourselves
yeah yes okay ok oh um uh hmm like just really actually kind sort lot lots bit little thing things stuff maybe
guess mean think thought know knew feel feels felt feeling feelings say said says tell told get got gets go goes
went going gone come came want wanted make made way time times day days week weeks today yesterday tomorrow
now still even much many well right good bad pretty quite something anything nothing everything someone anyone
one ones also back again always never sometimes lately last next first around since though
""".split()
)

_WORD = re.compile(r"[a-z][a-z']+")


def stem(word: str) -> str:
    word = word.strip("'")
    if word.endswith("'s"):
        word = word[:-2]
    for suffix in ("ingly", "edly", "ing", "ies", "ed", "es", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def content_terms(text: str) -> list[str]:
    return [stem(w) for w in _WORD.findall(text.lower()) if w not in STOPWORDS and len(w) > 2]
