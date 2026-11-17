#!/usr/bin/env bash
# Fetch the pinned official tla2tools.jar. Checksum fails closed.
# The jar is not required in the anonymous zip (see pack_paper_artifact.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${TLC_JAR:-$ROOT/eval/model/tla2tools.jar}"
URL="${TLC_JAR_URL:-https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar}"
# sha256 of the v1.8.0 GitHub asset pinned when this script was frozen.
# If the pre-release asset moves, this check fails; do not skip it.
EXPECTED_SHA256="${TLC_JAR_SHA256:-957b23b2bb31d08f19346e105e23585f93fea9a139a712b0ac347eedaf26afea}"

mkdir -p "$(dirname "$DEST")"

hash_of() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

if [[ -f "$DEST" ]]; then
  actual="$(hash_of "$DEST")"
  if [[ "$actual" == "$EXPECTED_SHA256" ]]; then
    echo "tla2tools.jar ok ($actual)"
    exit 0
  fi
  echo "tla2tools.jar checksum mismatch (got $actual); re-fetching" >&2
  rm -f "$DEST"
fi

tmp="$DEST.download"
curl -fsSL -o "$tmp" "$URL"
actual="$(hash_of "$tmp")"
if [[ "$actual" != "$EXPECTED_SHA256" ]]; then
  echo "downloaded tla2tools.jar sha256 $actual != $EXPECTED_SHA256" >&2
  rm -f "$tmp"
  exit 1
fi
mv "$tmp" "$DEST"
echo "wrote $DEST ($actual)"
