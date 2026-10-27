"""Sondas de regras de negócio (executadas contra a API em execução, banco descartável)."""
import os

PW = os.environ["PLUSEDUC_EVAL_PASSWORD"]  # senha das contas de teste do banco descartável (defina no ambiente)
import json, sys, datetime
import httpx
from pymongo import MongoClient
from bson import ObjectId

BASE, DBN = sys.argv[1], sys.argv[2]
db = MongoClient('mongodb://localhost:27017')[DBN]
c = httpx.Client(base_url=BASE, timeout=60)
t = c.post('/api/auth/login', json={'email': 'marina.ferreira@pluseduc.local', 'password': PW}).json()['accessToken']
H = {'Authorization': 'Bearer ' + t}
lucas = db.students.find_one({'email': 'lucas.carvalho@aluno.local'})
henrique = next(s for s in db.students.find({'active': {'$ne': False}, 'class_id': {'$exists': True, '$nin': [None, lucas['class_id']]}})
         if db.users.find_one({'email': s.get('email'), 'role': 'STUDENT'}))
cid_l, cid_h = lucas['class_id'], henrique['class_id']
today = datetime.datetime.now(datetime.timezone.utc)
out = []


def show(name, r, extra=''):
    print(f'{name}: HTTP {r.status_code} {extra} {r.text[:160]}')
    out.append((name, r.status_code))


# P1: nota para aluno que não pertence à turma informada
r = c.post('/api/grades', headers=H, json={'studentId': str(henrique['_id']), 'classroomId': cid_l, 'grade': 7.0, 'subject': 'Matematica', 'date': today.isoformat()})
show('P1 nota com aluno de outra turma', r)
if r.status_code in (200, 201):
    c.delete(f'/api/grades/{r.json()["id"]}', headers=H)
# P5: nota com data futura
r = c.post('/api/grades', headers=H, json={'studentId': str(lucas['_id']), 'classroomId': cid_l, 'grade': 7.0, 'subject': 'Matematica', 'date': '2030-01-01T00:00:00Z'})
show('P5 nota com data em 2030', r)
if r.status_code in (200, 201):
    c.delete(f'/api/grades/{r.json()["id"]}', headers=H)
# P2: matricular em outra turma sem sair da anterior
before_old = [str(x) for x in db.classrooms.find_one({'_id': ObjectId(cid_h)}).get('students', [])]
r = c.post(f'/api/classrooms/{cid_l}/enroll/{henrique["_id"]}', headers=H)
show('P2 matrícula em 2ª turma sem desmatricular da 1ª', r)
old_after = [str(x) for x in db.classrooms.find_one({'_id': ObjectId(cid_h)}).get('students', [])]
new_after = [str(x) for x in db.classrooms.find_one({'_id': ObjectId(cid_l)}).get('students', [])]
print('   aluno continua na turma antiga?', str(henrique['_id']) in old_after, '| está na nova?', str(henrique['_id']) in new_after, '| class_id do aluno =', db.students.find_one({'_id': henrique['_id']}).get('class_id') == cid_l)
# restaura
db.classrooms.update_one({'_id': ObjectId(cid_l)}, {'$set': {'students': [str(lucas['_id'])]}})
db.classrooms.update_one({'_id': ObjectId(cid_h)}, {'$set': {'students': before_old}})
db.students.update_one({'_id': henrique['_id']}, {'$set': {'class_id': cid_h}})
# P3: excluir aluno matriculado: continua na lista da turma?
mail = f'aluno.temp.{int(datetime.datetime.now().timestamp())}@aluno.local'
r = c.post('/api/students', headers=H, json={'name': 'Aluno Temporario Sprint8', 'email': mail, 'birthDate': '2012-03-04', 'classId': cid_l, 'learningGaps': []})
show('P3a criar aluno temporário na turma do Lucas', r)
sid = r.json().get('id')
cl = db.classrooms.find_one({'_id': ObjectId(cid_l)})
print('   turma lista o aluno temporário?', sid in [str(x) for x in cl.get('students', [])])
r = c.delete(f'/api/students/{sid}', headers=H)
show('P3b excluir aluno', r)
cl = db.classrooms.find_one({'_id': ObjectId(cid_l)})
print('   após excluir, a turma ainda lista o aluno?', sid in [str(x) for x in cl.get('students', [])])
rc = c.get(f'/api/classrooms/{cid_l}', headers=H)
print('   GET turma -> students:', [s.get('name') if isinstance(s, dict) else s for s in rc.json().get('students', rc.json().get('studentIds', []))][:5])
# P4: data de nascimento futura
r = c.post('/api/students', headers=H, json={'name': 'Aluno Futuro Sprint8', 'email': 'futuro.sprint8@aluno.local', 'birthDate': '2031-03-04', 'classId': cid_l, 'learningGaps': []})
show('P4 aluno com nascimento em 2031', r)
if r.status_code == 201:
    db.students.delete_one({'_id': ObjectId(r.json()['id'])})
# P6: ano letivo absurdo
r = c.post('/api/classrooms', headers=H, json={'name': 'Turma Sprint8 Ano 1900', 'year': 1900, 'gradeLevel': '7º Ano do Ensino Fundamental', 'teacherId': str(db.teachers.find_one({'email': 'marina.ferreira@pluseduc.local'})['_id']), 'studentIds': []})
show('P6 turma com ano 1900', r)
if r.status_code == 201:
    c.delete(f'/api/classrooms/{r.json()["id"]}', headers=H)
# limpa o aluno temporário
db.students.delete_many({'email': mail})
db.users.delete_many({'email': mail})
db.classrooms.update_one({'_id': ObjectId(cid_l)}, {'$set': {'students': [str(lucas['_id'])]}})
