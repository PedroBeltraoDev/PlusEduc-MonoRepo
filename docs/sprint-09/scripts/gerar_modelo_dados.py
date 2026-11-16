"""Gera docs/MODELO_DE_DADOS.md lendo as coleções reais do MongoDB (nomes e tipos dos campos, nunca os valores).

    python gerar_modelo_dados.py pluseduc_sprint9_eval
"""
import json
import sys
from datetime import date
from collections import Counter, defaultdict
from pathlib import Path

from pymongo import MongoClient

DBN = sys.argv[1]
ROOT = Path(__file__).resolve().parents[3]
db = MongoClient("mongodb://localhost:27017")[DBN]

DESCRICAO = {
    "users": "Contas de acesso (login). Um documento por pessoa que entra no sistema; o papel (role) decide as permissões.",
    "students": "Cadastro pedagógico do aluno (matrícula, turma, lacunas de aprendizagem). Exclusão lógica (active=false).",
    "teachers": "Cadastro do professor (disciplinas, turmas). A senha fica em bcrypt; o login usado é o documento de users.",
    "classrooms": "Turmas: série, ano letivo, alunos matriculados e o professor responsável por cada matéria (subjectTeachers).",
    "subjects": "Catálogo de matérias (componentes curriculares) ativas e inativas.",
    "subject_topics": "Tópicos sugeridos por matéria, usados na criação de atividades.",
    "activities": "Atividades (objetivas e discursivas); o conteúdo das questões, com o gabarito, fica em content.",
    "activity_submissions": "Respostas dos alunos e o resultado da correção (content). Índice único (activity_id, student_id) impede reenvio.",
    "grades": "Notas e presença (um documento por lançamento). Pode apontar para a atividade que a originou (activityId).",
    "audit_logs": "Histórico de operações que alteram dados: autor, ação, entidade, resultado e antes/depois das notas.",
}
RELACOES = [
    ("students.class_id", "classrooms._id", "turma do aluno (a lista classrooms.students[] guarda a mesma matrícula)"),
    ("students.user_id / users.studentId", "users._id / students._id", "login do aluno"),
    ("classrooms.teacher_id", "teachers._id", "professor responsável pela turma"),
    ("classrooms.subjectTeachers[].subjectId / teacherId", "subjects._id / teachers._id", "um professor por matéria na turma (RF08)"),
    ("activities.classroom_id / student_id / created_by", "classrooms._id / students._id / users._id", "turma da atividade, aluno específico (opcional) e autor"),
    ("activity_submissions.activity_id / student_id", "activities._id / students._id", "resposta de um aluno a uma atividade"),
    ("grades.studentId / classroomId / activityId", "students._id / classrooms._id / activities._id", "nota do aluno na turma, opcionalmente vinda de uma atividade"),
    ("audit_logs.actorId / entityId", "users._id / qualquer coleção", "quem fez e sobre qual registro"),
    ("teachers.email = users.email", "—", "o login do professor é o documento de users com o mesmo e-mail"),
]


def tname(v):
    return type(v).__name__


out = [
    "# Modelo de dados (MongoDB)",
    "",
    f"Gerado em {date.today():%d/%m/%Y} a partir das coleções reais do banco de avaliação (`{DBN}`, cópia do `escola_db`) por `docs/sprint-09/scripts/gerar_modelo_dados.py`.",
    "Mostra os nomes e os tipos dos campos encontrados, nunca os valores. \"Presença\" é a parcela dos documentos que traz o campo.",
    "O banco não tem esquema fixo (MongoDB): as regras de integridade estão nos serviços da API, não no banco.",
    "",
    "## Visão geral das coleções",
    "",
    "| Coleção | Documentos | Para que serve |",
    "|---|---:|---|",
]
detail = []
for name in sorted(db.list_collection_names()):
    docs = list(db[name].find({}))
    out.append(f"| `{name}` | {len(docs)} | {DESCRICAO.get(name, '')} |")
    fields = defaultdict(Counter)
    for doc in docs:
        for key, val in doc.items():
            fields[key][tname(val)] += 1
            if isinstance(val, dict):
                for k2, v2 in val.items():
                    fields[f"{key}.{k2}"][tname(v2)] += 1
    idx = [f"`{i['name']}`" + (" (único)" if i.get("unique") else "") + " " + str(list(i["key"].items())) for i in db[name].list_indexes()]
    detail += ["", f"### `{name}`", "", DESCRICAO.get(name, ""), "", "| Campo | Tipo(s) | Presença |", "|---|---|---:|"]
    for key in sorted(fields):
        types = ", ".join(f"{t}" for t, _ in fields[key].most_common())
        pct = round(100 * sum(fields[key].values()) / max(len(docs), 1))
        detail.append(f"| `{key}` | {types} | {pct}% |")
    detail += ["", "Índices: " + "; ".join(idx)]
out += ["", "## Relações entre as coleções", "", "| Campo | Aponta para | Significado |", "|---|---|---|"] + [f"| `{a}` | `{b}` | {c} |" for a, b, c in RELACOES]
out += ["", "## Pontos de atenção do modelo (débitos conhecidos)", "",
        "* **Nomes misturados:** os dados mais antigos usam `snake_case` (`class_id`, `created_at`) e os mais novos `camelCase` (`studentId`, `createdAt`), às vezes na mesma coleção. A API aceita as duas formas; a padronização exige migração.",
        "* **Matrícula em dois lugares:** `students.class_id` e `classrooms.students[]`. A API mantém os dois ao matricular, desmatricular e excluir aluno, mas criar aluno já com `classId` preenche só o primeiro.",
        "* **Ids como texto:** referências entre coleções são gravadas como texto (24 caracteres), enquanto `_id` é `ObjectId`; as consultas testam as duas formas.",
        "* **Gabarito dentro da atividade:** `activities.content` guarda as questões com a resposta correta; a proteção é feita na API (o portal do aluno remove o gabarito).",
        "* **Datas de notas** antigas estão como texto ISO e as novas como data/hora; os serviços normalizam as duas formas.",
        "", "## Detalhe por coleção"] + detail
(ROOT / "docs" / "MODELO_DE_DADOS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("MODELO_DE_DADOS.md gerado:", len(db.list_collection_names()), "coleções")
