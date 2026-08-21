from app.services.pedagogical_recommendation_service import PedagogicalRecommendationService


class FakeStudentRepository:
    def find_by_id(self, student_id: str):
        if student_id != "student-1":
            return None
        return {
            "_id": student_id,
            "name": "Aluno de Teste",
            "learningGaps": [
                {
                    "subject": "Matematica",
                    "topic": "Equacoes do Segundo Grau",
                    "severity_level": "HIGH",
                    "improved": False,
                },
                {
                    "subject": "Portugues",
                    "topic": "Interpretacao de Texto",
                    "severity_level": "MEDIUM",
                    "improved": False,
                },
            ],
        }


class FakeGradeRepository:
    def find_by_student(self, student_id: str):
        return [
            {"student_id": student_id, "subject": "Matemática", "gradeValue": 4.0},
            {"student_id": student_id, "subject": "Matemática", "gradeValue": 5.0},
            {"student_id": student_id, "subject": "Português", "gradeValue": 8.0},
        ]


class FakeClassroomRepository:
    pass


def test_recommendation_prioritizes_high_severity_gap_and_low_average():
    service = PedagogicalRecommendationService(
        FakeStudentRepository(),
        FakeGradeRepository(),
        FakeClassroomRepository(),
    )

    result = service.recommend("student-1")

    assert result.studentName == "Aluno de Teste"
    assert result.recommendedSubject == "Matematica"
    assert result.recommendedTopic == "Equacoes do Segundo Grau"
    assert result.priority == "HIGH"
    assert result.recommendedDifficulty == "FACIL"
    assert result.recommendedQuestionsCount == 5
    assert result.evidences
    assert "lacuna" in result.rationale.lower()


def test_recommendation_returns_diagnostic_when_student_has_no_learning_data():
    class EmptyStudentRepository:
        def find_by_id(self, student_id: str):
            return {"_id": student_id, "name": "Aluno Sem Histórico", "learningGaps": []}

    class EmptyGradeRepository:
        def find_by_student(self, student_id: str):
            return []

    result = PedagogicalRecommendationService(
        EmptyStudentRepository(),
        EmptyGradeRepository(),
        FakeClassroomRepository(),
    ).recommend("student-2")

    assert result.priority == "LOW"
    assert result.recommendedTopic == "Revisão dos conteúdos recentes"
    assert result.recommendedQuestionsCount == 3
    assert result.evidences[0].signal == "diagnóstico inicial"
