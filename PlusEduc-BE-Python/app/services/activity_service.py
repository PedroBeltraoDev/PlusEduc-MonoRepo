from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.auth import UserPrincipal
from app.repositories.activity_repository import ActivityRepository
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.activity import (
    ActivityCreateRequest,
    ActivityGenerationRequest,
    ActivityResponse,
    ActivityUpdateRequest,
    GeneratedQuestion,
)
from app.services.demo_ai_service import DemoAIService
from app.services.gemini_service import GeminiGenerationError, GeminiGenerationRequest, GeminiService


class ActivityService:
    def __init__(
        self,
        repository: ActivityRepository,
        student_repository: StudentRepository,
        classroom_repository: ClassroomRepository,
        mongo,
        settings=None,
    ) -> None:
        self.repository = repository
        self.student_repository = student_repository
        self.classroom_repository = classroom_repository
        self.mongo = mongo
        self.settings = settings
        self.demo_ai_service = DemoAIService()

    def create(self, request: ActivityCreateRequest, current_user: UserPrincipal) -> ActivityResponse:
        self.require_classroom(request.classroomId)
        if request.studentId:
            self.require_student(request.studentId)
        content = self.serialize_content(request.questions, request.content)
        document = {
            "title": request.title,
            "subject": request.subject,
            "topic": request.topic,
            "difficulty_level": request.difficultyLevel,
            "questions_count": request.questionsCount,
            "format": request.format,
            "classroom_id": request.classroomId,
            "student_id": request.studentId,
            "disability_adaptations": request.disabilityAdaptations or [],
            "content": content,
            "pdf_url": request.pdfUrl,
            "generated_by_ai": False,
            "ai_provider": None,
            "created_by": current_user.user_id,
            "created_at": datetime.now(timezone.utc),
        }
        document = {key: value for key, value in document.items() if value is not None}
        return self.to_response(self.repository.insert(document))

    def generate(self, request: ActivityGenerationRequest, current_user: UserPrincipal) -> ActivityResponse:
        classroom = self.require_classroom(request.classroomId)
        student = self.resolve_student_for_classroom(request.studentId, classroom) if request.studentId else None
        learning_gaps = self.learning_gaps_text(student)
        ai_request = GeminiGenerationRequest(
            subject=request.subject,
            topic=request.topic,
            difficulty_level=request.difficultyLevel,
            questions_count=request.questionsCount,
            format=request.format,
            learning_gaps=learning_gaps,
            disability_adaptations=tuple(request.disabilityAdaptations or []),
            additional_instructions=request.additionalInstructions or "",
        )

        questions: list[GeneratedQuestion]
        provider = "Google Gemini"
        gemini = GeminiService(
            api_key=getattr(self.settings, "gemini_api_key", ""),
            model=getattr(self.settings, "gemini_model", GeminiService.DEFAULT_MODEL),
            api_version=getattr(self.settings, "gemini_api_version", GeminiService.DEFAULT_API_VERSION),
            temperature=getattr(self.settings, "gemini_temperature", 0.7),
            connect_timeout_seconds=getattr(self.settings, "gemini_connect_timeout_seconds", 10.0),
            read_timeout_seconds=getattr(self.settings, "gemini_read_timeout_seconds", 45.0),
        )
        try:
            questions = gemini.generate(ai_request)
        except GeminiGenerationError as exc:
            if not getattr(self.settings, "ai_demo_fallback_enabled", True):
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            questions = self.demo_ai_service.generate(ai_request)
            provider = DemoAIService.name

        if not questions:
            questions = self.reuse_questions_from_database(request)
            provider = "Banco de questões"
        questions = self.adapt_generated_questions(
            questions,
            request.disabilityAdaptations or [],
            request.format,
        )
        if not questions:
            raise HTTPException(status_code=400, detail="A IA não retornou questões válidas")

        adaptations = list(request.disabilityAdaptations or [])
        if request.learningGapId and request.learningGapId not in adaptations:
            adaptations.append(request.learningGapId)
        document = {
            "title": f"Atividade de Reforço: {request.subject} - {request.topic}",
            "subject": request.subject,
            "topic": request.topic,
            "difficulty_level": request.difficultyLevel,
            "questions_count": len(questions),
            "format": request.format,
            "classroom_id": str(classroom.get("_id", classroom.get("id", request.classroomId))),
            "student_id": str(student.get("_id", student.get("id"))) if student else None,
            "disability_adaptations": adaptations,
            "content": self.serialize_questions(questions),
            "generated_by_ai": True,
            "ai_provider": provider,
            "created_by": current_user.email or current_user.user_id,
            "created_at": datetime.now(timezone.utc),
        }
        document = {key: value for key, value in document.items() if value is not None}
        return self.to_response(self.repository.insert(document))

    def list_all(self) -> list[ActivityResponse]:
        return [self.to_response(item) for item in self.repository.find_all()]

    def get(self, activity_id: str) -> ActivityResponse:
        item = self.repository.find_by_id(activity_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Atividade não encontrada: {activity_id}")
        return self.to_response(item)

    def update(self, activity_id: str, request: ActivityUpdateRequest, current_user: UserPrincipal) -> ActivityResponse:
        if not self.repository.find_by_id(activity_id):
            raise HTTPException(status_code=404, detail=f"Atividade não encontrada: {activity_id}")
        values = request.model_dump(exclude_unset=True)
        if "classroomId" in values:
            self.require_classroom(values["classroomId"])
        if values.get("studentId"):
            self.require_student(values["studentId"])
        mapping = {
            "title": "title", "subject": "subject", "topic": "topic", "difficultyLevel": "difficulty_level",
            "questionsCount": "questions_count", "format": "format", "classroomId": "classroom_id",
            "studentId": "student_id", "disabilityAdaptations": "disability_adaptations", "content": "content", "pdfUrl": "pdf_url",
        }
        updates: dict[str, Any] = {}
        if "questions" in values:
            updates["content"] = self.serialize_questions(values.pop("questions"), values.get("content"))
        for key, value in values.items():
            if key in mapping:
                updates[mapping[key]] = value
        return self.to_response(self.repository.update(activity_id, updates))

    def delete(self, activity_id: str) -> None:
        if not self.repository.delete(activity_id):
            raise HTTPException(status_code=404, detail=f"Atividade não encontrada: {activity_id}")

    def by_classroom(self, classroom_id: str) -> list[ActivityResponse]:
        self.require_classroom(classroom_id)
        return [self.to_response(item) for item in self.repository.find_by_classroom(classroom_id)]

    def by_student(self, student_id: str) -> list[ActivityResponse]:
        self.require_student(student_id)
        return [self.to_response(item) for item in self.repository.find_by_student(student_id)]

    def by_teacher(self, teacher_id: str) -> list[ActivityResponse]:
        classroom_ids = [str(item.get("_id")) for item in self.mongo.database.classrooms.find({"$or": [{"teacher_id": teacher_id}, {"teacherId": teacher_id}]}, {"_id": 1})]
        activities = self.repository.find_by_classrooms(classroom_ids)
        activities.extend(self.mongo.database.activities.find({"created_by": teacher_id}))
        unique = {str(item.get("_id")): item for item in activities}
        return [self.to_response(item) for item in unique.values()]

    def require_classroom(self, classroom_id: str) -> dict[str, Any]:
        classroom = self.classroom_repository.find_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=400, detail=f"Turma não encontrada: {classroom_id}")
        return classroom

    def require_student(self, student_id: str) -> dict[str, Any]:
        student = self.student_repository.find_by_id(student_id)
        if not student:
            raise HTTPException(status_code=400, detail=f"Aluno não encontrado: {student_id}")
        return student

    def resolve_student_for_classroom(self, student_id: str, classroom: dict[str, Any]) -> dict[str, Any]:
        student = self.require_student(student_id)
        classroom_id = str(classroom.get("_id", classroom.get("id", "")))
        student_class_id = student.get("classId", student.get("class_id"))
        if student_class_id and str(student_class_id) != classroom_id:
            raise HTTPException(status_code=400, detail="O aluno informado não pertence à turma selecionada")
        student_ids = classroom.get("studentIds", classroom.get("student_ids", [])) or []
        if student_ids and student_id not in {str(value) for value in student_ids}:
            raise HTTPException(status_code=400, detail="O aluno informado não está matriculado na turma selecionada")
        return student

    @staticmethod
    def learning_gaps_text(student: dict[str, Any] | None) -> str:
        if not student:
            return ""
        gaps = student.get("learningGaps", student.get("learning_gaps", [])) or []
        values: list[str] = []
        for gap in gaps:
            if isinstance(gap, dict):
                subject = gap.get("subject", "")
                topic = gap.get("topic", "")
                if subject or topic:
                    values.append(f"{subject} - {topic}".strip(" -"))
        return ", ".join(values)

    @staticmethod
    def serialize_questions(questions: list[GeneratedQuestion] | list[dict[str, Any]], content: str | None = None) -> str:
        if questions:
            data = [question.model_dump(by_alias=True) if isinstance(question, GeneratedQuestion) else question for question in questions]
            return json.dumps({"questions": data}, ensure_ascii=False)
        return content or json.dumps({"questions": []}, ensure_ascii=False)

    @classmethod
    def serialize_content(cls, questions: list[GeneratedQuestion] | None, content: str | None) -> str:
        return cls.serialize_questions(questions or [], content)

    @classmethod
    def parse_questions(cls, content: Any) -> list[GeneratedQuestion]:
        if not content:
            return []
        if isinstance(content, list):
            return [GeneratedQuestion.model_validate(item) for item in content]
        if isinstance(content, dict):
            raw = content.get("questions", content.get("items", []))
            return [GeneratedQuestion.model_validate(item) for item in raw]
        text = str(content)
        try:
            decoded = json.loads(text)
            return cls.parse_questions(decoded)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        pattern = re.compile(r"GeneratedQuestion\(questionText=(.*?), questionType=(.*?), options=\[(.*?)\], correctAnswer=(.*?), explanation=(.*?)(?:, difficultyLevel=(.*?))?\)")
        questions: list[GeneratedQuestion] = []
        for match in pattern.finditer(text):
            options = [option.strip() for option in match.group(3).split(",") if option.strip()]
            questions.append(GeneratedQuestion(
                questionText=match.group(1).strip(),
                questionType=match.group(2).strip(),
                options=options,
                correctAnswer=match.group(4).strip(),
                explanation=match.group(5).strip(),
                difficultyLevel=match.group(6).strip() if match.group(6) else None,
            ))
        if questions:
            return questions
        return [GeneratedQuestion(
            questionText=text.strip(),
            questionType="DISCURSIVA",
            options=[],
            explanation="Conteúdo original salvo como texto livre.",
            difficultyLevel="LIVRE",
        )]

    def reuse_questions_from_database(self, request: ActivityGenerationRequest) -> list[GeneratedQuestion]:
        query = {"subject": {"$regex": f"^{re.escape(request.subject)}$", "$options": "i"}}
        candidates = list(self.mongo.database.activities.find(query).sort("created_at", -1))
        exact = [item for item in candidates if str(item.get("topic", "")).lower() == request.topic.lower()]
        ordered = exact + [item for item in candidates if item not in exact]
        result: list[GeneratedQuestion] = []
        seen: set[str] = set()
        for activity in ordered:
            for question in self.parse_questions(activity.get("content")):
                key = question.questionText.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    result.append(question)
                if len(result) >= request.questionsCount:
                    return result
        return result

    @classmethod
    def adapt_generated_questions(
        cls,
        questions: list[GeneratedQuestion],
        adaptations: list[str],
        preferred_format: str,
    ) -> list[GeneratedQuestion]:
        adapted: list[GeneratedQuestion] = []
        for index, original in enumerate(questions):
            question_type = (original.questionType or "DISCURSIVA").strip().upper()
            text = cls.apply_accessibility_to_text(original.questionText, adaptations)
            explanation = cls.apply_accessibility_to_explanation(original.explanation, adaptations)
            options = [cls.trim_option(option, adaptations) for option in (original.options or [])]
            if cls.contains_adaptation(adaptations, "dislexia") and index % 2 == 0 and question_type == "DISCURSIVA":
                question_type = "VERDADEIRO_FALSO"
                options = ["Verdadeiro", "Falso"]
                correct_answer = original.correctAnswer or "Verdadeiro"
            else:
                correct_answer = original.correctAnswer
            if question_type == "VERDADEIRO_FALSO" and not options:
                options = ["Verdadeiro", "Falso"]
            adapted.append(original.model_copy(update={
                "questionText": text,
                "questionType": question_type,
                "options": options,
                "correctAnswer": correct_answer,
                "explanation": explanation,
                "difficultyLevel": original.difficultyLevel or "MEDIO",
            }))
        return adapted

    @staticmethod
    def contains_adaptation(adaptations: list[str], keyword: str) -> bool:
        return any(keyword in (value or "").strip().lower() for value in adaptations)

    @classmethod
    def apply_accessibility_to_text(cls, text: str, adaptations: list[str]) -> str:
        adapted = (text or "").strip()
        if cls.contains_adaptation(adaptations, "tdah"):
            for command in ("grife", "sublinhe", "calcule", "resolva", "marque", "explique", "compare"):
                adapted = re.sub(rf"\b{command}\b", command.upper(), adapted, flags=re.IGNORECASE)
        if cls.contains_adaptation(adaptations, "dislexia") and len(adapted) > 180:
            adapted = adapted[:177].rstrip() + "..."
        return adapted

    @classmethod
    def apply_accessibility_to_explanation(cls, explanation: str | None, adaptations: list[str]) -> str | None:
        if not explanation:
            return explanation
        adapted = explanation.strip()
        if cls.contains_adaptation(adaptations, "dislexia") and len(adapted) > 140:
            adapted = adapted[:137].rstrip() + "..."
        if cls.contains_adaptation(adaptations, "tdah"):
            adapted = "Passo a passo: " + adapted
        return adapted

    @classmethod
    def trim_option(cls, option: str, adaptations: list[str]) -> str:
        text = option or ""
        if cls.contains_adaptation(adaptations, "dislexia") and len(text) > 90:
            return text[:87].rstrip() + "..."
        return text

    def to_response(self, document: dict[str, Any]) -> ActivityResponse:
        activity_id = str(document.get("_id", document.get("id")))
        classroom_id = document.get("classroom_id", document.get("classroomId"))
        student_id = document.get("student_id", document.get("studentId"))
        classroom = self.mongo.database.classrooms.find_one({"_id": self._object_id(classroom_id)}) if classroom_id else None
        if classroom is None and classroom_id:
            classroom = self.mongo.database.classrooms.find_one({"_id": classroom_id})
        student = self.student_repository.find_by_id(str(student_id)) if student_id else None
        return ActivityResponse(
            id=activity_id,
            title=document.get("title", ""),
            subject=document.get("subject"),
            topic=document.get("topic"),
            difficultyLevel=document.get("difficulty_level", document.get("difficultyLevel")),
            questionsCount=document.get("questions_count", document.get("questionsCount")),
            format=document.get("format"),
            classroomId=str(classroom_id) if classroom_id else None,
            classroomName=classroom.get("name") if classroom else None,
            studentId=str(student_id) if student_id else None,
            studentName=student.get("name") if student else None,
            disabilityAdaptations=document.get("disability_adaptations", document.get("disabilityAdaptations", [])) or [],
            questions=self.parse_questions(document.get("content")),
            content=document.get("content"),
            pdfUrl=document.get("pdf_url", document.get("pdfUrl")),
            generatedByAi=document.get("generated_by_ai", document.get("generatedByAi")),
            aiProvider=document.get("ai_provider", document.get("aiProvider")),
            createdBy=document.get("created_by", document.get("createdBy")),
            creatorName=None,
            createdAt=document.get("created_at", document.get("createdAt")),
        )

    @staticmethod
    def _object_id(value: Any):
        if value is None:
            return value
        try:
            return __import__("bson").ObjectId(str(value))
        except Exception:
            return value
