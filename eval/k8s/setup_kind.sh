#!/usr/bin/env bash
# Author-controlled kind cluster for the C5 headline. Not a cloud vendor.
# Fails if kind cannot be obtained. Does not copy fixture 22/22 numbers.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BIN="$ROOT/eval/k8s/bin"
mkdir -p "$BIN"
export PATH="$BIN:$PATH"

if ! command -v kind >/dev/null 2>&1; then
  arch="$(uname -m)"
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  case "$arch" in
    arm64|aarch64) asset="kind-${os}-arm64" ;;
    x86_64|amd64) asset="kind-${os}-amd64" ;;
    *)
      echo "kind not installed and arch $arch is not downloaded here" >&2
      exit 2
      ;;
  esac
  # kind v0.27.0; pin recorded in the artifact via this script.
  curl -fsSL -o "$BIN/kind" "https://kind.sigs.k8s.io/dl/v0.27.0/${asset}"
  chmod +x "$BIN/kind"
fi
if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not installed" >&2
  exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "docker not installed; kind cannot create tei-lab" >&2
  exit 2
fi

kind create cluster --name tei-lab --config "$ROOT/eval/k8s/kind-config.yaml" || true
kubectl config use-context kind-tei-lab
kubectl apply -f "$ROOT/eval/k8s/rbac.yaml"
kubectl apply -f "$ROOT/eval/k8s/crds.yaml"

GATEKEEPER_VERSION="${GATEKEEPER_VERSION:-v3.17.1}"
ATTRIBUTE_BASELINE="none"
if kubectl apply -f "https://raw.githubusercontent.com/open-policy-agent/gatekeeper/${GATEKEEPER_VERSION}/deploy/gatekeeper.yaml"; then
  kubectl wait --for=condition=established --timeout=180s \
    crd/constrainttemplates.templates.gatekeeper.sh || true
  kubectl apply -f "$ROOT/eval/k8s/gatekeeper/k8srequiredapprovalref.yaml"
  kubectl wait --for=condition=established --timeout=180s \
    crd/k8srequiredapprovalref.constraints.gatekeeper.sh || true
  kubectl apply -f "$ROOT/eval/k8s/gatekeeper/constraint.yaml" || true
  ATTRIBUTE_BASELINE="gatekeeper"
  echo "attribute baseline: Gatekeeper ${GATEKEEPER_VERSION}"
else
  echo "Gatekeeper install failed; installing ValidatingAdmissionPolicy of the same request-attribute class" >&2
  kubectl apply -f "$ROOT/eval/k8s/vap-attribute.yaml"
  ATTRIBUTE_BASELINE="validatingadmissionpolicy"
  echo "attribute baseline: ValidatingAdmissionPolicy (not Gatekeeper)"
fi
echo "$ATTRIBUTE_BASELINE" > "$ROOT/eval/k8s/.attribute-baseline"

WEBHOOK_DIR="$ROOT/eval/k8s/webhook"
if [[ ! -f "$WEBHOOK_DIR/tls.crt" || ! -f "$WEBHOOK_DIR/tls.key" ]]; then
  openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$WEBHOOK_DIR/tls.key" \
    -out "$WEBHOOK_DIR/tls.crt" \
    -days 30 \
    -subj "/CN=host.docker.internal" \
    -addext "subjectAltName=DNS:host.docker.internal,DNS:localhost,IP:127.0.0.1"
fi
CABUNDLE="$(base64 < "$WEBHOOK_DIR/tls.crt" | tr -d '\n')"
sed "s#CABUNDLE_PLACEHOLDER#${CABUNDLE}#" "$WEBHOOK_DIR/webhook.yaml" \
  > "$WEBHOOK_DIR/webhook.generated.yaml"

PYTHON="${PYTHON:-$ROOT/backend/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi
if [[ ! -f "$WEBHOOK_DIR/webhook.pid" ]] || ! kill -0 "$(cat "$WEBHOOK_DIR/webhook.pid")" 2>/dev/null; then
  nohup "$PYTHON" "$WEBHOOK_DIR/server.py" > "$WEBHOOK_DIR/webhook.log" 2>&1 &
  echo $! > "$WEBHOOK_DIR/webhook.pid"
  sleep 1
fi
kubectl apply -f "$WEBHOOK_DIR/webhook.generated.yaml"
echo "C5 numbers come from make paper-eval-k8s-kind with TEI_K8S_KIND=1"
echo "Never copy fixture 22/22 into eval/results/k8s-kind/"
