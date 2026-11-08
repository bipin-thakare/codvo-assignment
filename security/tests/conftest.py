import json, os, subprocess, uuid
import pytest, requests

BASE = os.environ.get("BASE_URL", "http://localhost:8080")
NS = os.environ.get("NS", "boutique")

@pytest.fixture
def s():
    sess = requests.Session()
    sess.headers["User-Agent"] = "sec-suite"
    return sess

@pytest.fixture
def base():
    return BASE

def kubectl(*args, check=True):
    r = subprocess.run(["kubectl", "-n", NS, *args], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout

@pytest.fixture
def kj():
    def _get(kind):
        return json.loads(kubectl("get", kind, "-o", "json"))
    return _get

@pytest.fixture
def kube():
    return kubectl

CHECKOUT = {
    "email": "sec@example.com", "street_address": "1 Main St", "zip_code": "94043", "city": "MV", "state": "CA",
    "country": "United States", "credit_card_number": "4432801561520454",
    "credit_card_expiration_month": "1", "credit_card_expiration_year": "2039", "credit_card_cvv": "672",
}
