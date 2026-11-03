"""Capturas de responsividade (celular, 390x844) e modo escuro — RNF10. Requer backend :8091 e frontend :5183."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evid  # noqa: E402
from evid import By, clear_session, goto, login_ui, make_driver, shot, xp  # noqa: E402

evid.OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidencias")
RES = []
d = make_driver(390, 844)
try:
    clear_session(d)
    goto(d, "/login")
    overflow = d.execute_script("return document.documentElement.scrollWidth > window.innerWidth + 2")
    RES.append({"tela": "login", "largura": 390, "rolagem_horizontal": bool(overflow)})
    shot(d, "r01_celular_login", "Celular (390 px) — tela de login")
    login_ui(d, "marina.ferreira@pluseduc.local", expect_path="/dashboard")
    goto(d, "/dashboard", 3)
    overflow = d.execute_script("return document.documentElement.scrollWidth > window.innerWidth + 2")
    RES.append({"tela": "dashboard do professor", "largura": 390, "rolagem_horizontal": bool(overflow)})
    shot(d, "r02_celular_dashboard", "Celular (390 px) — dashboard do professor, menu recolhido")
    xp(d, "//button[@aria-label='Abrir menu']", 8).click()
    time.sleep(1)
    shot(d, "r03_celular_menu", "Celular (390 px) — menu lateral aberto pelo botão")
    d.refresh()
    for path, name, label in (("/notas", "r04_celular_notas", "notas e frequência"), ("/relatorios", "r05_celular_relatorios", "relatórios")):
        goto(d, path, 3)
        overflow = d.execute_script("return document.documentElement.scrollWidth > window.innerWidth + 2")
        RES.append({"tela": label, "largura": 390, "rolagem_horizontal": bool(overflow)})
        shot(d, name, f"Celular (390 px) — {label}")
    login_ui(d, "lucas.carvalho@aluno.local", expect_path="/aluno")
    goto(d, "/aluno/notas", 3)
    overflow = d.execute_script("return document.documentElement.scrollWidth > window.innerWidth + 2")
    RES.append({"tela": "notas do aluno", "largura": 390, "rolagem_horizontal": bool(overflow)})
    shot(d, "r06_celular_aluno_notas", "Celular (390 px) — Minhas Notas (aluno)")
    d.set_window_size(1366, 860)
    login_ui(d, "marina.ferreira@pluseduc.local", expect_path="/dashboard")
    goto(d, "/dashboard", 3)
    d.execute_script("document.documentElement.classList.add('dark')")
    time.sleep(0.8)
    shot(d, "r07_modo_escuro", "Modo escuro — dashboard do professor (classe dark do Tailwind ativada)")
finally:
    json.dump(RES, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resultados", "responsividade.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(evid.MANIFEST, open(os.path.join(evid.OUT, "manifest_s9_resp.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    d.quit()
print(RES)
