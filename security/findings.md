# Security results (fill from your run: `security/run.sh`)

Expected on upstream Online Boutique (hypotheses to confirm, not results):
| Check | Expected | Why it matters |
|---|---|---|
| S01 headers | FAIL (warn) | no CSP / nosniff / frame protection |
| S02 cookie flags | FAIL (warn) | session cookie theft/CSRF |
| S03 error leakage | PASS? | verify - if gRPC text appears it blocks |
| S04 input validation | PASS? | invalid card should be rejected, not 5xx |
| S05 cross-user cart | FAIL (blocker) | cookie is the only identity (no auth) |
| S06 rate limit | FAIL (warn) | availability |
| S07 TLS | FAIL (blocker) | PII/card in cleartext |
| S08 unauth gRPC | FAIL -> PASS after fix | lateral movement |
| S09 netpol exists | FAIL -> PASS after fix | flat network |
| S10 pod security | PASS? | upstream sets hardening; verify |
| S11 secrets | PASS | shows a check that can pass |
| F01 payment down | ? | fail-closed vs fail-open |
| F02 invalid flood | ? | |

**Fix shown:** `security/fixes/networkpolicies.yaml` -> rerun S08/S09. Record before/after output here.

## Where security and performance/resilience pull against each other
1. **Rate limiting vs load testing.** A limiter that protects checkout will throttle k6 and invalidate capacity numbers. Decision: limiter is per-client-IP with an allowlisted load-test source, enforced in prod and test, so we measure the system *with* its limiter on; capacity = what real distinct clients get.
2. **Retries vs attack amplification.** Retries with backoff fix chaos exp1 but multiply load during a flood (3 retries = 4x requests). Decision: retry only idempotent calls, budget retries to ~10% of traffic, add jitter, and make the circuit breaker open before the limiter is saturated.
(Also: NetworkPolicies/mTLS add latency and moving parts - measure p95 before and after.)
