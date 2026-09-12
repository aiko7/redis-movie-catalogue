import json

import redis

from src.normalization import normalize_genre, normalize_title


class MovieRepository:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
    ):
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
        )

    def ping(self) -> bool:
        return bool(self.redis.ping())

    def get_by_id(self, imdb_id: str) -> dict | None:
        """
        Retrieve a movie directly by IMDb ID.

        Example:
            get_by_id("tt0133093")
        """
        data = self.redis.get(f"movie:{imdb_id}")

        if data is None:
            return None

        return json.loads(data)

    def find_by_title(
        self,
        title: str,
        year: int | None = None,
    ) -> list[dict]:
        """
        Find movies by exact normalized title.

        If year is supplied, use the more specific title+year index.

        Examples:
            find_by_title("The Matrix")
            find_by_title("The Matrix", 1999)
        """
        normalized = normalize_title(title)

        if year is None:
            key = f"title:{normalized}"
        else:
            key = f"title_year:{normalized}:{year}"

        movie_ids = self.redis.smembers(key)

        return self._get_movies(movie_ids)

    def get_by_year(
        self,
        year: int,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Return movies released in a particular year.
        """
        movie_ids = self.redis.smembers(f"year:{year}")

        if limit is not None:
            movie_ids = list(movie_ids)[:limit]

        return self._get_movies(movie_ids)

    def get_by_genre(
        self,
        genre: str,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Return movies belonging to a genre.

        Example:
            get_by_genre("Sci-Fi")
        """
        normalized = normalize_genre(genre)

        movie_ids = self.redis.smembers(
            f"genre:{normalized}"
        )

        if limit is not None:
            movie_ids = list(movie_ids)[:limit]

        return self._get_movies(movie_ids)

    def get_by_genre_and_year(
        self,
        genre: str,
        year: int,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Use Redis set intersection to find movies matching
        both a genre and a release year.
        """
        normalized = normalize_genre(genre)

        movie_ids = self.redis.sinter(
            f"genre:{normalized}",
            f"year:{year}",
        )

        if limit is not None:
            movie_ids = list(movie_ids)[:limit]

        return self._get_movies(movie_ids)

    def get_by_director(
        self,
        director_id: str,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Return movies associated with an IMDb director ID.

        Example:
            get_by_director("nm0000154")
        """
        movie_ids = self.redis.smembers(
            f"director:{director_id}"
        )

        if limit is not None:
            movie_ids = list(movie_ids)[:limit]

        return self._get_movies(movie_ids)

    def top_rated(
        self,
        limit: int = 10,
        min_votes: int = 1000,
    ) -> list[dict]:
        """
        Return the highest-rated movies.

        A minimum vote threshold prevents obscure movies
        with only a handful of ratings from dominating the
        results.
        """
        results = []

        batch_size = max(limit * 5, 100)
        start = 0

        while len(results) < limit:
            entries = self.redis.zrevrange(
                "ratings",
                start,
                start + batch_size - 1,
                withscores=True,
            )

            if not entries:
                break

            movie_ids = [
                movie_id
                for movie_id, _ in entries
            ]

            movies = self._get_movies(movie_ids)
            movies_by_id = {
                movie["id"]: movie
                for movie in movies
            }

            for movie_id, rating in entries:
                movie = movies_by_id.get(movie_id)

                if movie is None:
                    continue

                if (movie["num_votes"] or 0) < min_votes:
                    continue

                # The value should already match, but this makes
                # explicit that the sorted-set score is authoritative.
                movie["rating"] = float(rating)

                results.append(movie)

                if len(results) >= limit:
                    break

            start += batch_size

        return results

    def _get_movies(self, movie_ids) -> list[dict]:
        """
        Retrieve multiple movie JSON records efficiently using MGET.
        """
        movie_ids = list(movie_ids)

        if not movie_ids:
            return []

        keys = [
            f"movie:{movie_id}"
            for movie_id in movie_ids
        ]

        values = self.redis.mget(keys)

        movies = []

        for value in values:
            if value is not None:
                movies.append(json.loads(value))

        return movies

    def get_by_genres(
            self,
            genres: list[str],
    ) -> list[dict]:
        """
        Return movies belonging to at least one of the supplied genres.

        Redis performs a union of the genre sets.
        """
        if not genres:
            return []

        keys = [
            f"genre:{normalize_genre(genre)}"
            for genre in genres
        ]

        movie_ids = self.redis.sunion(*keys)

        return self._get_movies(movie_ids)