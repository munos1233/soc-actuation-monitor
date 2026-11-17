#!/usr/bin/env python3
"""TEI validating webhook for the kind lab. Re-GETs objects in the review."""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tei_admit import KIND_APPROVAL, Store, approval_ref_of, tei_admit  # noqa: E402

STORE = Store()
NS_DEFAULT = "tei-lab"

# In-cluster mode (hosted clusters, e.g. ACK): re-GET via the pod's service
# account instead of shelling out to kubectl. Same read paths, same scoring.
INCLUSTER = os.environ.get("TEI_WEBHOOK_INCLUSTER", "").strip() in {"1", "true"}
_SA_DIR = Path("/var/run/secrets/kubernetes.io/serviceaccount")


def _incluster_get(path: str) -> dict | None:
    try:
        token = (_SA_DIR / "token").read_text(encoding="utf-8").strip()
        ctx = ssl.create_default_context(cafile=str(_SA_DIR / "ca.crt"))
        req = urllib.request.Request(
            f"https://kubernetes.default.svc{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 — a failed re-GET means "not found" here
        return None


def _kubectl_json(*args: str) -> dict | None:
    if INCLUSTER:
        resource, name, namespace = args[1], args[2], args[4]
        paths = {
            "configmap": f"/api/v1/namespaces/{namespace}/configmaps/{name}",
            "approval.tei.lab": f"/apis/tei.lab/v1/namespaces/{namespace}/approvals/{name}",
            "isolate.tei.lab": f"/apis/tei.lab/v1/namespaces/{namespace}/isolates/{name}",
        }
        return _incluster_get(paths[resource])
    proc = subprocess.run(
        ["kubectl", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _refresh_ingest() -> None:
    raw = _kubectl_json("get", "configmap", "ingest-registry", "-n", NS_DEFAULT, "-o", "json")
    if not raw:
        return
    data = raw.get("data") or {}
    if data.get("identity"):
        STORE.ingest_identity = str(data["identity"])
    if data.get("workload"):
        STORE.ingest_workload = str(data["workload"])


def _refresh_approval(namespace: str, name: str) -> None:
    raw = _kubectl_json("get", "approval.tei.lab", name, "-n", namespace, "-o", "json")
    if not raw:
        return
    STORE.put(
        {
            "kind": KIND_APPROVAL,
            "namespace": namespace,
            "name": name,
            "spec": raw.get("spec") or {},
            "status": raw.get("status") or {},
        }
    )


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        review = body.get("request") or {}
        obj = review.get("object") or {}
        sa = ((review.get("userInfo") or {}).get("username") or "writer").split(":")[-1]
        verb = str(review.get("operation") or "CREATE").lower()
        mapped = {
            "kind": obj.get("kind") or (obj.get("spec") or {}).get("kind") or "Unknown",
            "namespace": obj.get("metadata", {}).get("namespace", NS_DEFAULT),
            "name": obj.get("metadata", {}).get("name", ""),
            "spec": obj.get("spec") or {},
            "annotations": (obj.get("metadata") or {}).get("annotations") or {},
            "labels": (obj.get("metadata") or {}).get("labels") or {},
            "status": obj.get("status") or {},
            "ownerReferences": (obj.get("metadata") or {}).get("ownerReferences") or [],
        }
        _refresh_ingest()
        ref = approval_ref_of(mapped)
        if ref:
            _refresh_approval(mapped["namespace"], ref)
        if mapped["kind"] == "Isolate":
            raw_iso = _kubectl_json(
                "get", "isolate.tei.lab", mapped["name"], "-n", mapped["namespace"], "-o", "json"
            )
            if raw_iso:
                STORE.put(
                    {
                        "kind": "Isolate",
                        "namespace": mapped["namespace"],
                        "name": mapped["name"],
                        "spec": raw_iso.get("spec") or {},
                        "status": raw_iso.get("status") or {},
                    }
                )
        if mapped["kind"] == KIND_APPROVAL:
            STORE.put(mapped)
        decision = tei_admit(STORE, sa, verb, mapped)
        allowed = decision.persist
        response = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": review.get("uid", ""),
                "allowed": allowed,
                "status": {"message": decision.reason},
            },
        }
        blob = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s\n" % (fmt % args))


def main() -> None:
    cert = Path(os.environ.get("TEI_WEBHOOK_TLS_CRT") or Path(__file__).with_name("tls.crt"))
    key = Path(os.environ.get("TEI_WEBHOOK_TLS_KEY") or Path(__file__).with_name("tls.key"))
    port = int(os.environ.get("TEI_WEBHOOK_PORT", "9443"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    if cert.is_file() and key.is_file():
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(cert), str(key))
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
