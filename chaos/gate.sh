#!/usr/bin/env bash
# Chaos gate: hold steady load, inject one experiment, judge with the SAME SLIs as Part A.
# Usage: chaos/gate.sh chaos/exp1-productcatalog-failure.yaml [rate]
# Exit 0 = steady state held; non-zero = SLI breach or abort (blocks release).
set -uo pipefail
cd "$(dirname "$0")/.."
EXP="${1:?experiment yaml}"; export RATE="${2:-10}" PROFILE=chaos
NAME=$(basename "$EXP" .yaml); OUT="chaos/results/$NAME-$(date +%Y%m%dT%H%M%S)"
cleanup() { kubectl delete -f "$EXP" --ignore-not-found >/dev/null 2>&1; }  # abort path: always remove fault
trap cleanup EXIT INT TERM

echo "[1/4] pre-check steady state (up to 3 tries: a 30 s smoke has only ~3 checkouts, one cold call can trip it)"
for try in 1 2 3; do BASE_URL="${BASE_URL:-http://localhost:8080}" PROFILE=smoke OUT=/tmp/pre k6 run -q perf/load.js && break
  [ $try = 3 ] && { echo "steady state NOT healthy before chaos; refusing to inject"; exit 2; }; echo "pre-check try $try failed, retrying"; sleep 10; done
echo "[2/4] start load ($RATE it/s) in background"
OUT="$OUT" DURATION="${DURATION:-4m}" k6 run -q perf/load.js & K6=$!
sleep 60                                  # 60 s of healthy baseline inside the same run
echo "[3/4] inject $NAME"; kubectl apply -f "$EXP"
wait $K6; RC=$?
echo "[4/4] recover + snapshot pod state"; cleanup
# recovery time: seconds after the fault is removed until the home AND a product page return 200 (cap 180 s)
T0=$(date +%s); until [ "$(curl -s -o /dev/null -w '%{http_code}' ${BASE_URL:-http://localhost:8080}/)" = 200 ] && [ "$(curl -s -o /dev/null -w '%{http_code}' ${BASE_URL:-http://localhost:8080}/product/OLJCESPC7Z)" = 200 ]; do
  [ $(( $(date +%s) - T0 )) -gt 180 ] && break; sleep 1; done
echo "recovery_seconds_after_fault_removed=$(( $(date +%s) - T0 ))" | tee "$OUT.recovery.txt"
 kubectl -n boutique get pods -o wide > "$OUT.pods.txt"
kubectl get events -n boutique --sort-by=.lastTimestamp | tail -40 > "$OUT.events.txt"
[ $RC -eq 0 ] && echo "PASS: SLIs held under $NAME" || echo "FAIL: SLI breach or abort (k6 exit $RC) under $NAME"
exit $RC
