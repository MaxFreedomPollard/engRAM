# Nucleus

**High-security, fully offline, encrypted vector memory for AI agents.**

The default install never touches the network — **not even once**. The
embedding model ships inside the package; a built-in seed knowledge pack
proves the whole pipeline works the minute install finishes; and every byte
at rest is AEAD-encrypted. Your agent's memory locks into a single portable
`.vault` file for transfer.

Works with any MCP-capable host — Hermes, OpenClaw, Claude Code, Claude
Desktop, and anything else that speaks MCP or can shell out to a CLI.

*In atomic physics, the nucleus holds nearly all the mass. In the brain, a
nucleus is a cluster of neurons. In a cell, the nucleus stores the genome —
the cell's memory. This one stores your agent's.*

## Why Nucleus is fast AND secure (same design)

Nucleus's security invariant — *plaintext never touches disk* — forces every
index into RAM. RAM-resident search happens to be the fastest possible
architecture: exact SIMD search below 20k records (perfect recall,
sub-millisecond), SIMD-accelerated HNSW (usearch) above it. Disk-based
vector formats exist to cope with corpora too big for RAM; agent memory is
not that, so Nucleus never pays the disk penalty — or leaves an index behind
for forensics.

Measured on an M-series laptop (8GB-RAM baseline hardware):
seed-pack hybrid query p50 **~2ms**, 20k-vector search p95 **<5ms**,
peak RSS a few hundred MB. Run `nucleus bench` for numbers on your machine.

## 5-minute quickstart

```bash
# from source (PyPI: `pipx install nucleus-vault` once published)
git clone <this-repository> nucleus && cd nucleus && pip install .

nucleus init                        # choose passphrase, get recovery phrase,
                                    # seed pack auto-installs (260 facts)
nucleus selftest                    # 20 canned queries must pass — with latencies
nucleus store "The staging DB password rotates on Mondays"
nucleus search "when does the staging password rotate"
```

`selftest` output ends with `"failed": 0` — that is your proof the entire
pipeline (crypto → store → embed → index → hybrid search) works, offline.

## How it remembers

The full write path, the three-stage write-decision math (triviality
filter → durability signals → novelty gate), and the argument for why this
design beats cloud memory, ANN-everywhere local stores, and turn-logging
is in **[docs/MEMORY.md](docs/MEMORY.md)**. The one-line version: storage
grows with unique information rather than turn count, retrieval is exact
(recall = 1.0) at personal scale, and the host agent's own model curates
explicitly through `nucleus_store` / `nucleus_forget` — Nucleus never
calls an LLM itself.

## The lock model

Locked by default, like all real encryption — but unlocked feels like an
open app:

- **Unlock once** (`nucleus unlock`, or automatically at `init`) → the vault
  stays continuously usable — through logouts and logins, for weeks or
  months, across every process that opens it.
- **Restart or power loss → locked again.** The stored credential is the
  master key wrapped by a key derived from the kernel's boot timestamp; a
  new boot can never open the old wrap, so the credential dies with the
  power. Enter the passphrase once after each boot and you're back.
- **`nucleus lock`** (or the `memory_lock` panic tool from any agent) locks
  immediately and clears every stored credential.
- macOS users who *want* unlock to survive reboots can opt in explicitly
  with `nucleus unlock --keychain` (tradeoff documented in SECURITY.md).

## Hermes: native memory provider

Nucleus plugs into Hermes as a first-class memory provider — selected the
same way as Hindsight or Mem0, with automatic recall before each turn,
automatic encrypted persistence of each turn, and `nucleus_search` /
`nucleus_store` / `nucleus_forget` agent tools:

```bash
# 1. install nucleus into the Hermes venv
~/.hermes/hermes-agent/venv/bin/python -m pip install nucleus-vault
# 2. install the provider plugin
cp -r integrations/hermes/nucleus ~/.hermes/plugins/nucleus
# 3. create + unlock your vault (once)
nucleus init
# 4. select it
#    ~/.hermes/config.yaml →  memory:
#                               provider: nucleus
hermes memory status        # → Provider: nucleus, available ✓
```

## Hooking up any other agent (MCP)

Unlock once on the machine (`nucleus unlock --keychain` on macOS, or set
`NUCLEUS_PASSPHRASE`), then point your host at `nucleus serve`. stdio
transport: **zero open ports** — only the host that spawns Nucleus can
reach it.

**Claude Code** (`.mcp.json` or `claude mcp add`):
```json
{
  "mcpServers": {
    "nucleus": {
      "command": "nucleus",
      "args": ["--vault", "/Users/you/.nucleus/memory.vault",
               "--caller", "claude-code", "serve"]
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`), **Hermes**
(`~/.hermes/config.yaml` → `mcp_servers:`), and **OpenClaw** use the same
three-part recipe: command `nucleus`, args as above, one instance per host
with its own `--caller` name. Namespace grants per caller live in
`<vault>.config.json`.

Tools exposed: `memory_store`, `memory_search`, `memory_get`,
`memory_forget` (with crypto-shred), `memory_list_namespaces`,
`memory_status`, `memory_selftest`, `memory_lock` (panic lock),
`memory_unlock` (disabled by default — see SECURITY.md).

## Transfer

```bash
nucleus lock                        # clear credentials; vault is one sealed file
scp ~/.nucleus/memory.vault other-machine:   # safe over any channel
nucleus --vault memory.vault unlock          # passphrase or 16-word recovery phrase
```

One vault can serve several agents at once (Hermes + Claude + CLI): writes
are serialized by an advisory file lock, every process detects when another
one has written and reloads, and per-caller namespace ACLs keep each
agent's memories separated.

A locked vault is a single AEAD-sealed file: an interceptor gets nothing,
and any modification — even one bit — makes unlock fail loudly. `nucleus
verify` checks structure and (for signed vaults) the Ed25519 manifest
without needing any credential.

## Memory packs

Signed, versioned knowledge add-ons that install offline with precomputed
vectors (zero compute when the model matches — which it always does for
first-party packs):

```bash
nucleus pack build facts.jsonl --name my-pack --creator "You"
nucleus pack install my-pack-1.0.0.mpack
nucleus pack remove my-pack
```

Install verifies the Ed25519 signature and content hash **first** and
refuses loudly on any mismatch. Pack records are read-only for every
caller. See PACKS.md.

## The offline guarantee, made checkable

- stdio MCP transport: no listeners, no ports.
- `--assert-offline` (or `NUCLEUS_ASSERT_OFFLINE=1`): the process aborts if
  anything attempts to create a network socket.
- The test suite runs the full lifecycle — init, seed install, selftest,
  store, search, shred, lock, unlock — **with socket creation blocked**.
- The one and only network-capable command is `nucleus setup
  download-model` (optional bigger/multilingual models, SHA-256 pinned),
  and it announces itself as such. Air-gapped machines skip it entirely:
  `nucleus setup airgap-bundle` builds a USB-installable archive.

## Security properties (full model in SECURITY.md)

XChaCha20-Poly1305 everywhere · Argon2id KDF · LUKS-style keyslots with a
16-word recovery phrase · per-record keys enabling `forget --shred`
(crypto-shred) · encrypted vectors (embedding-inversion resistance) ·
hash-chained tamper-evident audit log (`nucleus audit verify`) · per-caller
namespace ACLs · quarantine tier for untrusted content · signed vault
manifests · plaintext never on disk · no telemetry, ever.

## RAM budget (8GB baseline)

Bundled model: bge-small-en-v1.5 int8 ONNX, 384-dim, ~34MB on disk,
<300MB at inference. Vault RAM ≈ 200MB + ~3KB/record at f32. `nucleus
status` shows the projection; past ~250k records, `nucleus reindex --int8`
quarters vector RAM for ~1–2% recall cost.

## License

MIT.
