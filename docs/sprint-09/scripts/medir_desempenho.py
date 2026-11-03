"""Mede o tempo de resposta das consultas principais (RNF08: até 2 s para uma turma típica) contra a API em execução.

    PLUSEDUC_EVAL_PASSWORD=... python medir_desempenho.py http://127.0.0.1:8091 pluseduc_sprint9_eval saida.json
"""
import json
import os
import statistics
import sys
import time
import urllib.request

from pymongo import MongoClient

BASE, DBN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
PW = os.environ["PLUSEDUC_EVAL_PASSWORD"]
db = MongoClient("mongodb://localhost:27017")[DBN]


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = resp.read()
    return (time.perf_counter() - t0) * 1000, json.loads(payload or b"{}")


tok = call("POST", "/api/auth/login", body={"email": "marina.ferreira@pluseduc.local", "password": PW})[1]["accessToken"]
stok = call("POST", "/api/auth/login", body={"email": "lucas.carvalho@aluno.local", "password": PW})[1]["accessToken"]
biggest = max(db.classrooms.find({"active": {"$ne": False}}), key=lambda c: len(c.get("students", [])))
cid, size = str(biggest["_id"]), len(biggest.get("students", []))
sid = str(db.students.find_one({"email": "lucas.carvalho@aluno.local"})["_id"])
checks = [
    (f"Desempenho da turma (a maior, {size} alunos)", "GET", f"/api/classrooms/{cid}/performance", tok),
    (f"Resumo de notas da turma ({size} alunos)", "GET", f"/api/grades/classroom/{cid}/summary", tok),
    ("Dashboard (todas as turmas)", "GET", "/api/dashboard/overview", tok),
    ("Relatório Boletim (todos os alunos)", "GET", "/api/reports/boletim", tok),
    ("Pesquisa global", "GET", "/api/search?q=lucas", tok),
    ("Lista de turmas", "GET", "/api/classrooms", tok),
    ("Lista de atividades", "GET", "/api/activities", tok),
    ("Portal do aluno: desempenho", "GET", "/api/student-portal/performance", stok),
    ("Portal do aluno: atividades", "GET", "/api/student-portal/activities", stok),
]
rows = []
for name, method, path, token in checks:
    call(method, path, token)  # aquecimento
    times = sorted(call(method, path, token)[0] for _ in range(15))
    rows.append({"consulta": name, "mediana_ms": round(statistics.median(times), 1), "p95_ms": round(times[int(len(times) * 0.95) - 1], 1), "maximo_ms": round(times[-1], 1), "amostras": len(times), "dentro_de_2s": times[-1] <= 2000})
    print(f"{name:55} mediana {rows[-1]['mediana_ms']:7.1f} ms  p95 {rows[-1]['p95_ms']:7.1f} ms  máx {rows[-1]['maximo_ms']:7.1f} ms")
json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
