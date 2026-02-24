"""
Skrypt do uruchamiania testów eksperymentalnych dla różnych backendów
wielokrotnie i zbierania wyników oraz czasów wykonania.

Usage:
    python run_benchmark.py --runs 3
    python run_benchmark.py --runs 5 --backends cython numba
"""

import argparse
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
import pandas as pd
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

parser = argparse.ArgumentParser(
    description="Uruchamia testy eksperymentalne dla różnych backendów wielokrotnie"
)
parser.add_argument(
    "--runs",
    type=int,
    default=3,
    help="Liczba uruchomień dla każdego backendu (domyślnie: 3)",
)
parser.add_argument(
    "--backends",
    nargs="+",
    default=["cython", "numba"],
    choices=["cython", "numba"],
    help="Lista backendów do przetestowania (domyślnie: cython numba)",
)
parser.add_argument(
    "--base-output-dir",
    type=str,
    default=None,
    help="Bazowy katalog wyjściowy (domyślnie: benchmark_results w katalogu skryptu)",
)

args = parser.parse_args()

# Ścieżki
SCRIPT_DIR = Path(__file__).parent
TEST_SCRIPT = SCRIPT_DIR / "test_experimental_data.py"

if args.base_output_dir:
    BASE_OUTPUT_DIR = Path(args.base_output_dir)
else:
    BASE_OUTPUT_DIR = SCRIPT_DIR / "benchmark_results"

BASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# FUNCTIONS
# ============================================================================


def run_test(backend: str, run_number: int, timeout: float = None) -> dict:
    """
    Uruchamia test_experimental_data.py dla danego backendu i zwraca wyniki.
    
    Args:
        backend: Backend do użycia ('cython', 'numba')
        run_number: Numer uruchomienia (dla organizacji folderów)
        timeout: Maksymalny czas wykonania w sekundach (None = brak limitu)
    
    Returns:
        Słownik z wynikami: czas wykonania, status, ścieżka do wyników
    """
    print(f"\n{'='*70}")
    print(f"Uruchamianie: {backend} - Run {run_number}")
    if timeout:
        print(f"Timeout: {timeout:.2f} sekund (2x max(cython, numba))")
    print(f"{'='*70}")
    
    # Utwórz folder dla tego uruchomienia
    run_output_dir = BASE_OUTPUT_DIR / backend / f"run_{run_number:03d}"
    run_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Przygotuj komendę
    # Flaga -u wymusza unbuffered output w Pythonie (ważne dla logów w czasie rzeczywistym)
    cmd = [
        sys.executable,
        "-u",  # Unbuffered stdout/stderr
        str(TEST_SCRIPT),
        "--backend",
        backend,
        "--output-dir",
        str(run_output_dir),
    ]
    
    # Uruchom test i zmierz czas
    start_time = time.time()
    timeout_occurred = False
    stdout_lines = []
    stderr_lines = []
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ▶ Rozpoczynam obliczenia...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Komenda: {' '.join(cmd)}")
    if timeout:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏱  Limit czasu: {timeout:.2f} sekund")
    
    try:
        # Użyj Popen zamiast run, żeby móc wyświetlać output w czasie rzeczywistym
        # Na Windows używamy unbuffered (bufsize=0) dla lepszej responsywności
        import platform
        import os
        if platform.system() == 'Windows':
            bufsize = 0  # Unbuffered na Windows
            # Ustaw zmienne środowiskowe dla unbuffered output w Pythonie
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
        else:
            bufsize = 1  # Line buffered na Unix
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=bufsize,
            cwd=SCRIPT_DIR,
            universal_newlines=True,  # Dla kompatybilności
            env=env,  # Przekaż zmienne środowiskowe
        )
        
        # Funkcja do wyświetlania linii w czasie rzeczywistym
        def log_line(prefix, line, is_error=False):
            if line.strip():
                timestamp = datetime.now().strftime('%H:%M:%S')
                elapsed = time.time() - start_time
                if is_error:
                    print(f"[{timestamp}] [{elapsed:6.1f}s] {prefix}⚠ ERR: {line.rstrip()}", flush=True)
                else:
                    print(f"[{timestamp}] [{elapsed:6.1f}s] {prefix}{line.rstrip()}", flush=True)
        
        # Czytaj output w czasie rzeczywistym używając wątków
        def read_output(pipe, prefix, is_error=False, output_list=None):
            try:
                # Czytaj linia po linii - readline() powinien działać z unbuffered mode
                while True:
                    line = pipe.readline()
                    if not line:  # EOF
                        break
                    # Zapisz do listy jeśli potrzebne
                    if output_list is not None:
                        output_list.append(line)
                    # Wyświetl natychmiast
                    log_line(prefix, line, is_error)
            except Exception as e:
                error_msg = f"Error reading output: {e}\n"
                if output_list is not None:
                    output_list.append(error_msg)
                log_line(prefix, error_msg, is_error)
            finally:
                try:
                    pipe.close()
                except:
                    pass
        
        # Uruchom wątki do czytania stdout i stderr
        stdout_thread = threading.Thread(
            target=read_output,
            args=(process.stdout, f"[{backend.upper()}] ", False, stdout_lines),
            daemon=True
        )
        stderr_thread = threading.Thread(
            target=read_output,
            args=(process.stderr, f"[{backend.upper()}] ", True, stderr_lines),
            daemon=True
        )
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Czekaj na zakończenie procesu z timeoutem
        if timeout:
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ TIMEOUT! Przekroczono limit czasu ({timeout:.2f} sekund)")
                process.kill()
                process.wait()
                timeout_occurred = True
        else:
            process.wait()
        
        # Poczekaj aż wątki skończą czytać (max 2 sekundy)
        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)
        
        elapsed_time = time.time() - start_time
        
        # Utwórz obiekt result
        result = type('obj', (object,), {
            'returncode': process.returncode,
            'stdout': ''.join(stdout_lines),
            'stderr': ''.join(stderr_lines)
        })()
        
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        timeout_occurred = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ TIMEOUT! Przekroczono limit czasu ({timeout:.2f} sekund)")
        # Zabij proces jeśli jeszcze działa
        result = type('obj', (object,), {
            'returncode': -1,
            'stdout': ''.join(stdout_lines),
            'stderr': f'Timeout after {timeout:.2f} seconds (exceeded 2x efficiency requirement)'
        })()
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ BŁĄD podczas uruchamiania: {e}")
        result = type('obj', (object,), {
            'returncode': -1,
            'stdout': ''.join(stdout_lines),
            'stderr': str(e)
        })()
    
    elapsed_time = time.time() - start_time
    status_icon = "✓" if result.returncode == 0 and not timeout_occurred else "✗"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_icon} Zakończono w {elapsed_time:.2f} sekund (kod: {result.returncode})")
    
    # Zapisz output do pliku
    log_file = run_output_dir / "run_log.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Command: {' '.join(cmd)}\n")
        f.write(f"Return code: {result.returncode}\n")
        f.write(f"Elapsed time: {elapsed_time:.2f} seconds\n")
        if timeout:
            f.write(f"Timeout limit: {timeout:.2f} seconds\n")
        if timeout_occurred:
            f.write(f"TIMEOUT: Exceeded efficiency requirement (2x max(cython, numba))\n")
        f.write("\n")
        f.write("=" * 70 + "\n")
        f.write("STDOUT:\n")
        f.write("=" * 70 + "\n")
        f.write(result.stdout)
        f.write("\n" + "=" * 70 + "\n")
        f.write("STDERR:\n")
        f.write("=" * 70 + "\n")
        f.write(result.stderr)
    
    # Określ status
    if timeout_occurred:
        status = "efficiency_failed"
        status_message = "Przekroczono limit efektywności (2x max(cython, numba))"
    elif result.returncode == 0:
        status = "success"
        status_message = None
    else:
        status = "failed"
        status_message = None
    
    # Sprawdź czy są pliki wynikowe (tylko jeśli nie było timeoutu)
    results_data = {}
    if not timeout_occurred:
        comparison_initial = run_output_dir / "comparison_initial.csv"
        comparison_continuous = run_output_dir / "comparison_continuous.csv"
        
        # Wczytaj wyniki jeśli istnieją
        if comparison_initial.exists():
            try:
                df_initial = pd.read_csv(comparison_initial)
                results_data["initial_mean_error_%"] = df_initial["relative_error_%"].mean()
                results_data["initial_max_error_%"] = df_initial["relative_error_%"].max()
                results_data["initial_min_error_%"] = df_initial["relative_error_%"].min()
            except Exception as e:
                print(f"  Błąd przy wczytywaniu comparison_initial.csv: {e}")
        
        if comparison_continuous.exists():
            try:
                df_continuous = pd.read_csv(comparison_continuous)
                results_data["continuous_mean_error_%"] = df_continuous["relative_error_%"].mean()
                results_data["continuous_median_error_%"] = df_continuous["relative_error_%"].median()
                results_data["continuous_max_error_%"] = df_continuous["relative_error_%"].max()
                results_data["continuous_min_error_%"] = df_continuous["relative_error_%"].min()
                results_data["continuous_std_error_%"] = df_continuous["relative_error_%"].std()
                results_data["continuous_successful_calculations"] = len(df_continuous)
            except Exception as e:
                print(f"  Błąd przy wczytywaniu comparison_continuous.csv: {e}")
    
    result_dict = {
        "backend": backend,
        "run_number": run_number,
        "status": status,
        "elapsed_time_seconds": elapsed_time,
        "return_code": result.returncode,
        "output_dir": str(run_output_dir),
        **results_data,
    }
    
    if timeout_occurred:
        result_dict["timeout_limit"] = timeout
        result_dict["efficiency_requirement_failed"] = True
    
    return result_dict


def create_summary(all_results: list) -> pd.DataFrame:
    """
    Tworzy zestawienie wyników wszystkich uruchomień.
    """
    summary_data = []
    
    for result in all_results:
        summary_data.append(result)
    
    summary_df = pd.DataFrame(summary_data)
    return summary_df


def create_statistics_summary(summary_df: pd.DataFrame) -> pd.DataFrame:
    """
    Tworzy statystyki zbiorcze dla każdego backendu.
    """
    stats_list = []
    
    for backend in summary_df["backend"].unique():
        backend_data = summary_df[summary_df["backend"] == backend]
        successful_runs = backend_data[backend_data["status"] == "success"]
        efficiency_failed = backend_data[backend_data["status"] == "efficiency_failed"]
        failed_runs = backend_data[backend_data["status"] == "failed"]
        error_runs = backend_data[backend_data["status"] == "error"]
        
        stats = {
            "backend": backend,
            "total_runs": len(backend_data),
            "successful_runs": len(successful_runs),
            "efficiency_failed_runs": len(efficiency_failed),
            "failed_runs": len(failed_runs),
            "error_runs": len(error_runs),
        }
        
        if len(successful_runs) > 0:
            stats["mean_time_seconds"] = successful_runs["elapsed_time_seconds"].mean()
            stats["std_time_seconds"] = successful_runs["elapsed_time_seconds"].std()
            stats["min_time_seconds"] = successful_runs["elapsed_time_seconds"].min()
            stats["max_time_seconds"] = successful_runs["elapsed_time_seconds"].max()
            
            # Dodaj statystyki błędów jeśli są dostępne
            if "continuous_mean_error_%" in successful_runs.columns:
                stats["mean_continuous_error_%"] = successful_runs["continuous_mean_error_%"].mean()
                stats["std_continuous_error_%"] = successful_runs["continuous_mean_error_%"].std()
            
            if "initial_mean_error_%" in successful_runs.columns:
                stats["mean_initial_error_%"] = successful_runs["initial_mean_error_%"].mean()
        else:
            stats["mean_time_seconds"] = None
            stats["std_time_seconds"] = None
            stats["min_time_seconds"] = None
            stats["max_time_seconds"] = None
        
        # Dodaj informacje o efficiency_failed jeśli są
        if len(efficiency_failed) > 0:
            stats["efficiency_failed_mean_time"] = efficiency_failed["elapsed_time_seconds"].mean()
            stats["efficiency_failed_max_time"] = efficiency_failed["elapsed_time_seconds"].max()
        
        stats_list.append(stats)
    
    return pd.DataFrame(stats_list)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 70)
    print("BENCHMARK TESTÓW EKSPERYMENTALNYCH")
    print("=" * 70)
    print(f"Backendy: {', '.join(args.backends)}")
    print(f"Liczba uruchomień na backend: {args.runs}")
    print(f"Katalog wyjściowy: {BASE_OUTPUT_DIR}")
    print(f"Data rozpoczęcia: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = []
    
    # Uruchom testy dla każdego backendu
    total_runs = len(args.backends) * args.runs
    current_run = 0
    
    for backend in args.backends:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 Backend: {backend.upper()}")
        for run_num in range(1, args.runs + 1):
            current_run += 1
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 Postęp: {current_run}/{total_runs} uruchomień")
            result = run_test(backend, run_num)
            all_results.append(result)
            
            if result["status"] == "success":
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {backend} Run {run_num}: {result['elapsed_time_seconds']:.2f} sekund - SUKCES")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {backend} Run {run_num}: BŁĄD")
    
    # Utwórz zestawienia
    print("\n" + "=" * 70)
    print("TWORZENIE ZESTAWIENIA WYNIKÓW")
    print("=" * 70)
    
    summary_df = create_summary(all_results)
    stats_df = create_statistics_summary(summary_df)
    
    # Zapisz wyniki
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Pełne zestawienie
    summary_file = BASE_OUTPUT_DIR / f"summary_all_runs_{timestamp}.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"✓ Zapisano pełne zestawienie: {summary_file}")
    
    # Statystyki zbiorcze
    stats_file = BASE_OUTPUT_DIR / f"statistics_summary_{timestamp}.csv"
    stats_df.to_csv(stats_file, index=False)
    print(f"✓ Zapisano statystyki: {stats_file}")
    
    # JSON z metadanymi
    metadata = {
        "timestamp": timestamp,
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "backends": args.backends,
        "runs_per_backend": args.runs,
        "total_runs": len(all_results),
        "base_output_dir": str(BASE_OUTPUT_DIR),
    }
    metadata_file = BASE_OUTPUT_DIR / f"metadata_{timestamp}.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Zapisano metadane: {metadata_file}")
    
    # Wyświetl podsumowanie
    print("\n" + "=" * 70)
    print("PODSUMOWANIE")
    print("=" * 70)
    print("\nStatystyki czasów wykonania:")
    display_cols = ["backend", "mean_time_seconds", "std_time_seconds", 
                    "min_time_seconds", "max_time_seconds", 
                    "successful_runs", "total_runs"]
    available_cols = [col for col in display_cols if col in stats_df.columns]
    print(stats_df[available_cols].to_string(index=False))
    
    if "mean_continuous_error_%" in stats_df.columns:
        print("\nStatystyki błędów (continuous beam):")
        error_cols = ["backend", "mean_continuous_error_%", "std_continuous_error_%"]
        available_error_cols = [col for col in error_cols if col in stats_df.columns]
        if available_error_cols:
            print(stats_df[available_error_cols].to_string(index=False))
    
    print(f"\nWszystkie wyniki zapisane w: {BASE_OUTPUT_DIR}")
    print(f"Data zakończenia: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()

