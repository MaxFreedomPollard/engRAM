"""The shipped starter packs: present, signed, precomputed-vector, installable."""
import pathlib

import pytest

from nucleus import packs

DATA = pathlib.Path(__file__).resolve().parents[1] / "src" / "nucleus" / "data"
EXPECTED = ["core-facts", "akc-pragmatic", "os-macos", "os-windows", "os-linux"]


@pytest.mark.parametrize("name", EXPECTED)
def test_pack_ships_and_verifies(name):
    p = DATA / f"{name}.mpack"
    assert p.is_file(), f"{name}.mpack missing from package data"
    header, records, vectors = packs.read_pack(p.read_bytes())  # verifies sig+hash
    assert len(records) == vectors.shape[0] == header["records"]
    assert vectors.shape[1] == 384


def test_akc_pack_is_substantial():
    header, records, _ = packs.read_pack((DATA / "akc-pragmatic.mpack").read_bytes())
    assert len(records) > 3000  # "much more than 260"


def test_os_packs_are_pure_facts_for_their_platform(vault):
    # macOS pack installs and recalls a macOS-specific fact by meaning
    packs.install_pack(vault, (DATA / "os-macos.mpack").read_bytes(), caller="test")
    hit = vault.search("command to sign code on mac", caller="test",
                       namespace="packs/os-macos")["results"][0]
    assert "codesign" in hit["text"]


def test_windows_pack_has_registry_facts(vault):
    packs.install_pack(vault, (DATA / "os-windows.mpack").read_bytes(), caller="test")
    hit = vault.search("registry hive for machine-wide settings", caller="test",
                       namespace="packs/os-windows")["results"][0]
    assert "HKEY_LOCAL_MACHINE" in hit["text"] or "HKLM" in hit["text"]


def test_bundled_hermes_plugin_in_sync():
    """The pip package ships a copy of the Hermes provider plugin (for
    `nucleus integrate hermes`); it must match the canonical source."""
    root = pathlib.Path(__file__).resolve().parents[1]
    for f in ("__init__.py", "plugin.yaml"):
        canonical = (root / "integrations" / "hermes" / "nucleus" / f).read_bytes()
        shipped = (root / "src" / "nucleus" / "data" / "hermes-plugin" / f).read_bytes()
        assert canonical == shipped, f"{f} out of sync — re-copy into data/hermes-plugin"


def test_pack_export_roundtrip(tmp_path):
    """export → edit → rebuild keeps records intact (the hand-edit workflow)."""
    import json as _json
    from nucleus.embed import DEFAULT_MODEL, Embedder
    blob = (DATA / "os-macos.mpack").read_bytes()
    header, records, _ = packs.read_pack(blob)
    # export
    out = tmp_path / "edit.jsonl"
    with open(out, "w") as f:
        for r in records:
            f.write(_json.dumps(r, sort_keys=True) + "\n")
    # simulate a hand-edit: append one fact
    with open(out, "a") as f:
        f.write(_json.dumps({"id": "macos-9999",
                             "text": "Hand-added: the Dock lives at the bottom "
                                     "of the screen by default on macOS.",
                             "tags": ["os", "macos", "custom"]}) + "\n")
    edited = [_json.loads(l) for l in out.read_text().splitlines()]
    ident = packs.new_identity("editor")
    emb = Embedder(DEFAULT_MODEL)
    blob2 = packs.build_pack(
        name="os-macos", version="1.0.1", description="edited",
        records=edited, vectors=emb.embed_passages([r["text"] for r in edited]),
        model={"name": DEFAULT_MODEL, "sha256": emb.model_sha256, "dim": emb.dim},
        identity=ident)
    h2, r2, v2 = packs.read_pack(blob2)
    assert h2["records"] == len(records) + 1
    assert r2[-1]["id"] == "macos-9999"
