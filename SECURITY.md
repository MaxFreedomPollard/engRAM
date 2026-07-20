# Nucleus Security Model

Honest threat model. Read the "cannot protect against" section too — a
security product that claims everything protects nothing.

## Cryptography

| Purpose | Primitive |
|---|---|
| All encryption at rest | XChaCha20-Poly1305 AEAD (libsodium via PyNaCl) |
| Key derivation | Argon2id (t=3, m=64MiB, p=4; params stored in header) |
| Keyslots | LUKS-style: random 256-bit master key wrapped per slot |
| Recovery | 16 words from a 256-word list = 128 bits, own keyslot |
| Per-record keys | wrapped by master key → crypto-shred on `forget --shred` |
| Signing (vaults + packs) | Ed25519 |
| Integrity | AEAD tags everywhere + hash-chained audit log |

No homemade crypto. AAD binds every ciphertext to its role and vault
(payloads, journal entries by sequence number, keyslots, record bodies by
record id) — ciphertexts cannot be transplanted between contexts.

## What Nucleus protects against

- **Stolen disk / stolen laptop (vault at rest):** the vault file is a
  single AEAD-sealed blob under an Argon2id-wrapped key. No plaintext,
  no plaintext index, no temp files, no logs exist on disk — ever (I2).
- **Vault interception in transit:** a locked vault is safe to move over
  any channel. Optional Ed25519 manifest (`lock --sign`) lets the
  recipient verify origin and integrity without any credential.
- **Tampering:** any modified bit fails AEAD authentication loudly.
  Truncating the file, editing the header, splicing journal entries,
  and downgrade-style version games all produce specific errors.
- **Malicious or modified memory packs:** signature + content hash are
  verified before anything is parsed further; failure aborts install.
- **Forensic recovery of deleted memories:** `forget --shred` destroys the
  per-record key, deletes the row + FTS entries, VACUUMs, and rewrites the
  payload — the content is gone from the current vault file and its
  ciphertext history within that file.
- **Cross-agent memory access:** per-caller namespace grants (rw/ro/none);
  `packs/*` immutable for everyone. Run one server instance per host for
  boundary enforcement (see limitations).
- **Embedding inversion:** vectors can be partially inverted back toward
  text, so Nucleus encrypts vectors like everything else. No plaintext
  vector index ever exists on disk.
- **Stored prompt injection:** memories recalled from storage are wrapped
  with a data-not-instructions notice; content stored from untrusted
  sources can be flagged `quarantined`, which attaches an explicit warning
  envelope to every future recall. This is a mitigation, not a guarantee —
  the host agent must still treat memory as data.
- **History falsification:** the audit log is hash-chained; `nucleus audit
  verify` reports the first broken link.

## What Nucleus CANNOT protect against

- **A compromised OS while the vault is unlocked.** Anything that can read
  this process's RAM can read the working set and the master key. This is
  true of every encryption product; unlock only on machines you trust.
- **RAM at unlock time generally** — including swap in pathological cases.
  Python cannot guarantee zeroization (the GC may copy buffers); `lock`
  wipes what it can, best-effort. A future Rust core would tighten this.
- **Pre-shred backups.** Crypto-shred removes content from the *current*
  vault. Copies made before the shred still contain it (encrypted).
- **A hostile host agent within its granted namespaces.** The `--caller`
  identity is declarative. A host that lies about its name gets that
  name's grants. For real isolation, run one `nucleus serve` per host with
  its own config file and OS-level separation.
- **Weak passphrases.** Argon2id slows attackers; it cannot save
  "password1". The 16-word recovery phrase carries 128 bits — store it
  offline.
- **Search-audit persistence gap:** search audit entries are held in RAM
  until the next save/lock (writes are journaled immediately; reads don't
  cost an fsync). A kill -9 can lose recent *search* audit entries — never
  store/forget entries.

## Unlock paths, ranked

1. **macOS Keychain** (`nucleus unlock --keychain`): credential guarded by
   the OS; `nucleus serve` opens the vault without any passphrase in env,
   argv, or agent context. Cleared by `nucleus lock` or `memory_lock`.
2. **`NUCLEUS_PASSPHRASE` env var:** convenient; visible to anything that
   can read the process environment.
3. **`memory_unlock` MCP tool: DISABLED by default.** The passphrase would
   transit the agent's context window and possibly the host's logs/model
   provider. Enable only if you accept that
   (`settings.unlock_tool_enabled` in `<vault>.config.json`).

Auto-lock drops the in-RAM key after `auto_lock_minutes` (default 30) of
idle; with a Keychain credential present the next operation silently
re-unlocks (the credential represents standing user intent — clear it with
`nucleus lock`).

## Reporting

Report vulnerabilities privately to the maintainer. No telemetry exists in
this product; nothing phones home, so nothing can be recalled remotely.
