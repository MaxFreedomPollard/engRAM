#!/usr/bin/env bash
# Nucleus installer — macOS
# Installs the package, creates + unlocks a vault (with macOS starter facts),
# and prints the Hermes selection step. Fully offline after this script.
set -euo pipefail

echo "Nucleus installer (macOS)"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "python3 not found. Install from python.org or 'brew install python'."; exit 1; }

# From a source checkout, install this repo; otherwise install from PyPI.
if [ -f "$(dirname "$0")/../pyproject.toml" ]; then
  "$PY" -m pip install --user "$(cd "$(dirname "$0")/.." && pwd)"
else
  "$PY" -m pip install --user nucleus-vault
fi

echo
echo "Creating your vault (installs the 4,807-fact starter knowledge)…"
nucleus init

cat <<'EOF'

Done. Nucleus is installed and your vault is unlocked (it stays unlocked
through logins until the next restart, then asks for your passphrase once).

To use it with Hermes:
  1. python3 -m pip install --user nucleus-vault    # into the Hermes venv if separate
  2. cp -r integrations/hermes/nucleus ~/.hermes/plugins/nucleus
  3. hermes memory setup      # pick "nucleus" in the list

Verify anytime:  nucleus selftest
EOF
