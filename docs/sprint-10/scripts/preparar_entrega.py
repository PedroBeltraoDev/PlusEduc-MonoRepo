"""Prepara o banco descartável da entrega da Sprint 10 (versão atual da main, com a atualização de segurança).

    PLUSEDUC_EVAL_PASSWORD=... python preparar_entrega.py pluseduc_sprint10_entrega

1. copia o escola_db (só leitura) para o banco informado;
2. grava a verificação de consistência antes de qualquer alteração (entrega/resultados/banco_antes.*);
3. aplica a migração de segurança e integridade (scripts/migrate_security_integrity.py) e a repete, para mostrar que é idempotente;
4. remove os órfãos (check_database.py --repair) e grava a verificação depois (entrega/resultados/banco_depois.*);
5. define a senha de teste nas contas usadas pelos roteiros (professora, aluno, outro aluno, outro professor) e cria o ADMIN de avaliação.

A senha vem só da variável de ambiente e nunca é impressa. O escola_db não é alterado.
"""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BACKEND = ROOT / "PlusEduc-BE-Python"
OUT = HERE.parent / "entrega" / "resultados"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(BACKEND))

from pymongo import MongoClient  # noqa: E402

from app.core.passwords import hash_password  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "pluseduc_sprint10_entrega"
assert DB != "escola_db", "o banco de avaliação não pode ser o escola_db"
PW = os.environ["PLUSEDUC_EVAL_PASSWORD"]
env = {**os.environ, "MONGODB_DATABASE": DB, "PYTHONIOENCODING": "utf-8"}

client = MongoClient("mongodb://localhost:27017")
src = client["escola_db"]
client.drop_database(DB)
dst = client[DB]
for name in src.list_collection_names():
    docs = list(src[name].find({}))
    if docs:
        dst[name].insert_many(docs)
    for ix in src[name].list_indexes():
        if ix["name"] == "_id_":
            continue
        dst[name].create_index(list(ix["key"].items()), **{k: v for k, v in ix.items() if k not in ("key", "v", "ns")})
print("cópia:", {k: dst[k].count_documents({}) for k in sorted(dst.list_collection_names())})


def run(*args, save=None):
    result = subprocess.run([sys.executable, *args], cwd=BACKEND, env=env, capture_output=True, text=True, encoding="utf-8")
    if save:
        (OUT / save).write_text(result.stdout, encoding="utf-8")
    return result


CHECK = ["scripts/check_database.py", "--database", DB]
run(*CHECK, "--json", str(OUT / "banco_antes.json"), save="banco_antes.txt")
first = run("scripts/migrate_security_integrity.py", "--apply", save="migracao_1.json")
second = run("scripts/migrate_security_integrity.py", "--apply", save="migracao_2.json")
print("migração:", first.stdout.strip().replace("\n", " "))
print("repetida:", second.stdout.strip().replace("\n", " "))
run(*CHECK, "--repair", save="reparo.txt")
run(*CHECK, "--json", str(OUT / "banco_depois.json"), save="banco_depois.txt")

h = hash_password(PW)


def setpw(email: str) -> None:
    dst.users.update_one({"email": email}, {"$set": {"password": h, "active": True}})


setpw("marina.ferreira@pluseduc.local")
setpw("lucas.carvalho@aluno.local")
lucas = dst.students.find_one({"email": "lucas.carvalho@aluno.local"})
other = next(
    s for s in dst.students.find({"active": {"$ne": False}, "class_id": {"$nin": [None, "", lucas["class_id"]]}})
    if dst.users.find_one({"email": s.get("email"), "role": "STUDENT"})
)
setpw(other["email"])
teacher2 = next(
    t for t in dst.teachers.find({"email": {"$ne": "marina.ferreira@pluseduc.local"}, "active": {"$ne": False}})
    if dst.users.find_one({"email": t["email"], "role": "TEACHER"})
)
setpw(teacher2["email"])
dst.users.delete_many({"email": "admin.avaliacao@pluseduc.local"})
dst.users.insert_one({
    "email": "admin.avaliacao@pluseduc.local", "password": h, "role": "ADMIN", "active": True, "tokenVersion": 0,
    "name": "Administrador de Avaliação", "createdAt": datetime.datetime.now(datetime.timezone.utc),
})
print("contas de teste prontas: professora, aluno, outro aluno, outro professor e ADMIN de avaliação")
(OUT / "banco_entrega.json").write_text(json.dumps({"banco": DB, "gerado_em": datetime.datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")
