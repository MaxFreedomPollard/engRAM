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
