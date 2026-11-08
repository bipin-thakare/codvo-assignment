#!/usr/bin/env bash
# One-shot environment setup: kind cluster + Online Boutique + monitoring + Chaos Mesh.
set -euo pipefail
OB_REF="${OB_REF:-v0.10.2}"   # pin the microservices-demo release; change if you test another
cd "$(dirname "$0")/.."

kind create cluster --name boutique --config scripts/kind-config.yaml || true
kubectl create ns boutique --dry-run=client -o yaml | kubectl apply -f -

# Online Boutique (loadgenerator removed: we bring our own k6 load)
curl -sSL "https://raw.githubusercontent.com/GoogleCloudPlatform/microservices-demo/${OB_REF}/release/kubernetes-manifests.yaml" -o /tmp/ob.yaml
python3 scripts/strip_loadgen.py /tmp/ob.yaml > /tmp/ob-noload.yaml
kubectl -n boutique apply -f /tmp/ob-noload.yaml
kubectl -n boutique rollout status deploy --timeout=300s || true
./scripts/stabilise.sh

# Prometheus + Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo add chaos-mesh https://charts.chaos-mesh.org >/dev/null
helm repo update >/dev/null
helm upgrade --install mon prometheus-community/kube-prometheus-stack --version "${KPS_VERSION:-92.22.0}" -n monitoring --create-namespace \
  -f observability/kps-values.yaml --wait --timeout 10m
kubectl -n monitoring create configmap boutique-dashboard \
  --from-file=boutique.json=observability/dashboard.json --dry-run=client -o yaml \
  | kubectl label --local -f - grafana_dashboard=1 -o yaml | kubectl apply -f -
kubectl apply -f observability/alert-rules.yaml

echo "Done. Chaos Mesh is installed separately for Part B: ./scripts/install-chaos.sh (saves CPU/RAM on an 8 GB machine, see decisions D10)"
