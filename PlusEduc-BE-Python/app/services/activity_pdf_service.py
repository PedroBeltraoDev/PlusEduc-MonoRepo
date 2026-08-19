from __future__ import annotations

import io
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.student_repository import StudentRepository
from app.services.activity_service import ActivityService

logger = logging.getLogger(__name__)


class ActivityPdfService:
    HEADER_TITLE = "PlusEduc - Atividade de Reforço"
    OPTION_PREFIX = re.compile(r"^[A-D][).]\s*", re.IGNORECASE)

    def __init__(self, student_repository: StudentRepository, classroom_repository: ClassroomRepository) -> None:
        self.student_repository = student_repository
        self.classroom_repository = classroom_repository
        self.font_name, self.bold_font_name = self._register_fonts()

    def generate(self, activity: dict[str, Any], include_answers: bool) -> bytes:
        buffer = io.BytesIO()
        document = canvas.Canvas(buffer, pagesize=A4)
        document.setTitle(str(activity.get("title") or "Atividade PlusEduc"))
        document.setAuthor("PlusEduc API")
        width, height = A4
        margin = 18 * mm
        y = height - margin
        student = self._find_student(activity)
        classroom = self._find_classroom(activity)
        questions = ActivityService.parse_questions(activity.get("content"))
        styles = self._styles()

        y = self._header(document, y, width, margin, activity, student, classroom, styles)
        y = self._section(document, y, width, margin, "Contexto Pedagógico", styles["section"])
        if student:
            y = self._paragraph(document, y, width, margin, f"Aluno vinculado: {student.get('name', 'Não informado')}", styles["body"])
            gaps = student.get("learningGaps", student.get("learning_gaps", [])) or []
            if gaps:
                y = self._paragraph(document, y, width, margin, "Dificuldades identificadas:", styles["body_bold"])
                for gap in gaps:
                    if isinstance(gap, dict):
                        summary = f"• {gap.get('subject', 'Matéria')} - {gap.get('topic', 'Tópico')}"
                        if gap.get("description"):
                            summary += f" ({gap['description']})"
                        y = self._paragraph(document, y, width, margin, summary, styles["body"])
            else:
                y = self._paragraph(document, y, width, margin, "Dificuldades identificadas: nenhuma informada.", styles["body"])
        else:
            y = self._paragraph(document, y, width, margin, "Aluno: atividade sem aluno associado.", styles["body"])

        y -= 4 * mm
        instruction_title = "Versão do Professor" if include_answers else "Orientações de Aplicação"
        y = self._section(document, y, width, margin, instruction_title, styles["section"])
        if include_answers:
            guidance = "Este PDF inclui gabarito e explicações de apoio para revisão, correção ou planejamento de aula."
        else:
            guidance = f"Esta atividade contém {len(questions)} questão(ões). Registre o raciocínio e revise antes de entregar."
        y = self._paragraph(document, y, width, margin, guidance, styles["body"])
        if activity.get("generated_by_ai", activity.get("generatedByAi")) and activity.get("ai_provider", activity.get("aiProvider")):
            y = self._paragraph(document, y, width, margin, f"Conteúdo preparado com apoio de IA: {activity.get('ai_provider', activity.get('aiProvider'))}", styles["muted"])
        adaptations = activity.get("disability_adaptations", activity.get("disabilityAdaptations", [])) or []
        for adaptation, text in (("baixa", "Ajuste aplicado: fonte ampliada para baixa visão."), ("dislexia", "Ajuste aplicado: enunciados mais curtos."), ("tdah", "Ajuste aplicado: comandos destacados e espaçamento ampliado.")):
            if any(adaptation in str(item).lower() for item in adaptations):
                y = self._paragraph(document, y, width, margin, text, styles["muted"])

        for index, question in enumerate(questions, start=1):
            if y < 52 * mm:
                self._footer(document, width, margin)
                document.showPage()
                y = height - margin
            y = self._question(document, y, width, margin, index, question, include_answers, styles)

        if not questions:
            y = self._paragraph(document, y, width, margin, "Nenhuma questão estruturada foi encontrada no conteúdo desta atividade.", styles["body"])
        self._footer(document, width, margin)
        document.save()
        return buffer.getvalue()

    def _header(self, document, y, width, margin, activity, student, classroom, styles):
        document.setFillColor(colors.HexColor("#1F4E79"))
        document.roundRect(margin, y - 23 * mm, width - 2 * margin, 23 * mm, 3 * mm, fill=1, stroke=0)
        document.setFillColor(colors.white)
        document.setFont(self.bold_font_name, 16)
        document.drawCentredString(width / 2, y - 10 * mm, self.HEADER_TITLE)
        document.setFont(self.font_name, 8)
        document.drawCentredString(width / 2, y - 17 * mm, "PlusEduc")
        y -= 29 * mm
        title = activity.get("title") or "Atividade sem título"
        metadata = [
            str(title),
            f"{activity.get('subject') or 'Matéria não informada'} • {activity.get('topic') or 'Tópico não informado'}",
            f"Nível: {activity.get('difficulty_level', activity.get('difficultyLevel')) or 'Não informado'} • Aluno: {(student or {}).get('name', 'Atividade geral')}",
            f"Turma: {(classroom or {}).get('name', 'Não informada')} • Formato: {activity.get('format') or 'Não informado'}",
        ]
        y = self._paragraph(document, y, width, margin, metadata[0], styles["title"])
        for item in metadata[1:]:
            y = self._paragraph(document, y, width, margin, item, styles["body"])
        return y - 4 * mm

    def _question(self, document, y, width, margin, number, question, include_answers, styles):
        question_text = question.questionText or "Questão sem texto"
        question_type = question.questionType or "OBJETIVA"
        difficulty = question.difficultyLevel or "Não informada"
        document.setFillColor(colors.HexColor("#EFF4F8"))
        document.roundRect(margin, y - 16 * mm, width - 2 * margin, 16 * mm, 2 * mm, fill=1, stroke=0)
        document.setFillColor(colors.HexColor("#1F4E79"))
        document.setFont(self.bold_font_name, 11)
        document.drawString(margin + 5 * mm, y - 7 * mm, f"{number}.")
        y = self._paragraph(document, y - 2 * mm, width, margin + 12 * mm, question_text, styles["question"])
        y = self._paragraph(document, y - 1 * mm, width, margin + 12 * mm, f"Tipo: {question_type} • Dificuldade: {difficulty}", styles["muted"])
        y -= 2 * mm
        options = question.options or []
        if question_type.upper() == "DISCURSIVA":
            y = self._paragraph(document, y, width, margin + 12 * mm, "Espaço para resposta do aluno:", styles["body_bold"])
            for _ in range(4):
                y = self._paragraph(document, y, width, margin + 12 * mm, "____________________________________________________________", styles["line"])
        else:
            for option in options:
                option_text = str(option or "Opção não informada")
                correct = include_answers and self._is_correct_option(question.correctAnswer, option_text)
                suffix = "  [CORRETA]" if correct else ""
                y = self._paragraph(document, y, width, margin + 12 * mm, option_text + suffix, styles["correct"] if correct else styles["body"])
        if question.explanation:
            label = "Comentário pedagógico:" if include_answers else "Dica de correção:"
            y = self._paragraph(document, y + 1 * mm, width, margin + 12 * mm, label, styles["body_bold"])
            y = self._paragraph(document, y, width, margin + 12 * mm, question.explanation, styles["body"])
        return y - 7 * mm

    def _section(self, document, y, width, margin, text, style):
        return self._paragraph(document, y, width, margin, text, style) - 2 * mm

    def _paragraph(self, document, y, width, margin, text, style):
        paragraph = Paragraph(self._escape(text), style)
        _, height = paragraph.wrap(width - margin - (margin if margin == 18 * mm else 12 * mm), 100 * mm)
        paragraph.drawOn(document, margin, y - height)
        return y - height - 2 * mm

    @staticmethod
    def _escape(value: Any) -> str:
        text = str(value or "")
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _styles(self):
        low_vision = False
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle("phase8-title", parent=base["Title"], fontName=self.bold_font_name, fontSize=15, leading=19, textColor=colors.HexColor("#24364A"), spaceAfter=4),
            "section": ParagraphStyle("phase8-section", parent=base["Heading2"], fontName=self.bold_font_name, fontSize=12, leading=15, textColor=colors.HexColor("#1F4E79"), spaceBefore=5, spaceAfter=5),
            "question": ParagraphStyle("phase8-question", parent=base["BodyText"], fontName=self.bold_font_name, fontSize=10, leading=15, textColor=colors.HexColor("#1A5276")),
            "body": ParagraphStyle("phase8-body", parent=base["BodyText"], fontName=self.font_name, fontSize=9.5, leading=13, textColor=colors.HexColor("#37474F")),
            "body_bold": ParagraphStyle("phase8-body-bold", parent=base["BodyText"], fontName=self.bold_font_name, fontSize=9.5, leading=13, textColor=colors.HexColor("#24364A")),
            "muted": ParagraphStyle("phase8-muted", parent=base["BodyText"], fontName=self.font_name, fontSize=8, leading=11, textColor=colors.HexColor("#777777")),
            "line": ParagraphStyle("phase8-line", parent=base["BodyText"], fontName=self.font_name, fontSize=9, leading=15, textColor=colors.HexColor("#999999")),
            "correct": ParagraphStyle("phase8-correct", parent=base["BodyText"], fontName=self.bold_font_name, fontSize=9.5, leading=13, textColor=colors.HexColor("#1E8449")),
        }

    def _find_student(self, activity):
        student_id = activity.get("student_id", activity.get("studentId"))
        return self.student_repository.find_by_id(str(student_id)) if student_id else None

    def _find_classroom(self, activity):
        classroom_id = activity.get("classroom_id", activity.get("classroomId"))
        return self.classroom_repository.find_by_id(str(classroom_id)) if classroom_id else None

    @classmethod
    def _is_correct_option(cls, correct_answer: str | None, option: str) -> bool:
        if not correct_answer:
            return False
        answer = correct_answer.strip()
        normalized = option.strip()
        without_prefix = cls.OPTION_PREFIX.sub("", normalized).strip()
        return (
            normalized.lower() == answer.lower()
            or normalized.lower().startswith((answer + ")").lower())
            or normalized.lower().startswith((answer + ".").lower())
            or normalized.lower().startswith((answer + " ").lower())
            or without_prefix.lower() == answer.lower()
        )

    def _footer(self, document, width, margin):
        document.setFillColor(colors.HexColor("#777777"))
        document.setFont(self.font_name, 8)
        timestamp = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
        document.drawString(margin, 12 * mm, f"Gerado em: {timestamp} | PlusEduc API")
        document.setFillColor(colors.black)

    @staticmethod
    def _register_fonts() -> tuple[str, str]:
        regular = "PlusEduc-Regular"
        bold = "PlusEduc-Bold"
        if regular in pdfmetrics.getRegisteredFontNames():
            return regular, bold
        candidates = [
            ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        ]
        for regular_path, bold_path in candidates:
            if os.path.exists(regular_path) and os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont(regular, regular_path))
                pdfmetrics.registerFont(TTFont(bold, bold_path))
                return regular, bold
        return "Helvetica", "Helvetica-Bold"
