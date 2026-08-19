from __future__ import annotations

from app.schemas.activity import GeneratedQuestion
from app.services.gemini_service import GeminiGenerationRequest


class DemoAIService:
    name = "Demo Educacional"

    def generate(self, request: GeminiGenerationRequest) -> list[GeneratedQuestion]:
        questions: list[GeneratedQuestion] = []
        for index in range(1, request.questions_count + 1):
            question_type = self._question_type(request.format, index)
            questions.append(
                GeneratedQuestion(
                    questionText=(
                        f"Questão {index}: resolva uma situação sobre {request.topic} "
                        f"em {request.subject} e explique sua resposta."
                    ),
                    questionType=question_type,
                    options=self._options(question_type),
                    correctAnswer=self._correct_answer(question_type),
                    explanation="Resposta sugerida para revisão do professor antes da aplicação.",
                    difficultyLevel=request.difficulty_level or "MEDIO",
                )
            )
        return questions

    @staticmethod
    def _question_type(preferred_format: str | None, index: int) -> str:
        if not preferred_format or not preferred_format.strip():
            return "DISCURSIVA" if index % 2 == 0 else "MULTIPLA_ESCOLHA"
        return preferred_format.strip().upper()

    @staticmethod
    def _options(question_type: str) -> list[str]:
        if question_type == "VERDADEIRO_FALSO":
            return ["Verdadeiro", "Falso"]
        if question_type != "MULTIPLA_ESCOLHA":
            return []
        return [
            "A) Alternativa correta",
            "B) Alternativa parecida",
            "C) Alternativa incompleta",
            "D) Alternativa incorreta",
        ]

    @staticmethod
    def _correct_answer(question_type: str) -> str:
        if question_type == "VERDADEIRO_FALSO":
            return "Verdadeiro"
        if question_type == "MULTIPLA_ESCOLHA":
            return "A"
        return "Resposta discursiva esperada."
