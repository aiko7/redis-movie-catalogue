from src.repository import MovieRepository


class MovieRecommender:
    def __init__(self, repository: MovieRepository):
        self.repository = repository

    def recommend(
        self,
        imdb_id: str,
        limit: int = 10,
        min_votes: int = 1000,
    ) -> list[dict]:
        source = self.repository.get_by_id(imdb_id)

        if source is None:
            return []

        candidates = self.repository.get_by_genres(
            source["genres"]
        )

        scored = []

        source_genres = set(source["genres"])

        source_directors = {
            director["id"]
            for director in source["directors"]
        }

        for candidate in candidates:
            # Never recommend the movie itself.
            if candidate["id"] == source["id"]:
                continue

            if (candidate["num_votes"] or 0) < min_votes:
                continue

            score = self._score_movie(
                source,
                candidate,
                source_genres,
                source_directors,
            )

            scored.append({
                "movie": candidate,
                "score": score,
            })

        scored.sort(
            key=lambda result: (
                result["score"],
                result["movie"]["rating"] or 0,
                result["movie"]["num_votes"] or 0,
            ),
            reverse=True,
        )

        return scored[:limit]

    def _score_movie(
        self,
        source: dict,
        candidate: dict,
        source_genres: set[str],
        source_directors: set[str],
    ) -> float:
        score = 0.0

        #
        # Shared genres
        #
        candidate_genres = set(candidate["genres"])

        shared_genres = (
            source_genres & candidate_genres
        )

        score += len(shared_genres) * 3

        #
        # Same director
        #
        candidate_directors = {
            director["id"]
            for director in candidate["directors"]
        }

        if source_directors & candidate_directors:
            score += 2

        #
        # Similar release period
        #
        if abs(
            source["year"] - candidate["year"]
        ) <= 5:
            score += 1

        #
        # Small quality bonus
        #
        if candidate["rating"] is not None:
            score += candidate["rating"] / 10

        return round(score, 2)