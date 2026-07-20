"""Boot-session-bound unlock credential.

The lock model Nucleus ships by default:

- `nucleus unlock` once → the vault stays usable continuously — for weeks or
  months, across logouts/logins, across every new `nucleus`/`serve` process.
- Any RESTART or POWER LOSS locks it: the credential is the master key
  wrapped by a key derived from the kernel's boot timestamp (plus uid and
  hostname). A new boot has a new timestamp, so the old wrap can never be
  opened again — the file becomes dead ciphertext and is deleted on sight.
- `nucleus lock` (or the MCP panic tool) deletes it immediately.

This is deliberately a CONVENIENCE credential, weaker than the passphrase:
an attacker who can read the session file on the RUNNING, logged-in machine
could also read process memory. Once power is lost, the binding key is gone.
The optional macOS Keychain credential (explicit --keychain) is the stronger
alternative but survives reboots; see SECURITY.md for the comparison.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
from pathlib import Path

from . import crypto
from .crypto import CryptoError, TamperError
from .platforms import boot_time


def _session_dir() -> Path:
    d = Path(os.environ.get("NUCLEUS_SESSION_DIR",
                            Path.home() / ".nucleus" / "session"))
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    return d


def _boot_time() -> str:
    """Seconds-since-epoch of the current boot. Changes on every restart.
    Cross-platform (macOS sysctl / Linux /proc / Windows GetTickCount64)."""
    return boot_time()


def _uid() -> str:
    # os.getuid() is POSIX-only; on Windows fall back to the username.
    getuid = getattr(os, "getuid", None)
    return str(getuid()) if getuid else os.environ.get("USERNAME", "user")


def _boot_key() -> bytes:
    """Wrap key valid only for this boot session of this user on this host."""
    token = "|".join((
        "nucleus-session-v1",
        _boot_time(),
        _uid(),
        socket.gethostname(),
    ))
    return hashlib.sha256(token.encode()).digest()


def _file_for(vault_path: str) -> Path:
    h = hashlib.sha256(os.path.abspath(vault_path).encode()).hexdigest()[:16]
    return _session_dir() / f"{h}.session"


def store(vault_path: str, master_key: bytes) -> Path:
    """Persist a boot-bound unlock credential for this vault."""
    p = _file_for(vault_path)
    blob = crypto.seal(_boot_key(), master_key,
                       aad=b"nucleus-session:" + os.path.abspath(vault_path).encode())
    p.write_text(json.dumps({"vault": os.path.abspath(vault_path),
                             "wrapped": blob.hex()}))
    os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    return p


def get(vault_path: str) -> bytes | None:
    """Return the master key if a credential exists AND we are still in the
    same boot session; otherwise remove the stale file and return None."""
    p = _file_for(vault_path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text())
        return crypto.unseal(
            _boot_key(), bytes.fromhex(data["wrapped"]),
            aad=b"nucleus-session:" + os.path.abspath(vault_path).encode())
    except (TamperError, CryptoError, ValueError, KeyError, OSError):
        # different boot (restart/power loss) or corrupt file → locked
        try:
            p.unlink()
        except OSError:
            pass
        return None


def clear(vault_path: str) -> bool:
    p = _file_for(vault_path)
    if p.is_file():
        p.unlink()
        return True
    return False
