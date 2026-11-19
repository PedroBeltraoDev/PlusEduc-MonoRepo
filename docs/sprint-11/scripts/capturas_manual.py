"""Capturas dos fluxos do Manual do Usuário (Sprint 11), com o sistema em execução e um banco descartável.

    PLUSEDUC_EVAL_PASSWORD=... PLUSEDUC_EVID_DIR=docs/manuais/imagens python capturas_manual.py

Usa o mesmo apoio de captura da Sprint 10 (docs/sprint-10/scripts/evid.py). Requer a API (PLUSEDUC_API, padrão :8093)
e a interface (PLUSEDUC_UI, padrão :5193) apontando para o banco de avaliação preparado por
docs/sprint-10/scripts/preparar_entrega.py. Cria, pela API, uma atividade de demonstração para a turma do aluno de teste
(duas questões objetivas e uma discursiva), e depois percorre os fluxos de professor e aluno pela interface.
"""
import json
import os
import sys
import time
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "sprint-10" / "scripts"))
import evid  # noqa: E402
from evid import By, PW, UI, goto, login_ui, make_driver, shot, xp  # noqa: E402

API = os.environ.get("PLUSEDUC_API", "http://127.0.0.1:8093")
PROF, ALUNO = "marina.ferreira@pluseduc.local", "lucas.carvalho@aluno.local"
RUN = uuid.uuid4().hex[:4]


def api(method, path, body=None, token=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read() or b"{}")


def click_text(d, text, tag="*"):
    xp(d, f"//{tag}[contains(normalize-space(.), '{text}')]").click()
    time.sleep(1.2)


def esc(d):
    from selenium.webdriver.common.keys import Keys
    d.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    time.sleep(0.6)


# ---------------------------------------------------------------- atividade de demonstração (pela API)
tok = api("POST", "/api/auth/login", {"email": PROF, "password": PW})["accessToken"]
classe = next(c for c in api("GET", "/api/classrooms", token=tok) if c.get("studentIds"))
titulo = f"Revisão de frações {RUN}"
atividade = api("POST", "/api/activities", {
    "title": titulo, "subject": "Matemática", "topic": "Frações", "difficultyLevel": "FACIL", "questionsCount": 3,
    "format": "MISTA", "classroomId": classe["id"],
    "questions": [
        {"questionText": "Quanto é 1/2 + 1/4?", "questionType": "MULTIPLA_ESCOLHA", "options": ["2/6", "3/4", "1/8", "2/4"], "correctAnswer": "B"},
        {"questionText": "Qual fração é equivalente a 2/3?", "questionType": "MULTIPLA_ESCOLHA", "options": ["4/6", "3/2", "2/6", "6/4"], "correctAnswer": "A"},
        {"questionText": "Explique, com suas palavras, como somar frações com denominadores diferentes.", "questionType": "DISCURSIVA",
         "options": [], "correctAnswer": "Encontrar um denominador comum, converter as frações e somar os numeradores."},
    ],
}, token=tok)
ACT = atividade["id"]
print("atividade de demonstração:", titulo, ACT)

d = make_driver()
try:
    # ------------------------------------------------------------ professor: turmas, alunos, notas, atividades
    login_ui(d, PROF, expect_path="/dashboard")
    goto(d, "/turmas", 3)
    click_text(d, "Nova Turma", "button")
    shot(d, "p01_nova_turma", "Turmas — formulário de nova turma (nome, série, ano e letra)")
    esc(d)
    goto(d, "/turmas", 3)
    click_text(d, "Adicionar Aluno", "button")
    shot(d, "p02_adicionar_aluno", "Turmas — cadastro de aluno (nome, e-mail, nascimento, turma e lacunas de aprendizagem)")
    esc(d)
    goto(d, "/turmas", 3)
    nome_turma = classe["name"]
    xp(d, f"//*[contains(normalize-space(.), '{nome_turma}') and (self::button or self::div[@role='button'] or self::h3 or self::p)]").click()
    time.sleep(2)
    shot(d, "p03_turma_detalhe", "Turmas — detalhe da turma: alunos, matérias e professores, atividades", full=True)
    esc(d)
    goto(d, "/notas", 3)
    click_text(d, "Lançar nota", "button")
    shot(d, "p04_lancar_nota", "Notas e Frequência — lançamento de nota e presença de um aluno")
    esc(d)
    goto(d, "/nova-atividade", 2.5)
    shot(d, "p05_nova_atividade", "Atividades — criação manual: dados principais, questões e prévia", full=True)
    goto(d, "/gerar-atividade", 2.5)
    shot(d, "p06_gerar_atividade", "Atividades — geração com apoio de IA: matéria, tópico, dificuldade, formato e adaptações", full=True)
    goto(d, "/atividades", 3)
    shot(d, "p07_atividades", "Atividades — lista com filtros, atividades geradas com IA e correções pendentes")
    goto(d, "/relatorios", 3)
    shot(d, "p08_relatorios", "Relatórios — escolha do relatório, filtros e exportação (CSV, Excel e PDF)", full=True)

    # ------------------------------------------------------------ professor libera o portal para um aluno cadastrado pela escola
    novo = api("POST", "/api/students", {"name": "Bianca Souza Lima", "email": f"bianca.lima.{RUN}@aluno.local",
                                          "birthDate": "2012-08-14", "classId": classe["id"]}, token=tok)
    NOVO_ALUNO = novo["id"]
    goto(d, "/turmas", 3)
    xp(d, f"//*[contains(normalize-space(.), '{nome_turma}') and (self::button or self::div[@role='button'] or self::h3 or self::p)]").click()
    time.sleep(2)
    xp(d, "//h3[contains(., 'Bianca Souza Lima')]").click()
    time.sleep(2)
    shot(d, "p13_aluno_sem_acesso", "Turmas — aluno cadastrado pela escola ainda sem acesso ao portal: botão Liberar acesso ao portal")
    click_text(d, "Liberar acesso ao portal", "button")
    d.find_element(By.ID, "portal-password").send_keys(PW)
    d.find_element(By.ID, "portal-password-confirm").send_keys(PW)
    shot(d, "p14_liberar_acesso", "Turmas — liberação do acesso: o professor define a senha inicial do aluno")
    xp(d, "//button[@type='submit' and contains(., 'Liberar acesso')]").click()
    time.sleep(1.5)
    shot(d, "p15_acesso_liberado", "Turmas — acesso liberado: o aviso confirma e o botão some")
    ok_login = api("POST", "/api/auth/login", {"email": novo["email"], "password": PW}).get("studentId") == NOVO_ALUNO
    print("aluno novo entra no portal:", ok_login)

    # ------------------------------------------------------------ aluno: responde a atividade
    login_ui(d, ALUNO, expect_path="/aluno")
    goto(d, "/aluno/atividades", 3)
    shot(d, "s01_atividades_aluno", "Portal do aluno — atividades da turma, com a situação de cada uma")
    goto(d, f"/aluno/atividades/{ACT}", 3)
    radios = d.find_elements(By.CSS_SELECTOR, "input[type=radio]")
    radios[1].find_element(By.XPATH, "..").click()   # questão 1, alternativa B
    radios[4].find_element(By.XPATH, "..").click()   # questão 2, alternativa A
    d.find_element(By.CSS_SELECTOR, "textarea").send_keys("Primeiro encontro um denominador comum, transformo as frações e depois somo os numeradores.")
    time.sleep(1.5)
    shot(d, "s02_respondendo", "Portal do aluno — respondendo: a alternativa escolhida fica marcada e o rascunho é salvo no aparelho", full=True)
    click_text(d, "Enviar atividade", "button")
    time.sleep(2.5)
    shot(d, "s03_resultado", "Portal do aluno — atividade enviada: nota das objetivas e discursiva aguardando correção", full=True)

    # ------------------------------------------------------------ professor: acompanha e corrige
    login_ui(d, PROF, expect_path="/dashboard")
    goto(d, "/dashboard", 3)
    sino = [b for b in d.find_elements(By.CSS_SELECTOR, "button[aria-label*='correç'], button[aria-label='Notificações']") if b.is_displayed()]
    if sino:
        sino[0].click()
        time.sleep(1.2)
        shot(d, "p09_notificacoes", "Notificações — respostas discursivas aguardando correção")
        esc(d)
    goto(d, "/atividades", 3)
    painel = d.find_elements(By.XPATH, "//h2[contains(., 'Correções pendentes')]")
    if painel:
        d.execute_script("arguments[0].scrollIntoView({block: 'start'}); window.scrollBy(0, -90);", painel[0])
    d.find_element(By.CSS_SELECTOR, "textarea[placeholder*='Feedback']").send_keys("Muito bem! Você explicou o denominador comum com clareza.")
    time.sleep(0.6)
    shot(d, "p11_correcao_discursiva", "Atividades — correção da questão discursiva: feedback opcional e Marcar correta ou Marcar incorreta")
    click_text(d, "Marcar correta", "button")
    time.sleep(1.5)
    goto(d, f"/atividades/{ACT}", 3)
    shot(d, "p10_atividade_professor", "Atividade — detalhe para o professor: participação da turma, PDF e lançamento das notas no boletim")
    click_text(d, "Lançar notas no boletim", "button")
    time.sleep(1.2)
    shot(d, "p12_notas_lancadas", "Atividade — notas lançadas no boletim (o aviso confirma quantos alunos receberam nota)")

    # ------------------------------------------------------------ aluno: vê a correção e a nota
    login_ui(d, ALUNO, expect_path="/aluno")
    goto(d, f"/aluno/atividades/{ACT}", 3)
    shot(d, "s04_corrigida", "Portal do aluno — atividade corrigida, com o feedback do professor na questão discursiva", full=True)
    goto(d, "/aluno/notas", 3)
    shot(d, "s05_notas", "Portal do aluno — Minhas Notas: a nota da atividade aparece no boletim")
finally:
    try:
        d.quit()
    except Exception:  # noqa: BLE001
        pass
    try:
        limpeza = api("POST", "/api/auth/login", {"email": PROF, "password": PW})["accessToken"]
        api("DELETE", f"/api/activities/{ACT}", token=limpeza)
        if "NOVO_ALUNO" in globals():
            api("DELETE", f"/api/students/{NOVO_ALUNO}", token=limpeza)
    except Exception as exc:  # noqa: BLE001
        print("não foi possível remover os dados de demonstração:", exc)
    json.dump(evid.MANIFEST, open(os.path.join(evid._OUT_DIR, "manifest_manual.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("capturas:", len(evid.MANIFEST))
