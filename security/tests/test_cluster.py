"""Cluster-configuration and service-to-service checks. S08-S11."""
import json, subprocess, pytest

pytestmark = pytest.mark.cluster
APP_DEPLOYS = ["frontend", "cartservice", "checkoutservice", "paymentservice", "productcatalogservice",
               "currencyservice", "shippingservice", "emailservice", "recommendationservice", "adservice"]

@pytest.mark.blocker
def test_s08_unauthenticated_internal_grpc(kube):
    """From an unrelated pod, can we call paymentservice's gRPC port at all? (no authn, no mTLS)
    With NetworkPolicies this connection must be refused."""
    out = subprocess.run(
        ["kubectl", "-n", "boutique", "run", "intruder", "--rm", "-i", "--restart=Never", "--image=busybox:1.36",
         "--labels=app=intruder", "--", "sh", "-c", "nc -z -w 3 paymentservice 50051 && echo REACHABLE || echo BLOCKED"],
        capture_output=True, text=True, timeout=90)
    assert "BLOCKED" in out.stdout, f"intruder pod reached paymentservice:50051 -> {out.stdout.strip()[:80]}"

@pytest.mark.blocker
def test_s09_network_policies_exist(kj):
    pols = kj("networkpolicies")["items"]
    assert pols, "no NetworkPolicy in namespace: flat network, every pod can reach every service"

@pytest.mark.warn
def test_s10_pod_security(kj):
    """Non-root, no privilege escalation, read-only root FS, all caps dropped, on every app container."""
    bad = []
    for d in kj("deployments")["items"]:
        if d["metadata"]["name"] not in APP_DEPLOYS: continue
        spec = d["spec"]["template"]["spec"]
        psc = spec.get("securityContext", {})
        for c in spec["containers"]:
            sc = c.get("securityContext", {})
            if sc.get("privileged"): bad.append((d["metadata"]["name"], "privileged"))
            if not (sc.get("runAsNonRoot") or psc.get("runAsNonRoot")): bad.append((d["metadata"]["name"], "may run as root"))
            if sc.get("allowPrivilegeEscalation", True): bad.append((d["metadata"]["name"], "allowPrivilegeEscalation"))
            if not sc.get("readOnlyRootFilesystem"): bad.append((d["metadata"]["name"], "writable root FS"))
            if "ALL" not in sc.get("capabilities", {}).get("drop", []): bad.append((d["metadata"]["name"], "caps not dropped"))
    assert not bad, f"pod hardening gaps: {bad}"

@pytest.mark.warn
def test_s11_secrets_not_in_plain_env(kj):
    """No credential-looking literal values in container env (should be secretKeyRef)."""
    hits = []
    for d in kj("deployments")["items"]:
        for c in d["spec"]["template"]["spec"]["containers"]:
            for e in c.get("env", []):
                if any(w in e["name"].upper() for w in ["PASSWORD", "SECRET", "TOKEN", "API_KEY", "PRIVATE"]) and "value" in e:
                    hits.append((d["metadata"]["name"], e["name"]))
    assert not hits, f"secret-like literals in env: {hits}"
