import random
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.compute import GroupStats, grade_stats, stats_by

RUNTIME = grade_stats._State.runtime
RUNTIME.initialize()
needs_gpu = pytest.mark.skipif(not RUNTIME.ready, reason="nenhum dispositivo OpenCL com fp64 disponível")


@pytest.fixture(autouse=True)
def restore_state():
    saved = (grade_stats._State.enabled, grade_stats._State.min_records)
    yield
    grade_stats._State.enabled, grade_stats._State.min_records = saved


def make_grades(count: int, subjects: int, seed: int = 1) -> list[dict]:
    rng = random.Random(seed)
    start = datetime(2026, 3, 1)
    return [
        {
            "grade": round(rng.uniform(0, 10), 1),
            "subject": f"Disciplina {rng.randrange(subjects)}",
            "attendance": rng.choice([None, True, False]),
            "date": start + timedelta(minutes=rng.randrange(500_000)),
        }
        for _ in range(count)
    ]


def by_subject(grades):
    return stats_by(grades, lambda item: item["subject"], lambda item: item["date"])


def test_python_path_matches_manual_calculation():
    grade_stats._State.enabled = False
    grades = [
        {"grade": 8, "subject": "Matemática", "attendance": True, "date": datetime(2026, 1, 2)},
        {"grade": 6, "subject": "Matemática", "attendance": False, "date": datetime(2026, 1, 5)},
        {"gradeValue": 9, "subject": "Matemática", "date": datetime(2026, 1, 3)},  # sem presença registrada
        {"grade": 5, "subject": "Português", "attendance": 1, "date": None},  # 1 não é True
    ]
    stats = by_subject(grades)
    assert stats["Matemática"] == GroupStats(count=3, total=23.0, recorded=2, attended=1, last=datetime(2026, 1, 5))
    assert stats["Português"] == GroupStats(count=1, total=5.0, recorded=1, attended=0, last=None)
    assert stats["Matemática"].attendance_rate == 50
    assert stats["Matemática"].absences == 1
    assert GroupStats.combine(stats.values()).count == 4
    assert GroupStats().average == 0.0


@needs_gpu
@pytest.mark.parametrize("count,subjects", [(1, 1), (5, 2), (257, 7), (20_000, 50), (100_000, 3)])
def test_opencl_matches_python_path(count, subjects):
    grades = make_grades(count, subjects)
    grade_stats._State.enabled, grade_stats._State.min_records = True, 0
    calls_before = RUNTIME.kernel_calls
    on_gpu = by_subject(grades)
    assert RUNTIME.kernel_calls == calls_before + 1

    grade_stats._State.enabled = False
    on_cpu = by_subject(grades)
    assert on_gpu.keys() == on_cpu.keys()
    for subject, expected in on_cpu.items():
        got = on_gpu[subject]
        assert (got.count, got.recorded, got.attended, got.last) == (expected.count, expected.recorded, expected.attended, expected.last)
        assert got.total == pytest.approx(expected.total, rel=1e-12, abs=1e-9)


@needs_gpu
def test_small_inputs_stay_on_python_below_threshold():
    grade_stats._State.enabled, grade_stats._State.min_records = True, 1_000
    calls_before = RUNTIME.kernel_calls
    by_subject(make_grades(10, 2))
    assert RUNTIME.kernel_calls == calls_before


@needs_gpu
def test_gpu_failure_falls_back_to_python(monkeypatch):
    def broken(*args):
        raise RuntimeError("driver caiu")

    monkeypatch.setattr(RUNTIME, "grade_stats", broken)
    grades = make_grades(50, 3)
    grade_stats._State.enabled, grade_stats._State.min_records = True, 0
    result = by_subject(grades)
    grade_stats._State.enabled = False
    assert result == by_subject(grades)


def test_status_reports_configuration():
    grade_stats.configure(SimpleNamespace(opencl_enabled=False, opencl_min_records=7))
    assert grade_stats.status()["enabled"] is False
    assert grade_stats.status()["active"] is False
    assert grade_stats.status()["minRecords"] == 7
