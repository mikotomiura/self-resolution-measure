#!/usr/bin/env bash
# One-command reproduction. Stops (exit != 0) if an input hash, a gate, a self-test, the
# determinism check or the comparison with the bundled results/ fails (cmp; no git needed).
# Standard-library Python 3.11+ only.
#
#   bash run.sh                          # reproduce; results must equal the bundled ones
#   ALLOW_RESULT_CHANGE=1 bash run.sh    # after an intended change to code or data
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
RAW="$ROOT/raw"
ROWDATA="$RAW/rowData.json"
ROWDATA_SHA256="497df0b4da398c39cc0fd8b28544d4ac1d61c728708f4f9cdaa32469acda78b9"
# Either package works: their rowData.json is byte-identical (DATA.md).
ZIP_V1="replication_package_FSE2021.zip"
ZIP_V1_SHA256="6f506cba88ef30a7027b367967a6d92628c84e90d80b4a1a343190e1083d04b2"
ZIP_EMSE="Replication_Debugging.zip"
ZIP_EMSE_SHA256="523705d8f02f59bfe952328598f03ee28f1d2c8f2a5e3a26caf2d251c8108fe4"
D2_DIR="data/li-coblenz-2026"

PY="${PYTHON:-$(command -v python3 || command -v python || true)}"
[ -n "$PY" ] || { echo "python3 / python not found" >&2; exit 1; }
export PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1

if command -v sha256sum > /dev/null 2>&1; then
  sha256_of() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum > /dev/null 2>&1; then
  sha256_of() { shasum -a 256 "$1" | cut -d' ' -f1; }
else
  echo "neither sha256sum nor shasum found; cannot verify inputs" >&2; exit 1
fi

echo "Step 0: inputs"
mkdir -p "$RAW"
if [ ! -f "$ROWDATA" ]; then
  ZIP=""; MEMBER=""
  if [ -f "$RAW/$ZIP_EMSE" ]; then
    [ "$(sha256_of "$RAW/$ZIP_EMSE")" = "$ZIP_EMSE_SHA256" ] || { echo "hash mismatch: $ZIP_EMSE" >&2; exit 1; }
    ZIP="$RAW/$ZIP_EMSE"; MEMBER="Replication_Debugging/rowData.json"
  elif [ -f "$RAW/$ZIP_V1" ]; then
    [ "$(sha256_of "$RAW/$ZIP_V1")" = "$ZIP_V1_SHA256" ] || { echo "hash mismatch: $ZIP_V1" >&2; exit 1; }
    ZIP="$RAW/$ZIP_V1"; MEMBER="replication_package_FSE2021/rowData.json"
  else
    echo "No input package in raw/. See DATA.md ('How to obtain'): download either figshare zip in a browser." >&2
    exit 1
  fi
  # Extract one known member by name only (no path taken from the archive) into a
  # temporary file; move it into place only after its hash matches.
  "$PY" - "$ZIP" "$MEMBER" "$ROWDATA.tmp" <<'PYEOF'
import sys, zipfile
zpath, member, dest = sys.argv[1:4]
with zipfile.ZipFile(zpath) as zf:
    data = zf.read(member)
with open(dest, "wb") as out:
    out.write(data)
PYEOF
  if [ "$(sha256_of "$ROWDATA.tmp")" != "$ROWDATA_SHA256" ]; then
    rm -f "$ROWDATA.tmp"; echo "hash mismatch: extracted rowData.json" >&2; exit 1
  fi
  mv "$ROWDATA.tmp" "$ROWDATA"
fi
[ "$(sha256_of "$ROWDATA")" = "$ROWDATA_SHA256" ] || { echo "hash mismatch: raw/rowData.json" >&2; exit 1; }
for f in "$D2_DIR/transcription_a.csv" "$D2_DIR/transcription_b.csv" "$D2_DIR/text_external.csv"; do
  [ -f "$f" ] || { echo "missing $f" >&2; exit 1; }
done
echo "  ok"

echo "Step 1: self-test (gates must bite; controls must recover known values)"
"$PY" analysis/analyze.py --selftest

echo "Step 2: analysis (written to results/.new first; the bundled results are not touched yet)"
rm -rf results/.new results/.tmp
PYTHONHASHSEED=0 "$PY" analysis/analyze.py --out results/.new

echo "Step 3: determinism (a second run with another hash seed must be byte-identical)"
PYTHONHASHSEED=1 "$PY" analysis/analyze.py --out results/.tmp > /dev/null
cmp results/.new/metrics.json results/.tmp/metrics.json
cmp results/.new/report.md results/.tmp/report.md
rm -rf results/.tmp
echo "  ok"

echo "Step 4: compare with the bundled results (works without git)"
if [ -f results/metrics.json ] && [ -f results/report.md ]; then
  if cmp -s results/.new/metrics.json results/metrics.json && cmp -s results/.new/report.md results/report.md; then
    echo "  ok (identical to the bundled results)"
  elif [ "${ALLOW_RESULT_CHANGE:-0}" = "1" ]; then
    echo "  CHANGED (allowed by ALLOW_RESULT_CHANGE=1); replacing the bundled results"
  else
    echo "results differ from the bundled results/ (compare results/.new/ with results/)." >&2
    echo "Set ALLOW_RESULT_CHANGE=1 only after an intended change." >&2
    exit 1
  fi
else
  echo "  no bundled results; using this run"
fi
mv -f results/.new/metrics.json results/metrics.json
mv -f results/.new/report.md results/report.md
rm -rf results/.new

echo "Step 5: provenance"
{
  echo "rowdata_sha256=$ROWDATA_SHA256"
  for f in config.json SEED run.sh "$D2_DIR/transcription_a.csv" "$D2_DIR/transcription_b.csv" \
           "$D2_DIR/text_external.csv" analysis/analyze.py analysis/d1.py analysis/d2.py analysis/stats.py; do
    h="$(sha256_of "$f")"
    [ -n "$h" ] || { echo "cannot hash $f" >&2; exit 1; }
    echo "$f=$h"
  done
  echo "python=$("$PY" -c 'import platform; print(platform.python_version())')"
} > results/provenance.txt
cat results/provenance.txt
echo "done: results/metrics.json results/report.md results/provenance.txt"
