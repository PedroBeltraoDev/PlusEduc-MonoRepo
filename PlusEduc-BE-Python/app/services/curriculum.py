from __future__ import annotations

import re
import unicodedata


FUNDAMENTAL_SUBJECTS = [
    "Língua Portuguesa",
    "Matemática",
    "Ciências",
    "História",
    "Geografia",
    "Arte",
    "Educação Física",
    "Língua Inglesa",
]

MEDIO_SUBJECTS = [
    "Língua Portuguesa",
    "Matemática",
    "Língua Inglesa",
    "História",
    "Geografia",
    "Sociologia",
    "Filosofia",
    "Biologia",
    "Física",
    "Química",
    "Arte",
    "Educação Física",
    "Álgebra",
    "Geometria",
]

SUBJECT_AREAS = {
    "Língua Portuguesa": "Linguagens",
    "Língua Inglesa": "Linguagens",
    "Arte": "Linguagens",
    "Educação Física": "Linguagens",
    "Matemática": "Matemática",
    "Álgebra": "Matemática",
    "Geometria": "Matemática",
    "Ciências": "Ciências da Natureza",
    "Biologia": "Ciências da Natureza",
    "Física": "Ciências da Natureza",
    "Química": "Ciências da Natureza",
    "História": "Ciências Humanas",
    "Geografia": "Ciências Humanas",
    "Sociologia": "Ciências Humanas",
    "Filosofia": "Ciências Humanas",
}


def normalize_curriculum_key(value: str) -> str:
    folded = " ".join(str(value or "").strip().split()).casefold()
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", folded)
        if not unicodedata.combining(character)
    )


def school_stage_and_year(grade_level: str) -> tuple[str, int] | None:
    normalized = normalize_curriculum_key(grade_level)
    match = re.search(r"(?:^|\s)([1-9])\s*(?:º|°|o)?\s*ano", normalized)
    if not match:
        return None
    year = int(match.group(1))
    if "medio" in normalized or "médio" in str(grade_level).casefold():
        return "EM", year
    return "EF", year


def curriculum_subjects_for_grade(grade_level: str) -> list[str]:
    stage_year = school_stage_and_year(grade_level)
    if stage_year is None:
        return []
    stage, year = stage_year
    if stage == "EF" and 1 <= year <= 9:
        return list(FUNDAMENTAL_SUBJECTS)
    if stage == "EM" and 1 <= year <= 3:
        return list(MEDIO_SUBJECTS)
    return []


def subject_area(subject_name: str) -> str | None:
    key = normalize_curriculum_key(subject_name)
    for canonical_name, area in SUBJECT_AREAS.items():
        if normalize_curriculum_key(canonical_name) == key:
            return area
    return None


def all_curriculum_subjects() -> list[str]:
    ordered: list[str] = []
    for subject in FUNDAMENTAL_SUBJECTS + MEDIO_SUBJECTS:
        if subject not in ordered:
            ordered.append(subject)
    return ordered
