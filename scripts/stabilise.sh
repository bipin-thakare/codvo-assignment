#!/usr/bin/env bash
# Platform adjustment for amd64 images emulated on Apple Silicon (decision D10).
# Stock manifests have 200-300m CPU limits and 1 s probe timeouts, tuned for native x86.
# Under Rosetta that causes liveness-probe kills and CrashLoopBackOff. We raise CPU limits to 1 core
# (requests untouched) and probe timeouts to 5 s so results reflect the app, not the emulator.
# On a native x86 machine you can skip this script.
set -euo pipefail
NS=boutique
for d in $(kubectl -n $NS get deploy -o name | grep -v redis-cart); do
  n=$(kubectl -n $NS get $d -o jsonpath='{.spec.template.spec.containers[0].name}')
  kubectl -n $NS patch $d --type=strategic -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"$n\",\"resources\":{\"limits\":{\"cpu\":\"1000m\"}}}]}}}}" >/dev/null
  for probe in livenessProbe readinessProbe; do
    if kubectl -n $NS get $d -o jsonpath="{.spec.template.spec.containers[0].$probe}" | grep -q .; then
      kubectl -n $NS patch $d --type=json -p "[{\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/$probe/timeoutSeconds\",\"value\":5}]" >/dev/null
    fi
  done
done
kubectl -n $NS rollout status deploy --timeout=600s
