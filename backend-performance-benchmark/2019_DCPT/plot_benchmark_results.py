"""
Program do tworzenia wykresów na podstawie wyników benchmarków.

Usage:
    python plot_benchmark_results.py
    python plot_benchmark_results.py --input-dir benchmark_results
    python plot_benchmark_results.py --summary-file summary_all_runs_20251210_003508.csv
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# ============================================================================
# CONFIGURATION
# ============================================================================

parser = argparse.ArgumentParser(
    description="Tworzy wykresy na podstawie wyników benchmarków"
)
parser.add_argument(
    "--input-dir",
    type=str,
    default=None,
    help="Katalog z wynikami benchmarków (domyślnie: benchmark_results)",
)
parser.add_argument(
    "--summary-file",
    type=str,
    default=None,
    help="Konkretny plik CSV z wynikami (opcjonalnie, jeśli nie podano, znajdzie najnowszy)",
)
parser.add_argument(
    "--output-dir",
    type=str,
    default=None,
    help="Katalog wyjściowy dla wykresów (domyślnie: plots w katalogu wyników)",
)
parser.add_argument(
    "--backends",
    nargs="+",
    default=None,
    help="Lista backendów do uwzględnienia na wykresach (domyślnie: wszystkie dostępne)",
)
parser.add_argument(
    "--exclude-backends",
    nargs="+",
    default=None,
    help="Lista backendów do wykluczenia z wykresów",
)

args = parser.parse_args()

# Ścieżki
SCRIPT_DIR = Path(__file__).parent

if args.input_dir:
    INPUT_DIR = Path(args.input_dir)
else:
    INPUT_DIR = SCRIPT_DIR / "benchmark_results"

if args.output_dir:
    OUTPUT_DIR = Path(args.output_dir)
else:
    OUTPUT_DIR = INPUT_DIR / "plots"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# LOAD DATA
# ============================================================================

print("=" * 70)
print("TWORZENIE WYKRESÓW Z WYNIKÓW BENCHMARKÓW")
print("=" * 70)

# Znajdź plik z wynikami
if args.summary_file:
    summary_file = Path(args.summary_file)
    if not summary_file.is_absolute():
        summary_file = INPUT_DIR / summary_file
else:
    # Znajdź najnowszy plik summary
    summary_files = list(INPUT_DIR.glob("summary_all_runs_*.csv"))
    if not summary_files:
        print(f"BŁĄD: Nie znaleziono plików summary_all_runs_*.csv w {INPUT_DIR}")
        exit(1)
    summary_file = max(summary_files, key=lambda p: p.stat().st_mtime)
    print(f"Używam najnowszego pliku: {summary_file.name}")

print(f"Wczytuję dane z: {summary_file}")

# Wczytaj dane
summary_df = pd.read_csv(summary_file)
print(f"Wczytano {len(summary_df)} rekordów")

# Filtruj tylko udane uruchomienia
successful_df = summary_df[summary_df["status"] == "success"].copy()
print(f"Udane uruchomienia: {len(successful_df)}")

# Wyświetl dostępne backendy
available_backends = successful_df["backend"].unique()
print(f"Dostępne backendy: {', '.join(available_backends)}")

# Filtruj backendy zgodnie z argumentami
if args.backends:
    # Uwzględnij tylko wybrane backendy
    selected_backends = [b.lower() for b in args.backends]
    successful_df = successful_df[
        successful_df["backend"].str.lower().isin(selected_backends)
    ].copy()
    print(f"Wybrane backendy: {', '.join(selected_backends)}")

    # Sprawdź, które wybrane backendy mają wyniki
    found_backends = successful_df["backend"].unique()
    missing_backends = set(selected_backends) - set(b.lower() for b in found_backends)
    if missing_backends:
        print(
            f"⚠ OSTRZEŻENIE: Następujące backendy nie mają wyników: {', '.join(missing_backends)}"
        )
        print("   Będą pominięte na wykresach.")

if args.exclude_backends:
    # Wyklucz wybrane backendy
    excluded_backends = [b.lower() for b in args.exclude_backends]
    successful_df = successful_df[
        ~successful_df["backend"].str.lower().isin(excluded_backends)
    ].copy()
    print(f"Wykluczone backendy: {', '.join(excluded_backends)}")

if len(successful_df) == 0:
    print("BŁĄD: Brak udanych uruchomień do wizualizacji po zastosowaniu filtrów")
    print(f"   Dostępne backendy: {', '.join(available_backends)}")
    exit(1)

# Wyświetl finalne backendy do wizualizacji
final_backends = successful_df["backend"].unique()
print(f"Backendy do wizualizacji: {', '.join(final_backends)}")

# ============================================================================
# PLOT STYLE
# ============================================================================

sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 100
plt.rcParams["font.size"] = 10
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["xtick.labelsize"] = 10
plt.rcParams["ytick.labelsize"] = 10
plt.rcParams["legend.fontsize"] = 10

# Kolory dla backendów
colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12"]

# ============================================================================
# PLOT 1 & 2: Czas wykonania - porównanie średnich i rozkład (obok siebie)
# ============================================================================

print("\nTworzenie wykresu 1-2: Czas wykonania (porównanie średnich i rozkład)...")

# Przygotuj dane dla obu wykresów
backends = successful_df["backend"].unique()
means = []
stds = []
valid_backends = []
data_for_box = []
labels = []

for backend in backends:
    backend_data = successful_df[successful_df["backend"] == backend][
        "elapsed_time_seconds"
    ]
    if len(backend_data) > 0:
        means.append(backend_data.mean())
        stds.append(backend_data.std())
        valid_backends.append(backend)
        data_for_box.append(backend_data.values)
        labels.append(backend.upper())

if len(valid_backends) == 0:
    print("  ⚠ Pomijam wykres - brak danych")
    skip_plot_exec_time = True
else:
    skip_plot_exec_time = False
    backends = valid_backends

if not skip_plot_exec_time:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Wykres 1a: Średni czas wykonania z błędami (bar chart)
    x_pos = np.arange(len(backends))
    width = 0.6

    bars = ax1.bar(
        x_pos,
        means,
        width,
        yerr=stds,
        capsize=10,
        alpha=0.7,
        color=colors[: len(backends)],
        label="Mean ± std. dev.",
    )

    # Dodaj wartości na słupkach - umieść je nad error bars
    for i, (bar, mean, std) in enumerate(zip(bars, means, stds)):
        height = bar.get_height()
        # Umieść tekst nad error bar (height + std + mały margines)
        text_y = (
            height + std + max(20, height * 0.02)
        )  # Dynamiczny margines zależny od wysokości
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            text_y,
            f"{mean:.1f}±{std:.1f}s",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax1.set_ylabel("Execution Time [seconds]", fontsize=12)
    ax1.set_xlabel("Backend", fontsize=12)
    ax1.set_title("Mean Execution Time with Standard Deviation", fontsize=13)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([b.upper() for b in backends])
    ax1.grid(True, alpha=0.3, axis="y")

    # Wykres 1b: Rozkład czasów wykonania (boxplot)
    bp = ax2.boxplot(data_for_box, tick_labels=labels, patch_artist=True)

    # Koloruj boxy
    for patch, color in zip(bp["boxes"], colors[: len(bp["boxes"])]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Ukryj medianę (pomarańczową linię)
    for median in bp["medians"]:
        median.set_visible(False)

    # Dodaj wartości wariancji (odchylenie standardowe) nad każdym boxem - w stylu jak na innych wykresach
    for i, (data, label) in enumerate(zip(data_for_box, labels)):
        mean_val = np.mean(data)
        std_val = np.std(data)
        max_val = np.max(data)
        min_val = np.min(data)
        # Umieść tekst nad boxem (max_val + margines)
        text_y = max_val + (max_val - min_val) * 0.1
        ax2.text(
            i + 1,
            text_y,
            f"{mean_val:.1f}±{std_val:.1f}s",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    # Dodaj legendę wyjaśniającą elementy boxplotu
    from matplotlib.lines import Line2D

    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="w",
            markeredgecolor="black",
            markersize=8,
            linestyle="None",
            label="Outliers",
        ),
    ]
    ax2.legend(handles=legend_elements, loc="upper right", fontsize=10)

    ax2.set_ylabel("Execution Time [seconds]", fontsize=12)
    ax2.set_xlabel("Backend", fontsize=12)
    ax2.set_title("Execution Time Distribution for Different Backends", fontsize=13)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "execution_time_comparison.png", dpi=300, bbox_inches="tight")
    print("  Zapisano: execution_time_comparison.png")

# ============================================================================
# PLOT 3: Czas wykonania w czasie (dla każdego run)
# ============================================================================

print("\nTworzenie wykresu 3: Czas wykonania dla każdego run...")

fig, ax = plt.subplots(figsize=(12, 6))

has_data = False
# Sprawdź liczbę unikalnych runów
unique_runs = successful_df["run_number"].nunique() if len(successful_df) > 0 else 0
show_values = unique_runs < 20

for backend in successful_df["backend"].unique():
    backend_data = successful_df[successful_df["backend"] == backend].sort_values(
        "run_number"
    )
    if len(backend_data) > 0:
        ax.plot(
            backend_data["run_number"],
            backend_data["elapsed_time_seconds"],
            "o-",
            label=backend.upper(),
            markersize=8,
            linewidth=2,
            alpha=0.7,
        )
        # Dodaj wartości nad punktami jeśli jest mniej niż 20 runów
        if show_values:
            for _, row in backend_data.iterrows():
                ax.text(
                    row["run_number"],
                    row["elapsed_time_seconds"],
                    f"{row['elapsed_time_seconds']:.1f}s",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    fontweight="bold",
                )
        has_data = True

if not has_data:
    print("  ⚠ Pomijam wykres - brak danych")
    skip_plot3 = True
else:
    skip_plot3 = False

if not skip_plot3:
    ax.set_xlabel("Run Number", fontsize=12)
    ax.set_ylabel("Execution Time [seconds]", fontsize=12)
    ax.set_title("Execution Time for Consecutive Runs", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    if len(successful_df) > 0:
        ax.set_xticks(successful_df["run_number"].unique())

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "execution_time_runs.png", dpi=300, bbox_inches="tight")
    print("  Zapisano: execution_time_runs.png")

# ============================================================================
# PLOT 4: Stosunek czasów (speedup)
# ============================================================================

print("\nTworzenie wykresu 4: Stosunek czasów (speedup)...")

# Znajdź najwolniejszy backend jako referencję
slowest_backend = (
    successful_df.groupby("backend")["elapsed_time_seconds"].mean().idxmax()
)
slowest_mean = successful_df[successful_df["backend"] == slowest_backend][
    "elapsed_time_seconds"
].mean()

fig, ax = plt.subplots(figsize=(10, 6))

speedups = []
speedup_stds = []
labels_speedup = []

for backend in successful_df["backend"].unique():
    backend_data = successful_df[successful_df["backend"] == backend][
        "elapsed_time_seconds"
    ]
    speedup = slowest_mean / backend_data.mean()
    speedup_std = speedup * (backend_data.std() / backend_data.mean())
    speedups.append(speedup)
    speedup_stds.append(speedup_std)
    labels_speedup.append(backend.upper())

if len(speedups) > 0:
    x_pos = np.arange(len(labels_speedup))
    bars = ax.bar(
        x_pos,
        speedups,
        width=0.6,
        yerr=speedup_stds,
        capsize=10,
        alpha=0.7,
        color=colors[: len(labels_speedup)],
    )

    # Dodaj wartości na słupkach - umieść je nad error bars
    for bar, speedup, speedup_std in zip(bars, speedups, speedup_stds):
        height = bar.get_height()
        # Umieść tekst nad error bar (height + std + mały margines)
        text_y = height + speedup_std + 0.1
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            text_y,
            f"{speedup:.2f}x",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )

    # Linia referencyjna pokazuje baseline (1.0x = najwolniejszy backend)
    ax.axhline(
        y=1.0,
        color="k",
        linestyle="--",
        linewidth=1,
        alpha=0.5,
        label=f"Baseline ({slowest_backend.upper()})",
    )
    ax.set_ylabel("Speedup (relative to slowest)", fontsize=12)
    ax.set_xlabel("Backend", fontsize=12)
    ax.set_title(
        f"Speedup Relative to {slowest_backend.upper()} (baseline = 1.0x)", fontsize=14
    )
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels_speedup)
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "speedup_comparison.png", dpi=300, bbox_inches="tight")
    print("  Zapisano: speedup_comparison.png")

# ============================================================================
# PLOT 5: Błędy obliczeń (jeśli dostępne)
# ============================================================================

if "continuous_mean_error_%" in successful_df.columns:
    print("\nTworzenie wykresu 5: Błędy obliczeń...")

    # Sprawdź, które backendy mają dane o błędach
    backends_with_errors = []
    for backend in successful_df["backend"].unique():
        backend_errors = successful_df[successful_df["backend"] == backend][
            "continuous_mean_error_%"
        ]
        if len(backend_errors) > 0 and not backend_errors.isna().all():
            backends_with_errors.append(backend)

    if len(backends_with_errors) == 0:
        print("  ⚠ Pomijam wykres - brak danych o błędach")
    else:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Wykres 5a: Średni błąd
        backends = backends_with_errors
        mean_errors = []
        std_errors = []

        for backend in backends:
            backend_data = successful_df[successful_df["backend"] == backend][
                "continuous_mean_error_%"
            ]
            valid_data = backend_data.dropna()
            if len(valid_data) > 0:
                mean_errors.append(valid_data.mean())
                std_errors.append(valid_data.std())
            else:
                mean_errors.append(0)
                std_errors.append(0)

        if len(mean_errors) > 0:
            x_pos = np.arange(len(backends))
            bars1 = ax1.bar(
                x_pos,
                mean_errors,
                width=0.6,
                yerr=std_errors,
                capsize=10,
                alpha=0.7,
                color=colors[: len(backends)],
            )

            for bar, mean, std in zip(bars1, mean_errors, std_errors):
                height = bar.get_height()
                ax1.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + std + std * 0.5,
                    f"{mean:.3f}±{std:.3f}%",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                    fontweight="bold",
                )

            ax1.set_ylabel("Mean Relative Error [%]", fontsize=12)
            ax1.set_xlabel("Backend", fontsize=12)
            ax1.set_title("Mean Relative Error of Calculations", fontsize=13)
            ax1.set_xticks(x_pos)
            ax1.set_xticklabels([b.upper() for b in backends])
            ax1.grid(True, alpha=0.3, axis="y")

            # Wykres 5b: Rozkład błędów (boxplot)
            error_data = []
            error_labels = []
            for backend in backends:
                backend_errors = successful_df[successful_df["backend"] == backend][
                    "continuous_mean_error_%"
                ]
                valid_errors = backend_errors.dropna()
                if len(valid_errors) > 0:
                    error_data.append(valid_errors.values)
                    error_labels.append(backend.upper())

            if len(error_data) > 0:
                bp = ax2.boxplot(
                    error_data, tick_labels=error_labels, patch_artist=True
                )
                for patch, color in zip(bp["boxes"], colors[: len(bp["boxes"])]):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)

                # Ukryj medianę
                for median in bp["medians"]:
                    median.set_visible(False)

                # Dodaj wariancję (odchylenie standardowe) nad każdym boxem - w stylu jak na innych wykresach
                for i, (data, label) in enumerate(zip(error_data, error_labels)):
                    mean_val = np.mean(data)
                    std_val = np.std(data)
                    max_val = np.max(data)
                    min_val = np.min(data)
                    # Umieść tekst nad boxem (max_val + margines)
                    text_y = max_val + (max_val - min_val) * 0.1
                    ax2.text(
                        i + 1,
                        text_y,
                        f"{mean_val:.3f}±{std_val:.3f}%",
                        ha="center",
                        va="bottom",
                        fontsize=10,
                        fontweight="bold",
                    )

                ax2.set_ylabel("Relative Error [%]", fontsize=12)
                ax2.set_xlabel("Backend", fontsize=12)
                ax2.set_title("Relative Error Distribution", fontsize=13)
                ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(
                OUTPUT_DIR / "error_comparison.png", dpi=300, bbox_inches="tight"
            )
            print("  Zapisano: error_comparison.png")

# ============================================================================
# PLOT 6: Statystyki zbiorcze (tabela wizualna)
# ============================================================================

print("\nTworzenie wykresu 6: Statystyki zbiorcze...")

# Przygotuj dane do tabeli
stats_data = []
for backend in successful_df["backend"].unique():
    backend_data = successful_df[successful_df["backend"] == backend][
        "elapsed_time_seconds"
    ]
    if len(backend_data) > 0:
        stats_data.append(
            {
                "Backend": backend.upper(),
                "Mean [s]": f"{backend_data.mean():.2f}",
                "Standard Deviation [s]": f"{backend_data.std():.2f}",
                "Minimum [s]": f"{backend_data.min():.2f}",
                "Maximum [s]": f"{backend_data.max():.2f}",
                "Number of Runs": len(backend_data),
            }
        )

if "continuous_mean_error_%" in successful_df.columns:
    for i, backend in enumerate(successful_df["backend"].unique()):
        backend_data = successful_df[successful_df["backend"] == backend][
            "elapsed_time_seconds"
        ]
        if len(backend_data) > 0:
            # Znajdź odpowiedni indeks w stats_data
            backend_idx = next(
                (
                    j
                    for j, stat in enumerate(stats_data)
                    if stat["Backend"] == backend.upper()
                ),
                None,
            )
            if backend_idx is not None:
                backend_errors = successful_df[successful_df["backend"] == backend][
                    "continuous_mean_error_%"
                ]
                valid_errors = backend_errors.dropna()
                if len(valid_errors) > 0:
                    stats_data[backend_idx][
                        "Mean Relative Error [%]"
                    ] = f"{valid_errors.mean():.3f}"
                    stats_data[backend_idx][
                        "Standard Deviation Error [%]"
                    ] = f"{valid_errors.std():.3f}"
                else:
                    stats_data[backend_idx]["Mean Error [%]"] = "N/A"
                    stats_data[backend_idx]["Std Error [%]"] = "N/A"

stats_df = pd.DataFrame(stats_data)


# Funkcja do łamania długich nazw kolumn na wiele linii
def wrap_column_labels(columns, max_words_per_line=2):
    """Łamie długie nazwy kolumn na wiele linii."""
    wrapped_columns = []
    for col in columns:
        words = col.split()
        if len(words) > max_words_per_line:
            # Podziel na linie po max_words_per_line słów
            lines = []
            for i in range(0, len(words), max_words_per_line):
                lines.append(" ".join(words[i : i + max_words_per_line]))
            wrapped_columns.append("\n".join(lines))
        else:
            wrapped_columns.append(col)
    return wrapped_columns


# Utwórz tabelę jako obraz
fig, ax = plt.subplots(figsize=(14, max(4, len(stats_df) * 0.5 + 1)))
ax.axis("tight")
ax.axis("off")

# Przygotuj etykiety kolumn z łamaniem linii
wrapped_col_labels = wrap_column_labels(stats_df.columns, max_words_per_line=2)

table = ax.table(
    cellText=stats_df.values,
    colLabels=wrapped_col_labels,
    cellLoc="center",
    loc="center",
    bbox=[0, 0, 1, 1],
)

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2.2)  # Zwiększ wysokość, żeby pomieścić wieloliniowe nagłówki

# Koloruj nagłówki
for i in range(len(stats_df.columns)):
    table[(0, i)].set_facecolor("#4CAF50")
    table[(0, i)].set_text_props(weight="bold", color="white")

# Koloruj wiersze na przemian
for i in range(1, len(stats_df) + 1):
    for j in range(len(stats_df.columns)):
        if i % 2 == 0:
            table[(i, j)].set_facecolor("#f0f0f0")

plt.title("Benchmark Summary Statistics", fontsize=14, fontweight="bold", pad=20)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "summary_statistics.png", dpi=300, bbox_inches="tight")
print("  Zapisano: summary_statistics.png")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("WYKRESY ZAPISANE")
print("=" * 70)
print(f"Wszystkie wykresy zapisane w: {OUTPUT_DIR}")
print("\nUtworzone pliki:")
for plot_file in sorted(OUTPUT_DIR.glob("*.png")):
    print(f"  - {plot_file.name}")

print("\n" + "=" * 70)
