#!/usr/bin/env bash
# Fix for bottleneck B1: currencyservice OOMKilled at the stock 128Mi memory limit (peak 125 MiB = 98%).
# Raises the memory limit to 256Mi (request 128Mi). Revert with: kubectl -n boutique set resources deploy/currencyservice --limits=memory=128Mi --requests=memory=64Mi
set -euo pipefail
kubectl -n boutique set resources deploy/currencyservice --limits=memory=256Mi --requests=memory=128Mi
kubectl -n boutique rollout status deploy/currencyservice --timeout=180s
