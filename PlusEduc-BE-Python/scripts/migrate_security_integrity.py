"""Migração idempotente de segurança e integridade dos dados (pode ser executada várias vezes).

O que faz, sem apagar documentos:

1. Senhas em ``teachers``: o campo ``password`` deixa de existir nessa coleção. Se o professor não
   tem conta em ``users``, a conta é criada; uma senha antiga em texto puro é convertida para bcrypt
   (uma senha que já era hash bcrypt é aproveitada). O texto puro nunca é impresso.
2. Contas de professor: professor ativo sem conta recebe uma conta TEACHER; professor inativo tem a
   conta desativada.
3. Contas de aluno: aluno desativado tem a conta do portal desativada.
4. Vínculo aluno/turma: ``students.class_id`` e ``classrooms.students`` ficam coerentes; um aluno
   fica em uma única turma (a do ``class_id``; sem ``class_id``, a primeira turma ativa que o lista).
5. Contas duplicadas por e-mail com letras maiúsculas/minúsculas são apenas relatadas.

Uso (PowerShell, a partir de PlusEduc-BE-Python):

    .\\.venv\\Scripts\\python.exe scripts\\migrate_security_integrity.py            # simulação
    .\\.venv\\Scripts\\python.exe scripts\\migrate_security_integrity.py --apply    # grava

Variáveis: MONGODB_URI e MONGODB_DATABASE (padrão: o .env do backend).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from pymongo import MongoClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.core.passwords import hash_password  # noqa: E402


def is_bcrypt(value: object) -> bool:
    return isinstance(value, str) and value.startswith(("$2a$", "$2b$", "$2y$")) and len(value) == 60


def text(value: object) -> str:
    return "" if value is None else str(value)


def migrate(db, apply: bool) -> dict:
    now = datetime.now(timezone.utc)
    report: dict[str, int | list] = defaultdict(int)

    users_by_email = {text(u.get("email")).lower(): u for u in db.users.find({}, {"email": 1, "role": 1, "active": 1, "password": 1})}

    # 1 e 2: professores
    for teacher in db.teachers.find({}):
        email = text(teacher.get("email")).strip().lower()
        if not email:
            continue
        legacy = teacher.get("password")
        user = users_by_email.get(email)
        active = teacher.get("active", True) is not False
        if user is None:
            password_hash = None
            if legacy:
                password_hash = legacy if is_bcrypt(legacy) else hash_password(str(legacy))
                report["teacher_plaintext_passwords_hashed" if not is_bcrypt(legacy) else "teacher_hashes_moved"] += 1
            pending = teacher.get("approval_status") == "PENDING"
            document = {
                "email": email,
                "role": "TEACHER",
                "active": active and not pending,
                "tokenVersion": 0,
                "name": teacher.get("name"),
                "createdAt": now,
                "migratedFrom": "teachers",
            }
            if password_hash:
                document["password"] = password_hash
            if pending:
                # Cadastro público ainda não aprovado: continua aguardando o ADMIN (RF04).
                document["pendingApproval"] = True
            report["teacher_users_created"] += 1
            if apply:
                db.users.insert_one(document)
        else:
            if legacy and not is_bcrypt(legacy):
                report["teacher_plaintext_passwords_discarded"] += 1  # a conta em users já tem a senha válida
            if not active and user.get("active", True) is not False:
                report["teacher_users_deactivated"] += 1
                if apply:
                    db.users.update_one({"_id": user["_id"]}, {"$set": {"active": False, "updatedAt": now}, "$inc": {"tokenVersion": 1}})
        if "password" in teacher:
            report["teacher_password_fields_removed"] += 1
            if apply:
                db.teachers.update_one({"_id": teacher["_id"]}, {"$unset": {"password": ""}})
        if email != teacher.get("email"):
            report["teacher_emails_normalized"] += 1
            if apply:
                db.teachers.update_one({"_id": teacher["_id"]}, {"$set": {"email": email}})

    # 3: alunos desativados com conta ativa
    for student in db.students.find({"active": False}, {"email": 1, "user_id": 1}):
        email = text(student.get("email")).lower()
        user = users_by_email.get(email)
        if user and user.get("role") == "STUDENT" and user.get("active", True) is not False:
            report["student_users_deactivated"] += 1
            if apply:
                db.users.update_one({"_id": user["_id"]}, {"$set": {"active": False, "updatedAt": now}, "$inc": {"tokenVersion": 1}})

    # 4: coerência entre students.class_id e classrooms.students
    classrooms = list(db.classrooms.find({}, {"students": 1, "active": 1, "name": 1}))
    active_ids = {text(c["_id"]) for c in classrooms if c.get("active", True) is not False}
    listed_in: dict[str, list[str]] = defaultdict(list)
    for classroom in classrooms:
        for member in classroom.get("students", []) or []:
            listed_in[text(member)].append(text(classroom["_id"]))

    for student in db.students.find({"active": {"$ne": False}}, {"class_id": 1, "classId": 1}):
        student_id = text(student["_id"])
        class_id = text(student.get("class_id") or student.get("classId"))
        lists = listed_in.get(student_id, [])
        if class_id and class_id not in active_ids:
            report["students_pointing_to_inactive_or_missing_class"] += 1
            if apply:
                db.students.update_one({"_id": student["_id"]}, {"$set": {"class_id": None, "updated_at": now}})
            class_id = ""
        target = class_id or next((cid for cid in lists if cid in active_ids), "")
        if target and not class_id:
            report["students_class_id_restored"] += 1
            if apply:
                db.students.update_one({"_id": student["_id"]}, {"$set": {"class_id": target, "updated_at": now}})
        if target and target not in lists:
            report["students_added_to_class_list"] += 1
            if apply:
                db.classrooms.update_one({"_id": next(c["_id"] for c in classrooms if text(c["_id"]) == target)}, {"$addToSet": {"students": student_id}})
        extra = [cid for cid in lists if cid != target]
        if extra:
            report["duplicate_memberships_removed"] += len(extra)
            if apply:
                for cid in extra:
                    db.classrooms.update_one(
                        {"_id": next(c["_id"] for c in classrooms if text(c["_id"]) == cid)},
                        {"$pull": {"students": {"$in": [student_id, student["_id"]]}}},
                    )

    # 5: e-mails duplicados (só relatório; resolver manualmente)
    seen: dict[str, int] = defaultdict(int)
    for user in db.users.find({}, {"email": 1}):
        seen[text(user.get("email")).strip().lower()] += 1
    report["duplicate_user_emails"] = sorted(email for email, count in seen.items() if count > 1 and email)
    return dict(report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="grava as alterações (sem isto, só simula)")
    args = parser.parse_args()
    settings = Settings(_env_file=str(BACKEND_ROOT / ".env"))
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    try:
        result = migrate(client[settings.mongodb_database], args.apply)
    finally:
        client.close()
    print(json.dumps({"database": settings.mongodb_database, "applied": args.apply, **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
