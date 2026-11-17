#!/usr/bin/env bash
# Build the anonymous TOPS artifact. No product name, no frontend, no contracts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="${PAPER_ARTIFACT_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT="${PAPER_ARTIFACT_OUT:-$ROOT/paper/artifact-anonymous-$STAMP.zip}"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/tops-artifact.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

test -f "$ROOT/paper/main.pdf" || {
  echo "paper/main.pdf missing; run make paper-pdf first" >&2
  exit 1
}

mkdir -p "$STAGE/artifact"
cp "$ROOT/paper/main.pdf" "$STAGE/artifact/main.pdf"
cp "$ROOT/REPRODUCE.md" "$STAGE/artifact/REPRODUCE.md"
cp "$ROOT/paper/cover-letter.md" "$STAGE/artifact/cover-letter.md"
cp "$ROOT/paper/SUBMISSION.md" "$STAGE/artifact/SUBMISSION.md"

mkdir -p "$STAGE/artifact/eval/results" "$STAGE/artifact/eval/harness" \
  "$STAGE/artifact/eval/policy" "$STAGE/artifact/eval/cases" \
  "$STAGE/artifact/eval/model" "$STAGE/artifact/eval/taxonomy" \
  "$STAGE/artifact/eval/k8s"
cp "$ROOT/paper/appendix-b-grids.md" "$STAGE/artifact/appendix-b-grids.md"
cp -R "$ROOT/eval/harness/." "$STAGE/artifact/eval/harness/"
cp -R "$ROOT/eval/policy/." "$STAGE/artifact/eval/policy/"
cp -R "$ROOT/eval/cases/." "$STAGE/artifact/eval/cases/"
if [[ -d "$ROOT/eval/model" ]]; then
  cp -R "$ROOT/eval/model/." "$STAGE/artifact/eval/model/"
  rm -f "$STAGE/artifact/eval/model/tla2tools.jar"
  rm -rf "$STAGE/artifact/eval/model/states"
  rm -f "$STAGE/artifact/eval/model/"*TTrace* "$STAGE/artifact/eval/model/"*.dmp
fi
mkdir -p "$STAGE/artifact/scripts"
cp "$ROOT/scripts/fetch_tlc.sh" "$STAGE/artifact/scripts/fetch_tlc.sh"
if [[ -d "$ROOT/eval/taxonomy" ]]; then
  cp -R "$ROOT/eval/taxonomy/." "$STAGE/artifact/eval/taxonomy/"
fi
if [[ -d "$ROOT/eval/k8s" ]]; then
  cp -R "$ROOT/eval/k8s/." "$STAGE/artifact/eval/k8s/"
  rm -rf "$STAGE/artifact/eval/k8s/bin"
  rm -f "$STAGE/artifact/eval/k8s/webhook/tls.crt" \
    "$STAGE/artifact/eval/k8s/webhook/tls.key" \
    "$STAGE/artifact/eval/k8s/webhook/webhook.pid" \
    "$STAGE/artifact/eval/k8s/webhook/webhook.log" \
    "$STAGE/artifact/eval/k8s/.attribute-baseline"
fi
# Frozen matrices only. Skip planner-arm checkpoints (may carry prompts).
for name in latest.json latest.md; do
  test -f "$ROOT/eval/results/$name" && cp "$ROOT/eval/results/$name" "$STAGE/artifact/eval/results/"
done
if [[ -d "$ROOT/eval/results/model" ]]; then
  mkdir -p "$STAGE/artifact/eval/results/model"
  cp -R "$ROOT/eval/results/model/." "$STAGE/artifact/eval/results/model/"
fi
if [[ -d "$ROOT/eval/results/planner_arm" ]]; then
  mkdir -p "$STAGE/artifact/eval/results/planner_arm"
  for name in latest.json latest.md; do
    test -f "$ROOT/eval/results/planner_arm/$name" && \
      cp "$ROOT/eval/results/planner_arm/$name" "$STAGE/artifact/eval/results/planner_arm/"
  done
fi
if [[ -d "$ROOT/eval/results/overhead" ]]; then
  mkdir -p "$STAGE/artifact/eval/results/overhead"
  for name in latest.json latest.md; do
    test -f "$ROOT/eval/results/overhead/$name" && \
      cp "$ROOT/eval/results/overhead/$name" "$STAGE/artifact/eval/results/overhead/"
  done
fi
# Do not pack planner_arm_family2: the paper does not report a second family.
for extra in adaptive search backlog process_split sangfor_stub scale comparator tla k8s k8s-kind lattice replay repeat heldout playbook_semantic signed_attribute independent mutation gold_ext b2 reexec gate-review; do
  dest="$extra"
  if [[ "$extra" == "sangfor_stub" ]]; then
    dest="envelope_b"
  fi
  if [[ -d "$ROOT/eval/results/$extra" ]]; then
    mkdir -p "$STAGE/artifact/eval/results/$dest"
    for name in latest.json latest.md README.md tlc-traces.json \
      tlc-full.log tlc-attribute-only.log tlc-view-pair.log tlc-minus-cas.log \
      protocol.md PENDING_JOINT_FREEZE.md r1-checklist.md env.example.json \
      packet.md g1-review.md g2-review.md filter-log.md out-of-knob.md; do
      test -f "$ROOT/eval/results/$extra/$name" && \
        cp "$ROOT/eval/results/$extra/$name" "$STAGE/artifact/eval/results/$dest/"
    done
    # Nested CVE scoring packet under k8s-kind
    if [[ "$extra" == "k8s-kind" && -d "$ROOT/eval/results/k8s-kind/cve-scoring" ]]; then
      mkdir -p "$STAGE/artifact/eval/results/k8s-kind/cve-scoring"
      for name in summaries.md scale.md blind-packet.md k1-scores.json k2-adjudication.md latest.md; do
        test -f "$ROOT/eval/results/k8s-kind/cve-scoring/$name" && \
          cp "$ROOT/eval/results/k8s-kind/cve-scoring/$name" \
            "$STAGE/artifact/eval/results/k8s-kind/cve-scoring/"
      done
    fi
  fi
done

test -f "$ROOT/eval/README.md" && cp "$ROOT/eval/README.md" "$STAGE/artifact/eval/README.md"

# Anonymized production slice the harness actually imports.
mkdir -p "$STAGE/artifact/backend/app" "$STAGE/artifact/backend/migrations/versions"
python3 - "$ROOT" "$STAGE/artifact/backend" <<'PY'
import pathlib
import shutil
import sys

root = pathlib.Path(sys.argv[1])
dest = pathlib.Path(sys.argv[2])
keep_dirs = [
    "backend/app/eval_suite",
    "backend/app/eval_monitor.py",
    "backend/app/core",
    "backend/app/db",
    "backend/app/models",
    "backend/app/services",
    "backend/app/agents",
    "backend/app/adapters",
    "backend/app/tasks",
    "backend/migrations/versions",
    "backend/pyproject.toml",
]
# Copy selected trees, then drop vendor packs and product comments later.
for item in keep_dirs:
    src = root / item
    if not src.exists():
        continue
    target = dest / pathlib.Path(item).relative_to("backend")
    if src.is_dir():
        shutil.copytree(src, target, dirs_exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)

# Drop vendor-specific adapters from the anonymous slice.
sangfor = dest / "app" / "adapters" / "sangfor"
if sangfor.exists():
    shutil.rmtree(sangfor)

# Upper-case forms are separate entries because these names reach the
# artifact as constant and environment-variable identifiers, not only as
# prose. The leak grep below is case-insensitive, so a casing that is
# missing here fails the pack rather than shipping.
replacements = (
    ("SHADOWTRACE", "ACTUATION"),
    ("ShadowTrace", "Actuation"),
    ("shadowtrace", "actuation"),
    ("深信服", "vendor"),
    ("SANGFOR", "VENDOR"),
    ("Sangfor", "Vendor"),
    ("sangfor", "vendor"),
    ("张家口", "site"),
    ("揭榜", "challenge"),
)
artifact = dest.parent
for path in artifact.rglob("*"):
    if not path.is_file():
        continue
    if path.suffix not in {".py", ".md", ".toml", ".txt", ".sql", ".json"}:
        continue
    text = path.read_text(encoding="utf-8")
    updated = text
    for old, new in replacements:
        updated = updated.replace(old, new)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
PY

# Fail closed if a product or site name leaked into staged reviewer text.
# Case-insensitive on purpose: the replacement table is case-sensitive, so
# this is what catches a casing the table does not cover.
if grep -R -I -n -E -i 'shadowtrace|深信服|张家口|揭榜|sangfor' \
  "$STAGE/artifact" \
  >/tmp/artifact-blind.txt 2>/dev/null; then
  echo "anonymous artifact leaked a product or site name:" >&2
  cat /tmp/artifact-blind.txt >&2
  exit 1
fi

rm -f "$OUT"
(cd "$STAGE/artifact" && zip -qr "$OUT" .)
echo "wrote $OUT"
