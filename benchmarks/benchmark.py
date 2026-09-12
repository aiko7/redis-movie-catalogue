import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

import redis


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.normalization import normalize_title
from src.repository import MovieRepository


RESULTS_DIR = ROOT / "benchmarks" / "results"


def iterate_movies(r, batch_size=1000):
    """
    Iterate over every movie record in Redis.

    This deliberately ignores all secondary indexes.
    """
    cursor = 0

    while True:
        cursor, keys = r.scan(
            cursor=cursor,
            match="movie:*",
            count=batch_size,
        )

        if keys:
            values = r.mget(keys)

            for value in values:
                if value is not None:
                    yield json.loads(value)

        if cursor == 0:
            break


# ---------------------------------------------------------
# Full-scan implementations
# ---------------------------------------------------------

def full_scan_get_by_id(r, imdb_id):
    """
    Scan the ENTIRE collection.

    We deliberately do not stop when the movie is found,
    because Redis SCAN order is unspecified. This makes
    measurements comparable across runs and dataset sizes.
    """
    result = None

    for movie in iterate_movies(r):
        if movie["id"] == imdb_id:
            result = movie

    return result


def full_scan_find_by_title(r, title):
    normalized_target = normalize_title(title)

    results = []

    for movie in iterate_movies(r):
        if normalize_title(movie["title"]) == normalized_target:
            results.append(movie)

    return results


def full_scan_genre_and_year(r, genre, year):
    normalized_genre = genre.casefold()

    results = []

    for movie in iterate_movies(r):
        movie_genres = {
            g.casefold()
            for g in movie["genres"]
        }

        if (
            movie["year"] == year
            and normalized_genre in movie_genres
        ):
            results.append(movie)

    return results


# ---------------------------------------------------------
# Timing
# ---------------------------------------------------------

def result_count(result):
    if isinstance(result, list):
        return len(result)

    return int(result is not None)


def measure(function, repeats=5, warmup=True):
    """
    Run one unmeasured warm-up followed by measured runs.
    """

    if warmup:
        function()

    times = []
    result = None

    for _ in range(repeats):
        start = time.perf_counter()

        result = function()

        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000

        times.append(elapsed_ms)

    return {
        "median_ms": statistics.median(times),
        "mean_ms": statistics.mean(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "result_count": result_count(result),
    }


def benchmark(
    label,
    repeats,
    movie_id,
    genre,
    year,
):
    repo = MovieRepository()

    r = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True,
    )

    if not r.ping():
        raise RuntimeError("Redis is unavailable")

    target = repo.get_by_id(movie_id)

    if target is None:
        raise ValueError(
            f"{movie_id} does not exist in dataset {label}"
        )

    title = target["title"]

    movie_count_raw = r.get("meta:movie_count")

    movie_count = (
        int(movie_count_raw)
        if movie_count_raw is not None
        else 0
    )

    print(f"Dataset: {label}")
    print(f"Movies: {movie_count:,}")
    print(f"Redis keys: {r.dbsize():,}")
    print(
        f"Fixed ID/title target: "
        f"{title} [{movie_id}]"
    )
    print(
        f"Fixed genre/year query: "
        f"{genre}, {year}"
    )
    print()

    tests = [
        {
            "query": "id_lookup",
            "indexed": lambda: repo.get_by_id(
                movie_id
            ),
            "full_scan": lambda: full_scan_get_by_id(
                r,
                movie_id,
            ),
        },
        {
            "query": "title_lookup",
            "indexed": lambda: repo.find_by_title(
                title
            ),
            "full_scan": lambda: full_scan_find_by_title(
                r,
                title,
            ),
        },
        {
            "query": "genre_year",
            "indexed": lambda: repo.get_by_genre_and_year(
                genre,
                year,
            ),
            "full_scan": lambda: full_scan_genre_and_year(
                r,
                genre,
                year,
            ),
        },
    ]

    rows = []

    for test in tests:
        query = test["query"]

        print(f"Benchmarking {query}...")

        indexed = measure(
            test["indexed"],
            repeats=repeats,
        )

        scan = measure(
            test["full_scan"],
            repeats=repeats,
        )

        # Sanity check: both implementations should
        # return the same number of movies.
        if (
            indexed["result_count"]
            != scan["result_count"]
        ):
            raise RuntimeError(
                f"Result mismatch for {query}: "
                f"indexed={indexed['result_count']}, "
                f"full_scan={scan['result_count']}"
            )

        speedup = (
            scan["median_ms"]
            / indexed["median_ms"]
        )

        print(
            f"  indexed:   "
            f"{indexed['median_ms']:.4f} ms"
        )

        print(
            f"  full scan: "
            f"{scan['median_ms']:.4f} ms"
        )

        print(
            f"  speedup:   "
            f"{speedup:,.1f}x"
        )

        print(
            f"  results:   "
            f"{indexed['result_count']}"
        )

        print()

        for method, stats in [
            ("indexed", indexed),
            ("full_scan", scan),
        ]:
            rows.append({
                "dataset": label,
                "dataset_movies": movie_count,
                "redis_keys": r.dbsize(),
                "query": query,
                "method": method,
                "median_ms": round(
                    stats["median_ms"],
                    4,
                ),
                "mean_ms": round(
                    stats["mean_ms"],
                    4,
                ),
                "min_ms": round(
                    stats["min_ms"],
                    4,
                ),
                "max_ms": round(
                    stats["max_ms"],
                    4,
                ),
                "result_count": stats[
                    "result_count"
                ],
                "speedup": round(
                    speedup,
                    2,
                ),
                "target_movie": movie_id,
                "target_title": title,
                "target_genre": genre,
                "target_year": year,
            })

    return rows


def save_results(rows, filename):
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = RESULTS_DIR / filename

    with open(
        output,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys(),
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"Results saved to {output}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--label",
        required=True,
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--movie-id",
        default="tt0007205",
    )

    parser.add_argument(
        "--genre",
        default="Drama",
    )

    parser.add_argument(
        "--year",
        type=int,
        default=1920,
    )

    args = parser.parse_args()

    rows = benchmark(
        label=args.label,
        repeats=args.repeats,
        movie_id=args.movie_id,
        genre=args.genre,
        year=args.year,
    )

    save_results(
        rows,
        f"benchmark_{args.label}.csv",
    )


if __name__ == "__main__":
    main()