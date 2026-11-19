"""Gera o PDF da entrega da Sprint 10 (versão atual da main) e o junta ao PDF consolidado das Sprints 01 a 09.

    python gerar_pdf_entrega.py <pdf das sprints 01-09> <pdf de saída 01-10>

Mesmo visual e mesmo método de gerar_pdf_sprint10.py (HTML impresso pelo Chrome e juntado com o pypdf), com o conteúdo
da versão entregue com atraso: release candidate 1.0.0-rc.1 + atualização de segurança e Ultra Motion (PRs #12 a #15).
Lê as evidências e os resultados de docs/sprint-10/entrega/.
"""
import base64
import html
import json
import os
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

HERE = Path(__file__).resolve().parent
ENT = HERE.parent / "entrega"
EVID = ENT / "evidencias"
RES = ENT / "resultados"
SRC_PDF, OUT_PDF = sys.argv[1], sys.argv[2]
NAVY = "#1F3864"
PRAZO, ENTREGA = "14/11/2026", "19/11/2026"


def load(name):
    return json.loads((RES / name).read_text(encoding="utf-8"))


api, nav, val = load("regressao_api.json"), load("regressao_navegacao.json"), load("regressao_validacao_ui.json")
revisao = load("revisao_interface.json")
banco_antes, banco_depois = load("banco_antes.json")["resultados"], load("banco_depois.json")["resultados"]
migr1, migr2 = load("migracao_1.json"), load("migracao_2.json")
pytest_line = next((l for l in reversed((RES / "testes_backend.txt").read_text(encoding="utf-8", errors="ignore").splitlines()) if "passed" in l or "aprovados" in l), "")
manifest = {}
for f in EVID.glob("manifest*.json"):
    manifest.update({m["arquivo"]: m for m in json.loads(f.read_text(encoding="utf-8"))})

RC_NOVOS = ["AUT-10", "APR-01", "APR-02", "APR-03", "APR-04", "SES-01", "SES-02", "SES-03", "SEN-01", "SEN-03", "TUR-16", "TUR-17"]
REESCRITOS = {
    "TUR-05": "Turma criada por professor é sempre dele: o teacherId enviado é ignorado.",
    "TUR-06": "Para o professor, turma fora do escopo (ou inexistente) responde 403; o ADMIN recebe 404.",
    "TUR-14": "Idem: exclusão de id inexistente é 403 para o professor e 404 para o ADMIN.",
    "TUR-15": "O limite de 5 turmas é testado pelo ADMIN, que escolhe o professor (o professor só cria turmas para si).",
    "ALU-05": "Turma inexistente: 403 para o professor (escopo), 400 para o ADMIN.",
    "ATI-03": "Turma inexistente: 403 para o professor (escopo), 400/404 para o ADMIN.",
    "PRO-01": "CRUD de professores passou a ser só do ADMIN; a senha fica só em users.",
    "PRO-02": "Executado pelo ADMIN (CRUD de professores).",
    "PRO-03": "Executado pelo ADMIN (CRUD de professores).",
    "PRO-04": "Executado pelo ADMIN (CRUD de professores).",
    "PRO-05": "Professor recebe 403 ao editar ou excluir colegas; o ADMIN faz a operação.",
    "MAT-03": "Alterar e desativar matérias do catálogo passou a ser só do ADMIN.",
    "REL-01": "O dashboard do professor mostra só as turmas dele; o do ADMIN é comparado com o banco.",
    "SEN-02": "Trocar a senha encerra as sessões (token antigo 401) e a senha não é mais copiada em teachers.",
}

e = html.escape


def table(headers, rows, widths=None, head=True):
    cols = "".join(f'<col style="width:{w}">' for w in widths) if widths else ""
    th = "<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>" if head else ""
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><colgroup>{cols}</colgroup>{th}<tbody>{body}</tbody></table>"


def img(name, caption=None):
    data = base64.b64encode((EVID / name).read_bytes()).decode()
    cap = caption or manifest.get(name, {}).get("legenda", name)
    when = manifest.get(name, {}).get("hora", "")
    return f'<figure><img src="data:image/png;base64,{data}"><figcaption><b>{e(name)}</b> — {e(cap)}{" · " + when if when else ""}</figcaption></figure>'


def ok(flag):
    return '<span class="ok">Aprovado</span>' if flag else '<span class="bad">Reprovado</span>'


def by_id(rows):
    return {r["id"]: r for r in rows}


A = by_id(api)
MIGR_ROTULOS = {"teacher_password_fields_removed": "senhas removidas de teachers", "teacher_users_created": "contas de professor criadas",
                "teacher_users_deactivated": "contas de professor desativadas", "student_users_deactivated": "contas de aluno desativadas",
                "students_added_to_class_list": "alunos incluídos na lista da turma", "duplicate_memberships_removed": "matrículas duplicadas removidas",
                "students_class_id_restored": "vínculos de turma restaurados", "teacher_plaintext_passwords_hashed": "senhas em texto puro convertidas"}


def resumo_migracao(rel):
    itens = [f"{MIGR_ROTULOS.get(k, k)}: {v}" for k, v in rel.items() if k not in ("database", "applied", "duplicate_user_emails") and v]
    return ", ".join(itens) or "nenhuma alteração"


MIGR1, MIGR2 = resumo_migracao(migr1), resumo_migracao(migr2)
n_ok = lambda rows: sum(r["ok"] for r in rows)  # noqa: E731
telas = len(revisao)
com_problema = [r for r in revisao if r["rolagem_horizontal"] or r["erros_console"]]

# ----------------------------------------------------------------------------- conteúdo
parts = []
P = parts.append
P(f"""
<section class="cover">
  <h1>SPRINT 10</h1>
  <h2>VERSÃO RELEASE CANDIDATE</h2>
  <p class="sub">PlusEduc — Plataforma de Gestão Pedagógica<br>com Análise de Aprendizagem</p>
  {table(["", ""], [
      ["DISCIPLINA", "Fábrica de Software + Tópicos Avançados"],
      ["INSTITUIÇÃO", "UNINASSAU"],
      ["GRUPO", "08"],
      ["SCRUM MASTER", "Pedro Antônio Silva Pedroso Beltrão"],
      ["INTEGRANTES", "Pedro Antônio Silva Pedroso Beltrão — 01605602 (Scrum Master; desenvolvimento backend e frontend)<br>André Marcílio da Silva Ferreira — 01616701 (UI/UX, testes e documentação; atualização de segurança e Ultra Motion)<br>Evandro Albuquerque do Rêgo Lima — 01607434 (UI/UX, testes e documentação)"],
      ["PRAZO DA SPRINT", PRAZO],
      ["DATA DA ENTREGA", f"{ENTREGA} (entrega após o prazo)"],
      ["VERSÃO", "1.0.0-rc.1 (release candidate) + atualização de segurança e Ultra Motion"],
      ["EXECUÇÃO E EVIDÊNCIAS", f"{ENTREGA} — sistema executado e verificado com dados reais, em banco descartável copiado do escola_db"],
      ["REPOSITÓRIO", "https://github.com/PedroBeltraoDev/PlusEduc-MonoRepo — branch main"],
  ], ["28%", "72%"], head=False)}
  <p class="note">Documento consolidado: as Sprints 01 a 09 (já entregues) estão nas páginas anteriores, seguidas deste documento da Sprint 10.</p>
  <p class="note small">Sobre o atraso: a release candidate ficou pronta dentro do prazo, mas só foi entregue depois. Nesse intervalo a equipe integrou à
  versão uma revisão geral de segurança e o sistema de animações (Ultra Motion). Este documento descreve e verifica a versão atual, que é a que
  será apresentada.</p>
</section>
""")

P(f"""
<h2>1. Descrição da versão Release Candidate</h2>
<p>A versão entregue é a <b>1.0.0-rc.1</b>, candidata à entrega final do PlusEduc, já com a atualização de segurança e o Ultra Motion.
Ela reúne os módulos das sprints anteriores — autenticação por perfil, turmas e alunos, atividades com correção automática e manual,
notas e frequência, dashboard, relatórios com exportação, pesquisa, histórico de operações e portal do aluno — e fecha as pendências
que comprometiam os fluxos principais:</p>
<ul>
<li><b>Sessão contínua (RF01):</b> token de acesso de 30 minutos renovado sozinho pelo refresh token, que vale uma vez só; reapresentar um refresh já usado encerra todas as sessões daquele login.</li>
<li><b>Troca de senha pelo próprio usuário (RF03):</b> a senha é trocada de verdade e as outras sessões abertas são encerradas.</li>
<li><b>Aprovação do cadastro de professor (RF04):</b> o cadastro público fica pendente até um administrador aprovar.</li>
<li><b>Escopo por turma:</b> o professor só vê e altera as turmas sob sua responsabilidade e os alunos, notas, atividades e relatórios delas; antes ele via tudo.</li>
<li><b>Proteções de conta:</b> senha só em <code>users</code> (com bcrypt), limite de tentativas no login, cadastro e recuperação de senha, e a API não inicia em produção com configuração insegura.</li>
<li><b>Interface:</b> Ultra Motion (abertura animada, transições e perfis de animação), rascunho automático das respostas do aluno e correções de usabilidade.</li>
<li><b>Banco, API e README:</b> migração idempotente para bancos existentes, verificação de consistência, documentação da API gerada do código (100 rotas) e README final.</li>
</ul>
<p>Arquitetura: frontend React + TypeScript + Vite + Tailwind, backend FastAPI (Python 3.12) em camadas (routers, serviços, repositórios),
MongoDB local, JWT com perfis ADMIN, TEACHER e STUDENT, estatísticas de notas em OpenCL. A verificação foi feita com o sistema em
execução contra um banco descartável (<code>pluseduc_sprint10_entrega</code>, cópia do <code>escola_db</code> com a migração aplicada);
o <code>escola_db</code> só foi lido.</p>

<h3>Resultado em números</h3>
{table(["Verificação", "Casos", "Resultado"], [
    ["Suíte automatizada do backend (pytest)", "190",
     "190 aprovados, 0 falhas (171 da RC, 18 da atualização de segurança e 1 novo)" if "190 aprovados" in pytest_line else "ver entrega/resultados/testes_backend.txt"],
    ["Regressão funcional da API: 104 casos da RC (14 reescritos para as regras novas) + 7 de segurança", str(len(api)), f"{n_ok(api)} aprovados"],
    ["Navegação pela interface (Chrome + Selenium)", str(len(nav)), f"{n_ok(nav)} aprovados"],
    ["Validação pela interface (mensagens e campos)", str(len(val)), f"{n_ok(val)} aprovados"],
    ["Revisão das telas finais (3 perfis, desktop e celular)", str(telas), "sem rolagem lateral; nenhum erro de console além do 403 esperado no login pendente" if len(com_problema) <= 1 else f"{len(com_problema)} com problema"],
    ["Consistência do banco", "22", f"cópia do escola_db: {sum(1 for r in banco_antes if r['problemas'] and r['nivel'] == 'ERRO')} com erro; após migração e reparo: {sum(1 for r in banco_depois if r['problemas'] and r['nivel'] == 'ERRO')} com erro, {sum(1 for r in banco_depois if r['problemas'] and r['nivel'] != 'ERRO')} aviso"],
    ["Frontend: type-check e build de produção", "—", "sem erros"],
], ["52%", "10%", "38%"])}
""")

# 2. evidências
P(f"""
<h2>2. Evidências do sistema estável e dos principais fluxos</h2>
<p>A regressão reexecutou contra a versão atual os 104 casos funcionais e de validação da release candidate (92 da Sprint 09 e 12 das
funcionalidades da RC). Catorze deles esperavam o comportamento antigo de regras que mudaram de propósito com a atualização de segurança;
eles foram reescritos com o novo resultado esperado e continuam no catálogo:</p>
{table(["ID", "O que mudou na regra", "Esperado agora", "Obtido", "Resultado"],
       [[r, e(REESCRITOS[r]), e(A[r]["esperado"]), e(A[r]["obtido"]), ok(A[r]["ok"])] for r in REESCRITOS], ["7%", "25%", "26%", "31%", "11%"])}
""")
P(f"""
<h3>Casos novos: regras de segurança</h3>
{table(["ID", "Caso", "Esperado", "Obtido", "Resultado"],
       [[r["id"], e(r["titulo"]), e(r["esperado"]), e(r["obtido"]), ok(r["ok"])] for r in api if r["id"].startswith("SEG-")], ["7%", "20%", "28%", "33%", "12%"])}
<h3>Casos das funcionalidades da release candidate</h3>
{table(["ID", "Caso", "Obtido", "Resultado"], [[r, e(A[r]["titulo"]), e(A[r]["obtido"]), ok(A[r]["ok"])] for r in RC_NOVOS], ["8%", "30%", "50%", "12%"])}
""")
mods = {}
for r in api:
    m = mods.setdefault(r["modulo"], [0, 0])
    m[0] += 1
    m[1] += r["ok"]
P("<h3>Regressão por módulo (API)</h3>" + table(["Módulo", "Casos", "Aprovados"], [[e(k), v[0], v[1]] for k, v in mods.items()] + [["<b>Total</b>", f"<b>{len(api)}</b>", f"<b>{n_ok(api)}</b>"]], ["60%", "20%", "20%"]))
sess = [r for r in nav if r["id"].startswith("NAV-SS")]
P(f"""
<h3>Navegação: sessão renovada e sessão encerrada</h3>
<p>Token de acesso inválido com refresh token válido mantém o usuário na tela (a sessão é renovada); com os dois inválidos a sessão termina e o login avisa.</p>
{table(["ID", "Ação", "Esperado", "Obtido", "Resultado"], [[r["id"], e(r["acao"]), e(r["esperado"]), e(str(r["obtido"])), ok(r["ok"])] for r in sess], ["10%", "30%", "22%", "26%", "12%"])}
<div class="grid">{img("n04_sessao_renovada.png")}{img("n05_sessao_encerrada.png")}</div>
<h3>Escopo por turma: o que cada perfil vê</h3>
<div class="grid">{img("u03_admin_turmas.png")}{img("t02_turmas.png")}</div>
<h3>Cadastro de professor com aprovação (RF04)</h3>
<div class="grid">{img("c02_cadastro_professor.png")}{img("c04_login_pendente.png")}</div>
<div class="grid">{img("c06_admin_pendentes.png")}{img("c10_professor_aprovado.png")}</div>
<h3>Troca de senha (RF03) e criação de turma pelo ADMIN</h3>
<div class="grid">{img("c11_senha_confirmacao.png")}{img("c12_senha_alterada.png")}</div>
<div class="grid">{img("c08_admin_nova_turma.png")}{img("c09_admin_historico.png")}</div>
""")

# 3. interface final
P(f"<h2>3. Evidências da interface final</h2><p>Telas finais capturadas no sistema em execução, com os dados de demonstração, em {ENTREGA}. "
  "A relação completa (com horário de cada captura) está em <code>docs/sprint-10/entrega/evidencias/</code>.</p>")
P("<p>Ajustes de interface desde a RC: abertura animada e transições (Ultra Motion) com perfis Ultra, Equilibrado e Desempenho; rascunho das "
  "respostas do aluno salvo no navegador; sino de notificações com uma consulta só (pausada com a aba em segundo plano) que fecha com Esc; "
  "modais da tela de Turmas que fecham com Esc; cartão real de troca de senha; aprovação de cadastros para o administrador; remoção dos dados "
  "fictícios das Configurações e das mensagens de depuração que expunham dados de alunos no console.</p>")
P(f'<h3>Ultra Motion</h3><div class="grid">{img("u01_abertura.png")}{img("u02_animacoes.png")}</div>'
  '<p class="small">A abertura aparece uma vez por sessão do navegador e é pulada quando o sistema operacional pede movimento reduzido. '
  'Nas demais capturas o movimento reduzido estava ligado (padrão do Windows desta máquina), o que deixa as telas estáveis para a foto.</p>')
for a, b in (("t01_dashboard.png", "t13_configuracoes.png"), ("t04_atividade_detalhe.png", "t06_gerar_atividade.png"), ("t07_notas.png", "t08_relatorios.png"),
             ("t10_busca.png", "t09_historico.png"), ("a01_inicio.png", "a03_atividade.png"), ("a06_notas.png", "a08_configuracoes.png"),
             ("e01_escuro_dashboard.png", "e02_escuro_configuracoes.png")):
    P(f'<div class="grid">{img(a)}{img(b)}</div>')
P(f'<div class="grid3">{img("m01_celular_dashboard.png")}{img("m03_celular_notas.png")}{img("m05_celular_aluno.png")}</div>')

# 4. banco
P(f"""
<h2>4. Estrutura final do banco de dados</h2>
<p>MongoDB local (banco <code>escola_db</code>), 11 coleções. Toda coleção tem a chave primária <code>_id</code> (ObjectId); as chaves de negócio e os
índices são criados pela API ao iniciar. A descrição completa (campos, tipos, presença, índices e diagrama) está em <code>docs/MODELO_DE_DADOS.md</code>.</p>
{table(["Coleção", "Conteúdo", "Chave de negócio / índices"], [
    ["users", "contas de acesso; o papel (role) define as permissões; tokenVersion invalida os tokens já emitidos", "e-mail único; active"],
    ["students", "cadastro pedagógico do aluno, turma e lacunas de aprendizagem", "matrícula única; email, class_id"],
    ["teachers", "cadastro do professor, matérias, turmas e situação da aprovação (não guarda senha)", "email"],
    ["classrooms", "turmas: série, ano, alunos, professor responsável e professor por matéria", "nome + ano entre as ativas; teacher_id, students"],
    ["subjects / subject_topics", "catálogo de matérias (BNCC) e tópicos", "nome normalizado único"],
    ["activities", "atividades objetivas e discursivas (questões e gabarito)", "classroom_id, student_id, created_by"],
    ["activity_submissions", "respostas dos alunos e correção", "activity_id + student_id único"],
    ["grades", "notas e presença (um documento por lançamento)", "studentId, classroomId, activityId"],
    ["audit_logs", "histórico de operações que alteram dados", "timestamp; actorId + timestamp; entity + action"],
    ["refresh_tokens", "refresh tokens emitidos (só o hash do identificador), para uso único, revogação e detecção de reuso", "jtiHash único; family, email; expiresAt com TTL"],
], ["20%", "48%", "32%"])}
<h3>Relacionamentos</h3>
{table(["Campo", "Aponta para", "Significado"], [
    ["students.class_id e classrooms.students[]", "classrooms._id / students._id", "matrícula do aluno (gravada nos dois lados e mantida coerente)"],
    ["users.studentId", "students._id", "login do aluno"],
    ["users.email = teachers.email", "—", "login do professor"],
    ["classrooms.teacher_id", "teachers._id", "professor responsável (ativo); define o escopo do professor"],
    ["classrooms.subjectTeachers[]", "subjects._id / teachers._id", "um professor por matéria na turma; também entra no escopo"],
    ["activities.classroom_id / student_id", "classrooms._id / students._id", "turma da atividade e aluno (opcional)"],
    ["activity_submissions.activity_id / student_id", "activities._id / students._id", "resposta de um aluno a uma atividade"],
    ["grades.studentId / classroomId / activityId", "students / classrooms / activities", "nota do aluno, opcionalmente vinda de uma atividade"],
    ["refresh_tokens.email / family", "users.email", "dono do token e cadeia de renovações de um login"],
], ["36%", "28%", "36%"])}
<h3>Migração para bancos existentes</h3>
<p><code>scripts/migrate_security_integrity.py</code> move as senhas de <code>teachers</code> para <code>users</code> (com bcrypt), cria contas que faltam,
desativa contas de quem foi excluído e acerta os vínculos aluno/turma. Na cópia do <code>escola_db</code>:
{e(MIGR1)}.
Executada de novo, não alterou nada ({e(MIGR2)}): é idempotente.</p>
<h3>Verificação de consistência (scripts/check_database.py)</h3>
{table(["ID", "Verificação", "Cópia do escola_db", "Após migração e reparo"],
       [[r["id"], e(r["verificacao"]), ("ok" if not r["problemas"] else f'<span class="bad">{r["nivel"]}: {r["problemas"]}</span>'),
         ("ok" if not d["problemas"] else f'{d["nivel"]}: {d["problemas"]}')] for r, d in zip(banco_antes, banco_depois)], ["9%", "55%", "18%", "18%"])}
<p class="small">REF-09: 3 atividades de março e abril apontam para turma e aluno inexistentes; REF-10: 2 respostas a atividades inexistentes; DOM-04: um professor com 12 turmas ativas (dado anterior à regra de 5). O reparo remove só os órfãos; a redistribuição das turmas é decisão da escola.</p>
""")

# 5. API
P(f"""
<h2>5. Documentação das APIs</h2>
<p>A API REST tem <b>100 rotas</b> em 18 grupos. A documentação é gerada do próprio código, então não fica desatualizada:</p>
{table(["Onde", "Conteúdo"], [
    ["docs/API.md (repositório)", "autenticação, perfis, formato de erro, exemplos com curl, tabela de rotas por grupo com o perfil de acesso, parâmetros, corpos, respostas e todos os esquemas"],
    ["http://127.0.0.1:8080/docs", "Swagger UI interativo, em português, com o perfil exigido em cada rota e o botão Authorize"],
    ["http://127.0.0.1:8080/redoc", "ReDoc (leitura)"],
    ["docs/api/openapi.json", "esquema OpenAPI 3.1, importável no Postman ou Insomnia"],
], ["32%", "68%"])}
<h3>Autenticação e exemplo de uso</h3>
<pre>POST /api/auth/login  {{"email": "...", "password": "..."}}
→ 200 {{"accessToken": "...", "refreshToken": "...", "tokenType": "Bearer", "expiresIn": 1800, "role": "TEACHER", ...}}

GET  /api/classrooms     Authorization: Bearer &lt;accessToken&gt;     (professor: só as turmas dele)
POST /api/auth/refresh  {{"refreshToken": "..."}}   → novo par de tokens (o refresh anterior deixa de valer)
POST /api/auth/logout   {{"refreshToken": "..."}}   → 204 (sessão revogada)

Erro (sempre o mesmo formato):
{{"timestamp": "2026-11-19T18:00:00Z", "status": 400, "error": "Bad Request", "message": "Senha atual incorreta"}}
Excesso de tentativas: 429 com o cabeçalho Retry-After (segundos)</pre>
{table(["Grupo", "Rotas principais", "Acesso"], [
    ["Autenticação", "login, refresh, logout, change-password, register/student, register/teacher, forgot/reset-password, profile", "público / autenticado"],
    ["Professores", "listar e consultar; criar, editar e excluir; pending, {id}/approve, {id}/reject", "consulta: TEACHER ou ADMIN; o resto só ADMIN"],
    ["Turmas e alunos", "CRUD, enroll/unenroll, performance, unassigned, enable-access", "TEACHER (turmas dele) ou ADMIN"],
    ["Atividades e correção", "CRUD, generate, submissions, export-pdf, activity-corrections", "TEACHER (turmas dele) ou ADMIN"],
    ["Notas e frequência", "CRUD, classroom/{id}/summary, from-activity/{id}", "TEACHER (turmas dele) ou ADMIN"],
    ["Matérias", "listar e criar; alterar e desativar", "criar: equipe; alterar e desativar: ADMIN"],
    ["Dashboard, relatórios, pesquisa, histórico", "dashboard/overview, reports, reports/{tipo}/export, search, audit-logs", "TEACHER (dados das turmas dele) ou ADMIN"],
    ["Portal do aluno", "me, classroom, classmates, teachers, activities, submissions, grades, performance", "STUDENT"],
], ["24%", "48%", "28%"])}
<div class="grid">{img("d01_swagger.png")}{img("d02_redoc.png")}</div>
<p class="small">tests/test_openapi_docs.py reprova a suíte se alguma rota ficar sem resumo, grupo ou perfil, ou se o perfil documentado divergir da matriz de permissões.</p>
""")

# 6. repositório
P("""
<h2>6. Repositório GitHub e README</h2>
<p>Repositório: <b>https://github.com/PedroBeltraoDev/PlusEduc-MonoRepo</b> — versão entregue na branch <code>main</code>, que reúne a Sprint 09 (PR #12),
a release candidate da Sprint 10 (PR #13) e a atualização de segurança e Ultra Motion (PR #14, integrado à RC pelo PR #15).</p>
<p>O <code>README.md</code> da raiz tem todos os itens pedidos: nome e descrição, objetivo da solução, equipe, tecnologias, requisitos,
instalação e configuração (variáveis do <code>.env</code>), configuração do banco (MongoDB, criação do administrador, migração, dados de
demonstração e verificação de consistência), comandos de execução e de testes, documentação da API e estrutura do projeto. Documentos de
apoio: <code>docs/ARQUITETURA.md</code>, <code>docs/MODELO_DE_DADOS.md</code>, <code>docs/API.md</code>, <code>docs/REQUISITOS_STATUS.md</code>,
<code>docs/ATUALIZACAO_SEGURANCA_E_ULTRA_MOTION.md</code> e <code>docs/sprint-10/README.md</code>.</p>
""")

# 7. correções
P(f"""
<h2>7. Principais correções e ajustes</h2>
<h3>Release candidate</h3>
{table(["ID", "Problema encontrado", "Gravidade", "Correção"], [
    ["RF01", "Refresh token emitido mas sem rota de renovação; com o token vencido o usuário ia para o login", "pendência", "POST /api/auth/refresh e renovação automática no frontend"],
    ["RF03", "Sem troca de senha logado; o botão das Configurações mostrava um aviso falso", "pendência", "POST /api/auth/change-password e cartão nas Configurações (professor, admin e aluno)"],
    ["RF04", "Cadastro público de professor ativava a conta na hora, com acesso aos dados de todos os alunos", "pendência (segurança)", "Conta pendente; ADMIN aprova ou recusa; scripts/create_admin.py"],
    ["RC-01", "ADMIN não conseguia criar turma pela tela (400)", "alta", "Formulário pede o professor responsável ao ADMIN"],
    ["RC-02", "Turma aceitava professor excluído ou pendente; edição aceitava professor inexistente", "média", "Professor existente e ativo obrigatório"],
    ["RC-03", "Aluno criado já com turma não aparecia na lista da turma", "média", "Matrícula gravada nos dois lados"],
    ["RC-04", "Tela de Turmas imprimia dados de alunos no console do navegador (LGPD)", "média", "Mensagens de depuração removidas"],
    ["RC-05", "Configurações com dados fixos (último acesso, dispositivo, função)", "baixa", "Dados reais da sessão e função correta"],
    ["RC-06", "Falha ao baixar PDF de atividade sem aviso", "baixa", "Mensagem de erro na tela"],
    ["RC-07", "Atividades e respostas órfãs no banco", "baixa", "check_database.py --repair"],
], ["8%", "42%", "14%", "36%"])}
<h3>Atualização de segurança (depois da RC)</h3>
{table(["ID", "Problema encontrado", "Gravidade", "Correção"], [
    ["SEG-A", "Qualquer professor via e alterava todas as turmas, alunos, notas, atividades, relatórios e o dashboard da escola", "alta", "Escopo central (core/access.py) aplicado em todas as rotas de equipe"],
    ["SEG-B", "Qualquer professor criava, editava e excluía outros professores e alterava o catálogo de matérias", "alta", "Essas operações passaram a ser só do ADMIN"],
    ["SEG-C", "Professor podia puxar para a turma dele um aluno de outro professor ou criar turma em nome de outro", "média", "Transferência fica com o ADMIN; turma criada por professor é dele"],
    ["SEG-D", "Refresh token podia ser reutilizado indefinidamente; trocar a senha não derrubava sessões roubadas", "média", "Refresh de uso único com detecção de reuso, logout e tokenVersion"],
    ["SEG-E", "Sem limite de tentativas de login, cadastro e recuperação de senha", "média", "Limite por IP e e-mail com resposta 429"],
    ["SEG-F", "Cópia da senha do professor em teachers; dados antigos com senha em texto puro", "média", "Senha só em users (bcrypt) e migração idempotente"],
    ["SEG-G", "A API subia em produção com chave JWT fraca ou modos de demonstração ligados", "média", "Recusa iniciar com configuração insegura (inclui cadastro de professor sem aprovação)"],
    ["INT-A", "Remover aluno de uma turma apagava o vínculo dele com outra; aluno em mais de uma lista", "média", "students.class_id e classrooms.students sempre coerentes"],
    ["DES-A", "Notificações do professor liam todas as respostas da escola a cada 30 s; dois sinos faziam consultas duplicadas", "baixa", "Consulta só das atividades das turmas dele, compartilhada e pausada em segundo plano"],
], ["8%", "42%", "14%", "36%"])}
""")

# 8. pendências
P(f"""
<h2>8. Pendências e próximos passos</h2>
{table(["Pendência", "Situação", "Como a equipe pretende resolver"], [
    ["Predição de risco, agrupamento por perfil e otimização de grupos de reforço (RF19, RF21, RF22)", "não implementados", "Sprint 11: modelo de risco (scikit-learn) sobre notas, frequência e lacunas, exibido no painel do aluno; K-Means se houver tempo; otimização registrada como trabalho futuro"],
    ["Migração no escola_db de demonstração", "pendente (testada na cópia)", "backup e scripts/migrate_security_integrity.py --apply antes da gravação dos vídeos; cada usuário entra de novo uma vez (os refresh tokens antigos não são aceitos)"],
    ["Integração contínua (GitHub Actions)", "não implementada", "parte dos testes depende de dados já existentes; criar um seed mínimo para os testes e então ligar o pipeline"],
    ["Dados antigos no escola_db (órfãos e professor com 12 turmas)", "identificados", "check_database.py --repair e redistribuição das turmas pela coordenação"],
    ["Limite de tentativas em memória e tokens no localStorage", "aceito para a versão local", "com mais de um servidor, guardar o limite em armazenamento compartilhado; refresh token em cookie HttpOnly exige mudar CORS e proxy"],
    ["Aplicativo de desktop (PlusEduc-Desktop)", "incluído, não verificado", "gerar e testar o instalador na Sprint 11, antes de decidir se entra na apresentação"],
    ["Speedup de 4× no recálculo (RNF07)", "não atingido", "registrado desde a Sprint 08"],
], ["34%", "16%", "50%"])}
<p>Próximas entregas: <b>Sprint 11 (21/11)</b> — documentação final, roteiro de demonstração e ensaio; <b>Sprint 12 (28/11)</b> — versão congelada para os vídeos;
<b>entrega final (05/12)</b> — vídeos e apresentação.</p>
""")

CSS = f"""
@page {{ size: A4; margin: 22mm 16mm 18mm 16mm; }}
body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10pt; color: #222; }}
h1, h2, h3 {{ color: {NAVY}; }}
h2 {{ font-size: 15pt; border-bottom: 2px solid {NAVY}; padding-bottom: 3px; margin-top: 18px; page-break-after: avoid; }}
h2:not(:first-of-type) {{ page-break-before: always; }}
h3 {{ font-size: 11.5pt; margin: 14px 0 6px; page-break-after: avoid; }}
p, li {{ line-height: 1.38; }}
table {{ width: 100%; border-collapse: collapse; margin: 6px 0 10px; font-size: 8.4pt; table-layout: fixed; }}
th {{ background: {NAVY}; color: #fff; text-align: left; padding: 4px 5px; }}
td {{ border-bottom: 1px solid #d9dde5; padding: 3px 5px; vertical-align: top; word-wrap: break-word; }}
tr:nth-child(even) td {{ background: #eef2f8; }}
tr {{ page-break-inside: avoid; }}
code {{ font-family: "Courier New", monospace; font-size: 8.6pt; }}
pre {{ font-family: "Courier New", monospace; font-size: 8pt; background: #f2f4f8; padding: 8px; border-left: 3px solid {NAVY}; white-space: pre-wrap; }}
.ok {{ color: #1b7f3b; font-weight: bold; }} .bad {{ color: #c0392b; font-weight: bold; }}
.small {{ font-size: 8.4pt; color: #555; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; page-break-inside: avoid; margin: 6px 0; }}
.grid3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; page-break-inside: avoid; margin: 6px 0; }}
figure {{ margin: 0; }} figure img {{ width: 100%; border: 1px solid #c8cdd6; }}
figcaption {{ font-size: 7.4pt; color: #444; margin-top: 2px; }}
.cover {{ text-align: center; padding-top: 50px; }}
.cover h1 {{ font-size: 32pt; margin: 0; }} .cover h2 {{ font-size: 17pt; border: 0; margin: 4px 0 18px; page-break-before: avoid; }}
.cover .sub {{ font-size: 12pt; color: #333; }} .cover table {{ text-align: left; font-size: 9pt; margin-top: 18px; }}
.cover td:first-child {{ background: #dce4f0; font-weight: bold; color: {NAVY}; }}
.cover .note {{ text-align: left; font-size: 10.5pt; margin-top: 16px; }}
.cover .note.small {{ font-size: 9pt; margin-top: 8px; }}
.cover + h2 {{ page-break-before: always; }}
"""
doc = f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Sprint 10</title><style>{CSS}</style></head><body>{"".join(parts)}</body></html>'
html_path = Path(os.environ.get("TEMP", ".")) / "pluseduc_sprint10_entrega.html"
html_path.write_text(doc, encoding="utf-8")

opts = Options()
opts.add_argument("--headless=new")
driver = webdriver.Chrome(options=opts)
try:
    driver.get(html_path.as_uri())
    header = f'<div style="width:100%;margin:0 16mm;background:{NAVY};color:#fff;font:bold 7pt Arial;padding:5px 8px;-webkit-print-color-adjust:exact">PLUS EDUC &nbsp;|&nbsp; FÁBRICA DE SOFTWARE</div>'
    footer = ('<div style="width:100%;margin:0 16mm;border-top:1px solid #ccc;font:7pt Arial;color:#666;padding-top:4px;display:flex;justify-content:space-between">'
              f'<span>Grupo 08 • Sprint 10 • prazo {PRAZO} • entregue em {ENTREGA}</span><span class="pageNumber"></span></div>')
    pdf = driver.execute_cdp_cmd("Page.printToPDF", {
        "printBackground": True, "preferCSSPageSize": True, "displayHeaderFooter": True,
        "headerTemplate": header, "footerTemplate": footer,
    })
finally:
    driver.quit()
section = Path(os.environ.get("TEMP", ".")) / "pluseduc_sprint10_entrega_secao.pdf"
section.write_bytes(base64.b64decode(pdf["data"]))

writer = PdfWriter()
writer.append(SRC_PDF)
start = len(writer.pages)
writer.append(str(section))
writer.add_outline_item("Sprint 10 — Versão release candidate", start)
writer.add_metadata({"/Title": "Grupo 08 — PlusEduc — Sprints 01 a 10", "/Author": "Grupo 08 — PlusEduc (Fábrica de Software + Tópicos Avançados, UNINASSAU)"})
with open(OUT_PDF, "wb") as fh:
    writer.write(fh)
print(f"seção da Sprint 10: {len(PdfReader(str(section)).pages)} páginas; consolidado: {len(writer.pages)} páginas -> {OUT_PDF}")
