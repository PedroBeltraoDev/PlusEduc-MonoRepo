"""Gera docs/sprint-08/README.md (texto fixo + tabela de capturas lida dos manifestos)."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
captures = []
for name in ("manifest_a.json", "manifest_b1.json", "manifest_b2.json", "manifest_b3.json"):
    captures += json.loads((BASE / "evidencias" / name).read_text(encoding="utf-8"))
seen = {}
for item in captures:  # a última captura de cada arquivo vale
    seen[item["arquivo"]] = item
rows = "\n".join(f"| `{a}` | {i['legenda']} | {i['hora']} |" for a, i in sorted(seen.items()) if (BASE / "evidencias" / a).exists())

TEXT = f"""# Sprint 08 — Sistema praticamente concluído (31/10/2026)

Material de apoio da entrega da Sprint 08 do PlusEduc (Grupo 08): revisão do controle de permissões, das regras de
negócio e da usabilidade, feita **rodando o sistema** (backend FastAPI + MongoDB local + frontend) e não apenas lendo o
código. O PDF da entrega (Sprints 01 a 08) é montado a partir destes resultados.

## O que foi feito nesta sprint

1. **Integração da Sprint 07 à `main`.** Dashboard, relatórios, exportação, pesquisa e histórico de operações só existiam
   numa branch local. Foram mesclados à linha atual da `main` (otimizações com OpenCL e build nativo), com dois conflitos
   triviais e a restauração de `StudentAnalyticsService.attendance_counts`, usado pelos relatórios.
2. **Permissões verificadas na prática.** As 94 rotas da API foram chamadas como anônimo, aluno, professor e administrador
   (`resultados/matriz_de_permissoes.md`) e foram feitas 33 verificações direcionadas (`resultados/verificacoes_*.txt`).
3. **Quatro lacunas de permissão corrigidas**, cada uma reproduzida antes e confirmada depois (tabela abaixo).
4. **Quatro regras de negócio ajustadas** (tabela abaixo).
5. **Melhorias de usabilidade** no frontend (sessão expirada, mensagens em português, matrícula no lugar do ID interno,
   data de nota limitada a hoje).
6. **Testes automatizados:** de 93 para 138 (`tests/test_permissions_sprint8.py` e `tests/test_business_rules_sprint8.py`)
   e a suíte inteira passou a rodar contra um banco descartável (`MONGODB_DATABASE`, ver `tests/database.py`).

## Lacunas de permissão encontradas e corrigidas

| # | Lacuna (reproduzida antes da correção) | Correção | Verificação depois |
|---|---|---|---|
| 1 | Aluno enviava respostas a uma atividade de **outra turma** (`POST /api/student-portal/activities/{{id}}/submissions` respondia 200 e gravava no banco). | A rota passou a usar o serviço do portal, que só aceita atividades da turma do aluno ou atribuídas a ele. | 404 e nenhuma submissão gravada (`resultados/envio_outra_turma_*.txt`). |
| 2 | O **refresh token** (7 dias) era aceito como token de acesso (a API não distinguia os dois tipos). | Claim `type` (`access`/`refresh`); a API só aceita `access`. | 401 ao usar o refresh token. Efeito: sessões abertas antes da atualização pedem novo login. |
| 3 | **Recuperação de senha em modo demonstração sempre ligado:** o código fixo `123456` voltava na resposta de `forgot-password`, permitindo trocar a senha de qualquer conta só conhecendo o e-mail (e revelando se a conta existe). | Modo demonstração virou opt-in (`PASSWORD_RESET_DEMO_MODE=true`, desligado por padrão). Desligado, o código é aleatório, vai por e-mail (SMTP) e nunca aparece na resposta nem no log. | Resposta sem código e igual para conta existente e inexistente; troca de senha sem o código recebido não funciona. |
| 4 | O perfil **ADMIN** não conseguia cadastrar, editar, excluir nem liberar acesso de alunos (rotas só para `TEACHER`), embora administrasse turmas, professores e notas. | Rotas passaram a aceitar `TEACHER` e `ADMIN`. | ADMIN passa na autorização (`matriz_de_permissoes.md`). |

**Importante para a demonstração:** para mostrar o fluxo "Esqueci minha senha" sem configurar SMTP, defina
`PASSWORD_RESET_DEMO_MODE=true` no `.env` local (somente em máquina local).

## Regras de negócio ajustadas

| # | Comportamento encontrado | Ajuste |
|---|---|---|
| 1 | Era possível lançar nota para um aluno em turma onde ele **não está matriculado**. | `POST /api/grades` valida a matrícula (400). Editar uma nota antiga só revalida se o aluno ou a turma mudarem. |
| 2 | Nota podia ter **data no futuro** (ex.: 2030). | Rejeitada com 422 (tolerância de 1 dia por fuso); o campo de data da tela já não passa de hoje. |
| 3 | Matricular um aluno em outra turma o deixava **nas duas** listas de turma. | A matrícula tira o aluno da turma anterior. |
| 4 | **Data de nascimento** no futuro ou anterior a 1900 era aceita. | Rejeitada com 422. |

## Limitações conhecidas (não corrigidas nesta sprint)

* O cadastro público de professor ativa a conta e dá acesso imediato aos dados de todos os alunos; o RF04 prevê aprovação.
* Não há escopo por turma: qualquer professor lê e lança notas em qualquer turma.
* A matrícula existe em dois lugares (`class_id` do aluno e lista `students` da turma) e criar aluno com `classId` só
  preenche o primeiro.
* Predição de risco (RF19), clustering (B17) e otimização de grupos (B18) não foram implementados.
* A meta de 4× de ganho no recálculo (RNF07) não foi atingida: o OpenCL só passa de 1× acima de ~100 mil registros
  (`resultados/benchmark_opencl.txt`).
* O frontend ainda não usa o refresh token.

## Como reproduzir

Defina `PLUSEDUC_EVAL_PASSWORD` (senha de teste) e `PY` (python do `.venv`), crie o banco descartável com
`scripts/clonar_banco.py` (copia `escola_db` para `pluseduc_sprint8_eval`, sem alterar o original), suba dois backends
(código antes: commit `a8ef154`, porta 8092; depois: `HEAD`, porta 8091, ambos com `MONGODB_DATABASE=pluseduc_sprint8_eval`)
e execute `scripts/executar_avaliacao.sh`. As capturas de tela usam `scripts/capturas_*.py` (Selenium + Chrome) com o
frontend em `http://127.0.0.1:5183` (`VITE_DEV_PROXY_TARGET=http://127.0.0.1:8091`). Os testes automatizados:

```powershell
$env:MONGODB_REQUIRED = "false"
$env:MONGODB_DATABASE = "pluseduc_sprint8_eval"   # banco descartável; sem isso usa escola_db
.\\.venv\\Scripts\\python.exe -m pytest -q
```

## Capturas de tela

As capturas ficam em `evidencias/` com uma faixa superior que mostra o endereço e a legenda (o Chrome headless não exibe
a barra de endereço). O campo de data do navegador de teste usa o formato mês/dia: `10/12/2026` na captura
`b13_nota_data_futura.png` é 10 de dezembro de 2026.

| Arquivo | O que comprova | Hora |
|---|---|---|
{rows}
"""
(BASE / "README.md").write_text(TEXT, encoding="utf-8")
print("README.md gerado com", len(seen), "capturas")
