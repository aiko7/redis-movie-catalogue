from src.repository import MovieRepository


repo = MovieRepository()

print("Redis:", repo.ping())

print("\nMovie by ID:")
print(repo.get_by_id("tt0111161"))

print("\nMovies named The Matrix:")
print(repo.find_by_title("The Matrix"))

print("\nSci-Fi movies from 2000:")
movies = repo.get_by_genre_and_year(
    "Sci-Fi",
    2000,
    limit=5,
)

for movie in movies:
    print(
        movie["title"],
        movie["year"],
        movie["rating"],
    )

print("\nTop rated:")
movies = repo.top_rated(
    limit=10,
    min_votes=10000,
)

for movie in movies:
    print(
        movie["title"],
        movie["year"],
        movie["rating"],
        movie["num_votes"],
    )