"""Cross-platform primitives so engRAM runs natively on macOS, Linux, and
Windows: an advisory exclusive file lock, and the boot-session identity used
by the locked-by-default credential.

Everything platform-specific is isolated here; the rest of the codebase calls
these functions and never imports fcntl / msvcrt / sysctl directly.
"""
from __future__ import annotations

import os
import platform
import subprocess
import time

IS_WINDOWS = os.name == "nt"


# ---------------------------------------------------------------------------
# Advisory exclusive file lock (context manager over an open file handle)
# ---------------------------------------------------------------------------

if IS_WINDOWS:
    import msvcrt

    def _lock_nb(fh) -> bool:
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    def _unlock(fh) -> None:
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl

    def _lock_nb(fh) -> bool:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def _unlock(fh) -> None:
        try:
            fcntl.flock(fh, fcntl.LOCK_UN)
        except OSError:
            pass


class FileLock:
    """Cross-platform advisory exclusive lock on a lock file path."""

    def __init__(self, path: str, timeout: float = 10.0):
        self.path = path
        self.timeout = timeout
        self._fh = None

    def __enter__(self):
        self._fh = open(self.path, "a+")
        deadline = time.time() + self.timeout
        while not _lock_nb(self._fh):
            if time.time() > deadline:
                self._fh.close()
                from .crypto import CryptoError
                raise CryptoError(
                    f"Vault is busy: another process holds the write lock "
                    f"(waited {self.timeout:.0f}s)")
            time.sleep(0.05)
        return self

    def __exit__(self, *exc):
        if self._fh is not None:
            _unlock(self._fh)
            self._fh.close()
            self._fh = None


# ---------------------------------------------------------------------------
# Boot time - changes on every restart/power loss (basis of the session cred)
# ---------------------------------------------------------------------------

def boot_time() -> str:
    """Seconds-since-epoch of the current boot as a string. Distinct after
    every restart, so a credential wrapped with it dies on reboot."""
    system = platform.system()
    if system == "Darwin":
        out = subprocess.run(["sysctl", "-n", "kern.boottime"],
                             capture_output=True, text=True, check=True).stdout
        import re
        m = re.search(r"sec = (\d+)", out)
        if m:
            return m.group(1)
    elif system == "Linux":
        try:
            with open("/proc/stat") as f:
                for line in f:
                    if line.startswith("btime "):
                        return line.split()[1].strip()
        except OSError:
            pass
    elif system == "Windows":
        # Kernel tick count since boot at ~10 MHz resolution; the wall-clock
        # boot instant = now - uptime, stable across the session, new each boot.
        try:
            import ctypes
            ticks = ctypes.windll.kernel32.GetTickCount64()  # ms since boot
            return str(int(time.time() - ticks / 1000))
        except Exception:
            pass
    raise RuntimeError(
        "Cannot determine boot time on this platform; use --keychain (macOS) "
        "or ENGRAM_PASSPHRASE instead of the boot-session credential")


def machine_id() -> str:
    """A stable identifier for this machine that does NOT change with
    network/hostname flaps (macOS renames the host per network). Falls back
    to hostname only if no platform id is available."""
    system = platform.system()
    try:
        if system == "Darwin":
            out = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, check=True).stdout
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    return line.split('"')[-2]
        elif system == "Linux":
            for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                if os.path.exists(p):
                    return open(p).read().strip()
        elif system == "Windows":
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Cryptography") as k:
                return winreg.QueryValueEx(k, "MachineGuid")[0]
    except Exception:
        pass
    import socket
    return socket.gethostname()
