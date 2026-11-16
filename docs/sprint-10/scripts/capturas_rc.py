"""Capturas da versão release candidate (Sprint 10): todas as telas dos três perfis e os fluxos novos.

    PLUSEDUC_EVAL_PASSWORD=... PLUSEDUC_EVAL_DB=pluseduc_sprint10_eval python capturas_rc.py

Requer o backend (PLUSEDUC_API, padrão :8093) e o frontend (PLUSEDUC_UI, padrão :5193) apontando para o banco
descartável, as contas de docs/sprint-08/scripts/preparar_usuarios.py e um ADMIN criado com
PlusEduc-BE-Python/scripts/create_admin.py (PLUSEDUC_ADMIN_EMAIL, padrão coordenacao@pluseduc.local).

Além das imagens, grava resultados/revisao_interface.json: para cada tela, se houve rolagem lateral e quantos
erros graves o console do navegador registrou.
"""
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evid  # noqa: E402
from evid import By, PW, UI, clear_session, goto, login_ui, make_driver, shot, xp  # noqa: E402
from pymongo import MongoClient  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
API = os.environ.get("PLUSEDUC_API", "http://127.0.0.1:8093")
ADMIN = os.environ.get("PLUSEDUC_ADMIN_EMAIL", "coordenacao@pluseduc.local")
PROF, ALUNO = "marina.ferreira@pluseduc.local", "lucas.carvalho@aluno.local"
db = MongoClient("mongodb://localhost:27017")[os.environ.get("PLUSEDUC_EVAL_DB", "pluseduc_sprint10_eval")]
lucas = db.students.find_one({"email": ALUNO})
ACT = str(db.activities.find_one({"classroom_id": lucas["class_id"]})["_id"])
RUN = uuid.uuid4().hex[:6]
NOVO_PROF = f"prof.rc.{RUN}@professor.local"
REVISAO = []


def revisar(d, perfil, tela, largura=1366):
    """Confere a tela aberta: rolagem lateral e erros graves no console do navegador."""
    overflow = d.execute_script("return document.documentElement.scrollWidth > window.innerWidth + 2")
    try:
        severe = [e["message"][:160] for e in d.get_log("browser") if e.get("level") == "SEVERE" and "favicon" not in e.get("message", "")]
    except Exception:  # noqa: BLE001 - nem todo driver expõe o log
        severe = []
    REVISAO.append({"perfil": perfil, "tela": tela, "largura": largura, "rolagem_horizontal": bool(overflow), "erros_console": severe})


def tela(d, perfil, path, nome, legenda, settle=2.6, full=False):
    goto(d, path, settle)
    revisar(d, perfil, path.replace(ACT, "{id}"))
    shot(d, nome, legenda, full=full)


def campos(d):
    return d.find_elements(By.CSS_SELECTOR, "input")


d = make_driver()
try:
    # ------------------------------------------------------------------ acesso público e cadastro com aprovação
    clear_session(d)
    d.get_log("browser")  # descarta o que veio antes
    tela(d, "público", "/login", "c01_login", "Acesso — tela de login (versão final)", 1.2)
    xp(d, "//*[contains(text(),'Cadastre-se como professor')]").click()
    time.sleep(0.6)
    ins = campos(d)
    ins[0].send_keys("Professora Release Candidate")
    ins[1].send_keys(NOVO_PROF)
    ins[2].send_keys(PW)
    ins[3].send_keys(PW)
    shot(d, "c02_cadastro_professor", "RF04 — cadastro público de professor: o texto avisa que o acesso depende de aprovação")
    xp(d, "//button[contains(., 'Solicitar acesso')]").click()
    time.sleep(2)
    revisar(d, "público", "/login (cadastro de professor enviado)")
    shot(d, "c03_cadastro_pendente", "RF04 — cadastro enviado: nenhum acesso é liberado; a tela volta ao login com o aviso")
    ins = campos(d)
    ins[1].send_keys(PW)
    xp(d, "//button[contains(., 'Entrar')]").click()
    time.sleep(1.8)
    shot(d, "c04_login_pendente", "RF04 — professor ainda não aprovado tenta entrar: o servidor recusa (403) e a tela explica")
    tela(d, "público", "/esqueci-senha", "c05_esqueci_senha", "Acesso — recuperação de senha por código", 1.2)

    # ------------------------------------------------------------------ administrador aprova
    login_ui(d, ADMIN, expect_path="/dashboard")
    tela(d, "admin", "/configuracoes", "c06_admin_pendentes", "RF04 — ADMIN em Configurações: cadastros de professores pendentes", full=True)
    xp(d, f"//li[contains(., '{NOVO_PROF}')]//button[contains(., 'Aprovar')]").click()
    time.sleep(1.5)
    shot(d, "c07_admin_aprovou", "RF04 — ADMIN aprovou: o cadastro sai da lista e o acesso é liberado")
    goto(d, "/turmas", 3)
    xp(d, "//button[contains(., 'Nova Turma')]").click()
    time.sleep(1)
    revisar(d, "admin", "/turmas (modal Nova Turma)")
    shot(d, "c08_admin_nova_turma", "Correção — ADMIN cria turma escolhendo o professor responsável (antes a criação falhava)")
    tela(d, "admin", "/historico", "c09_admin_historico", "Histórico — o ADMIN vê as operações de todos, inclusive a aprovação do cadastro")

    # ------------------------------------------------------------------ professor aprovado entra e troca a senha
    login_ui(d, NOVO_PROF, expect_path="/dashboard")
    revisar(d, "professor", "/dashboard (professor recém-aprovado)")
    shot(d, "c10_professor_aprovado", "RF04 — depois da aprovação, o professor entra normalmente")
    goto(d, "/configuracoes", 2)
    d.find_element(By.ID, "current-password").send_keys(PW)
    d.find_element(By.ID, "new-password").send_keys(PW + "x")
    d.find_element(By.ID, "confirm-password").send_keys(PW + "y")
    xp(d, "//button[contains(., 'Salvar nova senha')]").click()
    time.sleep(0.8)
    shot(d, "c11_senha_confirmacao", "RF03 — troca de senha: confirmação diferente é recusada na tela", full=True)
    d.find_element(By.ID, "confirm-password").clear()
    d.find_element(By.ID, "confirm-password").send_keys(PW + "x")
    xp(d, "//button[contains(., 'Salvar nova senha')]").click()
    time.sleep(1.6)
    revisar(d, "professor", "/configuracoes (troca de senha)")
    shot(d, "c12_senha_alterada", "RF03 — senha alterada pelo próprio usuário (aviso de sucesso)", full=True)
    login_ui(d, NOVO_PROF, password=PW + "x", expect_path="/dashboard")
    shot(d, "c13_login_senha_nova", "RF03 — login com a senha nova funciona")

    # ------------------------------------------------------------------ telas finais do professor
    login_ui(d, PROF, expect_path="/dashboard")
    for path, nome, legenda, full in (
        ("/dashboard", "t01_dashboard", "Interface final — Dashboard do professor", True),
        ("/turmas", "t02_turmas", "Interface final — Turmas", False),
        ("/atividades", "t03_atividades", "Interface final — Atividades", False),
        (f"/atividades/{ACT}", "t04_atividade_detalhe", "Interface final — Atividade: participação e respostas da turma", False),
        ("/nova-atividade", "t05_nova_atividade", "Interface final — Nova atividade (manual)", False),
        ("/gerar-atividade", "t06_gerar_atividade", "Interface final — Gerar atividade com apoio de IA", False),
        ("/notas", "t07_notas", "Interface final — Notas e Frequência", False),
        ("/relatorios", "t08_relatorios", "Interface final — Relatórios com filtros e exportação", False),
        ("/historico", "t09_historico", "Interface final — Histórico de operações", False),
        ("/busca?q=lucas", "t10_busca", "Interface final — Pesquisa global", False),
        ("/materias", "t11_materias", "Interface final — Matérias", False),
        ("/materias-topicos", "t12_topicos", "Interface final — Tópicos das matérias", False),
        ("/configuracoes", "t13_configuracoes", "Interface final — Configurações (perfil, tema, troca de senha e sessão)", True),
    ):
        tela(d, "professor", path, nome, legenda, 3.0, full)

    # ------------------------------------------------------------------ telas finais do aluno
    login_ui(d, ALUNO, expect_path="/aluno")
    for path, nome, legenda in (
        ("/aluno", "a01_inicio", "Interface final — Portal do aluno: início"),
        ("/aluno/atividades", "a02_atividades", "Interface final — Portal do aluno: atividades"),
        (f"/aluno/atividades/{ACT}", "a03_atividade", "Interface final — Portal do aluno: atividade (sem gabarito)"),
        ("/aluno/turma", "a04_turma", "Interface final — Portal do aluno: minha turma (sem e-mail dos colegas)"),
        ("/aluno/professores", "a05_professores", "Interface final — Portal do aluno: professores"),
        ("/aluno/notas", "a06_notas", "Interface final — Portal do aluno: minhas notas"),
        ("/aluno/desempenho", "a07_desempenho", "Interface final — Portal do aluno: desempenho por disciplina"),
        ("/aluno/configuracoes", "a08_configuracoes", "Interface final — Portal do aluno: configurações com troca de senha"),
    ):
        tela(d, "aluno", path, nome, legenda, 2.8, path.endswith("configuracoes"))

    # ------------------------------------------------------------------ modo escuro e celular
    login_ui(d, PROF, expect_path="/dashboard")
    for path, nome, legenda in (("/dashboard", "e01_escuro_dashboard", "Modo escuro — dashboard"), ("/configuracoes", "e02_escuro_configuracoes", "Modo escuro — configurações")):
        goto(d, path, 3)
        d.execute_script("document.documentElement.classList.add('dark')")
        time.sleep(0.8)
        shot(d, nome, legenda)
    d.quit()
    d = make_driver(390, 844)
    login_ui(d, PROF, expect_path="/dashboard")
    for path, nome, legenda in (("/dashboard", "m01_celular_dashboard", "dashboard"), ("/turmas", "m02_celular_turmas", "turmas"), ("/notas", "m03_celular_notas", "notas e frequência"),
                                ("/configuracoes", "m04_celular_configuracoes", "configurações")):
        goto(d, path, 3)
        revisar(d, "professor", path, 390)
        shot(d, nome, f"Celular (390 px) — {legenda}")
    login_ui(d, ALUNO, expect_path="/aluno")
    for path, nome, legenda in (("/aluno", "m05_celular_aluno", "início do aluno"), ("/aluno/configuracoes", "m06_celular_aluno_config", "configurações do aluno")):
        goto(d, path, 3)
        revisar(d, "aluno", path, 390)
        shot(d, nome, f"Celular (390 px) — {legenda}")
    d.quit()

    # ------------------------------------------------------------------ documentação da API publicada pelo servidor
    d = make_driver(1366, 1000)
    evid.UI = API
    d.get(API + "/docs")
    time.sleep(4)
    shot(d, "d01_swagger", "Documentação da API — Swagger UI servido pelo backend em /docs")
    d.get(API + "/redoc")
    time.sleep(5)
    shot(d, "d02_redoc", "Documentação da API — ReDoc servido pelo backend em /redoc")
finally:
    try:
        d.quit()
    except Exception:  # noqa: BLE001
        pass
    db.users.delete_many({"email": NOVO_PROF})
    db.teachers.delete_many({"email": NOVO_PROF})
    json.dump(REVISAO, open(os.path.join(HERE, "..", "resultados", "revisao_interface.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(evid.MANIFEST, open(os.path.join(HERE, "..", "evidencias", "manifest_rc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
problemas = [r for r in REVISAO if r["rolagem_horizontal"] or r["erros_console"]]
print(f"{len(REVISAO)} telas revisadas; com rolagem lateral ou erro de console: {len(problemas)}")
for p in problemas:
    print(" ", p)
