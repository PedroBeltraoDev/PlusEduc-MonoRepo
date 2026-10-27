import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evid import *

d = make_driver()
try:
    # A1 tela de login
    clear_session(d)
    goto(d, '/login')
    shot(d, 'a01_login', 'Tela de login (acesso público)')
    # A2 senha errada
    inputs = d.find_elements(By.CSS_SELECTOR, 'input')
    inputs[0].send_keys('marina.ferreira@pluseduc.local')
    inputs[1].send_keys('senha-incorreta')
    xp(d, "//button[contains(., 'Entrar')]").click()
    time.sleep(1.5)
    shot(d, 'a02_login_senha_errada', 'Senha incorreta: mensagem em português, sem revelar se a conta existe')
    # A3 anônimo tenta abrir área protegida
    clear_session(d)
    goto(d, '/dashboard')
    shot(d, 'a03_anonimo_dashboard', 'Sem login: /dashboard redireciona para /login')
    goto(d, '/aluno')
    shot(d, 'a03b_anonimo_aluno', 'Sem login: /aluno redireciona para /login')
    # A4 aluno
    login_ui(d, 'lucas.carvalho@aluno.local', expect_path='/aluno')
    shot(d, 'a04_aluno_home', 'ALUNO (Lucas) autenticado: área do aluno')
    goto(d, '/dashboard')
    shot(d, 'a05_aluno_tenta_dashboard', 'ALUNO acessa /dashboard (área do professor): é devolvido para /aluno')
    goto(d, '/relatorios')
    shot(d, 'a06_aluno_tenta_relatorios', 'ALUNO acessa /relatorios: é devolvido para /aluno')
    goto(d, '/historico')
    shot(d, 'a06b_aluno_tenta_historico', 'ALUNO acessa /historico: é devolvido para /aluno')
    # A7 professor
    login_ui(d, 'marina.ferreira@pluseduc.local', expect_path='/dashboard')
    shot(d, 'a07_professor_dashboard', 'PROFESSORA (Marina) autenticada: painel do educador')
    goto(d, '/aluno')
    shot(d, 'a08_professor_tenta_aluno', 'PROFESSORA acessa /aluno (portal do aluno): é devolvida para /dashboard')
    # A9 sessão inválida (token adulterado)
    d.execute_script("localStorage.setItem('accessToken','token.invalido.qualquer');")
    goto(d, '/turmas', settle=3)
    shot(d, 'a09_sessao_expirada', 'Token inválido/vencido: a sessão é encerrada e o usuário volta ao login com aviso')
    # A10 admin
    login_ui(d, 'admin.avaliacao@pluseduc.local', expect_path='/dashboard')
    shot(d, 'a10_admin_dashboard', 'ADMIN (conta de avaliação) autenticado: mesmo painel do educador')
    goto(d, '/historico', settle=3)
    shot(d, 'a11_admin_historico', 'ADMIN no Histórico: vê as operações de todos os usuários (texto no topo)')
    # A12 professor histórico com acessos negados
    login_ui(d, 'marina.ferreira@pluseduc.local', expect_path='/dashboard')
    goto(d, '/historico', settle=3)
    shot(d, 'a12_professor_historico', 'PROFESSORA no Histórico: vê apenas as próprias operações')
finally:
    json.dump(MANIFEST, open(os.path.join(OUT, 'manifest_a.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    d.quit()
