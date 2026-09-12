#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "===== 10k ====="
python scripts/import_imdb.py --limit 10000 --flush
python benchmarks/benchmark.py --label 10k --repeats 5

echo "===== 50k ====="
python scripts/import_imdb.py --limit 50000 --flush
python benchmarks/benchmark.py --label 50k --repeats 5

echo "===== 100k ====="
python scripts/import_imdb.py --limit 100000 --flush
python benchmarks/benchmark.py --label 100k --repeats 5

echo "===== 250k ====="
python scripts/import_imdb.py --limit 250000 --flush
python benchmarks/benchmark.py --label 250k --repeats 5

echo "===== FULL ====="
python scripts/import_imdb.py --flush
python benchmarks/benchmark.py --label full --repeats 5

echo
echo "All benchmarks complete."