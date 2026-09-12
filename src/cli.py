from src.repository import MovieRepository
from src.recommender import MovieRecommender

def print_movie(movie: dict) -> None:
    directors = ", ".join(
        director["name"] or director["id"]
        for director in movie["directors"]
    )

    genres = ", ".join(movie["genres"])

    rating = (
        f"{movie['rating']:.1f}"
        if movie["rating"] is not None
        else "N/A"
    )

    votes = (
        f"{movie['num_votes']:,}"
        if movie["num_votes"] is not None
        else "N/A"
    )

    print(
        f"{movie['title']} ({movie['year']})\n"
        f"  IMDb ID:   {movie['id']}\n"
        f"  Genres:    {genres or 'N/A'}\n"
        f"  Directors: {directors or 'N/A'}\n"
        f"  Runtime:   {movie['runtime_minutes'] or 'N/A'} min\n"
        f"  Rating:    {rating} ({votes} votes)"
    )


def print_movies(movies: list[dict]) -> None:
    if not movies:
        print("\nNo movies found.")
        return

    print()

    for i, movie in enumerate(movies, start=1):
        print(f"{i}. ", end="")
        print_movie(movie)
        print()


def find_by_id(repo: MovieRepository) -> None:
    imdb_id = input("IMDb ID: ").strip()

    movie = repo.get_by_id(imdb_id)

    if movie is None:
        print("\nMovie not found.")
        return

    print()
    print_movie(movie)


def find_by_title(repo: MovieRepository) -> None:
    title = input("Title: ").strip()

    year_input = input(
        "Year (press Enter to ignore): "
    ).strip()

    year = int(year_input) if year_input else None

    movies = repo.find_by_title(title, year)

    print_movies(movies)


def list_by_genre(repo: MovieRepository) -> None:
    genre = input("Genre: ").strip()

    limit_input = input(
        "Maximum results [20]: "
    ).strip()

    limit = int(limit_input) if limit_input else 20

    movies = repo.get_by_genre(
        genre,
        limit=limit,
    )

    print_movies(movies)


def list_by_year(repo: MovieRepository) -> None:
    year = int(input("Year: ").strip())

    limit_input = input(
        "Maximum results [20]: "
    ).strip()

    limit = int(limit_input) if limit_input else 20

    movies = repo.get_by_year(
        year,
        limit=limit,
    )

    print_movies(movies)


def list_by_genre_and_year(repo: MovieRepository) -> None:
    genre = input("Genre: ").strip()
    year = int(input("Year: ").strip())

    limit_input = input(
        "Maximum results [20]: "
    ).strip()

    limit = int(limit_input) if limit_input else 20

    movies = repo.get_by_genre_and_year(
        genre,
        year,
        limit=limit,
    )

    print_movies(movies)


def show_top_rated(repo: MovieRepository) -> None:
    limit_input = input(
        "Number of movies [10]: "
    ).strip()

    min_votes_input = input(
        "Minimum IMDb votes [100000]: "
    ).strip()

    limit = int(limit_input) if limit_input else 10
    min_votes = (
        int(min_votes_input)
        if min_votes_input
        else 100_000
    )

    movies = repo.top_rated(
        limit=limit,
        min_votes=min_votes,
    )

    print_movies(movies)

def recommend_movies(
    repo: MovieRepository,
    recommender: MovieRecommender,
) -> None:
    imdb_id = input("IMDb ID: ").strip()

    source = repo.get_by_id(imdb_id)

    if source is None:
        print("\nMovie not found.")
        return

    limit_input = input(
        "Number of recommendations [10]: "
    ).strip()

    limit = int(limit_input) if limit_input else 10

    print("\nRecommendations based on:")
    print_movie(source)

    recommendations = recommender.recommend(
        imdb_id,
        limit=limit,
    )

    if not recommendations:
        print("\nNo recommendations found.")
        return

    print("\nRecommended movies:\n")

    for i, result in enumerate(
        recommendations,
        start=1,
    ):
        movie = result["movie"]
        score = result["score"]

        print(f"{i}. Similarity score: {score}")
        print_movie(movie)
        print()

def print_menu() -> None:
    print(
        "\n"
        "===== Redis Movie Catalogue =====\n"
        "1. Find movie by IMDb ID\n"
        "2. Find movie by exact title\n"
        "3. List movies by genre\n"
        "4. List movies by year\n"
        "5. List movies by genre and year\n"
        "6. Show top-rated movies\n"
        "7. Recommend similar movies\n"
        "0. Exit\n"
    )



def main() -> None:
    repo = MovieRepository()
    recommender = MovieRecommender(repo)
    try:
        if not repo.ping():
            print("Could not connect to Redis.")
            return
    except Exception as exc:
        print(f"Could not connect to Redis: {exc}")
        return

    while True:
        print_menu()

        choice = input("Choose an option: ").strip()

        try:
            if choice == "1":
                find_by_id(repo)

            elif choice == "2":
                find_by_title(repo)

            elif choice == "3":
                list_by_genre(repo)

            elif choice == "4":
                list_by_year(repo)

            elif choice == "5":
                list_by_genre_and_year(repo)

            elif choice == "6":
                show_top_rated(repo)

            elif choice == "7":
                recommend_movies(repo, recommender)

            elif choice == "0":
                print("Goodbye.")
                break

            else:
                print("Invalid option.")

        except ValueError:
            print("\nInvalid numeric input.")

        except KeyboardInterrupt:
            print("\n")
            continue


if __name__ == "__main__":
    main()