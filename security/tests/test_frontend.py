"""HTTP-level checks against the frontend. S01-S07."""
import re, time, uuid
import pytest, requests
from conftest import CHECKOUT

@pytest.mark.warn
def test_s01_security_headers(s, base):
    """Defense in depth against clickjacking/MIME sniffing/XSS. Upstream sends none; expected to FAIL."""
    h = s.get(base + "/").headers
    missing = [k for k in ["Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options|frame-ancestors", "Referrer-Policy"]
               if not any(re.search(k, name, re.I) for name in h) and not ("frame-ancestors" in h.get("Content-Security-Policy", ""))]
    assert not missing, f"missing headers: {missing}"

@pytest.mark.warn
def test_s02_cookie_flags(s, base):
    """Session cookie must be HttpOnly + SameSite (+ Secure when served over TLS)."""
    r = s.get(base + "/")
    sc = [v for k, v in r.raw.headers.items() if k.lower() == "set-cookie"]
    assert sc, "no cookie issued"
    ck = " ".join(sc).lower()
    assert "httponly" in ck and "samesite" in ck, f"weak cookie flags: {sc}"

@pytest.mark.blocker
def test_s03_error_pages_do_not_leak(s, base):
    """Unknown product id: user must not see stack traces, gRPC internals or file paths."""
    r = s.get(base + "/product/DOES-NOT-EXIST")
    body = r.text.lower()
    leaks = [w for w in ["goroutine", "rpc error", "grpc", "panic", "/src/", ".go:", "traceback", "productcatalogservice:"] if w in body]
    assert not leaks, f"error page leaks internals {leaks} (status {r.status_code})"

@pytest.mark.blocker
def test_s04_input_validation_and_reflection(s, base):
    """Bad card number / script payload must be rejected, not 5xx, and never reflected unescaped."""
    s.post(base + "/cart", data={"product_id": "OLJCESPC7Z", "quantity": "1"})
    bad = dict(CHECKOUT, credit_card_number="not-a-card", email="<script>alert(1)</script>@x.io")
    r = s.post(base + "/cart/checkout", data=bad)
    assert r.status_code < 500, f"server error {r.status_code} on invalid input"
    assert "<script>alert(1)</script>" not in r.text, "payload reflected unescaped"
    assert "Your order is complete" not in r.text, "order accepted with invalid card"

@pytest.mark.blocker
def test_s05_cross_user_cart_access(base):
    """Authorization: user B must not see user A's cart by presenting A's session id.
    Online Boutique has no auth: the cookie IS the identity. We prove that the id is not bound to anything else."""
    a = requests.Session(); a.get(base + "/")
    a.post(base + "/cart", data={"product_id": "OLJCESPC7Z", "quantity": "2"})
    sid = a.cookies.get("shop_session-id")
    assert sid, "no session cookie"
    # Positive control: A must see the item in A's OWN cart, otherwise "B sees nothing" proves nothing (e.g. cart service down).
    own = a.get(base + "/cart")
    assert own.status_code == 200 and "Sunglasses" in own.text, f"control failed: A cannot see own cart ({own.status_code})"
    b = requests.Session()  # different client, different "browser", same stolen id
    b.cookies.set("shop_session-id", sid)
    cart_b = b.get(base + "/cart").text
    # PASS means B could NOT see A's items. Expected to FAIL on upstream: session id alone grants access.
    assert "Sunglasses" not in cart_b and "OLJCESPC7Z" not in cart_b, "cross-user cart read via stolen/forged session id"

@pytest.mark.warn
def test_s06_rate_limiting(s, base):
    """Burst of 200 requests from one client should hit 429 at some point. Upstream has no limiter."""
    codes = [s.get(base + "/").status_code for _ in range(200)]
    assert 429 in codes, f"no throttling observed in 200 rapid requests (codes seen: {sorted(set(codes))})"

@pytest.mark.blocker
def test_s07_tls_front_door(base):
    """Checkout carries PII/card data: front door must serve HTTPS (directly or via ingress)."""
    https = base.replace("http://", "https://")
    try:
        requests.get(https + "/", timeout=5, verify=False)
        ok = True
    except requests.exceptions.RequestException:
        ok = False
    assert ok, "HTTPS not available on the frontend endpoint (plaintext HTTP only)"
