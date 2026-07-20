"""Build src/nucleus/data/core-facts.mpack from tools/seed/core_facts.jsonl.

Embeds every fact with the BUNDLED model (so installs use the precomputed
vectors with zero compute) and signs with the first-party Nucleus identity
(tools/pack_identity.json — generated on first run; keep it private).
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from nucleus import packs
from nucleus.embed import DEFAULT_MODEL, Embedder

ROOT = pathlib.Path(__file__).resolve().parents[1]
IDENTITY_FILE = ROOT / "tools" / "pack_identity.json"
SEED_FILE = ROOT / "tools" / "seed" / "core_facts.jsonl"
OUT = ROOT / "src" / "nucleus" / "data" / "core-facts.mpack"

if IDENTITY_FILE.exists():
    identity = json.loads(IDENTITY_FILE.read_text())
else:
    identity = packs.new_identity("Nucleus Project")
    IDENTITY_FILE.write_text(json.dumps(identity, indent=2))
    print(f"generated first-party pack identity → {IDENTITY_FILE} (keep private)")

VERSION = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"

records = [json.loads(l) for l in SEED_FILE.read_text().splitlines() if l.strip()]
ids = [r["id"] for r in records]
if len(set(ids)) != len(ids):
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    raise SystemExit(f"duplicate ids in core_facts.jsonl: {dupes} — fix before building")
emb = Embedder(DEFAULT_MODEL)
vectors = emb.embed_passages([r["text"] for r in records])

blob = packs.build_pack(
    name="core-facts",
    version=VERSION,
    description="Nucleus core seed pack: frozen general facts for install "
                "verification and regression benchmarking.",
    records=records,
    vectors=vectors,
    model={"name": DEFAULT_MODEL, "sha256": emb.model_sha256, "dim": emb.dim},
    identity=identity,
)
OUT.parent.mkdir(exist_ok=True)
OUT.write_bytes(blob)
print(f"built {OUT} ({len(records)} records, {len(blob)/1024:.0f} KB, "
      f"signer {identity['pub_hex'][:16]}…)")
