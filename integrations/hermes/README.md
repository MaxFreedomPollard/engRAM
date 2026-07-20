# Hermes integration

`nucleus/` is a native Hermes **memory provider plugin** — the same
mechanism Hindsight and Mem0 use. Hermes discovers user-installed providers
in `~/.hermes/plugins/<name>/` and activates the one named by
`memory.provider` in `~/.hermes/config.yaml`.

Install (four steps, see the plugin's docstring for detail):

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install nucleus-vault
cp -r nucleus ~/.hermes/plugins/nucleus
nucleus init                     # once; stays unlocked until restart
# config.yaml → memory.provider: nucleus
hermes memory status             # Provider: nucleus, available ✓
```

What Hermes gets: automatic recall injected before each turn, automatic
AEAD-encrypted persistence of each turn, `nucleus_search` /
`nucleus_store` / `nucleus_forget` agent tools, `hermes backup` coverage of
the vault file, and the locked-by-default guarantee (after any restart,
memory is unavailable until `nucleus unlock`).

Prefer MCP instead? `nucleus serve` works with `hermes mcp add` like any
MCP server — but the provider integration is the recommended path for
Hermes because recall/persistence become automatic rather than
tool-invoked.
