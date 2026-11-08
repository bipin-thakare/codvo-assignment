#!/usr/bin/env bash
# Usage: perf/run.sh baseline|ramp|spike|soak|smoke   (needs ./scripts/portforward.sh running)
set -euo pipefail
cd "$(dirname "$0")/.."
P="${1:?profile}"; export PROFILE="$P"
export K6_PROMETHEUS_RW_SERVER_URL="${K6_PROMETHEUS_RW_SERVER_URL:-http://localhost:9090/api/v1/write}"
export K6_PROMETHEUS_RW_TREND_STATS="p(95),p(99),avg"
k6 run -o experimental-prometheus-rw --tag testid="$P-$(date +%s)" perf/load.js
