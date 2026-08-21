from __future__ import annotations

from app.services.curriculum import curriculum_subjects_for_grade, normalize_curriculum_key


def test_fundamental_curriculum_does_not_include_high_school_subjects():
    subjects = curriculum_subjects_for_grade("6º Ano do Ensino Fundamental")

    assert "Língua Portuguesa" in subjects
    assert "Matemática" in subjects
    assert "Ciências" in subjects
    assert "Física" not in subjects
    assert "Química" not in subjects
    assert "Álgebra" not in subjects
    assert "Geometria" not in subjects


def test_high_school_curriculum_includes_science_and_math_specializations():
    subjects = curriculum_subjects_for_grade("2º Ano do Ensino Médio")

    assert "Biologia" in subjects
    assert "Física" in subjects
    assert "Química" in subjects
    assert "Álgebra" in subjects
    assert "Geometria" in subjects


def test_curriculum_accepts_accent_and_spacing_variations():
    first = curriculum_subjects_for_grade("9º Ano do Ensino Fundamental")
    second = curriculum_subjects_for_grade("  9o   ano do ensino fundamental ")

    assert first == second
    assert normalize_curriculum_key("Matemática") == normalize_curriculum_key("Matematica")
