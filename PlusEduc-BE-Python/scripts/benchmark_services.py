"""Benchmark dos serviços mais pesados: conta consultas ao MongoDB e mede o tempo.

Usa um banco TEMPORÁRIO (``pluseduc_bench_<hex>``) criado e apagado pelo próprio script;
nunca toca no banco configurado em ``MONGODB_DATABASE``. Só o servidor (``MONGODB_URI``) é reaproveitado.

    python scripts/benchmark_services.py [--classrooms 8] [--students 30] [--activities 40]
        [--latency-ms 20]   # simula o RTT de um MongoDB remoto (ex.: Atlas) em cada comando
        [--sequential]      # desliga o paralelismo intra-requisição para comparar
"""
from __future__ import annotations

import argparse
import secrets
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bson import ObjectId  # noqa: E402
from pymongo import MongoClient, monitoring  # noqa: E402

from app.core.auth import UserPrincipal  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.core.database import MongoConnection  # noqa: E402
from app.repositories.activity_repository import ActivityRepository  # noqa: E402
from app.repositories.activity_submission_repository import ActivitySubmissionRepository  # noqa: E402
from app.repositories.classroom_repository import ClassroomRepository  # noqa: E402
from app.repositories.grade_repository import GradeRepository  # noqa: E402
from app.repositories.student_repository import StudentRepository  # noqa: E402
from app.repositories.teacher_repository import TeacherRepository  # noqa: E402
from app.services.activity_service import ActivityService  # noqa: E402
from app.services.classroom_service import ClassroomService  # noqa: E402
from app.services.grade_service import GradeService  # noqa: E402
from app.services.teacher_correction_service import TeacherCorrectionService  # noqa: E402


class CommandCounter(monitoring.CommandListener):
    def __init__(self) -> None:
        self.count = 0
        self.latency_seconds = 0.0

    def started(self, event) -> None:
        if self.latency_seconds and event.command_name in {"find", "aggregate", "count", "getMore", "insert", "update", "delete"}:
            time.sleep(self.latency_seconds)  # roda na thread que emitiu o comando, como uma espera de rede
        if event.command_name in {"find", "aggregate", "count", "getMore", "insert", "update", "delete"}:
            self.count += 1

    def succeeded(self, event) -> None:
        pass

    def failed(self, event) -> None:
        pass


COUNTER = CommandCounter()
monitoring.register(COUNTER)


def seed(db, classrooms: int, students: int, activities: int) -> UserPrincipal:
    now = datetime.now(timezone.utc)
    teacher_id = ObjectId()
    db.teachers.insert_one({"_id": teacher_id, "name": "Prof Bench", "email": "bench@x.local", "active": True})
    discursive = (
        '{"correctCount":0,"totalQuestions":1,"scorePercent":0,"pendingCount":1,"results":'
        '[{"questionIndex":0,"questionText":"Explique","questionType":"DISCURSIVA","selectedAnswer":"x",'
        '"correct":false,"reviewStatus":"PENDING"}]}'
    )
    classroom_ids: list[str] = []
    for c in range(classrooms):
        classroom_id = ObjectId()
        student_docs = [
            {"_id": ObjectId(), "name": f"Aluno {c}-{s}", "email": f"a{c}.{s}@x.local", "active": True,
             "class_id": str(classroom_id), "learning_gaps": []}
            for s in range(students)
        ]
        db.students.insert_many(student_docs)
        db.classrooms.insert_one({
            "_id": classroom_id, "name": f"Turma {c}", "year": now.year, "grade_level": "6º ano",
            "teacher_id": str(teacher_id), "students": [str(d["_id"]) for d in student_docs],
            "subjects": ["Matemática"], "subjectTeachers": [{"subjectId": "s", "subjectName": "Matemática", "teacherId": str(teacher_id)}],
            "active": True, "created_at": now, "updated_at": now,
        })
        classroom_ids.append(str(classroom_id))
        for index in range(activities // max(classrooms, 1)):
            activity_id = ObjectId()
            db.activities.insert_one({
                "_id": activity_id, "title": f"Atividade {c}-{index}", "subject": "Matemática", "topic": "Frações",
                "classroom_id": str(classroom_id), "created_by": str(teacher_id), "created_at": now, "content": "{}",
            })
            for doc in student_docs[: students // 2]:
                db.activity_submissions.insert_one({
                    "activity_id": str(activity_id), "student_id": str(doc["_id"]),
                    "submitted_at": now, "content": discursive,
                })
                db.grades.insert_one({
                    "studentId": str(doc["_id"]), "classroomId": str(classroom_id), "grade": 7.5,
                    "subject": "Matemática", "date": now,
                })
    return UserPrincipal(user_id=str(teacher_id), email="bench@x.local", role="TEACHER")


def measure(label: str, fn, runs: int = 5) -> None:
    fn()  # aquecimento (conexões, imports preguiçosos)
    counts: list[int] = []
    times: list[float] = []
    for _ in range(runs):
        COUNTER.count = 0
        started = time.perf_counter()
        fn()
        times.append((time.perf_counter() - started) * 1000)
        counts.append(COUNTER.count)
    print(f"{label:<42} consultas={counts[-1]:>5}   tempo mediano={statistics.median(times):>8.1f} ms")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classrooms", type=int, default=8)
    parser.add_argument("--students", type=int, default=30)
    parser.add_argument("--activities", type=int, default=40)
    parser.add_argument("--latency-ms", type=float, default=0.0)
    parser.add_argument("--sequential", action="store_true")
    args = parser.parse_args()
    if args.sequential:
        for module in list(sys.modules.values()):
            if getattr(module, "run_parallel", None) is not None and module.__name__.startswith("app."):
                module.run_parallel = lambda *tasks: [task() for task in tasks]

    base = Settings(_env_file=None, jwt_secret="bench-only-secret-bench-only-secret")
    database_name = f"pluseduc_bench_{secrets.token_hex(4)}"
    settings = base.model_copy(update={"mongodb_database": database_name})
    mongo = MongoConnection(settings)
    mongo.connect()
    admin = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    try:
        user = seed(mongo.database, args.classrooms, args.students, args.activities)
        students = StudentRepository(mongo)
        classrooms = ClassroomRepository(mongo)
        teachers = TeacherRepository(mongo)
        grades = GradeRepository(mongo)
        activities = ActivityRepository(mongo)
        submissions = ActivitySubmissionRepository(mongo)
        classroom_service = ClassroomService(classrooms, students, teachers, grades)
        activity_service = ActivityService(activities, students, classrooms, mongo, settings, submissions)
        correction_service = TeacherCorrectionService(activities, submissions, classrooms, students)
        grade_service = GradeService(grades, students, classrooms, activities, submissions)
        first_classroom = str(classrooms.find_active()[0]["_id"])
        COUNTER.latency_seconds = args.latency_ms / 1000

        print(f"Banco temporário: {database_name}  ({args.classrooms} turmas x {args.students} alunos, {args.activities} atividades, latência simulada {args.latency_ms:g} ms, {'sequencial' if args.sequential else 'paralelo'})")
        measure("ClassroomService.list_active", classroom_service.list_active)
        measure("ActivityService.list_all", activity_service.list_all)
        measure("ActivityService.list_all(participation)", lambda: activity_service.list_all(True))
        measure("ActivityService.by_teacher", lambda: activity_service.by_teacher(user.user_id))
        measure("TeacherCorrectionService.list_pending", lambda: correction_service.list_pending(user))
        measure("GradeService.classroom_summary", lambda: grade_service.classroom_summary(first_classroom))
    finally:
        admin.drop_database(database_name)
        admin.close()
        mongo.close()
        print(f"Banco temporário {database_name} removido.")


if __name__ == "__main__":
    main()
