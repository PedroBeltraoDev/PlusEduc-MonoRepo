"""Verificações direcionadas de permissão e isolamento de dados (executadas contra a API em execução)."""
import os

PW = os.environ["PLUSEDUC_EVAL_PASSWORD"]  # senha das contas de teste do banco descartável (defina no ambiente)
import json, sys, re, time, datetime
import httpx, jwt as pyjwt
from pymongo import MongoClient

BASE, DBN, OUT, ROUTES = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
db = MongoClient('mongodb://localhost:27017')[DBN]
c = httpx.Client(base_url=BASE, timeout=60)


def login(email, pw=PW):
    return c.post('/api/auth/login', json={'email': email, 'password': pw})


def tok(email):
    return login(email).json()['accessToken']


def H(t):
    return {'Authorization': f'Bearer {t}'}


T = {'ALUNO': tok('lucas.carvalho@aluno.local'), 'PROF': tok('marina.ferreira@pluseduc.local'), 'ADMIN': tok('admin.avaliacao@pluseduc.local')}
raw = {'PROF': login('marina.ferreira@pluseduc.local').json()}
lucas = db.students.find_one({'email': 'lucas.carvalho@aluno.local'})
sid = str(lucas['_id'])
cid = lucas['class_id']
other = next(s for s in db.students.find({'active': {'$ne': False}, 'class_id': {'$exists': True, '$nin': [None, lucas['class_id']]}})
         if db.users.find_one({'email': s.get('email'), 'role': 'STUDENT'}))
oid = str(other['_id'])
ocid = other['class_id']
oact = db.activities.find_one({'classroom_id': ocid})
lact = db.activities.find_one({'classroom_id': cid})
results = []


def rec(group, name, expect, resp, note=''):
    st = resp.status_code if hasattr(resp, 'status_code') else resp
    ok = (st in expect) if isinstance(expect, (list, tuple, set)) else st == expect
    results.append({'grupo': group, 'verificacao': name, 'esperado': expect, 'obtido': st, 'ok': ok, 'nota': note})
    print('OK   ' if ok else 'FALHA', f'[{group}]', name, '-> esperado', expect, 'obtido', st, note)


g = 'A. Isolamento entre alunos'
rec(g, 'Aluno consulta o próprio desempenho', 200, c.get(f'/api/students/{sid}/performance', headers=H(T['ALUNO'])))
rec(g, 'Aluno consulta a própria frequência', 200, c.get(f'/api/students/{sid}/attendance', headers=H(T['ALUNO'])))
rec(g, 'Aluno consulta desempenho de OUTRO aluno', 403, c.get(f'/api/students/{oid}/performance', headers=H(T['ALUNO'])))
rec(g, 'Aluno consulta frequência de OUTRO aluno', 403, c.get(f'/api/students/{oid}/attendance', headers=H(T['ALUNO'])))
rec(g, 'Aluno consulta recomendação pedagógica de OUTRO aluno', 403, c.get(f'/api/students/{oid}/pedagogical-recommendation', headers=H(T['ALUNO'])))
rec(g, 'Aluno lê dados cadastrais de OUTRO aluno (GET /api/students/{id})', 403, c.get(f'/api/students/{oid}', headers=H(T['ALUNO'])))
rec(g, 'Aluno lê as notas de OUTRO aluno (GET /api/grades/student/{id})', 403, c.get(f'/api/grades/student/{oid}', headers=H(T['ALUNO'])))
rec(g, 'Aluno abre atividade de OUTRA turma pelo portal', 404, c.get(f'/api/student-portal/activities/{oact["_id"]}', headers=H(T['ALUNO'])))
import json as _j
_q = _j.loads(oact['content']) if isinstance(oact['content'], str) else oact['content']
_q = _q.get('questions', []) if isinstance(_q, dict) else _q
_pl = {'answers': [{'questionIndex': i, 'selectedAnswer': 'A'} for i in range(len(_q))]}
_r = c.post(f'/api/student-portal/activities/{oact["_id"]}/submissions', headers=H(T['ALUNO']), json=_pl)
_n = db.activity_submissions.count_documents({'activity_id': str(oact['_id']), 'student_id': sid})
rec(g, 'Aluno envia respostas completas a atividade de OUTRA turma (não pode gravar)', 404, _r, f'submissões gravadas no banco: {_n}')
db.activity_submissions.delete_many({'activity_id': str(oact['_id']), 'student_id': sid})
r = c.get('/api/student-portal/activities', headers=H(T['ALUNO']))
j = r.json()
items = j if isinstance(j, list) else (j.get('items') or j.get('activities') or [])
ids = [str(a.get('id')) for a in items]
rec(g, 'Lista do portal não contém atividade de outra turma', 200 if str(oact['_id']) not in ids else -1, r, f'{len(ids)} atividades listadas')

g = 'B. Validade do token'
rec(g, 'Sem token', 401, c.get('/api/students'))
rec(g, 'Token aleatório ("abc")', 401, c.get('/api/students', headers=H('abc')))
now = datetime.datetime.now(datetime.timezone.utc)
secret_wrong = pyjwt.encode({'sub': 'marina.ferreira@pluseduc.local', 'exp': now + datetime.timedelta(hours=1)}, 'segredo-errado-com-32-bytes-ou-mais-xx', algorithm='HS256')
rec(g, 'Token assinado com outro segredo (forjado)', 401, c.get('/api/students', headers=H(secret_wrong)))
none_tok = pyjwt.encode({'sub': 'marina.ferreira@pluseduc.local'}, key=None, algorithm='none')
rec(g, 'Token com algoritmo "none"', 401, c.get('/api/students', headers=H(none_tok)))
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3] / 'PlusEduc-BE-Python'))
from app.core.config import get_settings
s = get_settings()
expired = pyjwt.encode({'sub': 'marina.ferreira@pluseduc.local', 'iat': now - datetime.timedelta(hours=9), 'exp': now - datetime.timedelta(hours=1)}, s.jwt_secret, algorithm='HS256')
rec(g, 'Token vencido', 401, c.get('/api/students', headers=H(expired)))
escalated = pyjwt.encode({'sub': 'lucas.carvalho@aluno.local', 'role': 'ADMIN', 'iat': now, 'exp': now + datetime.timedelta(hours=1), 'type': 'access'}, s.jwt_secret, algorithm='HS256')
rec(g, 'Token do aluno com claim role=ADMIN adulterada (o papel vem do banco, não do token)', 403, c.get('/api/students', headers=H(escalated)))
rec(g, 'Refresh token usado como token de acesso', 401, c.get('/api/students', headers=H(raw['PROF']['refreshToken'])), 'o refresh de 7 dias não deve abrir a API')
db.users.update_one({'email': 'lucas.carvalho@aluno.local'}, {'$set': {'active': False}})
rec(g, 'Token de usuário desativado depois do login', 401, c.get('/api/student-portal/me', headers=H(T['ALUNO'])))
rec(g, 'Login de usuário desativado', 401, login('lucas.carvalho@aluno.local'))
db.users.update_one({'email': 'lucas.carvalho@aluno.local'}, {'$set': {'active': True}})

g = 'C. Login'
r1 = login('marina.ferreira@pluseduc.local', 'senha-errada')
r2 = login('nao.existe@x.com', 'senha-errada')
rec(g, 'Senha errada', 401, r1)
rec(g, 'E-mail inexistente (não revela se a conta existe)', 401, r2, 'mensagens iguais' if r1.json()['message'] == r2.json()['message'] else 'MENSAGENS DIFERENTES')

g = 'D. Cadastro público'
em = f'avaliacao.aluno.{int(time.time())}@aluno.local'
r = c.post('/api/auth/register/student', json={'name': 'Aluno Avaliacao Sprint8', 'email': em, 'password': PW, 'role': 'ADMIN'})
rec(g, 'Cadastro de aluno com campo extra role=ADMIN é recusado (o papel não pode ser escolhido pelo cliente)', 422, r)
r = c.post('/api/auth/register/student', json={'name': 'Aluno Avaliacao Sprint8', 'email': em, 'password': PW})
rec(g, 'Cadastro público de aluno gera o papel STUDENT', 200, r, 'papel: ' + str(r.json().get('role')))
em2 = f'avaliacao.prof.{int(time.time())}@professor.local'
r = c.post('/api/auth/register/teacher', json={'name': 'Professor Avaliacao Sprint8', 'email': em2, 'password': PW})
t2 = r.json().get('accessToken')
r_students = c.get('/api/students', headers=H(t2)) if t2 else None
obt = f'cadastro={r.status_code}; GET /api/students={r_students.status_code if r_students is not None else None}'
results.append({'grupo': g, 'verificacao': 'Cadastro público de professor dá acesso imediato aos dados de todos os alunos (sem aprovação)', 'esperado': 'RF04: ativação por aprovação', 'obtido': obt, 'ok': False, 'nota': 'LACUNA registrada'})
print('INFO [D]', obt)

g = 'E. Escopo do professor'
r_t2 = c.get(f'/api/grades/classroom/{cid}', headers=H(t2)) if t2 else None
results.append({'grupo': g, 'verificacao': 'Professor recém-cadastrado, sem turmas, lê as notas da turma de outra professora', 'esperado': 'restrito à própria turma', 'obtido': r_t2.status_code, 'ok': r_t2.status_code == 403, 'nota': 'LIMITAÇÃO registrada (sem restrição por turma)'})
print('INFO [E] professor sem turma lendo notas de uma turma ->', r_t2.status_code)

g = 'F. Segredos nas respostas'
routes = json.load(open(ROUTES))
leaks = []
scanned = 0
real = {'classroom_id': cid, 'class_id': cid, 'student_id': sid, 'teacher_id': str(db.teachers.find_one({'email': 'marina.ferreira@pluseduc.local'})['_id']), 'activity_id': str(lact['_id']), 'grade_id': str(db.grades.find_one({'studentId': sid})['_id']), 'subject_id': str(db.subjects.find_one({})['_id']), 'item_id': '000000000000000000000000', 'year': '2026', 'subject': 'Matematica', 'email': 'marina.ferreira@pluseduc.local', 'report_type': 'boletim', 'submission_id': '000000000000000000000000', 'question_index': '0'}
for rt in routes:
    if rt['method'] != 'GET' or rt['path'] == '/health' or 'export' in rt['path']:
        continue
    p = re.sub(r'\{(\w+)\}', lambda m: real.get(m.group(1), 'x'), rt['path'])
    for who in ('PROF', 'ALUNO'):
        resp = c.get(p + ('?q=lucas' if rt['path'] == '/api/search' else ''), headers=H(T[who]))
        if resp.status_code == 200:
            scanned += 1
            txt = resp.text
            if re.search(r'\$2[aby]\$', txt) or '"password"' in txt.lower() or 'passwordresetcodehash' in txt.lower():
                leaks.append((who, p))
results.append({'grupo': g, 'verificacao': f'{scanned} respostas GET com 200 varridas à procura de hash de senha / código de recuperação', 'esperado': 0, 'obtido': len(leaks), 'ok': len(leaks) == 0, 'nota': str(leaks[:5])})
print('[F]', scanned, 'respostas varridas; vazamentos:', leaks)
fmt = lact.get('format') or 'MULTIPLA_ESCOLHA'
cr = c.post('/api/activities', headers=H(T['PROF']), json={'title': 'Atividade de verificacao de gabarito', 'subject': 'Matematica', 'topic': 'Verificacao', 'difficultyLevel': 'MEDIO', 'questionsCount': 1, 'format': fmt, 'classroomId': cid, 'questions': [{'questionText': 'Quanto e 1+1?', 'questionType': 'MULTIPLA_ESCOLHA', 'options': ['A) 1', 'B) 2', 'C) 3', 'D) 4'], 'correctAnswer': 'B'}]})
new_id = cr.json().get('id')
r = c.get(f'/api/student-portal/activities/{new_id}', headers=H(T['ALUNO']))
leak = 'correctanswer' in r.text.lower() or '"b) 2"' in r.text.lower().replace('b) 2', '"b) 2"') and False
leak = 'correctanswer' in r.text.lower()
results.append({'grupo': g, 'verificacao': 'Portal do aluno não devolve o gabarito (correctAnswer) de atividade ainda não enviada', 'esperado': 'ausente', 'obtido': 'presente' if leak else 'ausente', 'ok': (not leak), 'nota': f'criação={cr.status_code}; portal={r.status_code}'})
print('[F] gabarito vazado ao aluno?', leak, cr.status_code, r.status_code)
if new_id:
    c.delete(f'/api/activities/{new_id}', headers=H(T['PROF']))

g = 'G. CORS'
r = c.options('/api/students', headers={'Origin': 'http://site-malicioso.example', 'Access-Control-Request-Method': 'GET'})
acao = r.headers.get('access-control-allow-origin')
results.append({'grupo': g, 'verificacao': 'Origem não autorizada não recebe Access-Control-Allow-Origin', 'esperado': 'ausente', 'obtido': acao or 'ausente', 'ok': acao is None, 'nota': f'status {r.status_code}'})
r = c.options('/api/students', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET'})
acao = r.headers.get('access-control-allow-origin')
results.append({'grupo': g, 'verificacao': 'Origem do frontend (http://localhost:5173) autorizada', 'esperado': 'http://localhost:5173', 'obtido': acao or 'ausente', 'ok': acao == 'http://localhost:5173', 'nota': ''})

g = 'H. Histórico de operações'
ra = c.get('/api/audit-logs?size=100', headers=H(T['ADMIN']))
rp = c.get('/api/audit-logs?size=100', headers=H(T['PROF']))
rs = c.get('/api/audit-logs', headers=H(T['ALUNO']))


def total(r):
    j = r.json()
    return j.get('totalElements', j.get('total', len(j.get('items', j.get('content', []))))) if isinstance(j, dict) else len(j)


results.append({'grupo': g, 'verificacao': 'Administrador vê operações de todos; professor só as próprias; aluno 403', 'esperado': 'admin >= professor; aluno 403', 'obtido': f'admin={total(ra)} professor={total(rp)} aluno={rs.status_code}', 'ok': rs.status_code == 403, 'nota': ''})
print('[H]', results[-1]['obtido'])
g = 'I. Recuperação de senha'
rf = c.post('/api/auth/forgot-password', json={'email': 'lucas.carvalho@aluno.local'})
rf2 = c.post('/api/auth/forgot-password', json={'email': 'nao.existe@x.com'})
code = rf.json().get('demoCode')
rec(g, 'Solicitação de recuperação não devolve o código na resposta', 200, rf, 'demoCode na resposta: ' + str(code))
results[-1]['ok'] = code is None
results.append({'grupo': g, 'verificacao': 'Resposta não revela se o e-mail existe (conta real x inexistente)', 'esperado': 'respostas iguais', 'obtido': 'iguais' if rf.json() == rf2.json() else 'DIFERENTES', 'ok': rf.json() == rf2.json(), 'nota': 'com demoCode apenas para contas existentes'})
tomada = False
if code:
    rr = c.post('/api/auth/reset-password', json={'email': 'lucas.carvalho@aluno.local', 'code': code, 'newPassword': PW + '-nova'})
    tomada = rr.status_code == 200 and login('lucas.carvalho@aluno.local', PW + '-nova').status_code == 200
results.append({'grupo': g, 'verificacao': 'Quem só conhece o e-mail NÃO consegue trocar a senha de outra conta', 'esperado': 'impossível', 'obtido': 'conta tomada (senha trocada sem posse do e-mail)' if tomada else 'impossível', 'ok': not tomada, 'nota': ''})
print('[I] código na resposta:', code, '| tomada de conta:', tomada)
json.dump(results, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('RESUMO:', sum(1 for r in results if r['ok']), 'ok /', len(results))
db.users.delete_many({'email': {'$in': [em, em2]}})
db.students.delete_many({'email': em})
db.teachers.delete_many({'email': em2})
