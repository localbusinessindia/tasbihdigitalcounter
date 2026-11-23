#!/usr/bin/env bash
# Repeat the audit: ./audit/run_all.sh   (from the project root)
# Needs: python3 + beautifulsoup4 lxml pillow playwright (pip), `playwright install chromium`,
#        node (for `node --check`), java (HTML validator), and `npm install` inside audit/.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
[ -d audit/node_modules ] || (cd audit && npm install --no-audit --no-fund)
python3 audit/static_audit.py "$ROOT" audit/results/static_after.json
python3 audit/browser_tests.py "$ROOT" audit/results/browser_after.json 8803
python3 audit/make_report.py
echo "Wrote AUDIT-RESULTS.md"
