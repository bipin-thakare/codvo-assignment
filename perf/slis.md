# SLIs and targets (checkout journey)

| # | SLI | Target | How measured |
|---|-----|--------|--------------|
| 1 | Checkout success rate (order-confirmation page returned) | >= 99.5% | k6 `checkout_success` |
| 2 | Checkout p95 latency (POST /cart/checkout) | < 400 ms | k6 `http_req_duration{step:place_order}` |
| 3 | Browse p95 latency (home + product pages) | < 200 ms | k6 `http_req_duration{journey:browse}` |
| 4 | HTTP error rate on checkout journey | < 0.5% | k6 `http_req_failed{journey:checkout}` |

## How the numbers were chosen
- Browse 800 ms: a page that fans out to ~6 services should still feel instant; common web guidance puts interactive pages under ~1 s at p95.
- Checkout 1500 ms: checkout fans out to cart, catalog, currency, shipping, payment, email, so it is allowed to be slower than browse. Users tolerate a short wait at the payment step.
- Success 99.5% (error budget 0.5%): a payment step that fails 1 in 100 is visible to customers; 99.5% is a conventional "two and a half nines" starting target for a non-critical-infra storefront.
- **These are provisional.** Re-calibrate after the baseline run: if the healthy system's p95 is 120 ms, a 1500 ms target hides regressions. Record the baseline and set targets near 2-3x baseline p95 (still inside the user-tolerance ceilings above). Final values: see `memo.md`.

## Journey mix
60% browse only / 30% add to cart and abandon / 10% checkout. Typical e-commerce funnels convert 2-4% of sessions, so 10% overweights checkout on purpose: we are stress-testing the expensive path, not simulating revenue. Override with `MIX_BROWSE`, `MIX_CART`.

## FINAL calibration (measured, 2026-11-08) - supersedes the provisional numbers above
Evidence: `perf/results/baseline-2026-11-08T06-46-12-365Z.json` and the ramp (`perf/results/ramp-*.json`, per-step table in `decisions-and-understanding.md` 5e).
- Healthy region: 20-60 it/s, browse p95 about 30-60 ms, place_order p95 about 65-75 ms, 0% errors.
- Targets set at roughly 3-4x the healthy p95 at a design load of 40 it/s: **browse p95 < 200 ms, place_order p95 < 400 ms**, success >= 99.5%, error rate < 0.5%. Tight enough to catch a regression (the old 800/1500 ms would have hidden a 10x slowdown), loose enough not to flap on single noisy windows (the 5 it/s warm-up window reached 306 ms max).
- Under the new browse target the knee is between 80 and 100 it/s (median browse p95 122 ms at 80, 280 ms at 100).
- Caveat: lean app (no ads/recommendations), emulated amd64 on a 4 vCPU VM; absolute numbers will differ on other hardware, ratios are what to compare.
