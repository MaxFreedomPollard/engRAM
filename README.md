# engRAM

### Superior agentic memory, encrypted at rest.

engRAM is the memory your AI agents plug into. Hermes selects it as a
native provider, Claude connects over MCP, OpenClaw registers it in one
command, and anything that runs a subprocess can use the CLI. Everything
is local. The default install never touches the network, not once: the
embedding model ships inside the package, and 4,808 starter facts arrive
as precomputed vectors, so recall works seconds after install. Every byte
at rest is AEAD-encrypted, the vectors included. The vault locks itself on
restart or power loss and unlocks once per boot.

*An **engram** is the physical trace a memory leaves in the brain. This
one lives in **RAM**: the whole index is held in memory, which is what
makes it both the fastest place to search and the safest place to keep
plaintext, because nothing decrypted is ever written to disk.*

## Why engRAM

Most memory tools ask you to choose: powerful, or private, or easy. engRAM
refuses the trade, because one design decision delivers all three.

**Better recall.** engRAM does not just store chat, it decides what
matters. A bare "OK" answering "may I edit the registry?" is captured as a
consent decision, with its question, at the highest priority. Facts about
you and your machine outrank world trivia. Search is hybrid (meaning plus
keywords) and, at personal scale, mathematically exact: the top result is
the true top result, not an approximation. It learns you first, and
forgets nothing.

**More secure, by construction.** Every byte at rest is authenticated-
encrypted, the embedding vectors included (most tools leave those in the
clear, and vectors can be inverted back toward text). Deletion is
cryptographic: destroy the record's key and it is gone, unrecoverable.
Tampering is detected, history is hash-chained, and the vault locks itself
on restart or power loss. It runs fully offline: a runtime guard aborts on
any network attempt, and CI proves it on three operating systems.

**Not one step harder.** One command installs it, seeds 4,808 facts, and
wires your agent. No API key, no cloud account, no daemon. You unlock once
and it stays open for weeks, like any app you leave running. The security
is free at the point of use because it falls out of the architecture, not
out of your patience: keeping plaintext off disk forces the index into
RAM, and a RAM-resident index is also the fastest one there is. Secure and
fast are the same choice here, and neither costs you a configuration step.

## Install

One command per platform. Each installs the package, creates your
encrypted vault preloaded with the starter knowledge, and wires the agent.

**Claude (Code + Desktop)** — macOS / Linux:
```bash
pip install engram-vault && engram init && engram integrate claude
```
Windows (PowerShell):
```powershell
py -m pip install engram-vault; engram init; engram integrate claude
```
Registers the MCP server with the Claude Code CLI (user scope, all
projects), prints the Claude Desktop config block, and prints the one-line
CLAUDE.md instruction that makes Claude treat engRAM as its memory.

**Hermes** — macOS / Linux:
```bash
pip install engram-vault && engram init && engram integrate hermes
```
Windows (PowerShell):
```powershell
py -m pip install engram-vault; engram init; engram integrate hermes
```
Installs the provider plugin, wires the Hermes venv, and runs
`hermes memory setup engram`. engRAM then appears in the
`hermes memory setup` picker beside hindsight and mem0, the only entry
marked **"no setup needed"**: no API key, no cloud account, no daemon.
Verify with `hermes memory status`.

**OpenClaw** — macOS / Linux:
```bash
pip install engram-vault && engram init && engram integrate openclaw
```
Windows (PowerShell):
```powershell
py -m pip install engram-vault; engram init; engram integrate openclaw
```
Writes the `mcpServers` entry into `~/.openclaw/openclaw.json` (with a
backup), then: `openclaw gateway restart` and confirm with
`openclaw mcp list`.

Anything else that speaks MCP gets the same server with one config block;
see [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md). Until the PyPI release,
replace `pip install engram-vault` with a clone + `pip install .`;
everything else is identical.

## Measured, on an 8 GB baseline laptop

Every number below is reproducible on your machine with `engram selftest`
and `engram bench`.

| Metric | Measured |
|---|---|
| Fresh install → working memory | 4,808 facts, seconds, zero network |
| Hybrid recall over the starter corpus | p50 ≈ 2 ms per query |
| Vector search, 20k records (HNSW) | p95 0.68 ms |
| Full hybrid search (embed + vector + BM25 + fuse) | p95 8.8 ms |
| Peak RSS, model + vault + index resident | 319 MB |
| Store one memory (embed + encrypt + fsync journal) | ~40 ms |
| Wheel size, model and starter packs included | 30 MB |
| Test suite (crypto, tamper, crash, offline, concurrency) | 63 tests, ~25 s |

A single network round-trip to a cloud memory API costs more than this
entire pipeline. The property that makes engRAM secure (no plaintext
index ever on disk, so all search is RAM-resident) is the same property
that makes it fast: below 20k records search is exact SIMD matrix math,
recall = 1.0 by construction; above it, SIMD HNSW at ~99% recall.

## The memory logic

Full write-path, decision math, and comparisons in
[docs/MEMORY.md](docs/MEMORY.md). The load-bearing ideas:

**Nearly everything is stored; nothing important is buried.** Only empty
turns are dropped. A bare "OK" is not noise, it is a decision: when the
agent asks *"Are you cool with me editing the registry to accomplish
this?"* and the user answers *"OK"*, engRAM resolves the question from
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
explicit: `engram reindex --re-embed`.

**No LLM inside.** Embeddings run locally (bundled 384-dim int8 ONNX
model, <300 MB RAM). Judgment belongs to the host model you already run,
via `engram_store` / `engram_forget`; engRAM contributes deterministic
capture, encryption, and total recall. That split is what makes the
offline guarantee absolute and every decision reproducible.

## Starter knowledge (never begin blank)

Every fresh vault is seeded with **one unified pack: `starter`, 4,808
facts**, Ed25519-signed, shipped with precomputed vectors (install does
zero embedding work). Its single editable source is
[`tools/starter/starter_facts.jsonl`](tools/starter/starter_facts.jsonl):
one JSON fact per line, readable and editable by hand. Exact contents:

- **260 general facts** (ids `core-*`, the frozen `selftest` corpus):
  60 world capitals · 30 chemical elements (symbol + atomic number) ·
  30 unit conversions · 30 historical dates · 40 science · 30 geography ·
  20 math · 20 astronomy.
- **4,394 pragmatic facts** (ids `akc-*`, from the
  [Artificial Knowledge Collection 6.0](https://github.com/MaxFreedomPollard/artificial-knowledge-collection-6.0),
  compilation CC BY-SA 4.0): 434 real-world measurements with ranges ·
  415 CODATA physical constants · 1,706 country facts (capital,
  population, area, government, languages, life expectancy for 261
  countries) · 645 named physical features · 594 element/planet/moon/
  constellation facts · 600 common-food nutrition facts.
- **153 operating-system facts** (ids `macos-*`, `windows-*`, `linux-*`),
  all platforms on every install: Windows registry hives and keys
  (HKLM/HKCU/HKCR, Run/Uninstall/Services), %APPDATA%-family paths,
  NTFS/FAT32/exFAT, reg/sfc/DISM/winget · macOS APFS, ~/Library, launchd,
  codesign/spctl/defaults, SIP/Gatekeeper/TCC · Linux FHS, systemd,
  apt/dnf/pacman, permission bits.

To change what ships: edit `starter_facts.jsonl`, run
`python tools/build_starter_pack.py`, done — every line is re-embedded and
the pack re-signed ([PACKS.md](PACKS.md)). Grow a live vault directly with
`engram store` / `engram import`.

## The lock model

Locked by default, like all real encryption, but unlocked feels like an
open app:

- **Unlock once** → continuously usable through logouts and logins, for
  weeks or months, across every process, until the next restart.
- **Restart or power loss → locked.** The stored credential is the master
  key wrapped by a key derived from the kernel's boot timestamp plus the
  stable machine id; a new boot can never open the old wrap. This is
  arithmetic, not a policy check.
- **`engram lock`** (or the `memory_lock` panic tool from any agent)
  locks instantly and clears every stored credential.
- Reboot-surviving unlock is an explicit opt-in on macOS
  (`engram unlock --keychain`), with the tradeoff documented.

## Security, in one paragraph

XChaCha20-Poly1305 AEAD on everything at rest including vectors
(embedding-inversion resistance) · Argon2id keyslots, LUKS-style, with a
16-word recovery phrase · per-record keys enabling `forget --shred`
(crypto-shred: key destroyed, content mathematically unrecoverable) ·
fsync'd sealed journal, atomic compaction, verified kill-9 crash recovery ·
hash-chained tamper-evident audit log (`engram audit verify`) · per-caller
namespace ACLs, quarantine tier for untrusted content, signed vault
manifests · stdio MCP transport: zero open ports · runtime offline guard
that aborts on any socket attempt; CI runs the whole suite with it active
on Linux, macOS, and Windows · no telemetry, ever. Full honest threat
model, including what engRAM cannot protect against, in
[SECURITY.md](SECURITY.md).

## One vault, many agents

Hermes, Claude, and the CLI can share a single vault simultaneously:
writes are serialized by an advisory file lock, every process detects
foreign writes and reloads, and each host gets its own caller identity
and namespace with rw/ro grants. A locked vault is one portable file,
safe to move over any channel; `engram lock --sign` seals it with an
Ed25519 manifest the recipient can verify without any credential.

```bash
engram lock
scp ~/.engram/memory.vault other-machine:
engram --vault memory.vault unlock     # passphrase or recovery phrase
```

## Documentation

| | |
|---|---|
| [docs/MEMORY.md](docs/MEMORY.md) | how memory is stored, what gets remembered, why the math wins |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | selecting engRAM in Hermes, OpenClaw, Claude, everything else |
| [SECURITY.md](SECURITY.md) | full threat model, honest limits |
| [FORMAT.md](FORMAT.md) | byte-level `.vault` and `.mpack` specs (language-agnostic) |
| [PACKS.md](PACKS.md) | authoring and shipping signed memory packs |

## License

MIT. Starter-pack contents carry their stated licenses
(`akc-pragmatic`: compilation CC BY-SA 4.0).
