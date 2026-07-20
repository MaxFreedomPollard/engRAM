# Selecting Nucleus as your agent's memory

How to make Nucleus the active memory in each ecosystem. Three mechanisms
exist in the wild — a native provider slot (Hermes, OpenClaw), MCP tool
registration (Claude and most modern agents), and plain CLI/JSON (anything
that can run a subprocess). Nucleus supports all three from one install.

---

## Hermes — native provider picker (works today)

Hermes selects external memory through `hermes memory setup`, an arrow-key
picker. Nucleus appears there as a first-class option once its plugin
directory is present:

```bash
# 1. nucleus into the Hermes environment
python -m pip install nucleus-vault
# 2. the provider plugin (from this repo)
cp -r integrations/hermes/nucleus ~/.hermes/plugins/nucleus
# 3. a vault (once) — seeds ~4,700 starter facts, stays unlocked until reboot
nucleus init
# 4. SELECT IT
hermes memory setup
```

The picker then shows:

```
  byterover     — API key / local
  hindsight     — API key / local
  holographic   — local
  honcho        — API key / local
  mem0          — API key / local
  openviking    — API key / local
  retaindb      — API key / local
  supermemory   — requires API key
▸ nucleus       — no setup needed        ← choose this
  Built-in only — MEMORY.md / USER.md
```

Nucleus is the only entry that needs no API key and no cloud account.
Selecting it writes `memory.provider: nucleus` to config.yaml; confirm with
`hermes memory status` (→ `Provider: nucleus`, `available ✓`). From then on
Hermes auto-recalls relevant memories before every turn, persists every
turn encrypted, and exposes `nucleus_search` / `nucleus_store` /
`nucleus_forget` tools.

**Shipping in Hermes out of the box** (no copy step for anyone): that
requires an upstream hermes-agent PR bundling this plugin under
`plugins/memory/nucleus` with `pip_dependencies: ["nucleus-vault"]` —
which in turn requires the PyPI release. Sequence: publish `nucleus-vault`
→ PR → every Hermes user sees Nucleus in the picker by default.

## OpenClaw — memory plugin slot

OpenClaw selects memory through a plugin slot: installing a memory plugin
"writes the plugin entry, enables it, and switches `plugins.slots.memory`"
to it (this is exactly how its LanceDB memory installs:
`openclaw plugins install @openclaw/memory-lancedb`).

- **Today (MCP):** OpenClaw speaks MCP — register `nucleus serve` as an MCP
  server and the `memory_*` tools are available to every OpenClaw agent
  immediately.
- **Native slot plugin (planned):** an `openclaw-memory-nucleus` plugin
  implementing OpenClaw's plugin architecture (`before_prompt_build`
  auto-recall hook + memory tools), bridging to the local `nucleus` CLI /
  MCP server. Selection then becomes:

  ```bash
  openclaw plugins install openclaw-memory-nucleus   # once published
  # → plugins.slots.memory: "memory-nucleus"
  openclaw gateway restart
  ```

## Claude (Code and Desktop) — MCP registration IS the selector

Claude has no memory-provider picker; registering an MCP server is how you
give Claude a memory. One command (Claude Code):

```bash
claude mcp add --scope user nucleus -- \
    nucleus --vault ~/.nucleus/memory.vault --caller claude-code serve
```

Claude Desktop (`claude_desktop_config.json`):

```json
{ "mcpServers": { "nucleus": {
    "command": "nucleus",
    "args": ["--vault", "/Users/you/.nucleus/memory.vault",
             "--caller", "claude-desktop", "serve"] } } }
```

The `memory_search` / `memory_store` / `memory_forget` / `memory_status` /
`memory_lock` tools then appear in every session. To make Claude treat it
as *the* memory (the analog of selecting a provider), add one standing
instruction to your `CLAUDE.md` / project memory:

> Use the nucleus `memory_search` tool to recall prior facts before
> answering questions about past work, and store durable facts and user
> decisions with `memory_store`.

## Everything else

| Agent kind | Mechanism | What to do |
|---|---|---|
| Any MCP-capable host (Cursor, Windsurf, custom SDK agents, …) | MCP stdio | the same one-block config as Claude, with its own `--caller` name |
| Python frameworks (LangChain/LlamaIndex-style) | vector-store adapter | import `nucleus.vault.Vault` directly, or use the CLI; a drop-in `VectorStore` adapter class is on the roadmap |
| Anything that can run a subprocess | CLI/JSON | `nucleus search "query" --json`, `nucleus store "text"` |

One vault serves all of them at once: writes are serialized across
processes, every host gets its own `--caller` identity and namespace, and
the per-caller ACLs in `<vault>.config.json` decide who reads what.
