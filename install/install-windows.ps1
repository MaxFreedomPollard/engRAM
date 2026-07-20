# Nucleus installer - Windows (PowerShell)
# Installs the package, creates + unlocks a vault (with Windows starter facts),
# and prints the Hermes selection step. Fully offline after this script.
$ErrorActionPreference = "Stop"

Write-Host "Nucleus installer (Windows)"
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $py --version *> $null
if ($LASTEXITCODE -ne 0) { Write-Error "Python not found. Install from python.org (check 'Add to PATH')."; exit 1 }

$repoRoot = Split-Path -Parent $PSScriptRoot
if (Test-Path (Join-Path $repoRoot "pyproject.toml")) {
    & $py -m pip install --user $repoRoot
} else {
    & $py -m pip install --user nucleus-vault
}

Write-Host ""
Write-Host "Creating your vault (installs core + AKC pragmatic + Windows fact packs)..."
nucleus init

Write-Host @"

Done. Nucleus is installed and your vault is unlocked (it stays unlocked
through logins until the next restart, then asks for your passphrase once).

To use it with Hermes:
  1. python -m pip install --user nucleus-vault    # into the Hermes venv if separate
  2. Copy-Item -Recurse integrations\nucleus `$env:USERPROFILE\.hermes\plugins\nucleus
  3. hermes memory setup      # pick "nucleus" in the list

Verify anytime:  nucleus selftest
"@
