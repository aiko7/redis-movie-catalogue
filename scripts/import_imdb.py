import argparse
import csv
import gzip
import json
import sys
from pathlib import Path

import redis


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.normalization import normalize_genre, normalize_title


DATA_DIR = ROOT / "data"


def open_tsv(filename):
    return gzip.open(
        DATA_DIR / filename,
        mode="rt",
        encoding="utf-8",
        newline=""
    )


def parse_int(value):
    if value == r"\N":
        return None
    return int(value)


def load_movies(limit=None):
    movies = {}

    with open_tsv("title.basics.tsv.gz") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            if row["titleType"] != "movie":
                continue

            if row["isAdult"] != "0":
                continue

            if row["startYear"] == r"\N":
                continue

            movie_id = row["tconst"]

            genres = (
                []
                if row["genres"] == r"\N"
                else row["genres"].split(",")
            )

            movies[movie_id] = {
                "id": movie_id,
                "title": row["primaryTitle"],
                "original_title": row["originalTitle"],
                "year": int(row["startYear"]),
                "runtime_minutes": parse_int(row["runtimeMinutes"]),
                "genres": genres,
                "rating": None,
                "num_votes": None,
                "directors": [],
            }

            if limit and len(movies) >= limit:
                break

    print(f"Loaded {len(movies):,} movie records")
    return movies


def attach_ratings(movies):
    with open_tsv("title.ratings.tsv.gz") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            movie = movies.get(row["tconst"])

            if movie is None:
                continue

            movie["rating"] = float(row["averageRating"])
            movie["num_votes"] = int(row["numVotes"])


def attach_directors(movies):
    required_director_ids = set()

    with open_tsv("title.crew.tsv.gz") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            movie = movies.get(row["tconst"])

            if movie is None:
                continue

            if row["directors"] == r"\N":
                continue

            director_ids = row["directors"].split(",")

            movie["directors"] = [
                {"id": director_id, "name": None}
                for director_id in director_ids
            ]

            required_director_ids.update(director_ids)

    director_names = {}

    with open_tsv("name.basics.tsv.gz") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            director_id = row["nconst"]

            if director_id in required_director_ids:
                director_names[director_id] = row["primaryName"]

    for movie in movies.values():
        for director in movie["directors"]:
            director["name"] = director_names.get(director["id"])


def write_to_redis(movies, r):
    pipe = r.pipeline(transaction=False)

    pending_movies = 0

    for movie in movies.values():
        movie_id = movie["id"]
        year = movie["year"]

        title_key = normalize_title(movie["title"])

        #
        # Primary record
        #
        pipe.set(
            f"movie:{movie_id}",
            json.dumps(movie, ensure_ascii=False)
        )

        #
        # Title indexes
        #
        pipe.sadd(
            f"title:{title_key}",
            movie_id
        )

        pipe.sadd(
            f"title_year:{title_key}:{year}",
            movie_id
        )

        #
        # Year index
        #
        pipe.sadd(
            f"year:{year}",
            movie_id
        )

        #
        # Genre indexes
        #
        for genre in movie["genres"]:
            genre_key = normalize_genre(genre)

            pipe.sadd(
                f"genre:{genre_key}",
                movie_id
            )

        #
        # Director indexes
        #
        for director in movie["directors"]:
            pipe.sadd(
                f"director:{director['id']}",
                movie_id
            )

        #
        # Rating sorted set
        #
        if movie["rating"] is not None:
            pipe.zadd(
                "ratings",
                {movie_id: movie["rating"]}
            )

        pending_movies += 1

        # Don't create one enormous pipeline when we later
        # import hundreds of thousands of movies.
        if pending_movies >= 500:
            pipe.execute()
            pipe = r.pipeline(transaction=False)
            pending_movies = 0

    if pending_movies:
        pipe.execute()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of movies to import"
    )

    parser.add_argument(
        "--flush",
        action="store_true",
        help="Delete existing Redis data before importing"
    )

    args = parser.parse_args()

    r = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True
    )

    print("Connecting to Redis...")

    if not r.ping():
        raise RuntimeError("Redis did not respond")

    print("Redis connection OK")

    if args.flush:
        print("Flushing Redis database...")
        r.flushdb()

    movies = load_movies(args.limit)

    print("Attaching ratings...")
    attach_ratings(movies)

    print("Attaching directors...")
    attach_directors(movies)

    print("Writing data to Redis...")
    write_to_redis(movies, r)

    r.set("meta:movie_count", len(movies))

    print()
    print("Import complete")
    print(f"Movies imported: {len(movies):,}")
    print(f"Redis keys: {r.dbsize():,}")


if __name__ == "__main__":
    main()