# Chaos runbook

Prereqs: cluster up (`scripts/setup.sh`), port-forward running, Grafana dashboard open. Load: `RATE=10` (about half of baseline so headroom exists; chaos must be the only variable).
Run: `chaos/gate.sh chaos/<exp>.yaml 10`. Results land in `chaos/results/`. **Abort = k6 aborts on >50% failures, the trap deletes the fault. Manual abort: `kubectl delete -f chaos/<exp>.yaml`.**
Common blast-radius rule for all three: namespace `boutique` only, one target Deployment, fault <= 120 s, no experiment on a cluster running anything else.

Steady state for all three = Part A SLIs: checkout success >= 99.5%, checkout p95 < 1500 ms, browse p95 < 800 ms, checkout errors < 0.5% (measured over the 60 s healthy window before injection).

## Exp 1 - productcatalogservice unavailable 60 s (dependency failure)
- **Hypothesis (written before running):** the catalog is a single replica and every page needs it, so browse and checkout both fail ~100% during the fault; frontend recovers within 15 s of the pod returning. Expected: SLIs breached (this is the "known weak spot" test).
- **Blast radius:** 1 Deployment, 60 s, all user traffic touches it.
- **Abort:** >50% request failures for 20 s (automatic) - expected to trip, which is fine and recorded.
- **Actual:** _TBD - paste from results_
- **Mitigation under test:** `chaos/mitigation/ha.yaml` (2 replicas + PDB). Rerun and compare table below.

## Exp 2 - 300 ms latency on currencyservice for 120 s (network latency)
- **Hypothesis:** currency conversion is called several times per page; if calls are serialized, each page adds roughly N x 300 ms. Browse p95 breaches 800 ms, errors stay ~0 (slow, not broken). Checkout p95 breaches 1500 ms.
- **Blast radius:** traffic *into* currencyservice only; 120 s.
- **Abort:** >50% failures, or browse p95 > 5 s sustained (manual check on Grafana).
- **Actual:** _TBD_ (watch for the opposite: gRPC deadlines in frontend may turn latency into errors)

## Exp 3 - redis-cart down 60 s (datastore failure)
- **Hypothesis:** cart reads/writes fail, add-to-cart and checkout fail, browse unaffected; redis has no persistence, so carts are *lost* on restart (data loss, not just downtime). Cartservice recovers on its own after redis returns (verify; reconnect behavior is the surprise candidate).
- **Blast radius:** 1 pod, 60 s, cart/checkout journeys only.
- **Abort:** checkout failures > 50% is expected; abort only if browse is affected (it should not be).
- **Actual:** _TBD_

## Before / after (worst result, exp1)
| | Before mitigation | After |
|---|---|---|
| browse p95 during fault | | |
| checkout success during fault | | |
| time to recover after fault ends | | |
