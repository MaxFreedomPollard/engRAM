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

One command per platform. Each installs the package, creates your
encrypted vault preloaded with the starter knowledge, and wires the agent.

**Claude (Code + Desktop)** — macOS / Linux:
```bash
pip install nucleus-vault && nucleus init && nucleus integrate claude
```
Windows (PowerShell):
```powershell
py -m pip install nucleus-vault; nucleus init; nucleus integrate claude
```
Registers the MCP server with the Claude Code CLI (user scope, all
projects), prints the Claude Desktop config block, and prints the one-line
CLAUDE.md instruction that makes Claude treat Nucleus as its memory.

**Hermes** — macOS / Linux:
```bash
pip install nucleus-vault && nucleus init && nucleus integrate hermes
```
Windows (PowerShell):
```powershell
py -m pip install nucleus-vault; nucleus init; nucleus integrate hermes
```
Installs the provider plugin, wires the Hermes venv, and runs
`hermes memory setup nucleus`. Nucleus then appears in the
`hermes memory setup` picker beside hindsight and mem0, the only entry
marked **"no setup needed"**: no API key, no cloud account, no daemon.
Verify with `hermes memory status`.

**OpenClaw** — macOS / Linux:
```bash
pip install nucleus-vault && nucleus init && nucleus integrate openclaw
```
Windows (PowerShell):
```powershell
py -m pip install nucleus-vault; nucleus init; nucleus integrate openclaw
```
Writes the `mcpServers` entry into `~/.openclaw/openclaw.json` (with a
backup), then: `openclaw gateway restart` and confirm with
`openclaw mcp list`.

Anything else that speaks MCP gets the same server with one config block;
see [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md). Until the PyPI release,
replace `pip install nucleus-vault` with a clone + `pip install .`;
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

Every fresh vault is seeded with **4,703 facts** (on macOS; 4,707 on
Windows, 4,705 on Linux), all Ed25519-signed and shipped with precomputed
vectors, so install does zero embedding work. Exact contents:

**`core-facts` — 260 facts** (the frozen `selftest` corpus):
60 world capitals · 30 chemical elements (symbol + atomic number) ·
30 unit conversions · 30 historical dates · 40 science facts ·
30 geography facts · 20 math facts · 20 astronomy facts.

**`akc-pragmatic` — 4,394 facts** (from the
[Artificial Knowledge Collection 6.0](https://github.com/MaxFreedomPollard/artificial-knowledge-collection-6.0),
compilation CC BY-SA 4.0):
434 real-world measurements (typical mass/size/speed of things, with
ranges) · 415 CODATA physical constants · 1,706 country facts (capital,
population, area, government, languages, life expectancy, region for 261
countries) · 645 named physical features (lakes, rivers, deserts) ·
594 element/astronomy facts (118 elements with properties, planets,
moons, the 88 constellations) · 600 common-food nutrition facts (kcal,
protein, fat per 100 g).

**One OS pack, auto-selected for your platform:**
`os-windows` (53 facts: registry hives HKLM/HKCU/HKCR/HKU/HKCC, the
Run/Uninstall/Services keys, hive backing files, `%APPDATA%`-family
paths, System32/SysWOW64, NTFS/FAT32/exFAT, reg/sfc/DISM/winget,
versions and builds) · `os-macos` (49 facts: APFS, `~/Library` layout,
launchd, codesign/spctl/defaults/launchctl, SIP/Gatekeeper/TCC/FileVault,
shortcuts) · `os-linux` (51 facts: FHS paths, /etc files, systemd,
apt/dnf/pacman/zypper, permission bits, core commands).

Add your own facts before or after install (see
[PACKS.md](PACKS.md)): `nucleus pack export` dumps any shipped pack to
editable JSONL, `nucleus pack build` re-signs it, and `nucleus store` /
`nucleus import` grow the live vault directly.

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
