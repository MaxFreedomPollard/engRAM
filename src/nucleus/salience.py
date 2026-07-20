"""Deciding what deserves to become a memory — offline, deterministic math.

Nucleus never calls an LLM, so the write decision is made from measurable
signals, in three stages (documented in docs/MEMORY.md):

1. TRIVIALITY FILTER (this module): pure-text heuristics drop turns that
   carry no durable content — bare acknowledgements, empty chatter.
2. DURABILITY SIGNALS (this module): phrases that mark long-lived facts
   ("remember", "always", "my X is", dates/schedules/identities) force the
   store and raise importance.
3. NOVELTY GATE (caller + vector index): a candidate WITHOUT a durability
   signal is embedded and compared against existing memories; if its
   nearest neighbor's cosine ≥ NOVELTY_THRESHOLD the turn adds almost no
   information to the vector space and is skipped. Storage therefore grows
   with unique information, not with raw turn count.

The exact-duplicate guard (cosine ≥ 0.97 → return the existing id) lives
in Vault.store and applies to every write from every integration.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Stage 3 threshold: below the 0.97 duplicate guard, above topical
# similarity. Full-turn texts only exceed 0.92 when genuinely repetitive.
NOVELTY_THRESHOLD = 0.92

# Bare acknowledgements: a user turn that IS one of these stores nothing.
_NOISE = {
    "ok", "okay", "k", "kk", "y", "n", "yes", "no", "yep", "nope", "sure",
    "thanks", "thank you", "thx", "ty", "great", "cool", "nice", "good",
    "continue", "go on", "next", "proceed", "done", "stop", "wait", "hmm",
    "lol", "haha", "got it", "sounds good", "perfect", "please continue",
}

# Durability signals: phrases that mark facts worth keeping long-term.
_KEEP = re.compile(
    r"\b(remember|don'?t forget|note that|for future|from now on|going forward"
    r"|always|never|prefer(?:s|red)?|favorite|favourite"
    r"|my \w+ (?:is|are)|call me|i am|i'?m|we (?:are|use|decided)"
    r"|decided|decision|agreed|the plan is|policy"
    r"|deadline|due (?:on|by|date)|schedule[ds]?|every (?:day|week|month|year"
    r"|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"|birthday|anniversary|address|email|phone|account|timezone"
    r"|password rotates|key lives|located (?:in|at)|stored (?:in|at))\b",
    re.IGNORECASE,
)

DEFAULT_IMPORTANCE = 0.4
SIGNAL_IMPORTANCE = 0.7
MIN_MEANINGFUL_CHARS = 12


@dataclass(frozen=True)
class Assessment:
    store: bool
    importance: float
    has_signal: bool     # True → caller must skip the novelty gate
    reason: str


def has_keep_signal(text: str) -> bool:
    return bool(_KEEP.search(text or ""))


def assess_turn(user_text: str, assistant_text: str) -> Assessment:
    """Stages 1+2. The caller applies stage 3 (novelty) only when
    has_signal is False and store is True."""
    u = (user_text or "").strip()
    signal = has_keep_signal(u) or has_keep_signal(assistant_text or "")
    if not u:
        return Assessment(False, 0.0, signal, "empty user turn")
    bare = u.lower().rstrip(".!?…")
    if bare in _NOISE and not signal:
        return Assessment(False, 0.0, False, f"bare acknowledgement {bare!r}")
    if len(u) < MIN_MEANINGFUL_CHARS and not signal:
        return Assessment(False, 0.0, False, "below meaningful length")
    if signal:
        return Assessment(True, SIGNAL_IMPORTANCE, True, "durability signal")
    return Assessment(True, DEFAULT_IMPORTANCE, False, "substantive turn")
