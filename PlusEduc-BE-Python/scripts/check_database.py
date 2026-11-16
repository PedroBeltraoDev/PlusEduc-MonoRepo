"""Verifica a consistência do banco do PlusEduc: referências entre coleções, duplicidades, senhas e índices.

    python scripts/check_database.py                 (banco do .env: MONGODB_URI / MONGODB_DATABASE)
    python scripts/check_database.py --database escola_db --json saida.json

    python scripts/check_database.py --repair        (remove apenas registros órfãos; ver abaixo)

Sem --repair é somente leitura: nada é alterado. O MongoDB não tem chaves estrangeiras, então as relações descritas em
docs/MODELO_DE_DADOS.md são garantidas pela API; este script confere se os dados gravados as respeitam.
Sai com código 1 se alguma verificação marcada como ERRO encontrar problema (AVISO não reprova).

--repair remove só o que não tem como ser recuperado, e mostra o que removeu: respostas cuja atividade não existe
mais e atividades cuja turma e cujo aluno não existem mais (com as respostas delas). Faça um backup (mongodump)
antes de usar em um banco com dados reais.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from bson import ObjectId
from pymongo import MongoClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402

EXPECTED_INDEXES = {
    "users": [("email",)],
    "teachers": [("email",)],
    "students": [("matricula",), ("email",), ("class_id",)],
    "classrooms": [("teacher_id",), ("students",)],
    "grades": [("studentId",), ("classroomId",), ("activityId",)],
    "activities": [("classroom_id",), ("created_by",)],
    "activity_submissions": [("activity_id", "student_id")],
    "audit_logs": [("timestamp",)],
}


def first(document: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if document.get(key) not in (None, ""):
            return document[key]
    return None


def ids_of(collection) -> set[str]:
    return {str(item["_id"]) for item in collection.find({}, {"_id": 1})}


def repair(db) -> None:
    """Remove registros órfãos (sem dono possível). Nunca toca em alunos, turmas, notas ou usuários."""
    classroom_ids, student_ids = ids_of(db.classrooms), ids_of(db.students)
    dead_activities = []
    for activity in db.activities.find({}, {"classroom_id": 1, "classroomId": 1, "student_id": 1, "studentId": 1}):
        classroom, student = first(activity, "classroom_id", "classroomId"), first(activity, "student_id", "studentId")
        classroom_gone = classroom is not None and str(classroom) not in classroom_ids
        student_gone = student is not None and str(student) not in student_ids
        # só quando nada do que a atividade referencia existe mais
        if (classroom_gone or classroom is None) and (student_gone or student is None) and (classroom_gone or student_gone):
            dead_activities.append(activity["_id"])
    if dead_activities:
        db.activities.delete_many({"_id": {"$in": dead_activities}})
    activity_ids = ids_of(db.activities)
    orphans = [s["_id"] for s in db.activity_submissions.find({}, {"activity_id": 1, "activityId": 1})
               if str(first(s, "activity_id", "activityId")) not in activity_ids]
    if orphans:
        db.activity_submissions.delete_many({"_id": {"$in": orphans}})
    print(f"REPARO: {len(dead_activities)} atividade(s) órfã(s) e {len(orphans)} resposta(s) órfã(s) removidas")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificação de consistência do banco do PlusEduc (somente leitura)")
    parser.add_argument("--database", help="nome do banco (padrão: MONGODB_DATABASE)")
    parser.add_argument("--json", help="arquivo para gravar o resultado em JSON")
    parser.add_argument("--repair", action="store_true", help="remove respostas e atividades órfãs antes de verificar")
    args = parser.parse_args()

    settings = get_settings()
    database = args.database or settings.mongodb_database
    db = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)[database]
    if args.repair:
        repair(db)
    results: list[dict[str, Any]] = []

    def check(code: str, level: str, title: str, problems: list[str]) -> None:
        results.append({"id": code, "nivel": level, "verificacao": title, "problemas": len(problems), "exemplos": problems[:5]})

    students = list(db.students.find({}))
    teachers = list(db.teachers.find({}))
    classrooms = list(db.classrooms.find({}))
    users = list(db.users.find({}))
    student_ids, teacher_ids, classroom_ids = ({str(d["_id"]) for d in docs} for docs in (students, teachers, classrooms))
    activity_ids = ids_of(db.activities)
    active = lambda doc: doc.get("active", True) is not False  # noqa: E731
    active_students = {str(s["_id"]): s for s in students if active(s)}
    active_classrooms = {str(c["_id"]): c for c in classrooms if active(c)}

    # ---------------------------------------------------------------- referências
    check("REF-01", "ERRO", "students.class_id aponta para uma turma existente",
          [f"aluno {sid}: turma {first(s, 'class_id', 'classId')}" for sid, s in active_students.items()
           if first(s, "class_id", "classId") and str(first(s, "class_id", "classId")) not in classroom_ids])
    check("REF-02", "ERRO", "classrooms.students[] só tem alunos existentes",
          [f"turma {cid}: aluno {sid}" for cid, c in active_classrooms.items() for sid in map(str, c.get("students") or []) if sid not in student_ids])
    check("REF-03", "AVISO", "matrícula coerente nos dois lados (students.class_id = turma que lista o aluno)",
          [f"turma {cid} lista {sid}, mas o aluno aponta para {first(active_students[sid], 'class_id', 'classId')}"
           for cid, c in active_classrooms.items() for sid in map(str, c.get("students") or [])
           if sid in active_students and str(first(active_students[sid], "class_id", "classId") or "") != cid]
          + [f"aluno {sid} aponta para a turma {first(s, 'class_id', 'classId')}, que não o lista"
             for sid, s in active_students.items()
             if first(s, "class_id", "classId") and str(first(s, "class_id", "classId")) in active_classrooms
             and sid not in map(str, active_classrooms[str(first(s, "class_id", "classId"))].get("students") or [])])
    check("REF-04", "AVISO", "aluno excluído (inativo) não fica na lista de uma turma ativa",
          [f"turma {cid}: aluno inativo {sid}" for cid, c in active_classrooms.items() for sid in map(str, c.get("students") or [])
           if sid in student_ids and sid not in active_students])
    check("REF-05", "ERRO", "classrooms.teacher_id aponta para um professor existente",
          [f"turma {cid}: professor {first(c, 'teacher_id', 'teacherId')}" for cid, c in active_classrooms.items()
           if str(first(c, "teacher_id", "teacherId") or "") not in teacher_ids])
    inactive_teachers = {str(t["_id"]) for t in teachers if not active(t)}
    check("REF-06", "AVISO", "professor responsável de turma ativa está ativo",
          [f"turma {cid}: professor inativo {first(c, 'teacher_id', 'teacherId')}" for cid, c in active_classrooms.items()
           if str(first(c, "teacher_id", "teacherId") or "") in inactive_teachers])
    grades = list(db.grades.find({}, {"studentId": 1, "classroomId": 1, "activityId": 1, "grade": 1}))
    check("REF-07", "ERRO", "grades.studentId e grades.classroomId existem",
          [f"nota {g['_id']}: aluno {g.get('studentId')} / turma {g.get('classroomId')}" for g in grades
           if str(g.get("studentId")) not in student_ids or str(g.get("classroomId")) not in classroom_ids])
    check("REF-08", "AVISO", "grades.activityId (quando preenchido) aponta para uma atividade existente",
          [f"nota {g['_id']}: atividade {g['activityId']}" for g in grades if g.get("activityId") and str(g["activityId"]) not in activity_ids])
    activities = list(db.activities.find({}, {"classroom_id": 1, "classroomId": 1, "student_id": 1, "studentId": 1}))
    check("REF-09", "ERRO", "activities.classroom_id e student_id (quando preenchidos) existem",
          [f"atividade {a['_id']}" for a in activities
           if (first(a, "classroom_id", "classroomId") and str(first(a, "classroom_id", "classroomId")) not in classroom_ids)
           or (first(a, "student_id", "studentId") and str(first(a, "student_id", "studentId")) not in student_ids)])
    submissions = list(db.activity_submissions.find({}, {"activity_id": 1, "activityId": 1, "student_id": 1, "studentId": 1}))
    check("REF-10", "ERRO", "activity_submissions aponta para atividade e aluno existentes (sem respostas órfãs)",
          [f"resposta {s['_id']}" for s in submissions
           if str(first(s, "activity_id", "activityId")) not in activity_ids or str(first(s, "student_id", "studentId")) not in student_ids])
    check("REF-11", "ERRO", "users de aluno (role STUDENT) apontam para um aluno existente",
          [f"usuário {u['email']}: aluno {first(u, 'studentId', 'student_id')}" for u in users
           if u.get("role") == "STUDENT" and active(u) and str(first(u, "studentId", "student_id") or "") not in student_ids])
    teacher_emails = {t.get("email") for t in teachers if active(t)}
    check("REF-12", "AVISO", "users de professor (role TEACHER) têm cadastro ativo em teachers com o mesmo e-mail",
          [f"usuário {u['email']}" for u in users if u.get("role") == "TEACHER" and active(u) and u.get("email") not in teacher_emails])
    active_user_emails = {u.get("email") for u in users if active(u)}
    check("REF-13", "AVISO", "professor ativo tem login (documento em users com o mesmo e-mail)",
          [f"professor {t.get('email')}" for t in teachers if active(t) and t.get("email") not in active_user_emails])

    # ---------------------------------------------------------------- duplicidades e domínios
    for code, title, values in (
        ("DUP-01", "e-mail único entre os usuários ativos", [u.get("email") for u in users if active(u)]),
        ("DUP-02", "matrícula única entre os alunos", [s.get("matricula") for s in students if s.get("matricula")]),
        ("DUP-03", "uma resposta por aluno em cada atividade",
         [(str(first(s, "activity_id", "activityId")), str(first(s, "student_id", "studentId"))) for s in submissions]),
        ("DUP-04", "nome e ano únicos entre as turmas ativas", [(c.get("name"), c.get("year")) for c in active_classrooms.values()]),
    ):
        check(code, "ERRO", title, [f"{value} ({count} vezes)" for value, count in Counter(values).items() if count > 1])
    check("DOM-01", "ERRO", "papel do usuário é ADMIN, TEACHER ou STUDENT",
          [f"{u.get('email')}: {u.get('role')}" for u in users if u.get("role") not in {"ADMIN", "TEACHER", "STUDENT"}])
    check("DOM-02", "ERRO", "notas entre 0 e 10",
          [f"nota {g['_id']}: {g.get('grade')}" for g in grades if not isinstance(g.get("grade"), (int, float)) or not 0 <= g["grade"] <= 10])
    check("DOM-03", "ERRO", "senhas gravadas com bcrypt (nunca em texto puro) em users e teachers",
          [f"{name} {d.get('email')}" for name, docs in (("users", users), ("teachers", teachers)) for d in docs
           if d.get("password") and not str(d["password"]).startswith(("$2a$", "$2b$", "$2y$"))])
    check("DOM-04", "AVISO", "no máximo 5 turmas ativas por professor",
          [f"professor {tid}: {count} turmas" for tid, count in Counter(str(first(c, "teacher_id", "teacherId")) for c in active_classrooms.values()).items() if count > 5])

    # ---------------------------------------------------------------- índices
    existing = set(db.list_collection_names())
    missing = []
    for collection, wanted in EXPECTED_INDEXES.items():
        if collection not in existing:
            continue
        present = [tuple(index["key"].keys()) for index in db[collection].list_indexes()]
        missing += [f"{collection}{list(fields)}" for fields in wanted if not any(keys[: len(fields)] == fields for keys in present)]
    check("IDX-01", "ERRO", "índices esperados existem (criados pela API ao iniciar)", missing)

    width = max(len(r["verificacao"]) for r in results)
    print(f"Banco: {database} | coleções: " + ", ".join(f"{name}={db[name].count_documents({})}" for name in sorted(existing)))
    for r in results:
        status = "ok" if r["problemas"] == 0 else r["nivel"]
        print(f"{r['id']}  {r['verificacao']:<{width}}  {status:<5} {r['problemas'] or ''}")
        for example in r["exemplos"]:
            print(f"        - {example}")
    errors = sum(1 for r in results if r["nivel"] == "ERRO" and r["problemas"])
    warnings = sum(1 for r in results if r["nivel"] == "AVISO" and r["problemas"])
    print(f"RESUMO: {len(results)} verificações; {errors} com erro; {warnings} com aviso")
    if args.json:
        Path(args.json).write_text(json.dumps({"banco": database, "resultados": results}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
