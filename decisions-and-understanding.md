# Decisions and understanding log

Running notes for the Codvo take-home. Purpose: in the 60-minute walkthrough I must explain every choice, and the interviewers will change one assumption. Update after every session. Facts and numbers only from my own runs.

## 1. The assignment in simple words
A shop website (Google Online Boutique, 11 small services) runs on my laptop in Kubernetes. A VP wants to know: **can we release this in two weeks?** I answer by testing it three ways, then writing a 2-page memo.

| Part | Question it answers | What I do | What I hand in |
|---|---|---|---|
| A Performance | Is it fast enough, and where does it break? | Define targets (SLIs) for checkout, send fake shoppers (k6) at 4 intensities, find ONE bottleneck and prove it with before/after numbers, watch it in Grafana | k6 results, dashboard JSON, bottleneck evidence |
| B Chaos | What happens when things break? | Break things on purpose (kill a pod, add delay, kill Redis) while under load. Write hypothesis first, compare with reality. Fix the worst one, rerun. Show it as a CI gate | experiment YAMLs, outputs, before/after, pipeline |
| C Security | Can it be attacked or leak? | Threat model (1 page), 8+ automated checks that can really fail, one failure scenario (fail open or closed?), fix one finding | threat model, test suite, report |
| D Memo | Should we release? | Findings ranked by risk, exit criteria, go / go-with-conditions / no-go, follow-up plan | memo (max 2 pages) |

How it is scored: evidence over claims, hypothesis-driven chaos with abort conditions, good scope judgment, someone else can rerun it from the README, a VP can act on the memo. **An honest, diagnosed failure beats a hidden one.**

Why the JD matters: the role is a technical owner of performance + chaos (core) and security (supporting). So A and B get the most depth, C stays smaller but real, D shows leadership.

## 2. Key terms (plain words)
- **SLI**: a measured number about user experience (e.g. checkout p95 latency). **SLO/target**: the number we say is acceptable.
- **p95**: 95 of 100 requests were faster than this.
- **Knee**: the load level where latency suddenly climbs. Past it the system is saturated.
- **Steady state**: what "healthy" looks like, defined with the SLIs, before breaking anything.
- **Blast radius**: how much we allow the experiment to damage. **Abort condition**: when we stop it.
- **kind**: Kubernetes running inside Docker on my laptop. **Helm**: installer for Kubernetes apps. **k6**: load generator. **Prometheus**: stores metrics. **Grafana**: draws them. **Chaos Mesh**: injects faults.

## 3. Plan (6 h hands-on)
| Session | Time | Work |
|---|---|---|
| 1 | 1h15 | Tools, cluster, walk through scaffold, smoke + baseline, calibrate SLIs |
| 2 | 1h15 | Part A: ramp, spike, soak, bottleneck, dashboard |
| 3 | 1h30 | Part B: 3 experiments, mitigation, CI gate |
| 4 | 1h15 | Part C: threat model, checks, fix, tensions |
| 5 | 0h45 | Part D memo, README, ai-usage, mock interview |

Cut first if short on time: shorten soak (say so) > tracing / extra panels > extra security checks beyond 8 > run CI only locally. Never cut: memo, hypotheses, honest failures.

## 4. Decisions and assumptions log
| # | Date | Decision / assumption | Why | Alternative I rejected |
|---|---|---|---|---|
| D1 | 2026-11-07 | Reuse the existing AI-drafted scaffold in `assignment/`, but review and run every file before trusting it | Saves time; I must still be able to defend each part | Start from scratch (slower, not clearly better) |
| D2 | 2026-11-07 | Depth on A and B, lighter but real C | JD: performance + chaos core, security supporting | Equal depth on all three |
| D3 | 2026-11-07 | k6 + Chaos Mesh + Prometheus/Grafana on kind | Named in the JD, defensible, local | JMeter, Litmus (no advantage here) |
| D4 | 2026-11-07 | SLI targets are provisional until the baseline run, then set near 2-3x healthy p95 | A target set before measuring is a guess | Keep the scaffold's numbers unmeasured |

| D5 | 2026-11-07 | Colima (4 CPU / 5 GB) instead of Docker Desktop | Machine has 8 CPU / 8 GB RAM; need to leave RAM for macOS | Docker Desktop (heavier) |
| D6 | 2026-11-07 | Trim Prometheus stack, use lower load rates, possibly shorter soak; say so in README/memo | 8 GB limit; saturating the laptop would measure the laptop, not the app | Run full stack and risk invalid results |
| D7 | 2026-11-07 | kind single node (was 3 nodes in scaffold); OB_REF stays v0.10.2 (verified exists; latest is v0.10.7) | 5 GB VM cannot host 3 nodes + app + monitoring; pinned version = reproducible | 3-node cluster; newest release |
| D8 | 2026-11-08 | Enable Rosetta in Colima (`--vm-type vz --vz-rosetta`), rebuild cluster | Online Boutique images (all tags v0.10.1-v0.10.5 checked) are amd64-only; on Apple Silicon QEMU emulation made pods miss probes and cartservice (.NET) crash with CoreCLR error 0x8007000E. Raising limits did not fix it (symptom treatment). | Build arm64 images from source (slow, heavy for 8 GB); run on x86 machine |
| D9 | 2026-11-08 | Pin kube-prometheus-stack chart to 92.22.0 (operator v0.94.2) | Newest chart 93.1.0 uses operator image v0.95.1, whose manifest has only amd64, so the arm64 kind node got `no match for platform` (ImagePullBackOff). Verified on quay: v0.94.2 has arm64. Unpinned installs were also non-reproducible. | Unpinned latest chart |
| D10 | 2026-11-08 | Platform adjustments for 8 GB / Apple Silicon: (a) Chaos Mesh moved out of base setup to `scripts/install-chaos.sh` (1 controller replica), installed only for Part B; (b) Prometheus trimmed (30 s scrape, control-plane scrape targets off); (c) `scripts/stabilise.sh` raises every service CPU limit to 1000m and probe timeouts to 5 s | Measured: node load average 60 on 4 vCPU, kube-apiserver at ~100% CPU, 5 services in CrashLoopBackOff from liveness-probe kills (stock limits 200-300m / 1 s probes assume native x86). After changes load fell to 2.5 and restarts stopped. | Leave stock limits (unstable); buy/borrow an x86 machine |
| D11 | 2026-11-08 | Fixed load script bug: card number sent without dashes (`4432801561520454`) | Frontend validator rejects the dashed form with 422 `Field 'CcNumber' is invalid`; found by replaying checkout with curl. Not an app defect. | - |
| D12 | 2026-11-08 | Baseline rate is 5 iterations/s (scaffold default was 20) | 4 vCPU VM shared with k6; saturating the laptop would measure the laptop | Default 20 it/s |
| D13 | 2026-11-08 | Baseline/diagnostic runs on this host are INVALID as performance evidence; keep as diagnosed failures | Host memory: `vm.swapusage` 13.0 GB used of 14.3 GB, 93.6 M swap-outs; Colima VM (5 GB configured) only ~580 MB resident; in-VM load average 16-44 while idle/light; kube-apiserver ~90% CPU. At 5 it/s browse p95 was 12.3 s with 73 dropped iterations; at 3 it/s 100% of requests timed out (30 s). At 2 it/s (smoke, calm host) browse p95 was 165 ms. Cause is host memory starvation (8 GB Mac running Chrome, VS Code, Asana, Claude app + a 5 GB VM), not the application. | Report these numbers as the app's capacity |
| D14 | 2026-11-08 | Lean mode: Colima VM 4 GB (was 5); adservice, recommendationservice, Grafana and prometheus-operator scaled to 0 during load runs (`scripts/lean.sh on/off`). Result is a SLIM Online Boutique (no ads, no recommendations) | After D13, the same 5 it/s baseline went from browse p95 12.3 s / 73 dropped to p95 32 ms / 0 dropped. Ads and recommendations are optional UI, not on the checkout journey. Must be stated in README and memo as a limitation: results do not include their load. | Keep full app and a swapping host; move to cloud x86 |
| D15 | 2026-11-08 | Keep setup/config/timings minimal (user instruction): spike ~4 min, soak 10 min (shortened from 30, labelled), bottleneck one 3-min before/after pair, chaos 3 experiments ~3 min each + 1 rerun, ~10 security checks, no tracing/Trivy/ZAP; Chaos Mesh installed only for Part B; Grafana up only for screenshots | 8 GB laptop and a 6 h budget; assignment says smaller and correct beats large and shallow | Full 30-min soak, full suite |
| D16 | 2026-11-08 | SLI targets recalibrated from data: browse p95 < 200 ms, checkout (place_order) p95 < 400 ms, success >= 99.5%, error < 0.5%; design load 40 it/s | Healthy p95 is 30-70 ms; the scaffold's 800/1500 ms would hide a 10x regression. Chosen at ~3-4x healthy p95. | Keep 800/1500 ms; use 2x baseline (flaps on noise) |

Starting machine (measured 2026-11-07): 8 CPU, 8 GB RAM, macOS; docker/kind/kubectl/helm/k6 not installed; brew, git, python3 present.

## 5. Things still unverified (do not state as fact yet)
- ~~Release tag v0.10.2 exists~~ VERIFIED (HTTP 200). k6 v2.3.0 contains `experimental-prometheus-rw` output (string present in binary); still to verify it actually writes to Prometheus.
- Does kind's default network plugin enforce NetworkPolicies?
- How much load does my laptop sustain? (decides rates and soak length)

## 5b. Smoke run evidence (2026-11-08, after D10/D11)
`perf/results/smoke-2026-11-08T06-27-22-337Z.json`: 180 requests, 0% failed, checkout success 100% (4 of 4), browse p95 165 ms, checkout place_order p95 288 ms. Earlier smoke runs on the unstabilised cluster failed (p95 ~23 s; then HTTP 500s because currencyservice was crash-looping). Kept as a diagnosed failure for the memo.

## 5c. VALID baseline (lean mode, 2026-11-08)
`perf/results/baseline-2026-11-08T06-46-12-365Z.json`, 5 it/s for 5 min, mix 60/30/10: 5598 requests (18.4 req/s), 0% failed, 0 dropped iterations, 0 pod restarts. Browse p50 12.0 / p95 32.2 / p99 146.4 ms. Checkout (place_order) p50 31.0 / p95 67.8 / p99 140.8 ms. Checkout success 100% (135/135).
Prediction check (my pre-run guess, browse p95 300-600 ms): WRONG, actual 32 ms, about 10x faster. Lesson: I over-estimated emulation cost and under-estimated how light 5 it/s is once the host is not swapping.

## 5d. Ramp hypothesis (author: Claude; written seconds after launch, before reading any ramp result)
Steps 5,10,20,30,40,60,80,100 it/s, 2 min each, MAX_VUS=600. At 5 it/s the shop used ~18 req/s with p95 32 ms. I expect the knee (browse p95 > 800 ms or errors > 0.5%) between 40 and 60 it/s, because the 4 vCPU VM saturates first; likely the frontend (it renders every page and fans out gRPC calls) and, with emulation, the Node.js/Go services. If the knee is below 20 it/s, the VM is the limit, not the app.

## 5e. RAMP result (2026-11-08, valid; lean mode)
`perf/results/ramp-2026-11-08T07-24-24-586Z.json` (file time = end of run), steps 2 min each, 135,371 requests, 0% failed, checkout 100%, no stock threshold (800/1500 ms) breached. Per-step from Prometheus (median / max of k6 5-s p95 windows, ms):
| it/s | req/s | browse p95 | place_order p95 |
|---|---|---|---|
| 5 | 18 | 88/306 | 114/433 |
| 10 | 31 | 46/52 | 173/277 |
| 20 | 61 | 29/33 | 73/86 |
| 30 | 99 | 31/36 | 64/74 |
| 40 | 137 | 44/51 | 65/78 |
| 60 | 197 | 61/76 | 66/80 |
| 80 | 273 | 122/226 | 75/97 |
| 100 | 346 | 280/453 | 111/160 |
Hypothesis check: predicted knee 40-60 it/s, frontend first. WRONG on the knee (>= 80 it/s; shows as latency, not errors). Partly right on who: at 100 it/s currencyservice used 0.63 cores and frontend 0.53 of 1.63 total (VM has 4). k6 dropped 220 iterations from 40 it/s up (VU spin-up in k6 on the Mac, not shop failures). Currency is on every page, so it is the bottleneck candidate.

## 5f. Spike hypothesis (written before the run)
Base 20 it/s, burst to 100 it/s in 10 s for 1 min, then back. Expect: browse p95 jumps above 200 ms during the burst (maybe 300-600 ms), no errors, some k6 dropped iterations while VUs spin up, recovery to under 100 ms within about 30 s after the burst ends.

## 5g. SPIKE BEFORE fix and bottleneck B1 (2026-11-08)
Spike hypothesis check: predicted burst latency > 200 ms but NO errors. WRONG on errors. Result (`perf/results/spike-BEFORE-fix-*.json`): 37,812 requests, 1.50% failed, checkout success 97.70%, 536 HTTP 500s (home 134, product 162, add_to_cart 92, view_cart 68, currency 50, place_order 30), 206 dropped iterations, browse threshold crossed.
Evidence chain (bottleneck B1, natural, not artificially constrained):
1. Symptom: 500s from every page type starting ~16 s into the spike, i.e. in the calm 20 it/s phase, before the burst at +60 s.
2. Localise: `kubectl get pod currencyservice` lastState = OOMKilled, finished 07:26:27Z, spike started 07:26:11Z. Frontend logs earlier showed `could not retrieve currencies ... connection refused` when currencyservice is down. Prometheus: currencyservice restarts +1 in the window.
3. Cause: memory limit 128 MiB; peak working set 125 MiB (98%), 107 MiB even afterwards (memory not released). cartservice and paymentservice also peak at 127 MiB (known next risks, not fixed here).
4. Why one pod hurts everything: 1 replica, on every page (price conversion), no retry in the frontend.
5. Change: `perf/fix-bottleneck.sh` memory limit 128Mi -> 256Mi (request 128Mi). Same spike profile rerun for AFTER.
After-hypothesis (before the run): 0 OOMKills, error rate about 0%, checkout success >= 99.5%; browse p95 still exceeds 200 ms during the 100 it/s burst (ramp showed 280 ms at 100 it/s), recovery within about 30 s.
Panel note for Part A: the CPU-throttling and CPU-usage panels did NOT localise this (CPU was 0.63 of 1 core); the container restarts / OOMKilled and memory working-set vs limit are what found it.

## 5h. Spike AFTER fix, run 1: CONFOUNDED (2026-11-08)
`perf/results/spike-AFTER-fix-run1-CONFOUNDED-*.json`: 36,745 requests, 20.26% failed, checkout success 77.83%, browse p95 505 ms, 307 dropped iterations. WORSE than before, but NOT because of the currency fix: currencyservice had 0 restarts (fix works on its own mechanism). Cause: cartservice container exited with code 139 (SIGSEGV) at 07:33:26Z, in the burst; every page header calls cartservice, so home/product/cart/checkout all returned 500 (peak ~297 500s/s at 07:33:44). Same short outage costs far more failures at 380 req/s than at 60 req/s.
Likely cause (NOT proven): .NET cartservice crashing under Rosetta x86 emulation (the same app failed to start earlier with CoreCLR error 0x8007000E under QEMU). Treat as platform artifact until reproduced on native x86. Real-world lesson that stays valid: cartservice is a single replica on every page's path, so any restart is a full outage (candidate for Part B: replicas + PDB).
Before/after rule: I will not claim an improvement from run 1. Rerun the identical spike once (run 2) and report both runs.
Run 2 hypothesis (written before): currency 0 OOMKills; if cartservice does not crash, errors <= 0.5% and checkout >= 99.5%; if it crashes again, that is a reproducible finding and goes to Part B.

## 5i. Spike run 2 and conclusion (2026-11-08)
Run 2 (`spike-AFTER-fix-run2-NOISY-*`): 31,178 reqs, 0% failed, checkout 100%, 0 restarts, BUT browse p95 4,372 ms, place_order p95 2,264 ms, 1,975 dropped. Host contention suspected (swap ~9 GB used, VM resident ~670 MB of 4 GB, ANECompilerService ~95% CPU), not proven. Latency from run 2 is not valid evidence. Hypothesis check: predicted clean run; errors yes (0%), latency no.
Conclusion: bottleneck B1 proven by mechanism; see `perf/bottleneck.md`. No clean latency A/B is claimed.

## 5j. Soak hypothesis (written before the run)
10 min (shortened from 30, 8 GB laptop, D15) at 14 it/s (0.7 x RATE 20). Expect: errors <= 0.5%, browse p95 stable under 200 ms with no upward drift, currencyservice memory plateau below 256 MiB (it grows under load, so this is the leak/limit check), 0 restarts. Risk: cartservice SIGSEGV again (Rosetta).

## 5k. SOAK result (2026-11-08) - SHORTENED to 10 min (30 in brief), 14 it/s
`perf/results/soak-2026-11-08T07-51-02-652Z.json`: 32,376 requests, 0% failed, checkout 100%, browse p50/p95/p99 = 11.4/91.0/673.9 ms, place_order p95 115.7 ms, 4 dropped iterations, 0 pod restarts during the run. Hypothesis check: all met. Not shown: whether memory creeps over 30 min (10 min too short to say).

## 5l. Security hypothesis (author: Claude; written after launch, before reading any result)
Expect FAIL (upstream has no hardening): S01 headers, S02 cookie flags, S05 cross-user cart via session id, S06 rate limiting, S07 TLS, S08 intruder pod reaches paymentservice, S09 no NetworkPolicy, S10 pod hardening. Expect PASS: S03 error pages (not sure), S04 input validation, S11 secrets in env. F01 (payment down): should fail closed; I expect it does. F02 (invalid-request flood): unsure, depends on the 200 ms SLI.

## 5m. SECURITY result (2026-11-08, clean rerun; `security/results/`)
13 checks: 5 pass, 8 fail. FAIL: S01 headers, S02 cookie flags (no HttpOnly/SameSite), S03 error page leaks `rpc error`/source paths on unknown product, S05 cross-user cart via stolen session id (with positive control), S06 no rate limit (200 rapid requests all 200), S07 no HTTPS, S08 intruder pod REACHABLE to paymentservice:50051, S09 no NetworkPolicy. PASS: S04 input validation, S10 pod hardening (upstream already sets it), S11 no secret literals, F01 payment-down fails CLOSED (with precondition), F02 invalid-request flood no 5xx and valid p95 < 200 ms.
Hypothesis check: predicted S10 fail (wrong, upstream is hardened), S03 pass (wrong, it leaks), S05 fail (right), F01 closed (right). Two corrections to my own suite during the run: dashed card number made F01 vacuous; S05 first "passed" only because cartservice was down (Rosetta translator assertion, exit 133) so a positive control was added. Lesson for the interview: a check that passes is only evidence if a control proves it could fail.

## 5n. SECURITY fix and rerun (2026-11-08)
Fix: `kubectl apply -f security/fixes/networkpolicies.yaml` (default-deny ingress + per-service allow rules from the call graph). Rerun: S08 PASS (intruder BLOCKED), S09 PASS (policies exist). Regression check: k6 smoke after the fix = 228 requests, 0% failed, checkout 100%, p95 70 ms. kind's default CNI (kindnet) enforced the policy, so Calico was not needed. Evidence: `security/results/after-fix-networkpolicy.txt`. NetworkPolicies stay applied for Part B.

## 5o. CHAOS exp1 hypothesis (productcatalogservice pod-failure 60 s, mode all, 1 replica; load 10 it/s)
Steady state (Part A SLIs): browse p95 < 200 ms, place_order p95 < 400 ms, success >= 99.5%, error < 0.5%; measured over the 60 s healthy window before injection.
Hypothesis: catalog is on every browse and checkout path and has one replica, so during the fault nearly all page requests fail (>50%), the k6 abort condition trips within about 20 s, and the shop recovers within 15 s of the pod returning. Blast radius: 1 Deployment, namespace boutique only, fault <= 60 s. Abort: >50% failed requests for 20 s (automatic, fault deleted by trap) or manual `kubectl delete -f chaos/exp1-productcatalog-failure.yaml`. Note: recovery is timed from fault removal, so after an abort it measures time-to-recover, not total outage length.

## 5p. CHAOS exp1 run 1: aborted early (2026-11-08)
`chaos/results/run1-early-abort/`: 2,290 requests, only 1.44% failed, checkout_success 100%, recovery 7 s after fault removed. The k6 SLI threshold `http_req_failed{journey:checkout} < 0.5%` had abortOnFail on for the chaos profile, so the run stopped seconds after injection and removed the fault; the full 60 s was never observed. Hypothesis ">50% fail" could NOT be evaluated; "recovers within 15 s" held (7 s). Fix to the harness: abortOnFail now off for ramp, spike AND chaos; chaos aborts only on the catastrophic rule (>50% of requests failing for 20 s). Rerun exp1 as run 2.

## 5q. CHAOS exp1 BEFORE mitigation (run 3, valid full-window run; 2026-11-08)
`chaos/results/exp1-BEFORE/`: productcatalogservice pod-failure 60 s (mode all, 1 replica), 10 it/s, 4 min total. 8,835 requests, 22.17% failed overall, checkout_success 99.60% (counts only checkouts that reached place_order), recovery 1 s after fault removal. Derived estimate (not measured per second): fault is ~25% of the run, so about 85-90% of requests failed inside the fault window. SLI verdict: FAIL (checkout error rate crossed 0.5%).
Hypothesis check: ">50% fail" RIGHT (estimated ~89% in window); "recovers < 15 s" RIGHT (1 s); "abort trips within 20 s" WRONG: the abort threshold is on the cumulative failure rate, which never passed 50%, so the fault ended by its own 60 s duration. Known weakness of the harness: should use a windowed rate. Also: gate.sh does not push chaos-run metrics to Prometheus, so no per-second timeline exists.
Process notes: run 1 aborted early by a too-strict SLI abort (kept in `run1-early-abort/`); run 2 was refused by the gate's pre-check (transient warm-up), then retries were added.

## 5r. MITIGATION M1 and AFTER hypothesis
Change: `chaos/mitigation/apply.sh` = productcatalogservice 2 replicas + PodDisruptionBudget minAvailable 1. For a fair A/B the fault is now mode `one` (one pod); with 1 replica that is identical to mode all, so BEFORE remains comparable.
After hypothesis (written before the run): with one of two catalog pods killed, kube-proxy/gRPC stop sending to it within seconds; expect error rate under 0.5% overall, possibly a short burst of errors in the first seconds (existing connections to the dead pod), browse p95 stays under 200 ms. If errors persist for the full 60 s, the frontend's gRPC connection pinning is the cause (no client-side retry).

## 5s. CHAOS exp1 AFTER mitigation (2026-11-08)
`chaos/results/exp1-AFTER/`: 9,140 requests, 0.00% failed, checkout 100%, browse p95 27.8 ms, place_order p95 78 ms, recovery 0 s; gate verdict PASS. Before: 22.17% failed, gate FAIL. Hypothesis right (even better than predicted: no error burst). Caveat: single run each; the before run killed ALL pods (1 replica) and the after run killed ONE of two, equivalent for 1 replica.

## 5t. CHAOS exp2 and exp3 hypotheses (written before running)
Common: 10 it/s, 4 min runs, fault 120 s (exp2) or 60 s (exp3) after 60 s healthy window; steady state = Part A SLIs; abort = windowed catastrophic rule is NOT implemented (known gap), so manual abort `kubectl delete -f chaos/<exp>.yaml`; blast radius: one Deployment in namespace boutique.
- EXP2 network latency, +300 ms (jitter 50) on traffic INTO currencyservice (single replica), 120 s. Hypothesis: every page converts prices, possibly several calls per page, so latency is added per call; browse p95 breaches 200 ms (expect 400 ms to over 1 s), errors stay about 0 (slow, not broken), place_order p95 breaches 400 ms. Possible contradiction: the frontend has gRPC deadlines that turn slowness into errors.
- EXP3 dependency failure, redis-cart down 60 s (mode all). The runbook said "browse unaffected"; I now expect that to be WRONG, because exp B1/spike showed every page header calls cartservice: expect ALL page types to fail (browse too), at a rate near the outage share. Also expect carts to be lost (redis-cart has no persistence). Unknown: does cartservice reconnect on its own after redis returns (watch recovery_seconds); the surprise candidate is a permanent failure needing a cartservice restart.

## 5u. CHAOS exp2 and exp3 results (2026-11-08)
EXP2 (`chaos/results/exp2/`, +300 ms jitter 50 into currencyservice, 120 s): 9,015 requests, 0.00% failed, checkout 100%, browse p95 4,082 ms (target 200), place_order p95 1,540 ms (target 400), 54 dropped, recovery 0 s. Gate FAIL on latency only. Hypothesis: slow-not-broken RIGHT; magnitude WRONG (predicted 0.4-1 s, got 4 s: pages call currency several times serially).
EXP3 (`chaos/results/exp3/`, redis-cart down 60 s): 8,409 requests, 19.49% failed, checkout_success 78.54%, browse p95 5,845 ms, place_order p95 1,564 ms, 128 dropped, recovery 0 s after fault removed. Gate FAIL. Hypothesis: runbook claim "browse unaffected" was WRONG (every page header calls cartservice); my revised "all pages fail" RIGHT; "cartservice reconnects on its own" RIGHT (recovery 0 s). NEW finding: cartservice OOMKilled (exit 137) at 08:20:14Z during the outage (128 MiB limit, exceptions from Redis calls); cart restarts 6 -> 7. So the Redis failure also crashed the cart service. Not fixed (time box). Carts lost: not measured, expected (no persistence).
Failure classes covered: pod kill / dependency unavailable (exp1), network latency (exp2), datastore dependency failure (exp3). Fixed and re-run: exp1 only.

## 6. Session notes (fill in as we go)
### Session 1
- My starting machine (paste from preflight): _TBD_
- What I understood / still unclear: _TBD (user delegated execution; walk-through to be done afterwards)_
- Baseline hypothesis, written BEFORE the run (author: Claude, on the user's instruction to proceed; user to review/replace): at 5 it/s the app is healthy; browse p95 about 300-600 ms (amd64 images under Rosetta on 4 vCPU, each page fans out to several gRPC calls); checkout success >= 99%; slowest tier likely frontend or recommendationservice (Python, CPU-heavy under emulation).

### Quiz answers (practice for live walkthrough)
_TBD after each part._
