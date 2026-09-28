#!/usr/bin/env bash
# Build the manuscript (paper/main.pdf) with Tectonic (developed with 0.17.0; it fetches
# TeX packages over the network on first use). Stops (exit != 0) if the template files do
# not match their published hashes, if make_results.py's self-test fails, if a
# qualitative statement checked in make_results.py no longer holds, if paper/results.tex
# is stale with respect to results/metrics.json, or if LaTeX reports an undefined
# citation or reference.
#
#   bash paper/build.sh                  # check results.tex, fetch the template if needed, build
#   UPDATE_RESULTS=1 bash paper/build.sh # rewrite results.tex after an intended change of results/
#   TECTONIC=/path/to/tectonic bash paper/build.sh
#
# The Springer Nature class and bibliography style are not redistributed here (their
# headers carry distribution conditions); they are taken from the publisher's template
# package and checked by SHA-256. You can also download the zip in a browser and put it
# into paper/ as sn-article-template.zip.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

ZIP_URL="https://cms-resources.apps.public.k8s.springernature.io/springer-cms/rest/v1/content/18782940/data/v12"
ZIP_NAME="sn-article-template.zip"   # "journal article template package (December 2024 version)", v3.1
ZIP_SHA256="812e76dcaa9c28dc1bff1fb6065d51729b67d4ea140552a05088317414a3ecae"
CLS_SHA256="36d0c3273a59d48dc6a9c7b080dfa1ec50dc10229d8751568d1f2e490ffa5ecc"
BST_SHA256="4b368414cc5593169907933b417aacfdb0ce905866a39bdf55d21aad65e9d46c"

PY="${PYTHON:-$(command -v python3 || command -v python || true)}"
[ -n "$PY" ] || { echo "python3 / python not found" >&2; exit 1; }
export PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1

if command -v sha256sum > /dev/null 2>&1; then
  sha256_of() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum > /dev/null 2>&1; then
  sha256_of() { shasum -a 256 "$1" | cut -d' ' -f1; }
else
  echo "neither sha256sum nor shasum found" >&2; exit 1
fi

echo "Step 1: template (sn-jnl.cls, sn-basic.bst)"
have_template() {
  [ -f sn-jnl.cls ] && [ -f sn-basic.bst ] \
    && [ "$(sha256_of sn-jnl.cls)" = "$CLS_SHA256" ] && [ "$(sha256_of sn-basic.bst)" = "$BST_SHA256" ]
}
if ! have_template; then
  if [ ! -f "$ZIP_NAME" ]; then
    command -v curl > /dev/null 2>&1 || { echo "curl not found; put $ZIP_NAME into paper/ by hand" >&2; exit 1; }
    rm -f "$ZIP_NAME.tmp"
    curl -fsSL --proto '=https' -o "$ZIP_NAME.tmp" "$ZIP_URL" \
      || { rm -f "$ZIP_NAME.tmp"; echo "download failed: $ZIP_URL" >&2; exit 1; }
    # Check the hash before the file gets its final name, so a wrong download is not reused.
    if [ "$(sha256_of "$ZIP_NAME.tmp")" != "$ZIP_SHA256" ]; then
      rm -f "$ZIP_NAME.tmp"
      echo "hash mismatch for the downloaded template; expected SHA-256 $ZIP_SHA256." >&2
      echo "Download it in a browser and put it into paper/ as $ZIP_NAME." >&2
      exit 1
    fi
    mv "$ZIP_NAME.tmp" "$ZIP_NAME"
  fi
  [ "$(sha256_of "$ZIP_NAME")" = "$ZIP_SHA256" ] \
    || { echo "hash mismatch: paper/$ZIP_NAME (expected $ZIP_SHA256); delete it and run again" >&2; exit 1; }
  # Extract two known members by name only (no path taken from the archive).
  "$PY" - "$ZIP_NAME" <<'PYEOF'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as zf:
    for member, dest in (("sn-article-template/sn-jnl.cls", "sn-jnl.cls"),
                         ("sn-article-template/bst/sn-basic.bst", "sn-basic.bst")):
        with open(dest, "wb") as out:
            out.write(zf.read(member))
PYEOF
  have_template || { echo "hash mismatch: extracted sn-jnl.cls / sn-basic.bst" >&2; exit 1; }
fi
echo "  ok"

echo "Step 2: results.tex must equal a fresh rendering of results/metrics.json"
"$PY" make_results.py --selftest > selftest.log 2>&1 || { cat selftest.log >&2; exit 1; }
"$PY" make_results.py --stdout > results.tex.new
if cmp -s results.tex.new results.tex; then
  rm -f results.tex.new
  echo "  ok"
elif [ "${UPDATE_RESULTS:-0}" = "1" ]; then
  mv -f results.tex.new results.tex
  echo "  UPDATED (UPDATE_RESULTS=1)"
else
  rm -f results.tex.new
  echo "paper/results.tex is stale: results/metrics.json changed. Re-run with UPDATE_RESULTS=1 after checking." >&2
  exit 1
fi

echo "Step 3: LaTeX"
TEC="${TECTONIC:-$(command -v tectonic || true)}"
[ -n "$TEC" ] || { echo "tectonic not found (set TECTONIC=/path/to/tectonic)" >&2; exit 1; }
"$TEC" --version > build.log 2>&1 || { echo "cannot run $TEC --version" >&2; cat build.log >&2; exit 1; }
# Remove old logs first: the checks below must read this run's log, never an earlier one.
rm -f main.log main.blg
"$TEC" -X compile --keep-logs main.tex >> build.log 2>&1 || { tail -30 build.log >&2; exit 1; }
[ -s main.log ] || { echo "main.log was not produced; cannot check for undefined citations" >&2; exit 1; }
# Tectonic wraps log lines at 79 characters, so a long per-citation warning can be split;
# the summary line "There were undefined ..." is what makes this check reliable.
if grep -E "(Citation|Reference) .* undefined|There were undefined (references|citations)" main.log > /dev/null; then
  grep -E "(Citation|Reference) .* undefined" main.log >&2 || true
  echo "undefined citations or references" >&2; exit 1
fi
[ -s main.blg ] || { echo "main.blg was not produced; cannot check the bibliography" >&2; exit 1; }
if grep -E "^Warning--" main.blg > /dev/null; then
  grep -E "^Warning--" main.blg >&2; echo "BibTeX warnings (incomplete or malformed entries in refs.bib)" >&2; exit 1
fi
if grep -E "^! " main.log > /dev/null; then
  grep -E -A3 "^! " main.log >&2; exit 1
fi
echo "  ok: paper/main.pdf"
