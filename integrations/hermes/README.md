# Hermes integration

`engram/` is a native Hermes **memory provider plugin** — the same
mechanism Hindsight and Mem0 use. Hermes discovers user-installed providers
in `~/.hermes/plugins/<name>/` and activates the one named by
`memory.provider` in `~/.hermes/config.yaml`.

Install (four steps, see the plugin's docstring for detail):

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install engram-vault
cp -r engram ~/.hermes/plugins/engram
engram init                     # once; stays unlocked until restart
# config.yaml → memory.provider: engram
hermes memory status             # Provider: engram, available ✓
```

What Hermes gets: automatic recall injected before each turn, automatic
AEAD-encrypted persistence of each turn, `engram_search` /
`engram_store` / `engram_forget` agent tools, `hermes backup` coverage of
the vault file, and the locked-by-default guarantee (after any restart,
memory is unavailable until `engram unlock`).

Prefer MCP instead? `engram serve` works with `hermes mcp add` like any
MCP server — but the provider integration is the recommended path for
Hermes because recall/persistence become automatic rather than
tool-invoked.
