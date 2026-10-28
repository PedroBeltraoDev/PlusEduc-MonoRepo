import json, os, sys, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evid import *
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

CLASS = '6ac2ebfb54fb67ac5e764134'
SET_VALUE = """
const el=arguments[0], v=arguments[1];
const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
setter.call(el,v); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true}));
"""

d = make_driver()
try:
    login_ui(d, 'marina.ferreira@pluseduc.local', expect_path='/dashboard')
    goto(d, f'/notas?turma={CLASS}', settle=3)
    shot(d, 'b12_notas_turma', 'Fluxo 6 — Notas e Frequência da turma 7º Ano D (nota vinda da atividade já no boletim)', full=True)
    # lançar nota manual com data futura (a interface limita a data; forçamos o valor para provar a regra do servidor)
    xp(d, "//button[contains(., 'Lançar nota')]").click()
    time.sleep(1)
    dlg = wait(d, '[role=dialog]')
    selects = dlg.find_elements(By.CSS_SELECTOR, 'select')
    Select(selects[0]).select_by_visible_text('Lucas Mendes Carvalho')
    Select(selects[1]).select_by_visible_text('Matemática')
    inputs = dlg.find_elements(By.CSS_SELECTOR, 'input')
    nota = [i for i in inputs if i.get_attribute('type') in ('number', 'text')][0]
    nota.send_keys('8.5')
    date_in = dlg.find_element(By.CSS_SELECTOR, 'input[type=date]')
    print('max do campo data:', date_in.get_attribute('max'))
    future = (datetime.date.today() + datetime.timedelta(days=45)).isoformat()
    d.execute_script(SET_VALUE, date_in, future)
    time.sleep(0.4)
    dlg.find_element(By.XPATH, ".//button[normalize-space()='Lançar']").click()
    time.sleep(1.5)
    shot(d, 'b13_nota_data_futura', 'Regra de negócio — nota com data no futuro é recusada pelo servidor (mensagem ao usuário)')
    d.execute_script(SET_VALUE, date_in, datetime.date.today().isoformat())
    time.sleep(0.4)
    dlg.find_element(By.XPATH, ".//button[normalize-space()='Lançar']").click()
    time.sleep(2)
    shot(d, 'b14_nota_lancada', 'Fluxo 6 — Nota manual lançada (data de hoje): média e frequência recalculadas', full=True)
    # exportação
    xp(d, "//button[normalize-space()='Excel']").click()
    time.sleep(2)
    shot(d, 'b15_exportar_boletim', 'Fluxo 6 — Exportação do boletim em Excel')
    # relatórios
    goto(d, '/relatorios', settle=3.5)
    shot(d, 'b16_relatorios', 'Fluxo 7 — Relatórios (boletim por turma com filtros e exportação)', full=True)
    # pesquisa global
    goto(d, '/dashboard', settle=2)
    box = [e for e in d.find_elements(By.CSS_SELECTOR, 'input[placeholder^="Pesquisar alunos"]') if e.is_displayed()][0]
    box.send_keys('tabuada')
    time.sleep(1.5)
    shot(d, 'b17_pesquisa_global', 'Fluxo 7 — Pesquisa global (resultado agrupado por tipo)')
    box.send_keys(Keys.ENTER)
    time.sleep(2)
    shot(d, 'b18_pagina_busca', 'Fluxo 7 — Página de resultados da pesquisa')
    # histórico do professor
    goto(d, '/historico', settle=3)
    shot(d, 'b19_historico_prof', 'Fluxo 7 — Histórico de operações: lançamento de nota, envio e recusas registradas', full=True)

    # aluno vê as notas
    login_ui(d, 'lucas.carvalho@aluno.local', expect_path='/aluno')
    goto(d, '/aluno/notas', settle=3)
    shot(d, 'b20_aluno_notas', 'Fluxo 8 — Aluno vê as próprias notas (inclui a nota da atividade online)', full=True)
    goto(d, '/aluno/desempenho', settle=3)
    shot(d, 'b21_aluno_desempenho', 'Fluxo 8 — Desempenho do aluno por disciplina', full=True)

    # recuperação de senha (sem modo demonstração)
    clear_session(d)
    goto(d, '/esqueci-senha', settle=2)
    d.find_elements(By.CSS_SELECTOR, 'input')[0].send_keys('lucas.carvalho@aluno.local')
    xp(d, "//button[@type='submit']").click()
    time.sleep(2)
    shot(d, 'b22_recuperar_senha', 'Recuperação de senha: a resposta é genérica e NENHUM código aparece na tela (modo demonstração desligado)')
finally:
    json.dump(MANIFEST, open(os.path.join(OUT, 'manifest_b3.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    d.quit()
