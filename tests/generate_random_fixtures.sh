#!/usr/bin/env bash
# Regenerate both random Instagram fixture folders (+ zips) for manual testing.
#
# Output: tests/random_instagram_fixture{,_legacy}/ and .zip
# Both gitignored — treat them as derived artifacts.
#
# Deterministic seed 42; pass --seed <n> to override.
#
# Usage:
#   ./tests/generate_random_fixtures.sh                 # default: realistic
#   ./tests/generate_random_fixtures.sh --scale small
#   ./tests/generate_random_fixtures.sh --scale large

set -euo pipefail

SCALE="realistic"
SEED="42"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --scale) SCALE="$2"; shift 2 ;;
        --seed)  SEED="$2";  shift 2 ;;
        -h|--help)
            sed -n '2,14p' "$0"; exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYDIR="$REPO_ROOT/packages/python"
OUT_NEWER="$REPO_ROOT/tests/random_instagram_fixture"
OUT_LEGACY="$REPO_ROOT/tests/random_instagram_fixture_legacy"

rm -rf "$OUT_NEWER" "$OUT_LEGACY"

cd "$PYDIR"
poetry run python -m tests.fixtures "$OUT_NEWER"  --format newer  --scale "$SCALE" --seed "$SEED" --zip
poetry run python -m tests.fixtures "$OUT_LEGACY" --format legacy --scale "$SCALE" --seed "$SEED" --zip

echo
echo "Done. Artifacts:"
ls -la "$OUT_NEWER.zip" "$OUT_LEGACY.zip"
