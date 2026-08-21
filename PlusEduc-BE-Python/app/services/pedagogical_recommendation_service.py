from __future__ import annotations

import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.analytics import (
    PedagogicalRecommendationResponse,
    RecommendationEvidence,
)


class PedagogicalRecommendationService:
    """Calcula recomendações explicáveis antes da geração textual por IA."""

    def __init__(
        self,
        student_repository: StudentRepository,
        grade_repository: GradeRepository,
        classroom_repository: ClassroomRepository,
    ) -> None:
        self.student_repository = student_repository
        self.grade_repository = grade_repository
        self.classroom_repository = classroom_repository

    def recommend(self, student_id: str) -> PedagogicalRecommendationResponse:
        student = self.student_repository.find_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")

        gaps = student.get("learningGaps", student.get("learning_gaps", [])) or []
        grades = self.grade_repository.find_by_student(student_id)
        subject_averages = self._subject_averages(grades)

        ranked: list[tuple[float, dict[str, Any]]] = []
        for gap in gaps:
            if not isinstance(gap, dict):
                continue
            subject = str(gap.get("subject", "")).strip()
            topic = str(gap.get("topic", "")).strip()
            if not subject or not topic:
                continue
            severity = self._severity_weight(gap.get("severityLevel", gap.get("severity_level", gap.get("severity"))))
            average = self._average_for_subject(subject_averages, subject)
            grade_pressure = 0.0 if average is None else max(0.0, 7.0 - average)
            improved = bool(gap.get("improved")) or str(gap.get("improvementStatus", "")).upper() in {"IMPROVED", "RESOLVED"}
            improvement_penalty = -1.5 if improved else 0.0
            score = severity * 3.0 + grade_pressure + improvement_penalty
            ranked.append((score, {"subject": subject, "topic": topic, "severity": severity, "average": average, "improved": improved}))

        if ranked:
            ranked.sort(key=lambda item: (-item[0], self._normalize(item[1]["subject"]), self._normalize(item[1]["topic"])))
            score, selected = ranked[0]
            priority = self._priority(score)
            difficulty = self._difficulty(priority, selected["average"])
            evidence = self._evidence_for(selected, score)
            rationale = self._rationale(selected, priority, difficulty)
            return PedagogicalRecommendationResponse(
                studentId=student_id,
                studentName=str(student.get("name", "Aluno")),
                priority=priority,
                recommendedSubject=selected["subject"],
                recommendedTopic=selected["topic"],
                recommendedDifficulty=difficulty,
                recommendedQuestionsCount=5 if priority == "HIGH" else 4,
                rationale=rationale,
                evidences=evidence,
                generatedAt=datetime.now(timezone.utc),
            )

        fallback_subject, fallback_average = self._lowest_subject(subject_averages)
        if fallback_subject:
            priority = "MEDIUM" if fallback_average < 7.0 else "LOW"
            difficulty = self._difficulty(priority, fallback_average)
            return PedagogicalRecommendationResponse(
                studentId=student_id,
                studentName=str(student.get("name", "Aluno")),
                priority=priority,
                recommendedSubject=fallback_subject,
                recommendedTopic="Revisão dos conteúdos recentes",
                recommendedDifficulty=difficulty,
                recommendedQuestionsCount=4,
                rationale=(
                    f"A recomendação usa a menor média registrada em {fallback_subject} "
                    f"({fallback_average:.1f}/10) para orientar uma revisão objetiva."
                ),
                evidences=[RecommendationEvidence(
                    signal="desempenho",
                    detail=f"Menor média registrada: {fallback_average:.1f}/10.",
                    weight=round(max(0.0, 7.0 - fallback_average), 2),
                )],
                generatedAt=datetime.now(timezone.utc),
            )

        return PedagogicalRecommendationResponse(
            studentId=student_id,
            studentName=str(student.get("name", "Aluno")),
            priority="LOW",
            recommendedSubject="",
            recommendedTopic="Revisão dos conteúdos recentes",
            recommendedDifficulty="MEDIO",
            recommendedQuestionsCount=3,
            rationale="Ainda não existem lacunas ou notas suficientes; a recomendação usa uma revisão diagnóstica inicial.",
            evidences=[RecommendationEvidence(
                signal="diagnóstico inicial",
                detail="Não há dados pedagógicos suficientes para priorizar um tópico.",
                weight=0.0,
            )],
            generatedAt=datetime.now(timezone.utc),
        )

    @classmethod
    def _subject_averages(cls, grades: list[dict[str, Any]]) -> dict[str, tuple[str, float]]:
        values: dict[str, list[float]] = defaultdict(list)
        labels: dict[str, str] = {}
        for grade in grades:
            subject = str(grade.get("subject", "")).strip()
            if not subject:
                continue
            try:
                value = float(grade.get("grade", grade.get("gradeValue", 0)) or 0)
            except (TypeError, ValueError):
                continue
            key = cls._normalize(subject)
            labels.setdefault(key, subject)
            values[key].append(value)
        return {
            key: (labels[key], sum(items) / len(items))
            for key, items in values.items()
            if items
        }

    @classmethod
    def _average_for_subject(cls, averages: dict[str, tuple[str, float]], subject: str) -> float | None:
        result = averages.get(cls._normalize(subject))
        return result[1] if result else None

    @classmethod
    def _lowest_subject(cls, averages: dict[str, tuple[str, float]]) -> tuple[str | None, float]:
        if not averages:
            return None, 0.0
        _, (subject, average) = min(averages.items(), key=lambda item: item[1][1])
        return subject, average

    @staticmethod
    def _severity_weight(value: Any) -> float:
        normalized = str(value or "MEDIUM").upper()
        return {"HIGH": 3.0, "ALTA": 3.0, "MEDIUM": 2.0, "MEDIO": 2.0, "LOW": 1.0, "BAIXA": 1.0}.get(normalized, 2.0)

    @staticmethod
    def _priority(score: float) -> str:
        if score >= 7.0:
            return "HIGH"
        if score >= 4.0:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _difficulty(priority: str, average: float | None) -> str:
        if priority == "HIGH" or (average is not None and average < 5.0):
            return "FACIL"
        if priority == "MEDIUM" or (average is not None and average < 7.0):
            return "MEDIO"
        return "DIFICIL"

    @staticmethod
    def _evidence_for(selected: dict[str, Any], score: float) -> list[RecommendationEvidence]:
        evidence = [RecommendationEvidence(
            signal="lacuna de aprendizagem",
            detail=f"Lacuna registrada em {selected['subject']} — {selected['topic']}.",
            weight=round(selected["severity"] * 3.0, 2),
        )]
        if selected["average"] is not None:
            evidence.append(RecommendationEvidence(
                signal="desempenho",
                detail=f"Média em {selected['subject']}: {selected['average']:.1f}/10.",
                weight=round(max(0.0, 7.0 - selected["average"]), 2),
            ))
        if selected["improved"]:
            evidence.append(RecommendationEvidence(
                signal="histórico de melhoria",
                detail="A lacuna já foi marcada como melhorada e recebeu menor prioridade.",
                weight=-1.5,
            ))
        evidence.append(RecommendationEvidence(
            signal="pontuação pedagógica",
            detail=f"Prioridade calculada: {score:.2f}.",
            weight=round(score, 2),
        ))
        return evidence

    @staticmethod
    def _rationale(selected: dict[str, Any], priority: str, difficulty: str) -> str:
        average_text = (
            f" A média atual em {selected['subject']} é {selected['average']:.1f}/10."
            if selected["average"] is not None else " Ainda não há média registrada para a matéria."
        )
        return (
            f"A lacuna {selected['topic']} foi priorizada com nível {priority.lower()} "
            f"para uma atividade de dificuldade {difficulty.lower()}." + average_text
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(
            char for char in unicodedata.normalize("NFKD", value.strip().lower())
            if not unicodedata.combining(char)
        )
