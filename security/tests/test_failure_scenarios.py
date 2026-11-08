"""Security failure scenarios. Each mutates the cluster and restores it in `finally`."""
import time, pytest, requests
from conftest import CHECKOUT

pytestmark = [pytest.mark.failure_scenario, pytest.mark.blocker]

def _scale(kube, dep, n):
    kube("scale", f"deploy/{dep}", f"--replicas={n}")
    if n:
        kube("rollout", "status", f"deploy/{dep}", "--timeout=120s")
    else:
        time.sleep(8)

def test_f01_payment_down_fails_closed(base, kube):
    """Dependency failure: if paymentservice is unavailable, checkout must FAIL CLOSED:
    no 'order complete' page, no confirmation without a charge."""
    sess = requests.Session()
    sess.post(base + "/cart", data={"product_id": "OLJCESPC7Z", "quantity": "1"})
    # Precondition (otherwise this check could pass vacuously): with payment UP the same checkout must succeed.
    ok = sess.post(base + "/cart/checkout", data=CHECKOUT, timeout=30)
    assert "Your order is complete" in ok.text, f"precondition failed: valid checkout not completing ({ok.status_code})"
    sess.post(base + "/cart", data={"product_id": "OLJCESPC7Z", "quantity": "1"})
    _scale(kube, "paymentservice", 0)
    try:
        r = sess.post(base + "/cart/checkout", data=CHECKOUT, timeout=30)
        assert "Your order is complete" not in r.text, "FAIL-OPEN: order confirmed while payment was down"
        assert r.status_code >= 400, f"expected error status, got {r.status_code}"
    finally:
        _scale(kube, "paymentservice", 1)

def test_f02_invalid_request_flood_does_not_degrade_valid_users(base):
    """Flood of invalid requests: valid browse p95 must stay < 200 ms (Part A SLI) and no 5xx on invalid input."""
    import concurrent.futures as cf, statistics
    def bad(_):
        return requests.post(base + "/cart/checkout", data={"credit_card_number": "x"}, timeout=15).status_code
    with cf.ThreadPoolExecutor(32) as ex:
        codes = list(ex.map(bad, range(400)))
    assert not [c for c in codes if c >= 500], f"5xx under invalid flood: {sorted(set(codes))}"
    lat = []
    for _ in range(20):
        t = time.time(); requests.get(base + "/", timeout=10); lat.append((time.time() - t) * 1000)
    assert statistics.quantiles(lat, n=20)[-1] < 200, f"valid-user p95 degraded: {max(lat):.0f} ms"
