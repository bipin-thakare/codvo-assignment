# Threat model: checkout journey (Online Boutique, local cluster)

**Journey:** browser -> `frontend` (HTTP, Go) -> `cartservice` (-> `redis-cart`), `productcatalogservice`, `currencyservice`, `shippingservice`, `checkoutservice` -> `paymentservice`, `emailservice`. Internal calls are plaintext gRPC.

**Assets:** customer PII (email, address), card data in transit (demo payment service, but treat as real), cart contents, order confirmation, availability of checkout.

**Trust boundaries:** (1) internet/browser to frontend, (2) frontend to internal services, (3) services to Redis, (4) pods to the Kubernetes control plane/other pods.

**Entry points:** `GET /`, `/product/{id}`, `POST /cart`, `POST /cart/checkout`, `POST /setCurrency`, cookie `shop_session-id`, any pod that can reach a ClusterIP.

## Top 5 threats, ranked (likelihood x impact, 1-5 each)
| # | Threat | L | I | Risk | Tested? | Check |
|---|---|---|---|---|---|---|
| 1 | Lateral movement: any compromised pod calls internal gRPC (payment, cart, checkout) with no authn and no NetworkPolicy | 4 | 5 | 20 | Yes | S08, S09 |
| 2 | Session = guessable/forgeable cookie; no auth, so setting another user's `shop_session-id` reads or edits their cart (broken access control) | 4 | 3 | 12 | Yes | S05 |
| 3 | Plaintext HTTP everywhere (no TLS front door, no mTLS): PII and card data sniffable | 3 | 5 | 15 | Yes (front door) | S07 |
| 4 | Unbounded requests: no rate limiting, one client can exhaust the checkout path (availability) | 4 | 3 | 12 | Yes | S06, F01 |
| 5 | Weak runtime hardening / secrets and leaky errors: root containers, writable FS, stack traces to users, secrets in env | 3 | 3 | 9 | Yes | S02-S04, S10, S11 |

**Order note:** risk = L x I. Threat 3 ranks above 2 on impact (card data) even though the demo payment service is fake.

## Not tested (and why)
- Real card-processing / PCI controls: payment service is a stub.
- XSS beyond reflected-input smoke test (S04): needs a browser-based scanner (ZAP) - listed as next step.
- Supply-chain (image provenance, CVEs): out of time box; would add Trivy in CI.
- Kubernetes control-plane / RBAC audit: local kind cluster, not representative of a hardened environment.
