"""Testes de validação pela interface da Sprint 09 (Chrome headless + Selenium): campos obrigatórios, formatos e mensagens.

    PLUSEDUC_EVAL_PASSWORD=... PLUSEDUC_EVAL_DB=pluseduc_sprint9_eval python testes_validacao_ui.py saida.json
"""
import json
import os
import sys
import time

import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evid  # noqa: E402
from evid import By, PW, UI, clear_session, goto, login_ui, make_driver, shot, wait, xp  # noqa: E402
from pymongo import MongoClient  # noqa: E402
from selenium.webdriver.support.ui import Select  # noqa: E402

evid.OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidencias")
OUT_JSON = sys.argv[1]
DBN = os.environ.get("PLUSEDUC_EVAL_DB", "pluseduc_sprint9_eval")
db = MongoClient("mongodb://localhost:27017")[DBN]


class _Api:
    """Cliente HTTP mínimo (o Python do sistema não tem httpx)."""

    def _call(self, method, path, headers=None, json_body=None):
        data = json.dumps(json_body).encode() if json_body is not None else None
        req = urllib.request.Request("http://127.0.0.1:8091" + path, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
        return type("R", (), {"json": lambda self_: json.loads(raw or b"{}")})()

    def post(self, path, headers=None, json=None):
        return self._call("POST", path, headers, json)

    def delete(self, path, headers=None):
        return self._call("DELETE", path, headers)


api = _Api()
RESULTS = []
SET_VALUE = """const el=arguments[0], v=arguments[1];
const proto = el.tagName==='TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
Object.getOwnPropertyDescriptor(proto,'value').set.call(el,v);
el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true}));"""


def rec(cid, tela, acao, esperado, obtido, ok):
    RESULTS.append({"id": cid, "tela": tela, "acao": acao, "esperado": esperado, "obtido": obtido, "ok": bool(ok)})
    print(("OK    " if ok else "FALHA ") + f"{cid} [{tela}] {acao} -> esperado {esperado}; obtido {obtido}")


def toast_text(d, wait_s=2.5):
    end = time.time() + wait_s
    while time.time() < end:
        t = d.execute_script("return [...document.querySelectorAll('[data-sonner-toast]')].map(e => e.innerText).join(' | ')")
        if t:
            return t.strip().replace("\n", " ")
        time.sleep(0.2)
    return ""


def banner_text(d):
    return d.execute_script("const e=[...document.querySelectorAll('div,p')].find(x=>x.className && /red-(50|600|700)/.test(x.className) && x.innerText && x.innerText.length<140); return e ? e.innerText.trim() : ''")


def set_value(d, el, value):
    d.execute_script(SET_VALUE, el, value)


d = make_driver()
try:
    # ---------------------------------------------------------------- login
    clear_session(d)
    goto(d, "/login")
    xp(d, "//button[contains(., 'Entrar')]").click()
    time.sleep(0.6)
    ins = d.find_elements(By.CSS_SELECTOR, "input")
    msgs = [i.get_attribute("validationMessage") for i in ins[:2]]
    rec("VAL-UI-01", "Login", "clicar em Entrar com e-mail e senha vazios", "o navegador bloqueia o envio e pede o campo obrigatório", f"{msgs}", all(msgs) and "login" in d.current_url)
    shot(d, "v01_login_vazio", "Validação — login com campos vazios: o formulário não é enviado")
    ins[0].send_keys("marina.ferreira@pluseduc.local")
    ins[1].send_keys("senha-errada")
    xp(d, "//button[contains(., 'Entrar')]").click()
    time.sleep(1.5)
    b = banner_text(d)
    rec("VAL-UI-02", "Login", "senha incorreta", "banner \"E-mail ou senha inválidos.\"", b, "inválidos" in b)
    shot(d, "v02_login_senha_errada", "Validação — senha incorreta: mensagem clara em português")
    # ---------------------------------------------------------------- cadastro
    goto(d, "/login")
    xp(d, "//*[contains(text(),'Cadastre-se como aluno')]").click()
    time.sleep(0.6)
    ins = d.find_elements(By.CSS_SELECTOR, "input")
    ins[0].send_keys("Aluno Validacao Teste")
    ins[1].send_keys("email-sem-arroba")
    ins[2].send_keys("senha-123")
    ins[3].send_keys("senha-123")
    xp(d, "//button[contains(., 'Criar acesso')]").click()
    time.sleep(0.6)
    vm = ins[1].get_attribute("validationMessage")
    rec("VAL-UI-03", "Cadastro de aluno", "e-mail sem arroba", "o navegador recusa o formato do e-mail", vm, bool(vm))
    shot(d, "v03_cadastro_email_invalido", "Validação — cadastro com e-mail em formato inválido")
    ins[1].clear()
    ins[1].send_keys("aluno.validacao@aluno.local")
    ins[3].clear()
    ins[3].send_keys("outra-senha")
    xp(d, "//button[contains(., 'Criar acesso')]").click()
    time.sleep(1)
    b = banner_text(d)
    rec("VAL-UI-04", "Cadastro de aluno", "senha e confirmação diferentes", "\"As senhas não coincidem\"", b, "não coincidem" in b)
    shot(d, "v04_cadastro_senhas_diferentes", "Validação — confirmação de senha diferente da senha")
    ins[3].clear()
    ins[3].send_keys("senha-123")
    ins[2].clear()
    ins[2].send_keys("123")
    ins[3].clear()
    ins[3].send_keys("123")
    xp(d, "//button[contains(., 'Criar acesso')]").click()
    time.sleep(1.2)
    vm = ins[2].get_attribute("validationMessage")
    b = banner_text(d)
    rec("VAL-UI-05", "Cadastro de aluno", "senha com 3 caracteres", "recusada (mínimo de 6 caracteres) com mensagem", f"navegador: {vm!r}; tela: {b!r}", bool(vm) or bool(b))
    shot(d, "v05_cadastro_senha_curta", "Validação — senha curta no cadastro")
    # nome curto: o navegador não valida, quem recusa é o servidor — a mensagem precisa ser compreensível
    ins[2].clear()
    ins[2].send_keys("senha-123")
    ins[3].clear()
    ins[3].send_keys("senha-123")
    ins[0].clear()
    ins[0].send_keys("Al")
    xp(d, "//button[contains(., 'Criar acesso')]").click()
    time.sleep(1.5)
    b = banner_text(d)
    rec("VAL-UI-05b", "Cadastro de aluno", "nome com 2 letras (validação do servidor)", "mensagem compreensível citando o campo Nome", b, "Nome" in b and "caracteres" in b)
    shot(d, "v05b_cadastro_nome_curto", "Validação — nome curto: o servidor recusa e a tela explica o motivo")
    # ---------------------------------------------------------------- recuperar senha
    goto(d, "/esqueci-senha")
    d.find_elements(By.CSS_SELECTOR, "input")[0].send_keys("lucas.carvalho@aluno.local")
    xp(d, "//button[@type='submit']").click()
    time.sleep(1.8)
    ins = d.find_elements(By.CSS_SELECTOR, "input")
    ins[0].send_keys("000000")
    ins[1].send_keys("nova-senha-123")
    ins[2].send_keys("nova-senha-123")
    xp(d, "//button[@type='submit']").click()
    time.sleep(1.5)
    b = banner_text(d) or toast_text(d, 1)
    rec("VAL-UI-06", "Esqueci minha senha", "código de verificação errado", "\"Código inválido ou expirado\"", b, "inválido" in b)
    shot(d, "v06_codigo_invalido", "Validação — código de recuperação inválido")
    # ---------------------------------------------------------------- nova atividade
    login_ui(d, "marina.ferreira@pluseduc.local", expect_path="/dashboard")
    goto(d, "/nova-atividade", 2)
    xp(d, "//button[contains(., 'Salvar Atividade')]").click()
    t = toast_text(d)
    rec("VAL-UI-07", "Nova atividade", "salvar com tudo em branco", "aviso pedindo título, matéria, tópico e turma", t, "Preencha" in t)
    shot(d, "v07_atividade_vazia", "Validação — nova atividade com campos em branco")
    d.find_element(By.CSS_SELECTOR, 'input[placeholder^="Ex: Lista"]').send_keys("Lista de teste de validação")
    Select(d.find_elements(By.CSS_SELECTOR, "select")[2]).select_by_visible_text("Matemática")
    time.sleep(0.4)
    d.find_element(By.CSS_SELECTOR, 'input[placeholder="Digite o tópico da atividade"]').send_keys("Frações")
    xp(d, "//button[contains(., 'Salvar Atividade')]").click()
    t = toast_text(d)
    rec("VAL-UI-08", "Nova atividade", "salvar sem enunciado e sem opções", "aviso pedindo enunciado, opções e resposta correta", t, "Preencha" in t or "enunciado" in t.lower() or "opç" in t.lower())
    shot(d, "v08_atividade_sem_enunciado", "Validação — nova atividade sem enunciado/opções da questão")
    # ---------------------------------------------------------------- notas
    lucas = db.students.find_one({"email": "lucas.carvalho@aluno.local"})
    goto(d, f"/notas?turma={lucas['class_id']}", 2.5)
    xp(d, "//button[contains(., 'Lançar nota')]").click()
    time.sleep(1)
    dlg = wait(d, "[role=dialog]")
    dlg.find_element(By.XPATH, ".//button[normalize-space()='Lançar']").click()
    t = toast_text(d) or banner_text(d)
    rec("VAL-UI-09", "Lançar nota", "lançar sem escolher o aluno", "aviso pedindo o aluno", t, bool(t))
    shot(d, "v09_nota_sem_aluno", "Validação — lançamento de nota sem aluno")
    Select(dlg.find_elements(By.CSS_SELECTOR, "select")[0]).select_by_visible_text("Lucas Mendes Carvalho")
    nota = [i for i in dlg.find_elements(By.CSS_SELECTOR, "input") if i.get_attribute("type") in ("number", "text")][0]
    nota.send_keys("11")
    dlg.find_element(By.XPATH, ".//button[normalize-space()='Lançar']").click()
    t = toast_text(d) or banner_text(d)
    rec("VAL-UI-10", "Lançar nota", "nota 11", "\"A nota deve ser um número entre 0 e 10.\"", t, "entre 0 e 10" in t)
    shot(d, "v10_nota_11", "Validação — nota fora da faixa 0 a 10")
    nota.clear()
    nota.send_keys("abc")
    dlg.find_element(By.XPATH, ".//button[normalize-space()='Lançar']").click()
    t = toast_text(d) or banner_text(d)
    rec("VAL-UI-11", "Lançar nota", "nota com texto (abc)", "aviso de nota inválida", t, bool(t))
    # ---------------------------------------------------------------- aluno envia sem responder
    tok = api.post("/api/auth/login", json={"email": "marina.ferreira@pluseduc.local", "password": PW}).json()["accessToken"]
    body = {"title": "Atividade validacao UI Sprint 9", "subject": "Matemática", "topic": "Adição", "difficultyLevel": "FACIL", "questionsCount": 1, "format": "MULTIPLA_ESCOLHA",
            "classroomId": lucas["class_id"], "questions": [{"questionText": "Quanto é 2 + 2?", "questionType": "MULTIPLA_ESCOLHA", "options": ["A) 3", "B) 4", "C) 5", "D) 6"], "correctAnswer": "B"}]}
    act_id = api.post("/api/activities", headers={"Authorization": f"Bearer {tok}"}, json=body).json()["id"]
    login_ui(d, "lucas.carvalho@aluno.local", expect_path="/aluno")
    goto(d, f"/aluno/atividades/{act_id}", 2.5)
    xp(d, "//button[contains(., 'Enviar')]").click()
    t = toast_text(d)
    rec("VAL-UI-12", "Atividade do aluno", "enviar sem marcar nenhuma resposta", "\"Preencha todas as questões antes de enviar.\"", t, "Preencha todas" in t)
    shot(d, "v12_aluno_sem_resposta", "Validação — aluno tenta enviar a atividade sem responder")
    api.delete(f"/api/activities/{act_id}", headers={"Authorization": f"Bearer {tok}"})
    # ---------------------------------------------------------------- aluno: dados duplicados na tela de turmas
    login_ui(d, "marina.ferreira@pluseduc.local", expect_path="/dashboard")
    goto(d, "/turmas", 2.5)
    xp(d, "//button[contains(., 'Adicionar Aluno')]").click()
    time.sleep(1.2)
    name = d.find_element(By.CSS_SELECTOR, 'input[placeholder="Digite o nome completo"]')
    mail = d.find_element(By.CSS_SELECTOR, 'input[placeholder="Digite o email"]')
    name.send_keys("Aluno Duplicado Teste")
    mail.send_keys("lucas.carvalho@aluno.local")
    form_btns = [b for b in d.find_elements(By.CSS_SELECTOR, "button") if b.is_displayed() and b.get_attribute("type") == "submit"]
    form_btns[-1].click()
    t = toast_text(d)
    rec("VAL-UI-13", "Adicionar aluno", "e-mail que já pertence a outro aluno", "aviso de e-mail já cadastrado", t, "cadastrado" in t.lower())
    shot(d, "v13_aluno_email_duplicado", "Validação — cadastro de aluno com e-mail já usado")
    set_value(d, mail, "email-invalido")
    form_btns[-1].click()
    time.sleep(0.8)
    vm = mail.get_attribute("validationMessage")
    t = toast_text(d, 1)
    rec("VAL-UI-14", "Adicionar aluno", "e-mail em formato inválido", "recusado antes do envio ou com aviso", f"navegador: {vm!r}; aviso: {t!r}", bool(vm) or bool(t))
finally:
    json.dump(RESULTS, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(evid.MANIFEST, open(os.path.join(evid.OUT, "manifest_s9_val.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    d.quit()
print("RESUMO:", sum(r["ok"] for r in RESULTS), "aprovados de", len(RESULTS))
