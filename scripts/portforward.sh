#!/usr/bin/env bash
# Frontend on :8080, Prometheus on :9090, Grafana on :3000 (admin/admin)
kubectl -n boutique port-forward svc/frontend 8080:80 &
kubectl -n monitoring port-forward svc/mon-kube-prometheus-stack-prometheus 9090:9090 &
kubectl -n monitoring port-forward svc/mon-grafana 3000:80 &
wait
