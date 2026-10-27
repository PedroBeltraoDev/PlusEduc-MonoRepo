import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evid import *
from selenium.webdriver.support.ui import Select

d = make_driver()
try:
    login_ui(d, 'marina.ferreira@pluseduc.local', expect_path='/dashboard')
    goto(d, '/dashboard', settle=3)
    shot(d, 'b01_dashboard', 'Fluxo 1 — Dashboard do professor com indicadores reais', full=True)
    goto(d, '/turmas', settle=2.5)
    shot(d, 'b02_turmas', 'Fluxo 2 — Lista de turmas')
    # abre a turma 7º Ano D
    xp(d, "//*[contains(text(), '7º Ano do Ensino Fundamental D')]").click()
    time.sleep(2.5)
    shot(d, 'b03_turma_detalhe', 'Fluxo 2 — Detalhe da turma (alunos, matérias e atividades)', full=True)
    # nova atividade
    goto(d, '/nova-atividade', settle=2)
    wait(d, 'input[placeholder^="Ex: Lista"]').send_keys('Lista de Exercícios — Tabuada (Sprint 8)')
    selects = d.find_elements(By.CSS_SELECTOR, 'select')
    Select(selects[0]).select_by_visible_text('7º Ano do Ensino Fundamental D')
    Select(selects[2]).select_by_visible_text('Matemática')
    time.sleep(0.5)
    wait(d, 'input[placeholder="Digite o tópico da atividade"]').send_keys('Multiplicação')
    d.find_element(By.CSS_SELECTOR, 'textarea[placeholder="Digite o enunciado da questão"]').send_keys('Quanto é 7 x 8?')
    for letter, text in zip('ABCD', ['54', '56', '63', '49']):
        d.find_element(By.CSS_SELECTOR, f'input[placeholder="Opção {letter}"]').send_keys(text)
    # marca B como correta (o segundo botão de opção)
    radios = d.find_elements(By.CSS_SELECTOR, 'button[title="Definir como correta"]')
    print('radios', len(radios))
    radios[1].click()
    time.sleep(0.5)
    shot(d, 'b04_nova_atividade_preenchida', 'Fluxo 3 — Professora cria atividade manual (formulário preenchido)', full=True)
    xp(d, "//button[contains(., 'Salvar Atividade')]").click()
    time.sleep(2.5)
    shot(d, 'b05_atividade_criada', 'Fluxo 3 — Atividade salva (aviso de sucesso e item na lista)')
finally:
    json.dump(MANIFEST, open(os.path.join(OUT, 'manifest_b1.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    d.quit()
