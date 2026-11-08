#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
kubectl -n boutique scale deploy/productcatalogservice --replicas=2
kubectl apply -f chaos/mitigation/ha.yaml
kubectl -n boutique rollout status deploy/productcatalogservice --timeout=180s
