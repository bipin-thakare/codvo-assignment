# Performance, Chaos and Security: Google Online Boutique (progress submission)

Local kind cluster. Tested on an 8 GB Apple Silicon Mac. **Read `memo.md` first, then `decisions-and-understanding.md` (every decision, hypothesis and result).**

## Status
| Part | State |
|---|---|
| A Performance | Done: SLIs (`perf/slis.md`), smoke, baseline, ramp, spike (3 runs), 10-min soak (shortened from 30), bottleneck B1 (`perf/bottleneck.md`), dashboard JSON |
| B Chaos | 3 experiments run (pod/dependency, latency, Redis); exp1 mitigated and rerun (22.17% to 0.00% failed); exp2, exp3 findings not yet fixed; CI gate file written, **not run on GitHub** |
| C Security | 13 checks run (8 fail, 5 pass), NetworkPolicy fix and rerun; threat model in `security/threat-model.md` |
| D Memo | `memo.md` |

## Setup (Mac, Apple Silicon)
```bash
brew install colima docker kind kubectl helm k6 python@3.12
colima start --cpu 4 --memory 4 --disk 30 --vm-type vz --vz-rosetta   # Rosetta is REQUIRED: the app images are amd64-only
./scripts/setup.sh              # kind + Online Boutique + Prometheus/Grafana (chart pinned 92.22.0) + stabilise.sh
./scripts/lean.sh on            # 8 GB laptops only: scales away ads, recommendations, Grafana, prometheus-operator
./scripts/portforward.sh &      # frontend :8080, Prometheus :9090, Grafana :3000 (admin/admin)
./scripts/install-chaos.sh      # Chaos Mesh, only needed for Part B
```
Tool versions used: kind 0.33.0, kubectl 1.37.2, helm 4.3.1, k6 2.3.0, Colima 0.10.3, Docker 29.9.3, kube-prometheus-stack chart 92.22.0, Online Boutique v0.10.2.

## Rerun
| What | Command |
|---|---|
| Smoke / baseline / ramp / spike / soak | `RATE=5 perf/run.sh baseline` (also ramp, `RATE=20 spike`, `RATE=20 DURATION=10m soak`) |
| Bottleneck fix | `perf/fix-bottleneck.sh` |
| Chaos (one experiment) | `chaos/gate.sh chaos/exp1-productcatalog-failure.yaml 10` (exp2, exp3 likewise) |
| Chaos mitigation | `chaos/mitigation/apply.sh`, then rerun exp1 |
| Security | `security/run.sh` (needs Python venv or `pip install -r security/requirements.txt`) |
| Security fix | `kubectl apply -f security/fixes/networkpolicies.yaml`, rerun `pytest -k "s08 or s09"` |
| Dashboard | Grafana > "Online Boutique: perf & chaos" (`observability/dashboard.json`); scale Grafana up first: `kubectl -n monitoring scale deploy/mon-grafana --replicas=1` |

## Honest limitations
- x86 images under Rosetta on a laptop; a cart-service crash with a Rosetta translator assertion was seen (likely emulation, not proven). Numbers are indicative, not capacity planning.
- Lean app: no ads or recommendations during runs. Soak 10 min, not 30.
- Platform tweaks: `scripts/stabilise.sh` raises CPU limits to 1 core and probe timeouts to 5 s (stock values crash-loop under emulation).
- `perf/results/invalid-host-swapping/` holds runs invalidated by host memory starvation, kept as a diagnosed failure. Runs named CONFOUNDED / NOISY / run1-early-abort are kept for the same reason.
- Chaos abort rule uses a cumulative failure rate (never tripped); no per-second chaos timeline in Prometheus.
- No Grafana screenshots are included yet.

## Not done / with another day
Native x86 rerun for clean A/B; fix exp2 (currency timeouts/cache) and exp3 (cart memory, Redis HA) and rerun; run the pipeline on GitHub Actions; TLS, security headers, session hardening; Trivy and ZAP scans; tracing; 30-min soak; windowed chaos abort; dashboard screenshots.
