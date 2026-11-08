#!/usr/bin/env bash
# "Lean mode" for an 8 GB laptop (decision D14). Scales away parts that are NOT on the checkout journey
# or only needed for screenshots. Revert with: ./scripts/lean.sh off
#   adservice, recommendationservice : frontend tolerates their absence (recommendations/ads are optional UI)
#   grafana + prometheus-operator    : Prometheus keeps scraping without the operator; scale Grafana up to take screenshots
set -euo pipefail
N=0; [ "${1:-on}" = "off" ] && N=1
kubectl -n boutique scale deploy/adservice deploy/recommendationservice --replicas=$N
kubectl -n monitoring scale deploy/mon-grafana deploy/mon-kube-prometheus-stack-operator --replicas=$N
