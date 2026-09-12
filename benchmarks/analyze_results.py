from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmarks" / "results"


def load_results():
    files = [
        file
        for file in RESULTS.glob("benchmark_*.csv")
        if file.name != "benchmark_summary.csv"
    ]

    if not files:
        raise RuntimeError(
            f"No benchmark CSV files found in {RESULTS}"
        )

    frames = []

    for file in files:
        print(f"Loading {file.name}")
        frames.append(pd.read_csv(file))

    df = pd.concat(
        frames,
        ignore_index=True,
    )

    return df


def create_summary(df):
    df = df.sort_values(
        [
            "dataset_movies",
            "query",
            "method",
        ]
    )

    summary_columns = [
        "dataset",
        "dataset_movies",
        "redis_keys",
        "query",
        "method",
        "median_ms",
        "mean_ms",
        "min_ms",
        "max_ms",
        "result_count",
        "speedup",
        "target_movie",
        "target_title",
        "target_genre",
        "target_year",
    ]

    summary = df[summary_columns]

    output = RESULTS / "benchmark_summary.csv"

    summary.to_csv(
        output,
        index=False,
    )

    print()
    print("===== Benchmark Summary =====")
    print()
    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print(f"Saved summary to {output}")

    return summary


def print_speedup_table(df):

    indexed = df[
        df["method"] == "indexed"
    ][
        [
            "dataset",
            "dataset_movies",
            "query",
            "median_ms",
        ]
    ].rename(
        columns={
            "median_ms": "indexed_ms"
        }
    )

    scanned = df[
        df["method"] == "full_scan"
    ][
        [
            "dataset",
            "dataset_movies",
            "query",
            "median_ms",
        ]
    ].rename(
        columns={
            "median_ms": "full_scan_ms"
        }
    )

    comparison = indexed.merge(
        scanned,
        on=[
            "dataset",
            "dataset_movies",
            "query",
        ],
    )

    comparison["speedup"] = (
        comparison["full_scan_ms"]
        / comparison["indexed_ms"]
    )

    comparison = comparison.sort_values(
        [
            "query",
            "dataset_movies",
        ]
    )

    print()
    print("===== Indexed vs Full Scan =====")
    print()

    print(
        comparison.to_string(
            index=False,
            formatters={
                "indexed_ms": lambda x: f"{x:.4f}",
                "full_scan_ms": lambda x: f"{x:.4f}",
                "speedup": lambda x: f"{x:,.1f}x",
            },
        )
    )

    output = (
        RESULTS
        / "benchmark_comparison.csv"
    )

    comparison.to_csv(
        output,
        index=False,
    )

    print()
    print(
        f"Saved comparison table to {output}"
    )

    return comparison


def plot_query_performance(df):

    queries = sorted(
        df["query"].unique()
    )

    for query in queries:
        subset = df[
            df["query"] == query
        ]

        plt.figure(
            figsize=(8, 5)
        )

        methods = [
            "indexed",
            "full_scan",
        ]

        for method in methods:
            data = subset[
                subset["method"] == method
            ].sort_values(
                "dataset_movies"
            )

            if data.empty:
                continue

            plt.plot(
                data["dataset_movies"],
                data["median_ms"],
                marker="o",
                label=method,
            )

        plt.yscale("log")

        plt.title(
            f"{query.replace('_', ' ').title()} Performance"
        )

        plt.xlabel(
            "Number of movies"
        )

        plt.ylabel(
            "Median query time (ms, log scale)"
        )

        plt.grid(
            True,
            which="both",
            alpha=0.25,
        )

        plt.legend()

        plt.tight_layout()

        output = (
            RESULTS
            / f"{query}_performance.png"
        )

        plt.savefig(
            output,
            dpi=200,
        )

        plt.close()

        print(
            f"Saved plot to {output}"
        )


def plot_speedup(df):

    indexed = df[
        df["method"] == "indexed"
    ][
        [
            "dataset_movies",
            "query",
            "median_ms",
        ]
    ].rename(
        columns={
            "median_ms": "indexed_ms"
        }
    )

    scanned = df[
        df["method"] == "full_scan"
    ][
        [
            "dataset_movies",
            "query",
            "median_ms",
        ]
    ].rename(
        columns={
            "median_ms": "full_scan_ms"
        }
    )

    comparison = indexed.merge(
        scanned,
        on=[
            "dataset_movies",
            "query",
        ],
    )

    comparison["speedup"] = (
        comparison["full_scan_ms"]
        / comparison["indexed_ms"]
    )

    plt.figure(
        figsize=(8, 5)
    )

    for query in sorted(
        comparison["query"].unique()
    ):
        data = comparison[
            comparison["query"] == query
        ].sort_values(
            "dataset_movies"
        )

        plt.plot(
            data["dataset_movies"],
            data["speedup"],
            marker="o",
            label=query.replace(
                "_",
                " ",
            ).title(),
        )

    plt.yscale("log")

    plt.title(
        "Indexed Query Speedup Over Full Scan"
    )

    plt.xlabel(
        "Number of movies"
    )

    plt.ylabel(
        "Speedup factor (log scale)"
    )

    plt.grid(
        True,
        which="both",
        alpha=0.25,
    )

    plt.legend()

    plt.tight_layout()

    output = (
        RESULTS
        / "speedup_comparison.png"
    )

    plt.savefig(
        output,
        dpi=200,
    )

    plt.close()

    print(
        f"Saved plot to {output}"
    )


def main():
    df = load_results()

    print()
    print(
        f"Loaded {len(df)} benchmark rows"
    )

    print(
        f"Dataset sizes: "
        f"{sorted(df['dataset_movies'].unique())}"
    )

    print(
        f"Queries: "
        f"{sorted(df['query'].unique())}"
    )

    create_summary(df)

    print_speedup_table(df)

    print()
    print("===== Generating Plots =====")
    print()

    plot_query_performance(df)

    plot_speedup(df)

    print()
    print("Analysis complete.")


if __name__ == "__main__":
    main()