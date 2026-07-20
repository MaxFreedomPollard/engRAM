"""Build the per-OS fact packs: os-macos, os-windows, os-linux.

Pure, verifiable facts about each operating system — file-system paths,
shell/command references, config locations, Windows registry hives and
keys, version/build identifiers, keyboard conventions. No opinions, no
recommendations. Each install gets only the pack for its platform (wired
in nucleus.cli init).

Usage:  python tools/build_os_packs.py [VERSION]
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from nucleus import packs
from nucleus.embed import DEFAULT_MODEL, Embedder

ROOT = pathlib.Path(__file__).resolve().parents[1]
IDENTITY_FILE = ROOT / "tools" / "pack_identity.json"
DATA = ROOT / "src" / "nucleus" / "data"

MACOS = [
    # Versions
    "macOS 15 is named Sequoia and was released in 2024.",
    "macOS 14 is named Sonoma and was released in 2023.",
    "macOS 13 is named Ventura and was released in 2022.",
    "macOS 12 is named Monterey and was released in 2021.",
    "macOS 11 is named Big Sur and was the first version to run on Apple silicon (2020).",
    "macOS 10.15 is named Catalina and was the last version to support 32-bit apps (it dropped them).",
    "The macOS kernel is named XNU and its Unix layer is certified UNIX 03.",
    "Apple silicon Macs use ARM64 (AArch64) processors; earlier Macs used Intel x86-64.",
    "Rosetta 2 translates Intel x86-64 apps to run on Apple silicon Macs.",
    # File system & paths
    "The default macOS file system is APFS (Apple File System), introduced in 2017.",
    "A user's home directory on macOS is /Users/<username>.",
    "Application bundles on macOS are directories ending in .app stored in /Applications.",
    "User-specific preferences on macOS are stored as .plist files in ~/Library/Preferences.",
    "System-wide launch daemons on macOS live in /Library/LaunchDaemons.",
    "Per-user launch agents on macOS live in ~/Library/LaunchAgents.",
    "The macOS system font directory is /System/Library/Fonts; user fonts go in ~/Library/Fonts.",
    "Trash on macOS is stored per volume in a hidden .Trashes directory and in ~/.Trash.",
    "macOS hides the ~/Library folder in Finder by default.",
    "Extended file attributes on macOS include com.apple.quarantine, set on downloaded files by Gatekeeper.",
    # Commands & tooling
    "The default shell on macOS since Catalina (10.15) is zsh; earlier it was bash.",
    "The macOS package manager command 'brew' refers to Homebrew, a third-party tool.",
    "The 'defaults' command reads and writes macOS user preference (.plist) values.",
    "The 'launchctl' command manages launchd services on macOS.",
    "The 'diskutil' command manages disks and volumes on macOS.",
    "The 'codesign' command signs and verifies code signatures on macOS.",
    "The 'spctl' command manages the Gatekeeper security assessment policy on macOS.",
    "The 'pmset' command configures power management settings on macOS.",
    "The 'sw_vers' command prints the macOS product name, version, and build.",
    "The 'system_profiler' command reports detailed hardware and software information on macOS.",
    "The 'plutil' command validates and converts property list (.plist) files on macOS.",
    "The 'xattr' command views and edits extended attributes, including removing the quarantine flag.",
    "The 'osascript' command runs AppleScript and JavaScript for Automation from the command line.",
    "The 'sips' command performs scriptable image processing on macOS.",
    "The 'caffeinate' command prevents macOS from sleeping while a command runs.",
    "The 'mdfind' command queries the Spotlight index from the command line on macOS.",
    "The 'security' command manages the macOS Keychain from the command line.",
    "The 'softwareupdate' command installs macOS system updates from the command line.",
    # Security
    "System Integrity Protection (SIP) on macOS restricts modification of protected system files even by root.",
    "Gatekeeper on macOS blocks running unsigned or unnotarized applications by default.",
    "TCC (Transparency, Consent, and Control) governs app access to files, camera, microphone, and more on macOS.",
    "FileVault provides full-disk encryption on macOS.",
    "The macOS Keychain stores passwords, keys, and certificates in encrypted .keychain-db files.",
    "The macOS Recovery partition is reached by holding Command-R at startup on Intel Macs.",
    # Conventions
    "On a Mac keyboard, the Command (Cmd) key is the primary modifier for shortcuts.",
    "Copy, paste, and cut on macOS use Command-C, Command-V, and Command-X.",
    "Spotlight search on macOS is opened with Command-Space.",
    "Force Quit on macOS is opened with Command-Option-Escape.",
    "A screenshot of the whole screen on macOS is taken with Command-Shift-3.",
    "The macOS clipboard manager service is called the pasteboard, accessed via 'pbcopy' and 'pbpaste'.",
]

WINDOWS = [
    # Versions & builds
    "Windows 11 was released in 2021; its first stable build was 22000.",
    "Windows 10 was released in 2015 and its version numbering used strings like 22H2.",
    "Windows 11 requires UEFI, Secure Boot, and a TPM 2.0 module.",
    "Windows NT is the kernel family underlying all modern Windows versions.",
    "64-bit Windows runs on the x86-64 (AMD64) and ARM64 architectures.",
    "The Windows system directory is C:\\Windows\\System32 (64-bit binaries on 64-bit Windows).",
    "On 64-bit Windows, 32-bit system binaries are stored in C:\\Windows\\SysWOW64.",
    # Registry hives
    "The Windows Registry root HKEY_LOCAL_MACHINE (HKLM) stores machine-wide settings.",
    "The Windows Registry root HKEY_CURRENT_USER (HKCU) stores settings for the logged-in user.",
    "The Windows Registry root HKEY_CLASSES_ROOT (HKCR) stores file associations and COM class registrations.",
    "The Windows Registry root HKEY_USERS (HKU) contains loaded user profiles by SID.",
    "The Windows Registry root HKEY_CURRENT_CONFIG (HKCC) stores the current hardware profile.",
    "The HKLM hive is backed by files in C:\\Windows\\System32\\config (SYSTEM, SOFTWARE, SAM, SECURITY).",
    "Each user's HKCU registry hive is stored in the file NTUSER.DAT in their profile folder.",
    # Registry keys
    "Programs listed under HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run start at user logon.",
    "The key HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run holds per-user startup programs.",
    "Installed-program metadata is under HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall.",
    "The Windows product name and build are under HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion.",
    "Environment variables for the machine are under HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment.",
    "Windows services are configured under HKLM\\SYSTEM\\CurrentControlSet\\Services.",
    "Common registry value types include REG_SZ (string), REG_DWORD (32-bit number), and REG_BINARY (binary data).",
    # Paths & environment
    "The Windows user profile directory is C:\\Users\\<username>.",
    "The %APPDATA% environment variable points to C:\\Users\\<username>\\AppData\\Roaming.",
    "The %LOCALAPPDATA% environment variable points to C:\\Users\\<username>\\AppData\\Local.",
    "The %PROGRAMFILES% environment variable points to C:\\Program Files by default.",
    "The %TEMP% environment variable points to a per-user temporary files directory.",
    "The %WINDIR% environment variable points to C:\\Windows.",
    "Windows uses the backslash (\\) as its path separator and drive letters like C:.",
    "Windows path components are case-insensitive but case-preserving.",
    # Commands & tooling
    "The Windows Registry Editor is launched with the command 'regedit'.",
    "The 'reg' command queries and edits the Windows Registry from the command line.",
    "The 'powershell' command starts Windows PowerShell; 'pwsh' starts PowerShell 7+.",
    "The 'cmd' command starts the legacy Windows Command Prompt.",
    "The 'sfc /scannow' command checks and repairs protected Windows system files.",
    "The 'DISM' command services Windows images and can repair the component store.",
    "The 'tasklist' and 'taskkill' commands list and terminate processes on Windows.",
    "The 'wmic' command queries Windows Management Instrumentation (deprecated in favor of PowerShell CIM cmdlets).",
    "The 'winget' command is the Windows Package Manager command-line tool.",
    "The 'gpedit.msc' console edits Local Group Policy on Windows Pro editions.",
    "The 'services.msc' console manages Windows services.",
    "The 'msconfig' command opens the System Configuration tool on Windows.",
    "The PowerShell cmdlet Get-ItemProperty reads registry values.",
    "The Windows file 'hosts' is located at C:\\Windows\\System32\\drivers\\etc\\hosts.",
    # File systems & security
    "NTFS is the default file system for Windows system drives.",
    "The FAT32 file system has a maximum single-file size of 4 GB minus 1 byte.",
    "exFAT is a Microsoft file system designed for flash drives without FAT32's 4 GB file-size limit.",
    "Windows drive encryption is provided by BitLocker.",
    "User Account Control (UAC) prompts for elevation before administrative actions on Windows.",
    "Windows Defender is the built-in antivirus and is branded Microsoft Defender.",
    "A Windows SID (Security Identifier) uniquely identifies each user and group account.",
    # Conventions
    "Copy, paste, and cut on Windows use Ctrl-C, Ctrl-V, and Ctrl-X.",
    "The Windows Task Manager is opened with Ctrl-Shift-Escape.",
    "Windows line endings are carriage return plus line feed (CRLF, \\r\\n).",
]

LINUX = [
    # Kernel & distros
    "The Linux kernel was first released by Linus Torvalds in 1991.",
    "Linux distributions include Debian, Ubuntu, Fedora, Red Hat Enterprise Linux, Arch, and openSUSE.",
    "The 'uname -r' command prints the running Linux kernel version.",
    "Linux commonly runs on x86-64, ARM64 (aarch64), and RISC-V architectures.",
    "The Filesystem Hierarchy Standard (FHS) defines the standard Linux directory layout.",
    # Filesystem paths
    "On Linux, / is the root of the single unified directory tree.",
    "User home directories on Linux are typically under /home/<username>; root's home is /root.",
    "System-wide configuration files on Linux live in /etc.",
    "The /etc/passwd file lists user accounts on Linux.",
    "Encrypted password hashes on Linux are stored in /etc/shadow.",
    "The /etc/fstab file defines file systems to mount at boot on Linux.",
    "The /etc/hosts file maps hostnames to IP addresses on Linux.",
    "User-installed programs commonly live in /usr/local/bin; distro binaries in /usr/bin.",
    "Variable data such as logs and spools lives in /var on Linux; logs are under /var/log.",
    "Temporary files on Linux live in /tmp, which is often cleared on reboot.",
    "The /proc file system on Linux exposes kernel and process information as virtual files.",
    "The /sys file system on Linux exposes kernel device and subsystem information.",
    "Device files on Linux live in /dev, for example /dev/sda for a disk and /dev/null.",
    "Per-user configuration on Linux follows the XDG spec, defaulting to ~/.config.",
    "Boot files and the kernel image on Linux live in /boot.",
    # Package managers
    "Debian and Ubuntu use the APT package manager with the 'apt' and 'dpkg' commands.",
    "Fedora and RHEL use the DNF package manager; older versions used YUM; packages are RPMs.",
    "Arch Linux uses the pacman package manager.",
    "openSUSE uses the zypper package manager.",
    "The 'snap' and 'flatpak' commands manage cross-distribution sandboxed application packages.",
    # Commands
    "The 'ls' command lists directory contents on Linux.",
    "The 'chmod' command changes file permission bits on Linux.",
    "The 'chown' command changes file ownership on Linux.",
    "The 'sudo' command runs a command as another user, by default root, on Linux.",
    "The 'ps' command lists running processes on Linux.",
    "The 'grep' command searches text using patterns on Linux.",
    "The 'systemctl' command controls services under the systemd init system.",
    "The 'journalctl' command reads logs from the systemd journal.",
    "The 'mount' command attaches a file system to the directory tree on Linux.",
    "The 'lsblk' command lists block devices on Linux.",
    "The 'ip' command configures network interfaces and routing on Linux (replacing 'ifconfig').",
    "The 'df' command reports file system disk space usage on Linux.",
    "The 'top' and 'htop' commands show live process and resource usage on Linux.",
    "The 'cron' daemon runs scheduled jobs defined in crontab files on Linux.",
    "The 'man' command displays manual pages for Linux commands.",
    # Permissions & init
    "Linux file permissions are read (4), write (2), and execute (1), set for owner, group, and others.",
    "The permission mode 755 means read-write-execute for the owner and read-execute for group and others.",
    "systemd is the most common init system and service manager on modern Linux distributions.",
    "A systemd unit file ending in .service defines how a service is started and managed.",
    "System-wide systemd units live in /etc/systemd/system and /usr/lib/systemd/system.",
    "The Linux superuser account is named root and has user ID 0.",
    # Conventions
    "Linux file and directory names are case-sensitive.",
    "Linux uses the forward slash (/) as its path separator.",
    "Linux text files use a single line feed (LF, \\n) as the line ending.",
    "A file or directory whose name begins with a dot is hidden by default on Linux.",
    "The most common default shells on Linux are bash and, increasingly, zsh.",
]

PACKS = {
    "os-macos": ("macos", "Pure factual reference for macOS: paths, commands, "
                 "config locations, versions, and conventions.", MACOS),
    "os-windows": ("windows", "Pure factual reference for Windows: registry hives "
                   "and keys, paths, commands, versions, and conventions.", WINDOWS),
    "os-linux": ("linux", "Pure factual reference for Linux: filesystem hierarchy, "
                 "commands, package managers, permissions, and conventions.", LINUX),
}


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"
    identity = json.loads(IDENTITY_FILE.read_text())
    emb = Embedder(DEFAULT_MODEL)
    for pack_name, (tag, desc, facts) in PACKS.items():
        records = [{"id": f"{tag}-{i+1:04d}", "text": t, "tags": ["os", tag]}
                   for i, t in enumerate(facts)]
        vectors = emb.embed_passages(facts)
        blob = packs.build_pack(
            name=pack_name, version=version, description=desc,
            records=records, vectors=vectors,
            model={"name": DEFAULT_MODEL, "sha256": emb.model_sha256, "dim": emb.dim},
            identity=identity)
        (DATA / f"{pack_name}.mpack").write_bytes(blob)
        print(f"built {pack_name}.mpack ({len(records)} facts)")


if __name__ == "__main__":
    main()
