from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import random
import re
import sys

from bson import ObjectId
from pymongo import MongoClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.passwords import hash_password

URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE = os.getenv("MONGODB_DATABASE", "escola_db")
SEED = "demo-population-2026"
DEMO_PASSWORD = os.getenv("PLUS_EDUC_DEMO_PASSWORD")
if not DEMO_PASSWORD:
    raise SystemExit("Defina PLUS_EDUC_DEMO_PASSWORD antes de executar o seed.")
RNG = random.Random(20260821)
NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

FIRST_NAMES = [
    "Gabriel", "Laura", "Miguel", "Sofia", "Rafael", "Helena", "Arthur", "Beatriz", "Lucas", "Manuela",
    "Gustavo", "Valentina", "Bernardo", "Isabela", "Samuel", "Lívia", "Enzo", "Mariana", "Theo", "Alice",
    "Davi", "Clara", "Heitor", "Luiza", "Nicolas", "Cecília", "Lorenzo", "Julia", "Matheus", "Eloá",
    "João", "Yasmin", "Breno", "Lorena", "Caio", "Heloísa", "Eduardo", "Maria", "Vitor", "Sarah",
    "Leonardo", "Ana", "Guilherme", "Maitê", "Vinícius", "Esther", "Pedro", "Nicole", "Felipe", "Amanda",
    "Rodrigo", "Carolina", "Diego", "Bárbara", "André", "Rebeca", "Bruno", "Letícia", "Daniel", "Isadora",
]
LAST_NAMES = ["Almeida", "Barbosa", "Cardoso", "Dias", "Freitas", "Gomes", "Lima", "Mendes", "Nogueira", "Ramos"]


def text_id(value) -> str:
    return str(value)


def classroom_members(classroom: dict) -> list[str]:
    return [text_id(value) for value in (classroom.get("students") or classroom.get("studentIds") or classroom.get("student_ids") or [])]


def next_matricula(students: list[dict]) -> str:
    highest = 0
    for student in students:
        match = re.search(r"MAT-\d{4}-(\d+)", str(student.get("matricula", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"MAT-2026-{highest + 1:04d}"


def student_user(db, student: dict, password_hash: str) -> str:
    student_id = text_id(student["_id"])
    email = str(student.get("email", "")).lower()
    user = db.users.find_one({"$or": [{"studentId": student_id}, {"email": email}]})
    if user:
        user_id = text_id(user["_id"])
        db.users.update_one({"_id": user["_id"]}, {"$set": {"studentId": student_id, "role": "STUDENT", "active": True, "password": password_hash, "updated_at": NOW}})
        db.students.update_one({"_id": student["_id"]}, {"$set": {"user_id": user_id}})
        return user_id
    user_id = ObjectId()
    db.users.insert_one({
        "_id": user_id,
        "email": email,
        "password": password_hash,
        "role": "STUDENT",
        "studentId": student_id,
        "active": True,
        "created_at": NOW,
        "updated_at": NOW,
        "created_by": SEED,
    })
    db.students.update_one({"_id": student["_id"]}, {"$set": {"user_id": text_id(user_id)}})
    return text_id(user_id)


def create_student(db, students: list[dict], classroom_id: str, index: int, password_hash: str) -> dict:
    matricula = next_matricula(students)
    first = FIRST_NAMES[index % len(FIRST_NAMES)]
    last = LAST_NAMES[(index // len(FIRST_NAMES)) % len(LAST_NAMES)]
    name = f"{first} {last}"
    email = f"aluno.demo.{matricula[-4:]}@aluno.local"
    document = {
        "_id": ObjectId(),
        "name": name,
        "email": email,
        "matricula": matricula,
        "birth_date": datetime(2010 + (index % 5), 2 + (index % 9), 10 + (index % 15), tzinfo=timezone.utc),
        "class_id": classroom_id,
        "learning_gaps": [],
        "active": True,
        "created_at": NOW,
        "updated_at": NOW,
        "created_by": SEED,
        "updated_by": SEED,
        "demo_population_key": f"{SEED}-student-{matricula}",
    }
    db.students.insert_one(document)
    student_user(db, document, password_hash)
    students.append(document)
    return document


def gap_for(student: dict, subject: str, index: int) -> None:
    student_id = text_id(student["_id"])
    gap = {
        "id": f"{SEED}-gap-{student_id}-{index}",
        "subject": subject,
        "topic": "Interpretação e resolução de problemas",
        "severity_level": "MEDIO" if index % 2 else "ALTO",
        "description": "Precisa consolidar estratégias e explicar o raciocínio com mais clareza.",
        "identifiedAt": NOW - timedelta(days=30),
        "lastAssessedAt": NOW - timedelta(days=3),
        "improved": False,
    }
    db.students.update_one({"_id": student["_id"]}, {"$addToSet": {"learning_gaps": gap}})


def questions_for(kind: str, subject: str) -> list[dict]:
    if kind == "objective":
        return [
            {
                "questionText": f"Qual conceito é fundamental para estudar {subject.lower()}?",
                "questionType": "MULTIPLA_ESCOLHA",
                "options": ["Organização e observação", "Decorar sem compreender", "Ignorar exemplos", "Não revisar"],
                "correctAnswer": "Organização e observação",
                "explanation": "A aprendizagem melhora quando o estudante observa, organiza e revisa os conceitos.",
                "difficultyLevel": "MEDIO",
            },
            {
                "questionText": "Qual atitude ajuda a resolver uma questão difícil?",
                "questionType": "MULTIPLA_ESCOLHA",
                "options": ["Ler o enunciado e montar uma estratégia", "Pular todas as etapas", "Chutar sempre", "Não conferir a resposta"],
                "correctAnswer": "Ler o enunciado e montar uma estratégia",
                "explanation": "A leitura cuidadosa e uma estratégia explícita tornam o raciocínio verificável.",
                "difficultyLevel": "MEDIO",
            },
            {
                "questionText": "Por que explicar o raciocínio é importante?",
                "questionType": "MULTIPLA_ESCOLHA",
                "options": ["Para identificar etapas e melhorar", "Para aumentar o enunciado", "Para evitar estudar", "Para substituir a resposta"],
                "correctAnswer": "Para identificar etapas e melhorar",
                "explanation": "Explicar o raciocínio permite localizar acertos e pontos que precisam de revisão.",
                "difficultyLevel": "MEDIO",
            },
        ]
    return [
        {
            "questionText": f"Explique com suas palavras como você estudaria o tema de {subject.lower()}.",
            "questionType": "DISCURSIVA",
            "options": [],
            "correctAnswer": None,
            "explanation": "A resposta deve apresentar uma estratégia coerente e exemplos.",
            "difficultyLevel": "DIFICIL",
        },
        {
            "questionText": "Cite uma dificuldade encontrada e descreva como pretende superá-la.",
            "questionType": "DISCURSIVA",
            "options": [],
            "correctAnswer": None,
            "explanation": "A reflexão deve relacionar dificuldade, estratégia e acompanhamento.",
            "difficultyLevel": "DIFICIL",
        },
    ]


def upsert_activity(db, classroom: dict, teacher_email: str, subject: str, kind: str) -> dict:
    classroom_id = text_id(classroom["_id"])
    marker = f"{SEED}-activity-{classroom_id}-{kind}"
    questions = questions_for(kind, subject)
    document = {
        "title": f"Demonstração | {'Atividade objetiva' if kind == 'objective' else 'Atividade discursiva'} | {classroom.get('name', '')}",
        "subject": subject,
        "topic": "Revisão e acompanhamento de aprendizagem",
        "difficulty_level": "MEDIO" if kind == "objective" else "DIFICIL",
        "questions_count": len(questions),
        "format": "MULTIPLA_ESCOLHA" if kind == "objective" else "DISCURSIVA",
        "classroom_id": classroom_id,
        "disability_adaptations": [],
        "content": json.dumps({"questions": questions}, ensure_ascii=False),
        "generated_by_ai": True,
        "ai_provider": "Demo Seed",
        "created_by": teacher_email,
        "created_at": NOW,
        "demo_population_key": marker,
    }
    db.activities.update_one({"demo_population_key": marker}, {"$setOnInsert": document}, upsert=True)
    return db.activities.find_one({"demo_population_key": marker})


def upsert_grade(db, student: dict, classroom: dict, subject: str, grade: float, attendance: bool, ordinal: int) -> None:
    student_id = text_id(student["_id"])
    classroom_id = text_id(classroom["_id"])
    marker = f"{SEED}-grade-{student_id}-{classroom_id}-{subject.lower().replace(' ', '-') }"
    db.grades.update_one(
        {"demo_population_key": marker},
        {"$setOnInsert": {
            "studentId": student_id,
            "classroomId": classroom_id,
            "subject": subject,
            "grade": grade,
            "attendance": attendance,
            "date": (NOW - timedelta(days=ordinal * 7)).replace(tzinfo=None).isoformat(),
            "activityType": "DEMO_SEED",
            "observations": "Registro criado para demonstração de desempenho.",
            "created_at": NOW,
            "demo_population_key": marker,
        }},
        upsert=True,
    )


def submission_content(kind: str, reviewed: bool, student_name: str, subject: str) -> str:
    if kind == "objective":
        results = [
            {"questionIndex": 0, "questionText": f"Qual conceito é fundamental para estudar {subject.lower()}?", "questionType": "MULTIPLA_ESCOLHA", "options": ["Organização e observação", "Decorar sem compreender", "Ignorar exemplos", "Não revisar"], "selectedAnswer": "Organização e observação", "correctAnswer": "Organização e observação", "correct": True, "reviewStatus": "AUTO_GRADED"},
            {"questionIndex": 1, "questionText": "Qual atitude ajuda a resolver uma questão difícil?", "questionType": "MULTIPLA_ESCOLHA", "options": ["Ler o enunciado e montar uma estratégia", "Pular todas as etapas", "Chutar sempre", "Não conferir a resposta"], "selectedAnswer": "Pular todas as etapas" if student_name.endswith("0") else "Ler o enunciado e montar uma estratégia", "correctAnswer": "Ler o enunciado e montar uma estratégia", "correct": not student_name.endswith("0"), "reviewStatus": "AUTO_GRADED"},
            {"questionIndex": 2, "questionText": "Por que explicar o raciocínio é importante?", "questionType": "MULTIPLA_ESCOLHA", "options": ["Para identificar etapas e melhorar", "Para aumentar o enunciado", "Para evitar estudar", "Para substituir a resposta"], "selectedAnswer": "Para identificar etapas e melhorar", "correctAnswer": "Para identificar etapas e melhorar", "correct": True, "reviewStatus": "AUTO_GRADED"},
        ]
        correct_count = sum(1 for item in results if item["correct"])
        return json.dumps({"answers": [{"questionIndex": item["questionIndex"], "selectedAnswer": item["selectedAnswer"]} for item in results], "results": results, "correctCount": correct_count, "totalQuestions": 3, "scorePercent": round(correct_count * 100 / 3), "pendingCount": 0}, ensure_ascii=False)

    results = [
        {"questionIndex": 0, "questionText": f"Explique com suas palavras como você estudaria o tema de {subject.lower()}.", "questionType": "DISCURSIVA", "options": [], "selectedAnswer": f"Eu revisaria os conceitos, faria exemplos e pediria feedback. Sou {student_name}.", "correctAnswer": None, "correct": reviewed, "reviewStatus": "REVIEWED" if reviewed else "PENDING", "teacherFeedback": "Boa estratégia; desenvolva mais os exemplos." if reviewed else None, "reviewedBy": "professor@pluseduc.com" if reviewed else None, "reviewedAt": (NOW - timedelta(days=2)).isoformat() if reviewed else None},
            {"questionIndex": 1, "questionText": "Cite uma dificuldade encontrada e descreva como pretende superá-la.", "questionType": "DISCURSIVA", "options": [], "selectedAnswer": "Minha dificuldade é organizar o raciocínio; vou separar a tarefa em etapas.", "correct": reviewed, "correctAnswer": None, "reviewStatus": "REVIEWED" if reviewed else "PENDING", "teacherFeedback": "Resposta coerente." if reviewed else None, "reviewedBy": "professor@pluseduc.com" if reviewed else None, "reviewedAt": (NOW - timedelta(days=2)).isoformat() if reviewed else None},
    ]
    correct_count = 2 if reviewed else 0
    return json.dumps({"answers": [{"questionIndex": item["questionIndex"], "selectedAnswer": item["selectedAnswer"]} for item in results], "results": results, "correctCount": correct_count, "totalQuestions": 2, "scorePercent": 100 if reviewed else 0, "pendingCount": 0 if reviewed else 2}, ensure_ascii=False)


def upsert_submission(db, activity: dict, student: dict, kind: str, reviewed: bool) -> None:
    activity_id = text_id(activity["_id"])
    student_id = text_id(student["_id"])
    marker = f"{SEED}-submission-{activity_id}-{student_id}"
    content = submission_content(kind, reviewed, str(student.get("name", "Aluno")), str(activity.get("subject", "Matéria")))
    db.activity_submissions.update_one(
        {"demo_population_key": marker},
        {"$setOnInsert": {"activity_id": activity_id, "student_id": student_id, "content": content, "submitted_at": NOW - timedelta(days=1), "demo_population_key": marker}},
        upsert=True,
    )


client = MongoClient(URI, serverSelectionTimeoutMS=5000)
client.admin.command("ping")
db = client[DATABASE]
password_hash = hash_password(DEMO_PASSWORD)

students = list(db.students.find({"active": {"$ne": False}}).sort("matricula", 1))
classrooms = list(db.classrooms.find({"active": {"$ne": False}}).sort("name", 1))
teachers = {text_id(item["_id"]): item for item in db.teachers.find({"active": {"$ne": False}})}

# Normalize the two old test rooms into presentable demo rooms and copy the complete
# 6th-grade curricular assignments without reusing any student membership.
curricular_template = next((item for item in classrooms if str(item.get("grade_level") or item.get("gradeLevel") or "") == "6º Ano do Ensino Fundamental" and "tempor" not in str(item.get("name", "")).lower()), None)
temporary_index = 0
for classroom in classrooms:
    if "tempor" in str(classroom.get("name", "")).lower():
        temporary_index += 1
        new_name = f"Turma 6º Ano do Ensino Fundamental {chr(ord('B') + temporary_index - 1)}"
        updates = {"name": new_name}
        if curricular_template:
            updates["subjects"] = curricular_template.get("subjects", [])
            updates["subjectTeachers"] = curricular_template.get("subjectTeachers", [])
        db.classrooms.update_one({"_id": classroom["_id"]}, {"$set": updates})
        classroom.update(updates)

# Complete every active demonstration classroom to at least five students.
created_students = 0
assigned_existing = 0
for classroom in classrooms:
    members = classroom_members(classroom)
    while len(members) < 5:
        available = [student for student in students if not student.get("class_id") and text_id(student["_id"]) not in members]
        if available:
            student = RNG.choice(available)
            assigned_existing += 1
        else:
            student = create_student(db, students, text_id(classroom["_id"]), len(students) + created_students, password_hash)
            created_students += 1
        student_id = text_id(student["_id"])
        db.classrooms.update_one({"_id": classroom["_id"]}, {"$addToSet": {"students": student_id}})
        db.students.update_one({"_id": student["_id"]}, {"$set": {"class_id": text_id(classroom["_id"]), "updated_at": NOW}})
        members.append(student_id)
    classroom["students"] = members

# Normalize legacy seed-grade markers and remove only duplicate records created by
# earlier executions of this same demo seed. Existing non-seed grades are untouched.
seen_grade_keys: set[tuple[str, str, str]] = set()
legacy_grades = list(db.grades.find({"demo_population_key": {"$regex": f"^{SEED}-grade-"}}).sort("_id", 1))
for legacy_grade in legacy_grades:
    grade_key = (str(legacy_grade.get("studentId", legacy_grade.get("student_id", ""))), str(legacy_grade.get("classroomId", legacy_grade.get("classroom_id", ""))), str(legacy_grade.get("subject", "")).lower())
    if grade_key in seen_grade_keys:
        db.grades.delete_one({"_id": legacy_grade["_id"]})
        continue
    seen_grade_keys.add(grade_key)
    canonical_marker = f"{SEED}-grade-{grade_key[0]}-{grade_key[1]}-{grade_key[2].replace(' ', '-') }"
    if legacy_grade.get("demo_population_key") != canonical_marker:
        db.grades.update_one({"_id": legacy_grade["_id"]}, {"$set": {"demo_population_key": canonical_marker}})

# Ensure newly created/linked students have a user and add explainable learning gaps to a subset.
for index, student in enumerate(students):
    student_user(db, student, password_hash)
    if index % 4 == 0:
        subject = "Matemática" if index % 2 == 0 else "Língua Portuguesa"
        gap_for(student, subject, index)

created_activities = 0
created_grades = 0
created_submissions = 0
for classroom_index, classroom in enumerate(classrooms):
    classroom_id = text_id(classroom["_id"])
    teacher = teachers.get(text_id(classroom.get("teacher_id") or classroom.get("teacherId")))
    teacher_email = str((teacher or {}).get("email", "professor@pluseduc.com"))
    grade_level = str(classroom.get("grade_level") or classroom.get("gradeLevel") or "")
    subject = "Física" if "Médio" in grade_level else "Matemática"
    members = [next(student for student in students if text_id(student["_id"]) == student_id) for student_id in classroom_members(classroom)]
    objective = upsert_activity(db, classroom, teacher_email, subject, "objective")
    written = upsert_activity(db, classroom, teacher_email, subject, "written")
    created_activities += 2

    for student_index, student in enumerate(members):
        base = 6.0 + ((classroom_index * 3 + student_index * 2) % 41) / 10
        for ordinal, grade_subject in enumerate([subject, "Língua Portuguesa", "Ciências"]):
            upsert_grade(db, student, classroom, grade_subject, round(min(base + ordinal * 0.4, 10.0), 1), attendance=(student_index + ordinal) % 5 != 0, ordinal=ordinal + classroom_index + 1)
            created_grades += 1

        # Participation is intentionally partial: some completed, some pending.
        if student_index % 3 != 0:
            upsert_submission(db, objective, student, "objective", reviewed=False)
            created_submissions += 1
        if student_index % 2 == 0:
            upsert_submission(db, written, student, "written", reviewed=(student_index % 4 == 0))
            created_submissions += 1

result = {
    "database": DATABASE,
    "seed": SEED,
    "targetClassrooms": len(classrooms),
    "createdStudents": created_students,
    "assignedExistingStudents": assigned_existing,
    "studentsAfter": db.students.count_documents({"active": {"$ne": False}}),
    "activitiesAfter": db.activities.count_documents({}),
    "gradesAfter": db.grades.count_documents({}),
    "submissionsAfter": db.activity_submissions.count_documents({}),
    "upsertOperations": {"activities": created_activities, "grades": created_grades, "submissions": created_submissions},
}
print(json.dumps(result, ensure_ascii=False))
client.close()
