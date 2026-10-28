"""Reproduz (ou confirma a correção de) o envio de respostas a atividade de outra turma."""
import os

PW = os.environ["PLUSEDUC_EVAL_PASSWORD"]  # senha das contas de teste do banco descartável (defina no ambiente)
import json, sys
import httpx
from pymongo import MongoClient

BASE, DBN = sys.argv[1], sys.argv[2]
db = MongoClient('mongodb://localhost:27017')[DBN]
c = httpx.Client(base_url=BASE, timeout=60)
t = c.post('/api/auth/login', json={'email': 'lucas.carvalho@aluno.local', 'password': PW}).json()['accessToken']
H = {'Authorization': 'Bearer ' + t}
lucas = db.students.find_one({'email': 'lucas.carvalho@aluno.local'})
other = next(s for s in db.students.find({'active': {'$ne': False}, 'class_id': {'$exists': True, '$nin': [None, lucas['class_id']]}})
         if db.users.find_one({'email': s.get('email'), 'role': 'STUDENT'}))
act = db.activities.find_one({'classroom_id': other['class_id']})
questions = json.loads(act['content']) if isinstance(act['content'], str) else act['content']
if isinstance(questions, dict):
    questions = questions.get('questions', [])
payload = {'answers': [{'questionIndex': i, 'selectedAnswer': 'A'} for i in range(len(questions))]}
before = db.activity_submissions.count_documents({'activity_id': str(act['_id']), 'student_id': str(lucas['_id'])})
r = c.post(f'/api/student-portal/activities/{act["_id"]}/submissions', headers=H, json=payload)
after = db.activity_submissions.count_documents({'activity_id': str(act['_id']), 'student_id': str(lucas['_id'])})
print('atividade da OUTRA turma:', act['_id'], '| título:', act.get('title'))
print('HTTP', r.status_code, r.text[:300])
print('submissões de Lucas nessa atividade: antes', before, 'depois', after)
print('resposta traz gabarito (correctAnswer)?', 'correctAnswer' in r.text and '"correctAnswer":null' not in r.text)
if len(sys.argv) > 3 and sys.argv[3] == 'cleanup':
    db.activity_submissions.delete_many({'activity_id': str(act['_id']), 'student_id': str(lucas['_id'])})
    print('limpeza feita')
