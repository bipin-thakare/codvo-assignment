# Release readiness memo: Online Boutique checkout
To: VP Engineering · From: Bipin Thakare · 2026-11-08 · **Recommendation: NO-GO today; GO WITH CONDITIONS if the five gates below pass at a re-test in week 2**

**Scope and honesty note.** Local kind cluster on an 8 GB Apple Silicon laptop, x86 images under Rosetta, a lean app (ads and recommendations scaled to zero), 10-minute soak instead of 30. Numbers are for ratios and findings, not absolute capacity. Evidence: `perf/results/`, `chaos/results/`, `security/results/`, narrative in `decisions-and-understanding.md`.

## Findings ranked by risk
| # | Finding (evidence) | Root cause | Recommendation | Owner |
|---|---|---|---|---|
| 1 | Another user's cart readable by presenting their session cookie (S05 FAIL, with positive control) | Cookie is the only identity, no auth or binding | Signed, rotating session tokens; auth for order history | Backend lead |
| 2 | No HTTPS on the checkout front door (S07 FAIL); no security headers, weak cookie flags, error page leaks `rpc error` and source paths (S01, S02, S03 FAIL) | Plain-HTTP service, defaults | TLS ingress + HSTS, headers, generic error page, HttpOnly/SameSite | Platform / Backend |
| 3 | Redis outage (60 s): 19.49% requests failed, checkout success 78.54%, and cartservice was OOMKilled during it (exp3) | Every page calls cartservice; Redis single instance, no persistence; cart memory limit 128Mi | Raise cart memory limit, 2+ cart replicas, Redis persistence/HA, serve pages without cart on failure | SRE |
| 4 | Catalog pod loss: 22.17% requests failed (exp1). **Fixed:** 2 replicas + PDB gave 0.00% on identical fault (gate FAIL to PASS) | Single replica on every page path | Apply to all request-path services | SRE |
| 5 | +300 ms on currency: 0% errors but browse p95 4,082 ms vs 200 ms target (exp2) | Page renders call currency repeatedly, serially, no timeout or cache | Cache rates, per-call deadlines, circuit breaker | Backend lead |
| 6 | currencyservice OOMKilled at 98% of 128Mi under load (spike): 1.5% failed, checkout 97.7%. **Fixed:** limit 256Mi, 0 kills across two reruns | Stock memory limit too low | Set limits from measured peak plus headroom | Service owner |
| 7 | Internal gRPC reachable from any pod (S08, S09 FAIL). **Fixed:** NetworkPolicies, both now PASS, shop unharmed | Flat network | Keep policies; plan mTLS | Platform |
| 8 | No rate limiting (S06 FAIL: 200 rapid requests, no 429) | Not implemented | Ingress limiter, exempt load-test source | Platform |
| 9 | cartservice crashed under emulation (Rosetta translator assertion, exit 133/139) | Likely x86 emulation, **not proven**; needs native x86 | Re-run on native x86 before relying on perf numbers | QA lead |

Passing and worth saying: payment outage **fails closed** (F01, no order without a charge), invalid-request flood caused no 5xx (F02), input validation (S04), pod hardening and secrets (S10, S11).

## Measured performance (lean app, valid runs)
Baseline 5 it/s: browse p95 32 ms, checkout p95 68 ms, 0% errors. Ramp to 100 it/s (346 req/s): 0% errors; browse p95 rises from about 30-60 ms to 280 ms at 100 it/s, so the knee is between 80 and 100 it/s. Soak 10 min at 14 it/s: 0% errors, browse p95 91 ms, no restarts. SLI targets (set at about 3-4x healthy p95): browse p95 < 200 ms, checkout p95 < 400 ms, success >= 99.5%, errors < 0.5%.

## Exit criteria (measurable)
- **Performance:** at 1.5x forecast peak for 30 min: browse p95 < 200 ms, checkout p95 < 400 ms, errors < 0.5%, 0 OOMKills or restarts, 0 dropped iterations.
- **Resilience:** exp1, exp2, exp3 each keep the SLIs (or degrade without 5xx on browse) and recover in < 30 s; the chaos gate passes in CI.
- **Security:** all blocker checks pass (S03, S04, S05, S07, S08, S09, F01, F02); no cross-user cart access; TLS on; no critical image CVEs (scan to be added).

## Release recommendation
**NO-GO today**: two blocker security failures on a checkout flow (S05, S07) and two resilience failures that take the shop down (Redis, currency latency). Evidence above. **Conditional go in two weeks** if: (1) S05 and S07 fixed, (2) cart memory and Redis resilience fixed with exp3 re-run passing, (3) currency timeouts/cache with exp2 re-run passing, (4) all gates green in CI, (5) a perf re-test on native x86 confirms the knee.

## Closing findings and running the team (4 engineers, 1 junior)
One tracker; each finding has severity, owner, SLA (critical 2 weeks, high 4, medium quarter) and the check ID that proves it: a finding closes only when its check passes in CI. Seniors take security fixes #1-2 and Redis/cart resilience; the junior owns k6 scenarios, dashboards and adding checks, in paired reviews with small PRs and a failing test first. Weekly 30-min risk review; monthly game day replaying the chaos gate.

## One decision I would reverse
I trimmed the stack to a lean app (no ads, no recommendations) to fit 8 GB. With more time I would run the full app on a native x86 machine: it would remove the emulation doubt (#9) and show whether ads and recommendations change the knee.
