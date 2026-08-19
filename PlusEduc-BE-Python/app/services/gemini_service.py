from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.schemas.activity import GeneratedQuestion

logger = logging.getLogger(__name__)


class GeminiGenerationError(RuntimeError):
    """Falha controlada de chamada ou interpretação da resposta Gemini."""


@dataclass(frozen=True)
class GeminiGenerationRequest:
    subject: str
    topic: str
    difficulty_level: str
    questions_count: int
    format: str
    learning_gaps: str = ""
    disability_adaptations: tuple[str, ...] = ()
    additional_instructions: str = ""


class GeminiService:
    API_BASE_URL = "https://generativelanguage.googleapis.com"
    DEFAULT_MODEL = "gemini-3.5-flash-lite"
    DEFAULT_API_VERSION = "v1"

    def __init__(
        self,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        api_version: str = DEFAULT_API_VERSION,
        temperature: float = 0.7,
        connect_timeout_seconds: float = 10.0,
        read_timeout_seconds: float = 45.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.model = (model or self.DEFAULT_MODEL).strip()
        self.api_version = (api_version or self.DEFAULT_API_VERSION).strip().strip("/") or self.DEFAULT_API_VERSION
        self.temperature = temperature
        self.connect_timeout_seconds = connect_timeout_seconds
        self.read_timeout_seconds = read_timeout_seconds

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, request: GeminiGenerationRequest) -> list[GeneratedQuestion]:
        if not self.is_available:
            raise GeminiGenerationError("Gemini API key não configurada")

        url = f"{self.API_BASE_URL}/{self.api_version}/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": self.build_prompt(request)}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        }
        timeout = httpx.Timeout(
            timeout=self.read_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        try:
            response = httpx.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": self.api_key,
                },
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            body = response.json()
            text = self.extract_text(body)
            return self.parse_questions(text)
        except GeminiGenerationError:
            raise
        except httpx.TimeoutException as exc:
            logger.warning("Timeout controlado ao chamar Gemini: %s", exc)
            raise GeminiGenerationError("Tempo limite excedido ao chamar Gemini") from exc
        except httpx.HTTPError as exc:
            logger.warning("Erro HTTP ao chamar Gemini: %s", exc)
            raise GeminiGenerationError("Falha ao chamar Gemini API") from exc
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Resposta inválida do Gemini: %s", exc)
            raise GeminiGenerationError("Falha ao interpretar resposta da Gemini API") from exc

    @classmethod
    def build_prompt(cls, request: GeminiGenerationRequest) -> str:
        lines = [
            "Você é um professor especialista em educação inclusiva e elaboração de atividades escolares.",
            "",
            f"Crie {request.questions_count} questões sobre {request.topic} da matéria de {request.subject}.",
            f"Nível de dificuldade: {request.difficulty_level}",
            f"Formato predominante: {request.format}",
            "As questões devem ser corretas, relevantes ao tópico e prontas para uso em sala.",
        ]
        if request.learning_gaps.strip():
            lines.extend([
                "",
                f"Dificuldades de aprendizagem do aluno/turma: {request.learning_gaps.strip()}. Foque em reforçar esses conceitos.",
            ])
        adaptations = [item.strip() for item in request.disability_adaptations if item and item.strip()]
        if adaptations:
            lines.extend(["", "Adaptações inclusivas obrigatórias:"])
            normalized = " ".join(adaptations).lower()
            if "dislexia" in normalized:
                lines.append("- Dislexia: reduza a densidade de texto e priorize enunciados curtos.")
            if "baixa" in normalized:
                lines.append("- Baixa visão: use enunciados objetivos e estrutura fácil de ampliar visualmente.")
            if "tdah" in normalized:
                lines.append("- TDAH: fracione o conteúdo, destaque comandos principais e evite blocos longos.")
        if request.additional_instructions.strip():
            lines.extend(["", f"Instruções adicionais do professor: {request.additional_instructions.strip()}"])
        lines.extend([
            "",
            "Regras obrigatórias:",
            "- Retorne APENAS JSON válido.",
            "- Use linguagem clara em português do Brasil.",
            "- Para MULTIPLA_ESCOLHA, forneça 4 opções.",
            '- Para VERDADEIRO_FALSO, use options com "Verdadeiro" e "Falso".',
            "- Não adicione markdown ou texto fora do JSON.",
            "",
            "Formato do JSON:",
            '[{"questionText":"texto","questionType":"MULTIPLA_ESCOLHA","options":["A) opção 1","B) opção 2","C) opção 3","D) opção 4"],"correctAnswer":"A","explanation":"explicação curta","difficultyLevel":"FACIL"}]',
        ])
        return "\n".join(lines)

    @staticmethod
    def extract_text(body: dict[str, Any]) -> str:
        if "error" in body:
            message = body.get("error", {}).get("message", "erro desconhecido")
            raise GeminiGenerationError(f"Gemini API error: {message}")
        try:
            return str(body["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiGenerationError("Formato de resposta inválido da Gemini API") from exc

    @staticmethod
    def parse_questions(text: str) -> list[GeneratedQuestion]:
        cleaned = (text or "").strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            raw = json.loads(cleaned.strip())
            if not isinstance(raw, list) or not raw:
                raise GeminiGenerationError("A IA não retornou questões válidas")
            questions = [GeneratedQuestion.model_validate(item) for item in raw]
            if not questions:
                raise GeminiGenerationError("A IA não retornou questões válidas")
            return questions
        except GeminiGenerationError:
            raise
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise GeminiGenerationError("Falha ao converter resposta da IA em questões") from exc
