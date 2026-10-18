"""Compara o cálculo de estatísticas de notas em Python x OpenCL (GPU) por tamanho de entrada.

    python scripts/benchmark_opencl.py

Mostra também onde a GPU passa a compensar, para escolher OPENCL_MIN_RECORDS. O tempo da GPU inclui
tudo o que a API paga: montar os arrays, copiar para o dispositivo, executar o kernel e ler o resultado.
"""
from __future__ import annotations

import random
import statistics
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.compute import grade_stats, stats_by  # noqa: E402


def make_grades(count: int, groups: int) -> list[dict]:
    rng = random.Random(42)
    start = datetime(2026, 3, 1)
    return [
        {
            "grade": round(rng.uniform(0, 10), 1),
            "studentId": str(rng.randrange(groups)),
            "attendance": rng.choice([None, True, False]),
            "date": start + timedelta(minutes=rng.randrange(500_000)),
        }
        for _ in range(count)
    ]


def median_ms(fn, runs: int) -> float:
    fn()
    times = []
    for _ in range(runs):
        started = time.perf_counter()
        fn()
        times.append((time.perf_counter() - started) * 1000)
    return statistics.median(times)


def main() -> None:
    grade_stats.configure(SimpleNamespace(opencl_enabled=True, opencl_min_records=0, opencl_device=""))
    state = grade_stats.status()
    print(f"Dispositivo OpenCL: {state['device'] or 'indisponível'}  ({state['error'] or 'ok'})\n")
    print(f"{'registros':>10} {'grupos':>7} {'Python (ms)':>12} {'OpenCL (ms)':>12} {'razão':>8}")
    for count, groups in [(100, 10), (1_000, 30), (10_000, 100), (100_000, 500), (1_000_000, 2_000)]:
        grades = make_grades(count, groups)
        key, stamp = (lambda item: item["studentId"]), (lambda item: item["date"])
        runs = 5 if count <= 100_000 else 3
        grade_stats._State.enabled = False
        python_ms = median_ms(lambda: stats_by(grades, key, stamp), runs)
        grade_stats._State.enabled = True
        opencl_ms = median_ms(lambda: stats_by(grades, key, stamp), runs) if state["active"] else float("nan")
        print(f"{count:>10,} {groups:>7,} {python_ms:>12.2f} {opencl_ms:>12.2f} {python_ms / opencl_ms:>7.2f}x")


if __name__ == "__main__":
    main()
