#!/usr/bin/env bash
# Usage: security/run.sh            -> blockers then warnings; exit != 0 if any BLOCKER fails
set -uo pipefail; cd "$(dirname "$0")"
pip install -q -r requirements.txt
mkdir -p results
python3 -m pytest tests -m "blocker and not failure_scenario" --junitxml=results/blockers.xml -q; B=$?
python3 -m pytest tests -m "failure_scenario" --junitxml=results/failure.xml -q; F=$?
python3 -m pytest tests -m "warn" --junitxml=results/warnings.xml -q || echo "(warnings do not block)"
exit $(( B || F ))
