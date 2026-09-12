# Redis Movie Catalogue

A movie catalogue built with **Redis + Python** using IMDb public datasets.

The project focuses on **key-value database design**, especially access-pattern-oriented modelling, denormalized indexes, Redis Sets/Sorted Sets, and performance compared with naive full scans.

## Features

* Find movie by IMDb ID
* Find movie by exact title
* List movies by genre
* List movies by year
* Query genre + year using Redis set intersection
* Show top-rated movies
* Basic content-based movie recommendations
* Benchmark indexed Redis queries vs full dataset scans

## Redis Model

Examples of the main keys:

```text
movie:<imdb_id>                  -> movie JSON
title:<normalized_title>         -> set of movie IDs
title_year:<title>:<year>        -> set of movie IDs
year:<year>                      -> set of movie IDs
genre:<genre>                    -> set of movie IDs
director:<director_id>           -> set of movie IDs
ratings                          -> sorted set by IMDb rating
```

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start Redis:

```bash
docker compose up -d
```

Download the required IMDb files into `data/`:

```bash
cd data

wget https://datasets.imdbws.com/title.basics.tsv.gz
wget https://datasets.imdbws.com/title.ratings.tsv.gz
wget https://datasets.imdbws.com/title.crew.tsv.gz
wget https://datasets.imdbws.com/name.basics.tsv.gz

cd ..
```

Import the full movie dataset:

```bash
python scripts/import_imdb.py --flush
```

A smaller import can be created with:

```bash
python scripts/import_imdb.py --limit 10000 --flush
```

## Run

Start the CLI:

```bash
python -m src.cli
```

## Benchmarks

Run all benchmark dataset sizes:

```bash
./benchmarks/run_all.sh
```

Generate the combined results and plots:

```bash
python benchmarks/analyze_results.py
```

The benchmark compares indexed Redis access against naive full scans at:

```text
10k
50k
100k
250k
full dataset
```
