# Bottleneck B1: currencyservice OOMKilled at 128Mi (natural, not artificially constrained)

Every page converts prices through currencyservice; it runs as ONE replica with a stock 128Mi memory limit.

## Evidence chain
| Step | Evidence |
|---|---|
| 1 Symptom (load results) | Spike BEFORE fix: 37,812 requests, **1.50% failed, checkout success 97.70%**, 536 HTTP 500s on home/product/cart/place_order (`results/spike-BEFORE-fix-*.json`). Errors began ~16 s in, in the calm 20 it/s phase, before the burst. |
| 2 Localise (metrics/state) | `kubectl get pod`: currencyservice lastState **OOMKilled**, finished 07:26:27Z, 16 s after the run started (07:26:11Z). Frontend logs: `could not retrieve currencies ... connection refused` while it was down. Prometheus: restarts +1. |
| 3 Cause | Prometheus `container_memory_working_set_bytes`: peak **125 MiB of a 128 MiB limit (98%)**, still 107 MiB after load stopped (memory not released). One replica + on every page + no frontend retry => one OOM kill = full outage for the restart window. |
| 4 Change | `perf/fix-bottleneck.sh`: memory limit 128Mi -> 256Mi (request 128Mi). |
| 5 After | New pod ran at a peak working set of **128 MiB (the old ceiling)** across two spike runs with **0 restarts / 0 OOMKills**. |

## Honest limits of the before/after (read before quoting numbers)
- Run 1 after fix (`...run1-CONFOUNDED...`): 20.26% failed, but cause was **cartservice SIGSEGV (exit 139)**, an unrelated crash, likely .NET under Rosetta emulation. currencyservice 0 restarts.
- Run 2 after fix (`...run2-NOISY...`): 0% failed, checkout 100%, but browse p95 4,372 ms and 1,975 dropped iterations; the host was under memory/CPU contention (swap in use, macOS background CPU). Latency from this run is not valid evidence.
- Therefore: the fix is proven by MECHANISM (OOM at 98% before; 0 kills at the old ceiling after), NOT by a clean latency before/after. A clean A/B needs a quiet native x86 host. Listed under "with another day".

## Panels
- Helped: container restarts / OOMKilled reason, memory working set vs limit.
- Did NOT help: CPU usage and CPU throttling (currency used 0.63 of a 1-core limit at 100 it/s, so CPU looked innocent), k6 average latency (hid the outage inside averages).
