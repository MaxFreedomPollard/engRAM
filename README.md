# Nucleus

**High-security, fully offline, encrypted vector memory for AI agents.**

Nucleus is a memory vault your agents plug into: Hermes selects it as a
native memory provider, Claude connects over MCP, and anything that can
run a subprocess can use the CLI. Everything is local. The default install
never touches the network, not even once: the embedding model ships inside
the package, and roughly 4,700 starter facts arrive as precomputed vectors,
so recall works seconds after install. Every byte at rest is
AEAD-encrypted, including the vectors. The vault locks itself on restart or
power loss and unlocks once per boot.

*In atomic physics, the nucleus holds nearly all the mass. In the brain, a
nucleus is a cluster of neurons. In a cell, the nucleus stores the genome:
the cell's memory. This one stores your agent's.*

## Install

**Hermes** (macOS / Linux):
```bash
pip install nucleus-vault && nucleus init && nucleus integrate hermes
```
**Hermes** (Windows, PowerShell):
```powershell
py -m pip install nucleus-vault; nucleus init; nucleus integrate hermes
```
`integrate hermes` installs the provider plugin, wires the Hermes venv,
and runs `hermes memory setup nucleus`. Nucleus then shows in
`hermes memory status` as the active provider, and in the
`hermes memory setup` picker beside hindsight and mem0, the only entry
marked **"no setup needed"**: no API key, no cloud account, no daemon.

**Claude Code / Claude Desktop** (macOS / Linux):
```bash
pip install nucleus-vault && nucleus init && nucleus integrate claude
```
**Claude** (Windows, PowerShell):
```powershell
py -m pip install nucleus-vault; nucleus init; nucleus integrate claude
```
`integrate claude` registers the MCP server with the Claude Code CLI
(user scope, all projects) and prints the Claude Desktop config block plus
the one-line CLAUDE.md instruction that makes Claude treat Nucleus as its
memory.

Anything else that speaks MCP gets the same server with one config block;
see [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md). Until the PyPI release,
replace `pip install nucleus-vault` with a clone + `pip install .` —
everything else is identical.

## Measured, on an 8 GB baseline laptop

Every number below is reproducible on your machine with `nucleus selftest`
and `nucleus bench`.

| Metric | Measured |
|---|---|
| Fresh install → working memory | ~4,700 facts, seconds, zero network |
| Hybrid recall over the starter corpus | p50 ≈ 2 ms per query |
| Vector search, 20k records (HNSW) | p95 0.68 ms |
| Full hybrid search (embed + vector + BM25 + fuse) | p95 8.8 ms |
| Peak RSS, model + vault + index resident | 319 MB |
| Store one memory (embed + encrypt + fsync journal) | ~40 ms |
| Wheel size, model and starter packs included | 30 MB |
| Test suite (crypto, tamper, crash, offline, concurrency) | 67 tests, ~10 s |

A single network round-trip to a cloud memory API costs more than this
entire pipeline. The property that makes Nucleus secure (no plaintext
index ever on disk, so all search is RAM-resident) is the same property
that makes it fast: below 20k records search is exact SIMD matrix math,
recall = 1.0 by construction; above it, SIMD HNSW at ~99% recall.

## The memory logic

Full write-path, decision math, and comparisons in
[docs/MEMORY.md](docs/MEMORY.md). The load-bearing ideas:

**Nearly everything is stored; nothing important is buried.** Only empty
turns are dropped. A bare "OK" is not noise, it is a decision: when the
agent asks *"Are you cool with me editing the registry to accomplish
this?"* and the user answers *"OK"*, Nucleus resolves the question from
the conversation and stores
`[decision 2026-07-20] Approved (answered "OK"): Are you cool with me
editing the registry…` at the top importance tier. Asking *"did the user
approve registry edits?"* later retrieves exactly that record.

**Deterministic importance tiers rank recall**: decisions/consent 0.90,
personal facts and preferences 0.80, the user's machine and configuration
0.75, other substantive statements 0.55, pleasantries 0.20 (kept, ranked
last). The fused score is
`RRF(vector) + RRF(keyword) + 0.02·cosine + 0.006·importance`: cosine
magnitude keeps the genuinely best match on top, importance settles
near-ties in favor of what matters. The agent learns the user and the
computer first, the world second, and forgets nothing.

**One pinned embedding space.** The model's SHA-256 is recorded in the
vault and enforced at open; cosine comparisons stay mathematically valid
forever instead of silently degrading when a model changes. Migration is
explicit: `nucleus reindex --re-embed`.

**No LLM inside.** Embeddings run locally (bundled 384-dim int8 ONNX
model, <300 MB RAM). Judgment belongs to the host model you already run,
via `nucleus_store` / `nucleus_forget`; Nucleus contributes deterministic
capture, encryption, and total recall. That split is what makes the
offline guarantee absolute and every decision reproducible.

## Starter knowledge (never begin blank)

| Pack | Facts | Contents |
|---|---|---|
| `core-facts` | 260 | capitals, elements, dates, science, math, astronomy; the frozen `selftest` corpus |
| `akc-pragmatic` | ~4,400 | measurements, physical constants, country facts, elements, planets/moons/constellations, common-food nutrition; from the Artificial Knowledge Collection 6.0 (compilation CC BY-SA 4.0) |
| `os-macos` / `os-windows` / `os-linux` | ~50 each | pure OS facts: paths, commands, Windows registry hives and keys, versions, conventions |

The OS pack is selected automatically for the platform you install on. All
packs are Ed25519-signed and carry precomputed vectors, so installs do no
embedding work. Build your own with `nucleus pack build`
([PACKS.md](PACKS.md)).

## The lock model

Locked by default, like all real encryption, but unlocked feels like an
open app:

- **Unlock once** → continuously usable through logouts and logins, for
  weeks or months, across every process, until the next restart.
- **Restart or power loss → locked.** The stored credential is the master
  key wrapped by a key derived from the kernel's boot timestamp plus the
  stable machine id; a new boot can never open the old wrap. This is
  arithmetic, not a policy check.
- **`nucleus lock`** (or the `memory_lock` panic tool from any agent)
  locks instantly and clears every stored credential.
- Reboot-surviving unlock is an explicit opt-in on macOS
  (`nucleus unlock --keychain`), with the tradeoff documented.

## Security, in one paragraph

XChaCha20-Poly1305 AEAD on everything at rest including vectors
(embedding-inversion resistance) · Argon2id keyslots, LUKS-style, with a
16-word recovery phrase · per-record keys enabling `forget --shred`
(crypto-shred: key destroyed, content mathematically unrecoverable) ·
fsync'd sealed journal, atomic compaction, verified kill-9 crash recovery ·
hash-chained tamper-evident audit log (`nucleus audit verify`) · per-caller
namespace ACLs, quarantine tier for untrusted content, signed vault
manifests · stdio MCP transport: zero open ports · runtime offline guard
that aborts on any socket attempt; CI runs the whole suite with it active
on Linux, macOS, and Windows · no telemetry, ever. Full honest threat
model, including what Nucleus cannot protect against, in
[SECURITY.md](SECURITY.md).

## One vault, many agents

Hermes, Claude, and the CLI can share a single vault simultaneously:
writes are serialized by an advisory file lock, every process detects
foreign writes and reloads, and each host gets its own caller identity
and namespace with rw/ro grants. A locked vault is one portable file,
safe to move over any channel; `nucleus lock --sign` seals it with an
Ed25519 manifest the recipient can verify without any credential.

```bash
nucleus lock
scp ~/.nucleus/memory.vault other-machine:
nucleus --vault memory.vault unlock     # passphrase or recovery phrase
```

## Documentation

| | |
|---|---|
| [docs/MEMORY.md](docs/MEMORY.md) | how memory is stored, what gets remembered, why the math wins |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | selecting Nucleus in Hermes, OpenClaw, Claude, everything else |
| [SECURITY.md](SECURITY.md) | full threat model, honest limits |
| [FORMAT.md](FORMAT.md) | byte-level `.vault` and `.mpack` specs (language-agnostic) |
| [PACKS.md](PACKS.md) | authoring and shipping signed memory packs |

## License

MIT. Starter-pack contents carry their stated licenses
(`akc-pragmatic`: compilation CC BY-SA 4.0).
