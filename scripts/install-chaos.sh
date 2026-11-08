#!/usr/bin/env bash
set -euo pipefail
helm repo add chaos-mesh https://charts.chaos-mesh.org >/dev/null
helm repo update >/dev/null
helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh --set controllerManager.replicaCount=1 -n chaos-mesh --create-namespace \
  --set chaosDaemon.runtime=containerd --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
  --set dashboard.create=false --set dnsServer.create=false --wait --timeout 10m

