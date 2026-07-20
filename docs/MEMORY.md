# How Nucleus Remembers

How memory is stored, how Nucleus decides what becomes a memory, and why
this design is mathematically stronger than the alternatives. Every claim
in this document is enforced by code and covered by the test suite.

---

## 1. How a memory is stored

When an agent finishes a turn (or calls `nucleus_store` / `memory_store`),
the following happens **locally, in about 40 milliseconds, with zero
network involvement**:

```
text
 │  1. EMBED         bundled bge-small int8 ONNX model, on your CPU
 ▼                   → one 384-dimensional unit vector (~25 ms)
vector + text
 │  2. DEDUPLICATE   nearest-neighbor cosine ≥ 0.97 in the same namespace
 ▼                   → return the existing record instead of double-storing
record
 │  3. ENCRYPT       fresh per-record key wraps the text (XChaCha20-Poly1305);
 ▼                   the per-record key itself is wrapped by the vault master
 │                   key — destroying it later = crypto-shred
 │  4. INDEX         vector → RAM-resident index (exact SIMD < 20k records,
 ▼                   SIMD HNSW above); tokens → FTS5 BM25 index
 │  5. PERSIST       the write is sealed (AEAD) and appended to the vault
 ▼                   journal with fsync — an acknowledged write survives
 │                   kill -9 and power loss
 └─ 6. AUDIT         a hash-chained, encrypted audit entry records who
                     stored what, when — history cannot be silently edited
```

Every stored record carries: the text (encrypted under its own key), its
384-dim float32 vector, namespace, tags, importance, quarantine flag,
provenance (host / agent / session), and timestamps. **The vector is
encrypted at rest too** — embeddings can be partially inverted back toward
their text, so treating vectors as non-sensitive (as most systems do) is a
hole; Nucleus doesn't have it.

New memories land in the writing agent's namespace (e.g. `hermes`), in the
same vault and the same searchable index as the starter pack
(`packs/core-facts`) — one vector space, searched together. Pack
namespaces stay read-only, so curated knowledge is never diluted by chat
traffic, and living memory never has to be shipped to be shared.

### Nothing embeds twice

Install time is the one moment most systems spend minutes embedding a
starter corpus — Nucleus spends zero, because memory packs ship their
vectors precomputed, bit-exact for the pinned model. Runtime embedding
happens exactly once per new memory, forever cached inside the vault.

## 2. How Nucleus decides what becomes a memory

Nucleus never calls an LLM (that is what keeps the offline guarantee
absolute), so the write decision is a **deterministic, three-stage
mathematical filter** plus one agent-directed path:

**Stage 1 — triviality filter.** Bare acknowledgements ("ok", "thanks",
"continue"), empty turns, and sub-signal fragments store nothing. No model
needed to know these carry no future value.

**Stage 2 — durability signals.** Phrases that mark long-lived facts —
*remember, always, never, prefer, my X is, deadline, every Monday,
timezone, address, decided…* — force the store and raise importance
(0.7 vs the default 0.4). An explicit "remember this" is never
second-guessed by later stages.

**Stage 3 — the novelty gate.** An unsignaled turn is embedded and
compared against existing memory. Let `s` be the cosine similarity of its
nearest neighbor; the turn is stored only if

&nbsp;&nbsp;&nbsp;&nbsp;**novelty = 1 − s > 0.08**  (i.e. nearest neighbor < 0.92)

with an exact-duplicate guard at 0.97 on every write path. The
consequence is the design's key growth property: **storage grows with
unique information, not with turn count.** Ask about the same topic
fifty times and the vault holds it once — while a genuinely new fact
always clears the gate, because novelty is measured in the same vector
space used for recall.

**The agent-directed path.** The host model (Hermes, Claude, anything)
also holds `nucleus_store` / `nucleus_forget` tools, so the intelligence
*you already pay for* curates memory explicitly — distilling a session
into durable facts, deleting stale ones, crypto-shredding sensitive ones.
Nucleus deliberately splits the labor: **the host model supplies judgment;
Nucleus supplies deterministic math, encryption, and total recall.** A
memory layer that runs its own LLM either phones home (privacy gone) or
ships a second multi-gigabyte model (your RAM gone) — and its decisions
become non-reproducible either way.

Recall closes the loop: before each turn the user's message is embedded
and the top memories above cosine 0.45 are injected as context, ranked by
reciprocal-rank fusion of vector similarity and BM25 keyword score.
Recalled content is always wrapped with a *data-not-instructions* notice,
and memories flagged `quarantined` (stored from untrusted sources) carry
an explicit warning envelope — stored-prompt-injection hygiene that
memory layers generally lack.

## 3. Why this is mathematically and logically stronger

**Exact search at personal scale — retrieval is provably optimal.** Below
20,000 records Nucleus computes all similarities with SIMD matrix math:
the top-k result is the true top-k, recall = 1.0 by construction, in
under a millisecond. Mainstream vector stores run approximate (ANN)
indexes at *every* scale, accepting 95–99% recall on corpora small enough
to search exactly — approximation error with no compensating benefit.
Nucleus only switches to HNSW (~99% recall, p95 < 15 ms at 1M) when the
corpus actually demands it, and `reindex` rebuilds from stored vectors at
any time.

**One pinned embedding space — cosine stays meaningful.** Similarity
between two vectors is only defined if one model produced both. Nucleus
records the embedding model's SHA-256 in the vault and **refuses to open**
with a mismatched model (explicit `reindex --re-embed` migrates instead).
Systems that let the embedding model drift silently corrupt every
similarity they compute afterward — the errors are invisible until
retrieval quietly degrades.

**Sub-linear memory growth.** The novelty gate bounds the vault by the
information content of your history rather than its length. Turn-logging
systems grow O(turns) and their retrieval drowns in near-duplicates of
whatever you discuss most — precisely the memories that add nothing.

**The write path is crash-proof by argument, not by luck.** An
acknowledged write is an fsync'd, AEAD-sealed journal entry; compaction is
write-temp → fsync → atomic rename. A `kill -9` at any instant loses at
most the single unacknowledged write in flight (verified by test). A
truncated tail is distinguishable *cryptographically* from tampering, so
crash recovery can be lenient exactly where malice is impossible.

**Security reduces to standard hard problems.** Forging any stored byte
means defeating Poly1305 authentication (success probability ≈ 2⁻¹²⁸ per
attempt); recovering a shredded memory means decrypting XChaCha20 without
its destroyed key; brute-forcing the passphrase costs 64 MiB × 3
iterations of Argon2id *per guess*; reviving an unlock credential after
power loss means re-deriving a key whose input (the boot timestamp) no
longer exists. No policy checks, no honor system — each guarantee is an
inequality about a well-studied primitive.

**Latency arithmetic.** Local embed ~25 ms + exact search <1 ms ≈ **one
network round-trip is already slower than our entire pipeline.** Cloud
memory APIs add tens to thousands of milliseconds per recall and per
store, on every single turn, plus an availability dependency and a
privacy surrender. The RAM-residency that makes Nucleus secure (no
plaintext index on disk) is the same property that makes it fast — in
this design, security and speed are the same decision.

**Honest limits** (see SECURITY.md for the full threat model): novelty
gating is heuristic, not semantic understanding — the host model's
explicit curation exists precisely to cover what heuristics miss; HNSW
above 20k records is ~99% recall, not 100%; and no memory system can
protect an unlocked vault from a fully compromised OS.

## 4. The same math, in one table

| Property | Nucleus | Cloud memory APIs | Typical local vector DB | Raw turn-logging |
|---|---|---|---|---|
| Recall correctness (personal scale) | exact, 1.0 | ANN ≈0.95–0.99 | ANN ≈0.95–0.99 | keyword only |
| Store/recall latency | ~25 ms / <1 ms | 100 ms–40 s | ms | ms |
| Storage growth | O(unique information) | O(turns) | O(turns) | O(turns) |
| Embedding-space consistency | hash-pinned, enforced | provider may change | unenforced | n/a |
| At-rest encryption (incl. vectors) | always, AEAD | provider-side | usually none | none |
| Deletion | crypto-shred | request + trust | row delete | row delete |
| Tamper evidence | AEAD + hash-chained audit | none visible | none | none |
| Works offline / air-gapped | always | never | usually | yes |
| Survives restart unlocked | no — locked by default | n/a | yes (no lock at all) | yes |
