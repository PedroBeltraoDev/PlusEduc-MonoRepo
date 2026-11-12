"""Gera a versão final de docs/MODELO_DE_DADOS.md (Sprint 10).

    python gerar_modelo_dados_final.py pluseduc_sprint10_eval

Reaproveita o gerador da Sprint 09 (campos, tipos e índices lidos das coleções reais) e acrescenta o que a
versão final precisa: diagrama de relacionamento, chaves e índices, regras de integridade e como verificar.
"""
import runpy
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DBN = sys.argv[1]
sys.argv = ["gerar_modelo_dados.py", DBN]
runpy.run_path(str(ROOT / "docs" / "sprint-09" / "scripts" / "gerar_modelo_dados.py"), run_name="__main__")

path = ROOT / "docs" / "MODELO_DE_DADOS.md"
text = path.read_text(encoding="utf-8")


def swap(old: str, new: str) -> None:
    global text
    assert old in text, old[:60]
    text = text.replace(old, new, 1)


swap("# Modelo de dados (MongoDB)", "# Modelo de dados (MongoDB) — versão final da release candidate")
swap("por `docs/sprint-09/scripts/gerar_modelo_dados.py`.", "por `docs/sprint-10/scripts/gerar_modelo_dados_final.py`.")
swap("O banco não tem esquema fixo (MongoDB): as regras de integridade estão nos serviços da API, não no banco.",
     "O banco não tem esquema fixo (MongoDB): as regras de integridade estão nos serviços da API e são conferidas por "
     "`PlusEduc-BE-Python/scripts/check_database.py` (seção \"Integridade\").")
swap("* **Matrícula em dois lugares:** `students.class_id` e `classrooms.students[]`. A API mantém os dois ao matricular, desmatricular e excluir aluno, mas criar aluno já com `classId` preenche só o primeiro.",
     "* **Matrícula em dois lugares:** `students.class_id` e `classrooms.students[]`. A API mantém os dois ao criar aluno com turma (corrigido na Sprint 10), matricular, desmatricular e excluir aluno.")

FINAL = f"""
## Diagrama de relacionamento

```mermaid
erDiagram
    USERS ||--o| STUDENTS : "studentId / user_id (login do aluno)"
    USERS ||--o| TEACHERS : "mesmo e-mail (login do professor)"
    TEACHERS ||--o{{ CLASSROOMS : "teacher_id (responsável)"
    CLASSROOMS ||--o{{ STUDENTS : "class_id e students[] (matrícula)"
    CLASSROOMS }}o--o{{ SUBJECTS : "subjects[] e subjectTeachers[]"
    TEACHERS ||--o{{ CLASSROOMS : "subjectTeachers[].teacherId (um por matéria)"
    SUBJECTS ||--o{{ SUBJECT_TOPICS : "tópicos da matéria"
    CLASSROOMS ||--o{{ ACTIVITIES : "classroom_id"
    STUDENTS ||--o{{ ACTIVITIES : "student_id (atividade individual, opcional)"
    ACTIVITIES ||--o{{ ACTIVITY_SUBMISSIONS : "activity_id"
    STUDENTS ||--o{{ ACTIVITY_SUBMISSIONS : "student_id"
    STUDENTS ||--o{{ GRADES : "studentId"
    CLASSROOMS ||--o{{ GRADES : "classroomId"
    ACTIVITIES ||--o{{ GRADES : "activityId (opcional)"
    USERS ||--o{{ AUDIT_LOGS : "actorId"
```

## Chaves e índices

Toda coleção tem a chave primária `_id` (`ObjectId`). As chaves de negócio e os índices abaixo são criados pela API
ao iniciar (`app/core/database.py` e os repositórios), então um banco novo já nasce com eles.

| Coleção | Chave de negócio (única) | Demais índices |
|---|---|---|
| `users` | `email` | `active` |
| `students` | `matricula` (única, esparsa) | `email`, `class_id`, `classId` |
| `teachers` | `email` (conferida pela API) | `email` |
| `classrooms` | `name` + `year` entre as ativas (conferida pela API) | `teacher_id`, `students` |
| `subjects` | `name_normalized` (única) | — |
| `activity_submissions` | `activity_id` + `student_id` (única: uma resposta por aluno) | `activityId`, `studentId` |
| `grades` | — (vários lançamentos por aluno) | `studentId`, `classroomId`, `activityId` |
| `activities` | — | `classroom_id`, `classroomId`, `student_id`, `studentId`, `created_by` |
| `audit_logs` | — | `timestamp`, `actorId` + `timestamp`, `entity` + `action` |

## Integridade (regras aplicadas pela API)

| Regra | Onde é aplicada |
|---|---|
| E-mail único por conta; matrícula gerada e única | cadastro de aluno e de professor; índice único |
| Senha sempre em bcrypt | `core/passwords.py`; conferida por `check_database.py` (DOM-03) |
| Exclusão lógica (`active=false`) de aluno, professor, turma e matéria; o login do excluído deixa de valer | serviços de aluno e professor |
| Aluno pertence a no máximo uma turma; a matrícula é gravada nos dois lados | criar aluno, matricular, desmatricular, excluir |
| Turma só com professor responsável existente e ativo; no máximo 5 turmas ativas por professor | criar e editar turma (Sprint 10) |
| Um professor por matéria em cada turma; matérias compatíveis com a série (BNCC) | atribuição de matéria |
| Nota de 0 a 10, com data até hoje, só para aluno matriculado na turma | lançar e editar nota |
| Atividade individual só para aluno da própria turma; excluir atividade remove as respostas | criar e excluir atividade |
| Uma resposta por aluno em cada atividade | índice único de `activity_submissions` |
| Cadastro público de professor nasce pendente (`users.pendingApproval`, `teachers.approval_status = PENDING`) e só o ADMIN ativa | cadastro e aprovação (Sprint 10) |

Campos acrescentados na Sprint 10: `users.pendingApproval` (só enquanto o cadastro está pendente) e
`teachers.approval_status`, `approved_by`, `approved_at`. Não houve mudança em coleções ou índices existentes,
então nenhum banco precisa de migração para esta versão.

### Como verificar

```powershell
cd PlusEduc-BE-Python
.\\.venv\\Scripts\\python.exe scripts\\check_database.py            # somente leitura; código 1 se houver erro
.\\.venv\\Scripts\\python.exe scripts\\check_database.py --repair   # remove respostas e atividades órfãs
```

São 22 verificações (referências entre coleções, duplicidades, faixas de valores, senhas e índices). Resultado da
Sprint 10 em `docs/sprint-10/resultados/banco_antes.txt` e `banco_depois.txt` (gerado em {date.today():%d/%m/%Y}).
"""
swap("\n## Pontos de atenção do modelo (débitos conhecidos)", FINAL + "\n## Pontos de atenção do modelo (débitos conhecidos)")
path.write_text(text, encoding="utf-8")
print("versão final gravada em", path)
