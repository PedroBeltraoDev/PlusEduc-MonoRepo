import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evid import *

d = make_driver()
try:
    login_ui(d, 'lucas.carvalho@aluno.local', expect_path='/aluno')
    goto(d, '/aluno/atividades', settle=2.5)
    shot(d, 'b06_aluno_atividades', 'Fluxo 4 — Aluno (Lucas) vê a atividade nova em "Pendentes"', full=True)
    xp(d, "//*[contains(text(), 'Tabuada (Sprint 8)')]").click()
    time.sleep(2)
    shot(d, 'b07_aluno_atividade_aberta', 'Fluxo 4 — Atividade aberta pelo aluno: questões sem gabarito', full=True)
    d.execute_script(r"""
      const el=[...document.querySelectorAll('label,button,div')].filter(e=>/^B\)\s*56$/.test(e.innerText.trim().replace(/\s+/g,' ')))[0];
      (el.querySelector('input')||el).click();""")
    time.sleep(0.5)
    shot(d, 'b08_aluno_respondendo', 'Fluxo 4 — Aluno marca a alternativa B')
    xp(d, "//button[contains(., 'Enviar')]").click()
    time.sleep(2.5)
    shot(d, 'b09_aluno_resultado', 'Fluxo 4 — Envio e correção automática (acerto e resposta correta)', full=True)

    login_ui(d, 'marina.ferreira@pluseduc.local', expect_path='/dashboard')
    goto(d, '/atividades', settle=2.5)
    xp(d, "//*[contains(text(), 'Tabuada (Sprint 8)')]").click()
    time.sleep(2.5)
    shot(d, 'b10_prof_atividade_participacao', 'Fluxo 5 — Professora acompanha a participação e as respostas da turma', full=True)
    xp(d, "//button[contains(., 'Lançar notas no boletim')]").click()
    time.sleep(2.5)
    shot(d, 'b11_prof_lancar_boletim', 'Fluxo 5 — "Lançar notas no boletim": nota criada a partir da atividade')
    goto(d, '/notas', settle=2.5)
    shot(d, 'b12_notas_pagina', 'Fluxo 5 — Notas e Frequência: escolha da turma')
finally:
    json.dump(MANIFEST, open(os.path.join(OUT, 'manifest_b2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    d.quit()
