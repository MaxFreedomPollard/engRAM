#!/usr/bin/env bash
# engRAM installer — macOS
# Installs the package, creates + unlocks a vault (with macOS starter facts),
# and prints the Hermes selection step. Fully offline after this script.
set -euo pipefail

echo "engRAM installer (macOS)"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "python3 not found. Install from python.org or 'brew install python'."; exit 1; }

# From a source checkout, install this repo; otherwise install from PyPI.
if [ -f "$(dirname "$0")/../pyproject.toml" ]; then
  "$PY" -m pip install --user "$(cd "$(dirname "$0")/.." && pwd)"
else
  "$PY" -m pip install --user engram-vault
fi

echo
echo "Creating your vault (installs the 4,807-fact starter knowledge)…"
engram init

cat <<'EOF'

Done. engRAM is installed and your vault is unlocked (it stays unlocked
through logins until the next restart, then asks for your passphrase once).

To use it with Hermes:
  1. python3 -m pip install --user engram-vault    # into the Hermes venv if separate
  2. cp -r integrations/hermes/engram ~/.hermes/plugins/engram
  3. hermes memory setup      # pick "engram" in the list

Verify anytime:  engram selftest
EOF
