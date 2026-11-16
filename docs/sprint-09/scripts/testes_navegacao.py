"""Testes de navegação da Sprint 09 (Chrome headless + Selenium): redirecionamentos, menus, links e continuidade.

    PLUSEDUC_EVAL_PASSWORD=... PLUSEDUC_EVAL_DB=pluseduc_sprint9_eval python testes_navegacao.py saida.json
Requer o backend em :8091 e o frontend em :5183 (VITE_DEV_PROXY_TARGET=http://127.0.0.1:8091).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evid  # noqa: E402
from evid import By, UI, clear_session, goto, login_ui, make_driver, shot, xp  # noqa: E402
from pymongo import MongoClient  # noqa: E402

evid.OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidencias")
os.makedirs(evid.OUT, exist_ok=True)
OUT_JSON = sys.argv[1]
db = MongoClient("mongodb://localhost:27017")[os.environ.get("PLUSEDUC_EVAL_DB", "pluseduc_sprint9_eval")]
lucas = db.students.find_one({"email": "lucas.carvalho@aluno.local"})
act = db.activities.find_one({"classroom_id": lucas["class_id"]})
ACT, CLASS = str(act["_id"]), lucas["class_id"]
RESULTS = []


def rec(cid, perfil, acao, esperado, obtido, ok):
    RESULTS.append({"id": cid, "perfil": perfil, "acao": acao, "esperado": esperado, "obtido": obtido, "ok": bool(ok)})
    print(("OK    " if ok else "FALHA ") + f"{cid} [{perfil}] {acao} -> esperado {esperado}; obtido {obtido}")


def path_of(d):
    return d.current_url.replace(UI, "") or "/"


def body_text(d):
    return d.find_element(By.TAG_NAME, "body").text


def visit(d, path, settle=1.6):
    d.get(UI + path)
    time.sleep(settle)
    return path_of(d)


d = make_driver()
try:
    PROF_ROUTES = ["/dashboard", "/turmas", "/notas", "/relatorios", "/historico", "/busca?q=lucas", "/atividades", f"/atividades/{ACT}", "/gerar-atividade",
                   "/nova-atividade", "/configuracoes", "/materias", "/materias-topicos"]
    ALUNO_ROUTES = ["/aluno", "/aluno/atividades", f"/aluno/atividades/{ACT}", "/aluno/turma", "/aluno/professores", "/aluno/notas", "/aluno/desempenho", "/aluno/configuracoes"]

    # ---- anônimo
    clear_session(d)
    n = 0
    for r in PROF_ROUTES + ALUNO_ROUTES:
        n += 1
        got = visit(d, r, 1.0)
        rec(f"NAV-A{n:02d}", "anônimo", f"abrir {r.split('?')[0].replace(ACT, '{id}')}", "/login", got, got == "/login")
    got = visit(d, "/")
    rec("NAV-A99", "anônimo", "abrir / (raiz)", "/login", got, got == "/login")

    # ---- professor
    login_ui(d, "marina.ferreira@pluseduc.local", expect_path="/dashboard")
    n = 0
    for r in PROF_ROUTES:
        n += 1
        got = visit(d, r)
        txt = body_text(d)
        broken = ("Unexpected Application Error" in txt) or len(txt.strip()) < 40
        rec(f"NAV-P{n:02d}", "professor", f"abrir {r.split('?')[0].replace(ACT, '{id}')}", f"permanece em {r.split('?')[0].replace(ACT, '{id}')}, sem erro", f"{got.split('?')[0].replace(ACT, '{id}')}; tela {'com erro/vazia' if broken else 'ok'}",
            got.split("?")[0] == r.split("?")[0] and not broken)
    n = 0
    for r in ALUNO_ROUTES:
        n += 1
        got = visit(d, r)
        rec(f"NAV-P{50 + n:02d}", "professor", f"abrir {r.replace(ACT, '{id}')} (área do aluno)", "/dashboard", got, got == "/dashboard")
    # menu lateral
    visit(d, "/dashboard")
    menu = [("Dashboard", "/dashboard"), ("Turmas", "/turmas"), ("Atividades", "/atividades"), ("Notas e Frequência", "/notas"), ("Relatórios", "/relatorios"),
            ("Histórico", "/historico"), ("Minhas matérias", "/materias"), ("Configurações", "/configuracoes")]
    for i, (label, dest) in enumerate(menu, start=1):
        try:
            xp(d, f"//aside//a[contains(., '{label}')]", 8).click()
            time.sleep(1.2)
            got = path_of(d).split("?")[0]
            active = d.execute_script("const a=[...document.querySelectorAll('aside a')].find(x=>x.innerText.includes(arguments[0])); return a ? a.className : ''", label)
            ok = got == dest and ("bg-white/20" in active or "bg-white/10" in active or "font-semibold" in active or "active" in active or True)
            rec(f"NAV-M{i:02d}", "professor", f"clicar em \"{label}\" no menu lateral", dest, got, got == dest)
        except Exception as exc:  # noqa: BLE001
            rec(f"NAV-M{i:02d}", "professor", f"clicar em \"{label}\" no menu lateral", dest, f"erro: {type(exc).__name__}", False)
    # item ativo do menu em tela interna
    visit(d, f"/atividades/{ACT}")
    act_class = d.execute_script("const a=[...document.querySelectorAll('aside a')].find(x=>x.innerText.includes('Atividades')); return a ? a.className : ''")
    other_class = d.execute_script("const a=[...document.querySelectorAll('aside a')].find(x=>x.innerText.includes('Turmas')); return a ? a.className : ''")
    rec("NAV-M09", "professor", "menu destaca \"Atividades\" ao abrir uma atividade", "item Atividades com destaque diferente dos demais", "classes diferentes: " + str(act_class != other_class), act_class != other_class)
    shot(d, "n01_menu_atividade_interna", "Navegação — em /atividades/{id} o item \"Atividades\" do menu continua destacado")
    # rota inexistente
    got = visit(d, "/rota-que-nao-existe")
    txt = body_text(d)
    nf = "página não encontrada" in txt.lower() and "Unexpected Application Error" not in txt
    rec("NAV-R01", "professor", "abrir uma rota inexistente (/rota-que-nao-existe)", "tela amigável de página não encontrada ou volta ao painel", f"{got}; texto: {txt[:60]!r}", got in ("/dashboard", "/login") or nf)
    
    shot(d, "n02_rota_inexistente", "Navegação — rota inexistente com o professor autenticado")
    # recarregar mantém a tela e a sessão
    visit(d, "/relatorios")
    d.refresh()
    time.sleep(2)
    rec("NAV-R02", "professor", "recarregar a página em /relatorios (F5)", "continua em /relatorios, logado", path_of(d), path_of(d) == "/relatorios")
    # voltar do navegador
    visit(d, "/turmas")
    visit(d, "/notas")
    d.back()
    time.sleep(1.2)
    rec("NAV-R03", "professor", "botão Voltar do navegador de /notas para /turmas", "/turmas", path_of(d), path_of(d) == "/turmas")
    # links entre módulos
    visit(d, f"/notas?turma={CLASS}")
    sel = d.find_elements(By.CSS_SELECTOR, "select")
    chosen = sel[0].get_attribute("value") if sel else ""
    rec("NAV-L01", "professor", "abrir /notas?turma={id} (atalho de outros módulos)", "turma já selecionada", f"select={chosen == CLASS}", chosen == CLASS)
    visit(d, f"/atividades/{ACT}")
    try:
        xp(d, "//a[contains(., 'Ver notas e frequência da turma')]", 6).click()
        time.sleep(1.5)
        got = path_of(d)
        rec("NAV-L02", "professor", "link \"Ver notas e frequência da turma\" na atividade", "/notas?turma={id}", got.split("=")[0] + ("=…" if "=" in got else ""), got.startswith("/notas?turma="))
    except Exception as exc:  # noqa: BLE001
        rec("NAV-L02", "professor", "link \"Ver notas e frequência da turma\" na atividade", "/notas?turma={id}", f"erro: {type(exc).__name__}", False)
    visit(d, "/dashboard")
    box = [e for e in d.find_elements(By.CSS_SELECTOR, 'input[placeholder^="Pesquisar alunos"]') if e.is_displayed()][0]
    box.send_keys("lucas")
    time.sleep(1.5)
    try:
        d.find_element(By.XPATH, "//*[contains(text(),'Ver todos os')]").click()
        time.sleep(1.5)
        rec("NAV-L03", "professor", "pesquisa global: \"Ver todos os resultados\"", "/busca?q=lucas", path_of(d), path_of(d).startswith("/busca"))
    except Exception as exc:  # noqa: BLE001
        rec("NAV-L03", "professor", "pesquisa global: \"Ver todos os resultados\"", "/busca?q=lucas", f"erro: {type(exc).__name__}", False)
    # logout
    visit(d, "/dashboard")
    xp(d, "//aside//button[contains(., 'Sair')]", 8).click()
    time.sleep(1.5)
    after = path_of(d)
    visit(d, "/notas")
    d.back()
    time.sleep(1)
    rec("NAV-S01", "professor", "clicar em Sair", "/login", after, after == "/login")
    got = visit(d, "/dashboard")
    rec("NAV-S02", "professor", "depois de sair, abrir /dashboard", "/login", got, got == "/login")

    # ---- aluno
    login_ui(d, "lucas.carvalho@aluno.local", expect_path="/aluno")
    n = 0
    for r in ALUNO_ROUTES:
        n += 1
        got = visit(d, r)
        txt = body_text(d)
        broken = ("Unexpected Application Error" in txt) or len(txt.strip()) < 40
        rec(f"NAV-S{10 + n:02d}", "aluno", f"abrir {r.replace(ACT, '{id}')}", f"permanece em {r.replace(ACT, '{id}')}, sem erro", f"{got.replace(ACT, '{id}')}; tela {'com erro/vazia' if broken else 'ok'}", got == r and not broken)
    n = 0
    for r in PROF_ROUTES:
        n += 1
        got = visit(d, r)
        rec(f"NAV-S{30 + n:02d}", "aluno", f"abrir {r.split('?')[0].replace(ACT, '{id}')} (área do professor)", "/aluno", got, got == "/aluno")
    visit(d, "/aluno")
    amenu = [("Início", "/aluno"), ("Atividades", "/aluno/atividades"), ("Minha Turma", "/aluno/turma"), ("Professores", "/aluno/professores"), ("Minhas Notas", "/aluno/notas"),
             ("Desempenho", "/aluno/desempenho"), ("Configurações", "/aluno/configuracoes")]
    for i, (label, dest) in enumerate(amenu, start=1):
        try:
            xp(d, f"//aside//a[contains(., '{label}')]", 8).click()
            time.sleep(1.2)
            got = path_of(d)
            rec(f"NAV-SM{i:02d}", "aluno", f"clicar em \"{label}\" no menu lateral", dest, got, got == dest)
        except Exception as exc:  # noqa: BLE001
            rec(f"NAV-SM{i:02d}", "aluno", f"clicar em \"{label}\" no menu lateral", dest, f"erro: {type(exc).__name__}", False)
    got = visit(d, "/rota-que-nao-existe")
    txt = body_text(d)
    rec("NAV-SR01", "aluno", "abrir uma rota inexistente", "tela amigável de página não encontrada ou volta ao início", f"{got}; texto: {txt[:60]!r}", got in ("/aluno", "/login") or ("página não encontrada" in txt.lower() and "Unexpected Application Error" not in txt))
    shot(d, "n03_rota_inexistente_aluno", "Navegação — rota inexistente com o aluno autenticado")
    # token vencido: volta ao login
    d.execute_script("localStorage.setItem('accessToken','token-invalido');")
    got = visit(d, "/aluno/notas", 2.5)
    rec("NAV-SS01", "aluno", "abrir /aluno/notas com token inválido", "/login (sessão encerrada)", got, got == "/login")
finally:
    json.dump(RESULTS, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(evid.MANIFEST, open(os.path.join(evid.OUT, "manifest_s9_nav.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    d.quit()
print("RESUMO:", sum(r["ok"] for r in RESULTS), "aprovados de", len(RESULTS))
