# Authoring Memory Packs

A memory pack is a signed, versioned `.mpack` file of knowledge that
installs into any Nucleus vault fully offline, with precomputed vectors.

## Build

1. Prepare records — `.jsonl` (one `{"text": "...", "tags": [...],
   "id": "stable-id"}` per line), `.csv` (columns `text`, `tags`
   semicolon-separated), or a directory of `.md` files (one record per
   file).
2. Build and sign:

```bash
nucleus pack build facts.jsonl \
    --name my-pack --version 1.0.0 \
    --description "What this pack knows" \
    --creator "Your Name" \
    --identity ~/.nucleus/identity.json      # created on first use — KEEP PRIVATE
```

The build embeds every record with the bundled default model, so consumers
install with zero compute. `--encrypt` additionally seals the body with a
pack passphrase (private distribution).

3. Distribute the `.mpack` file however you like — signature and content
   hash make tampering in transit detectable.

## Consume

```bash
nucleus pack install my-pack-1.0.0.mpack     # verifies signature + hash FIRST
nucleus pack list
nucleus pack remove my-pack
```

Records land read-only in `packs/my-pack` for every caller. Reinstalling a
pack replaces it wholesale (semver replace, never merge).

## Rules of the road

- **Keep `identity.json` private.** It contains your Ed25519 seed. The
  public key travels inside each pack; consumers can pin it.
- **Stable `id` fields** let you ship regression queries against your pack
  (the ids survive install as `id:` tags — this is exactly how the
  built-in seed pack's `selftest` works).
- **Never change published content within a version.** Version bumps are
  cheap; silent mutations defeat the signature's purpose.
- Facts should stand alone (one self-contained statement per record) —
  retrieval returns records, not documents.

## The core seed pack

`core-facts` ships inside the package, auto-installs at `init`, and is
frozen within a major version: it is Nucleus's install-verification and
regression corpus (`nucleus selftest`). Don't remove it unless you have a
reason; it costs ~1MB of RAM.
