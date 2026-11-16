"""Gera o PDF da Sprint 10 (mesmo visual das sprints anteriores) e o junta ao PDF consolidado das Sprints 01 a 09.

    python gerar_pdf_sprint10.py <pdf das sprints 01-09> <pdf de saída 01-10>

Usa o Chrome (Selenium + DevTools Page.printToPDF) para imprimir um HTML montado aqui e o pypdf para juntar.
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
S10 = HERE.parent
EVID = S10 / "evidencias"
RES = S10 / "resultados"
SRC_PDF, OUT_PDF = sys.argv[1], sys.argv[2]
NAVY = "#1F3864"

api = json.loads((RES / "regressao_api.json").read_text(encoding="utf-8"))
nav = json.loads((RES / "regressao_navegacao.json").read_text(encoding="utf-8"))
val = json.loads((RES / "regressao_validacao_ui.json").read_text(encoding="utf-8"))
banco_antes = json.loads((RES / "banco_antes.json").read_text(encoding="utf-8"))["resultados"]
banco_depois = json.loads((RES / "banco_depois.json").read_text(encoding="utf-8"))["resultados"]
manifest = {m["arquivo"]: m for m in json.loads((EVID / "manifest_rc.json").read_text(encoding="utf-8"))}
NOVOS = {"AUT-10", "APR-01", "APR-02", "APR-03", "APR-04", "SES-01", "SES-02", "SES-03", "SEN-01", "SEN-02", "SEN-03", "TUR-16", "TUR-17"}

e = html.escape


def table(headers, rows, widths=None):
    cols = "".join(f'<col style="width:{w}">' for w in widths) if widths else ""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<table><colgroup>{cols}</colgroup><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def img(name, caption=None):
    data = base64.b64encode((EVID / name).read_bytes()).decode()
    cap = caption or manifest.get(name, {}).get("legenda", name)
    when = manifest.get(name, {}).get("hora", "")
    return f'<figure><img src="data:image/png;base64,{data}"><figcaption><b>{e(name)}</b> — {e(cap)}{" · " + when if when else ""}</figcaption></figure>'


def ok(flag):
    return '<span class="ok">Aprovado</span>' if flag else '<span class="bad">Reprovado</span>'


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
      ["INTEGRANTES", "Pedro Antônio Silva Pedroso Beltrão — 01605602 (responsável pelo código)<br>André Marcílio da Silva Ferreira — 01616701 (UI/UX, testes e documentação)<br>Evandro Albuquerque do Rêgo Lima — 01607434 (UI/UX, testes e documentação)"],
      ["PRAZO DA SPRINT", "14/11/2026"],
      ["VERSÃO", "1.0.0-rc.1 (release candidate)"],
      ["EXECUÇÃO E EVIDÊNCIAS", "11/11/2026 (sistema executado e verificado com dados reais, em banco descartável copiado do escola_db)"],
      ["REPOSITÓRIO", "https://github.com/PedroBeltraoDev/PlusEduc-MonoRepo — branch claude/sprint-10-release-candidate-b2b088"],
  ], ["28%", "72%"]).replace("<thead><tr><th></th><th></th></tr></thead>", "")}
  <p class="note">Documento consolidado: as Sprints 01 a 09 (já entregues) estão nas páginas anteriores, seguidas deste documento da Sprint 10.</p>
</section>
""")

P(f"""
<h2>1. Descrição da versão Release Candidate</h2>
<p>A versão <b>1.0.0-rc.1</b> é a candidata à entrega final do PlusEduc. Ela reúne os módulos já entregues nas sprints anteriores —
autenticação por perfil, turmas e alunos, atividades com correção automática e manual, notas e frequência, dashboard, relatórios com
exportação, pesquisa, histórico de operações e portal do aluno — e fecha as pendências que comprometiam os fluxos principais:</p>
<ul>
<li><b>Sessão contínua (RF01):</b> o refresh token passou a ser usado; a sessão é renovada sem mandar o usuário de volta ao login.</li>
<li><b>Troca de senha pelo próprio usuário (RF03):</b> antes o botão mostrava um aviso falso; agora a senha é trocada de verdade.</li>
<li><b>Aprovação do cadastro de professor (RF04):</b> o cadastro público dava acesso imediato aos dados de todos os alunos; agora fica pendente até um administrador aprovar.</li>
<li><b>Correções</b> de turma, matrícula, interface e dados (seção 7), <b>verificação de consistência do banco</b>, <b>documentação da API</b> gerada do código e <b>README final</b>.</li>
</ul>
<p>Arquitetura: frontend React + TypeScript + Vite + Tailwind, backend FastAPI (Python 3.12) em camadas (routers, serviços, repositórios),
MongoDB local, JWT com perfis ADMIN, TEACHER e STUDENT, estatísticas de notas em OpenCL. Toda a verificação desta sprint foi feita com o
sistema em execução, contra um banco descartável (<code>pluseduc_sprint10_eval</code>, cópia do <code>escola_db</code>); o <code>escola_db</code> só foi lido.</p>

<h3>Resultado em números</h3>
{table(["Verificação", "Casos", "Resultado"], [
    ["Suíte automatizada do backend (pytest)", "171", "171 aprovados (158 na Sprint 09)"],
    ["Regressão funcional da API: 92 casos da Sprint 09 + 12 novos", str(len(api)), f"{sum(r['ok'] for r in api)} aprovados"],
    ["Navegação pela interface (Chrome + Selenium)", str(len(nav)), f"{sum(r['ok'] for r in nav)} aprovados"],
    ["Validação pela interface (mensagens e campos)", str(len(val)), f"{sum(r['ok'] for r in val)} aprovados"],
    ["Revisão das telas finais (3 perfis, desktop e celular)", "35", "sem rolagem lateral; nenhum erro de console além do 403 esperado no login pendente"],
    ["Consistência do banco", "22", "escola_db: 2 com erro e 1 aviso; após o reparo: 0 erros, 1 aviso"],
    ["Frontend: type-check e build de produção", "—", "sem erros"],
], ["52%", "10%", "38%"])}
<p class="small">A regressão da API e as capturas foram executadas antes de duas correções finais (RC-03 e o aviso duplicado no login);
ambas estão cobertas pela suíte pytest e pelo type-check/build refeitos depois delas.</p>
""")

# 2. evidências de sistema estável
novos = [r for r in api if r["id"] in NOVOS]
P(f"""
<h2>2. Evidências do sistema estável e dos principais fluxos</h2>
<p>A regressão reexecutou contra a versão RC os 92 casos funcionais e de validação da Sprint 09 (autenticação, turmas, alunos, professores,
matérias, atividades, submissões, notas, relatórios, histórico, pesquisa e portal) e acrescentou 12 casos das funcionalidades novas.
Todos passaram. Os casos novos, com o resultado real obtido:</p>
{table(["ID", "Caso", "Esperado", "Obtido", "Resultado"],
       [[r["id"], e(r["titulo"]), e(r["esperado"]), e(r["obtido"]), ok(r["ok"])] for r in novos], ["8%", "20%", "27%", "33%", "12%"])}
<h3>Regressão por módulo (API)</h3>
""")
mods = {}
for r in api:
    m = mods.setdefault(r["modulo"], [0, 0])
    m[0] += 1
    m[1] += r["ok"]
P(table(["Módulo", "Casos", "Aprovados"], [[e(k), v[0], v[1]] for k, v in mods.items()] + [["<b>Total</b>", f"<b>{len(api)}</b>", f"<b>{sum(r['ok'] for r in api)}</b>"]], ["60%", "20%", "20%"]))
sess = [r for r in nav if r["id"].startswith("NAV-SS")]
P(f"""
<h3>Navegação: sessão renovada e sessão encerrada</h3>
<p>Com a renovação de sessão, o caso da Sprint 09 "token inválido volta ao login" mudou de propósito: token de acesso inválido com refresh token
válido mantém o usuário na tela; só com os dois inválidos a sessão termina.</p>
{table(["ID", "Ação", "Esperado", "Obtido", "Resultado"], [[r["id"], e(r["acao"]), e(r["esperado"]), e(str(r["obtido"])), ok(r["ok"])] for r in sess], ["10%", "30%", "22%", "26%", "12%"])}
<div class="grid">{img("n04_sessao_renovada.png")}{img("n05_sessao_encerrada.png")}</div>
<h3>Fluxo novo: cadastro de professor com aprovação (RF04)</h3>
<div class="grid">{img("c02_cadastro_professor.png")}{img("c04_login_pendente.png")}</div>
<div class="grid">{img("c06_admin_pendentes.png")}{img("c10_professor_aprovado.png")}</div>
<h3>Fluxo novo: troca de senha (RF03) e correção da criação de turma pelo ADMIN</h3>
<div class="grid">{img("c11_senha_confirmacao.png")}{img("c12_senha_alterada.png")}</div>
<div class="grid">{img("c08_admin_nova_turma.png")}{img("c09_admin_historico.png")}</div>
""")

# 3. interface final
P("<h2>3. Evidências da interface final</h2><p>Telas finais capturadas no sistema em execução, com os dados de demonstração. A relação completa (44 capturas, com horário) está em <code>docs/sprint-10/evidencias/</code>.</p>")
for a, b in (("t01_dashboard.png", "t02_turmas.png"), ("t04_atividade_detalhe.png", "t06_gerar_atividade.png"), ("t07_notas.png", "t08_relatorios.png"),
             ("t10_busca.png", "t13_configuracoes.png"), ("a01_inicio.png", "a03_atividade.png"), ("a06_notas.png", "a08_configuracoes.png"),
             ("e01_escuro_dashboard.png", "e02_escuro_configuracoes.png")):
    P(f'<div class="grid">{img(a)}{img(b)}</div>')
P(f'<div class="grid3">{img("m01_celular_dashboard.png")}{img("m03_celular_notas.png")}{img("m05_celular_aluno.png")}</div>')
P("<p>Ajustes de interface desta sprint: remoção dos dados fictícios das Configurações, cartão real de troca de senha, cartão de aprovação para o administrador, campo de professor responsável na criação de turma pelo administrador, aviso de erro ao baixar PDF e remoção das 53 mensagens de depuração que expunham dados de alunos no console do navegador.</p>")

# 4. banco
desc = {r["id"]: r for r in banco_antes}
P(f"""
<h2>4. Estrutura final do banco de dados</h2>
<p>MongoDB local (banco <code>escola_db</code>), 10 coleções. Toda coleção tem a chave primária <code>_id</code> (ObjectId); as chaves de negócio e os índices
são criados pela API ao iniciar. A descrição completa (campos, tipos, presença, índices e diagrama) está em <code>docs/MODELO_DE_DADOS.md</code>.</p>
{table(["Coleção", "Conteúdo", "Chave de negócio / índices"], [
    ["users", "contas de acesso; o papel (role) define as permissões", "e-mail único; active"],
    ["students", "cadastro pedagógico do aluno, turma e lacunas de aprendizagem", "matrícula única; email, class_id"],
    ["teachers", "cadastro do professor, matérias, turmas, situação da aprovação", "email"],
    ["classrooms", "turmas: série, ano, alunos, professor responsável e professor por matéria", "nome + ano entre as ativas; teacher_id, students"],
    ["subjects / subject_topics", "catálogo de matérias (BNCC) e tópicos", "nome normalizado único"],
    ["activities", "atividades objetivas e discursivas (questões e gabarito)", "classroom_id, student_id, created_by"],
    ["activity_submissions", "respostas dos alunos e correção", "activity_id + student_id único"],
    ["grades", "notas e presença (um documento por lançamento)", "studentId, classroomId, activityId"],
    ["audit_logs", "histórico de operações que alteram dados", "timestamp; actorId + timestamp; entity + action"],
], ["20%", "48%", "32%"])}
<h3>Relacionamentos</h3>
{table(["Campo", "Aponta para", "Significado"], [
    ["students.class_id e classrooms.students[]", "classrooms._id / students._id", "matrícula do aluno (gravada nos dois lados)"],
    ["users.studentId", "students._id", "login do aluno"],
    ["users.email = teachers.email", "—", "login do professor"],
    ["classrooms.teacher_id", "teachers._id", "professor responsável (ativo)"],
    ["classrooms.subjectTeachers[]", "subjects._id / teachers._id", "um professor por matéria na turma"],
    ["activities.classroom_id / student_id", "classrooms._id / students._id", "turma da atividade e aluno (opcional)"],
    ["activity_submissions.activity_id / student_id", "activities._id / students._id", "resposta de um aluno a uma atividade"],
    ["grades.studentId / classroomId / activityId", "students / classrooms / activities", "nota do aluno, opcionalmente vinda de uma atividade"],
], ["36%", "28%", "36%"])}
<p>Campos acrescentados na Sprint 10: <code>users.pendingApproval</code>, <code>teachers.approval_status</code>, <code>approved_by</code> e <code>approved_at</code>. Não houve mudança em coleções nem índices existentes: nenhum banco precisa de migração.</p>
<h3>Verificação de consistência (scripts/check_database.py)</h3>
{table(["ID", "Verificação", "escola_db (somente leitura)", "Após o reparo (descartável)"],
       [[r["id"], e(r["verificacao"]), ("ok" if not r["problemas"] else f'<span class="bad">{r["nivel"]}: {r["problemas"]}</span>'),
         ("ok" if not d["problemas"] else f'{d["nivel"]}: {d["problemas"]}')] for r, d in zip(banco_antes, banco_depois)], ["9%", "55%", "18%", "18%"])}
<p class="small">REF-09: 3 atividades de março e abril apontam para turma e aluno inexistentes; REF-10: 2 respostas a atividades inexistentes; DOM-04: um professor com 12 turmas ativas (dado anterior à regra de 5). O reparo remove só os órfãos; a redistribuição das turmas é decisão da escola.</p>
""")

# 5. API
P(f"""
<h2>5. Documentação das APIs</h2>
<p>A API REST tem <b>99 rotas</b> em 18 grupos. A documentação é gerada do próprio código, então não fica desatualizada:</p>
{table(["Onde", "Conteúdo"], [
    ["docs/API.md (repositório)", "autenticação, perfis, formato de erro, 7 exemplos com curl, tabela de rotas por grupo com o perfil de acesso, parâmetros, corpos, respostas e todos os esquemas"],
    ["http://127.0.0.1:8080/docs", "Swagger UI interativo, em português, com o perfil exigido em cada rota e o botão Authorize"],
    ["http://127.0.0.1:8080/redoc", "ReDoc (leitura)"],
    ["docs/api/openapi.json", "esquema OpenAPI 3.1, importável no Postman ou Insomnia"],
], ["32%", "68%"])}
<h3>Autenticação e exemplo de uso</h3>
<pre>POST /api/auth/login  {{"email": "...", "password": "..."}}
→ 200 {{"accessToken": "...", "refreshToken": "...", "tokenType": "Bearer", "expiresIn": 28800, "role": "TEACHER", ...}}

GET /api/classrooms     Authorization: Bearer &lt;accessToken&gt;
POST /api/auth/refresh  {{"refreshToken": "..."}}   → novo par de tokens

Erro (sempre o mesmo formato):
{{"timestamp": "2026-11-11T18:00:00Z", "status": 400, "error": "Bad Request", "message": "Senha atual incorreta"}}</pre>
{table(["Grupo", "Rotas principais", "Acesso"], [
    ["Autenticação", "login, refresh, change-password, register/student, register/teacher, forgot/reset-password, profile", "público / autenticado"],
    ["Professores", "CRUD, pending, {{id}}/approve, {{id}}/reject", "TEACHER ou ADMIN; aprovação só ADMIN"],
    ["Turmas e alunos", "CRUD, enroll/unenroll, performance, unassigned, enable-access", "TEACHER ou ADMIN"],
    ["Atividades e correção", "CRUD, generate, submissions, export-pdf, activity-corrections", "TEACHER ou ADMIN"],
    ["Notas e frequência", "CRUD, classroom/{{id}}/summary, from-activity/{{id}}", "TEACHER ou ADMIN"],
    ["Dashboard, relatórios, pesquisa, histórico", "dashboard/overview, reports, reports/{{tipo}}/export, search, audit-logs", "TEACHER ou ADMIN"],
    ["Portal do aluno", "me, classroom, classmates, teachers, activities, submissions, grades, performance", "STUDENT"],
], ["24%", "50%", "26%"])}
<div class="grid">{img("d01_swagger.png")}{img("d02_redoc.png")}</div>
<p class="small">tests/test_openapi_docs.py reprova a suíte se alguma rota ficar sem resumo, grupo ou perfil, ou se o perfil documentado divergir da matriz de permissões.</p>
""")

# 6. repositório
P("""
<h2>6. Repositório GitHub e README</h2>
<p>Repositório: <b>https://github.com/PedroBeltraoDev/PlusEduc-MonoRepo</b> — trabalho da sprint no branch
<code>claude/sprint-10-release-candidate-b2b088</code> (inclui a Sprint 09, PR #12).</p>
<p>O <code>README.md</code> da raiz foi reescrito com todos os itens pedidos: nome e descrição, objetivo da solução, equipe, tecnologias, requisitos,
instalação e configuração (variáveis do <code>.env</code>), configuração do banco (MongoDB, criação do administrador, dados de demonstração e verificação de
consistência), comandos de execução e de testes, documentação da API e estrutura do projeto. Documentos de apoio: <code>docs/ARQUITETURA.md</code>,
<code>docs/MODELO_DE_DADOS.md</code>, <code>docs/API.md</code>, <code>docs/REQUISITOS_STATUS.md</code> e <code>docs/sprint-10/README.md</code>.</p>
""")

# 7. correções
P(f"""
<h2>7. Principais correções e ajustes</h2>
{table(["ID", "Problema encontrado", "Gravidade", "Correção"], [
    ["RF01", "Refresh token emitido mas sem rota de renovação; com o token vencido o usuário ia para o login", "pendência", "POST /api/auth/refresh e renovação automática no frontend"],
    ["RF03", "Sem troca de senha logado; o botão das Configurações mostrava um aviso falso", "pendência", "POST /api/auth/change-password e cartão nas Configurações (professor, admin e aluno)"],
    ["RF04", "Cadastro público de professor ativava a conta na hora, com acesso aos dados de todos os alunos", "pendência (segurança)", "Conta pendente; ADMIN aprova ou recusa; scripts/create_admin.py"],
    ["RC-01", "ADMIN não conseguia criar turma pela tela (400)", "alta", "Formulário pede o professor responsável ao ADMIN"],
    ["RC-02", "Turma aceitava professor excluído ou pendente; edição aceitava professor inexistente", "média", "Professor existente e ativo obrigatório"],
    ["RC-03", "Aluno criado já com turma não aparecia na lista da turma", "média", "Matrícula gravada nos dois lados"],
    ["RC-04", "Tela de Turmas imprimia dados de alunos no console do navegador (LGPD)", "média", "53 mensagens de depuração removidas"],
    ["RC-05", "Configurações com dados fixos (último acesso, dispositivo, função)", "baixa", "Dados reais da sessão e função correta"],
    ["RC-06", "Falha ao baixar PDF de atividade sem aviso", "baixa", "Mensagem de erro na tela"],
    ["RC-07", "Atividades e respostas órfãs no banco", "baixa", "check_database.py --repair"],
    ["Docs", "Swagger com rotas em inglês e sem perfil; README incompleto; versão 0.1.0", "—", "API documentada (99 rotas), README final, versão 1.0.0-rc.1"],
], ["8%", "42%", "14%", "36%"])}
""")

# 8. pendências
P(f"""
<h2>8. Pendências e próximos passos</h2>
{table(["Pendência", "Situação", "Como a equipe pretende resolver"], [
    ["Predição de risco, agrupamento por perfil e otimização de grupos de reforço (RF19, RF21, RF22)", "não implementados", "Sprint 11: modelo de risco (scikit-learn) sobre notas, frequência e lacunas, exibido no painel do aluno; K-Means se houver tempo; otimização registrada como trabalho futuro"],
    ["Escopo de dados por turma (qualquer professor vê qualquer turma)", "não implementado", "decidir com a orientação: manter (coordenação única) ou restringir pelo professor da matéria"],
    ["Integração contínua (GitHub Actions)", "não implementada", "cerca de 40 testes dependem de dados já existentes; criar um seed mínimo para os testes e então ligar o pipeline"],
    ["Dados antigos no escola_db (órfãos e professor com 12 turmas)", "identificados", "backup, check_database.py --repair e redistribuição das turmas antes da gravação dos vídeos"],
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
.cover {{ text-align: center; padding-top: 70px; }}
.cover h1 {{ font-size: 32pt; margin: 0; }} .cover h2 {{ font-size: 17pt; border: 0; margin: 4px 0 18px; page-break-before: avoid; }}
.cover .sub {{ font-size: 12pt; color: #333; }} .cover table {{ text-align: left; font-size: 9pt; margin-top: 18px; }}
.cover td:first-child {{ background: #dce4f0; font-weight: bold; color: {NAVY}; }}
.cover .note {{ text-align: left; font-size: 10.5pt; margin-top: 16px; }}
.cover + h2 {{ page-break-before: always; }}
"""
doc = f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Sprint 10</title><style>{CSS}</style></head><body>{"".join(parts)}</body></html>'
html_path = Path(os.environ.get("TEMP", ".")) / "pluseduc_sprint10.html"
html_path.write_text(doc, encoding="utf-8")

opts = Options()
opts.add_argument("--headless=new")
driver = webdriver.Chrome(options=opts)
try:
    driver.get(html_path.as_uri())
    header = f'<div style="width:100%;margin:0 16mm;background:{NAVY};color:#fff;font:bold 7pt Arial;padding:5px 8px;-webkit-print-color-adjust:exact">PLUS EDUC &nbsp;|&nbsp; FÁBRICA DE SOFTWARE</div>'
    footer = ('<div style="width:100%;margin:0 16mm;border-top:1px solid #ccc;font:7pt Arial;color:#666;padding-top:4px;display:flex;justify-content:space-between">'
              '<span>Grupo 08 • Sprint 10 • 14/11/2026</span><span class="pageNumber"></span></div>')
    pdf = driver.execute_cdp_cmd("Page.printToPDF", {
        "printBackground": True, "preferCSSPageSize": True, "displayHeaderFooter": True,
        "headerTemplate": header, "footerTemplate": footer,
    })
finally:
    driver.quit()
section = Path(os.environ.get("TEMP", ".")) / "pluseduc_sprint10_secao.pdf"
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
