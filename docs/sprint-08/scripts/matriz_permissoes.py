"""Matriz de permissões: chama cada rota da API como anônimo, ALUNO, PROFESSOR e ADMIN."""
import os

PW = os.environ["PLUSEDUC_EVAL_PASSWORD"]  # senha das contas de teste do banco descartável (defina no ambiente)
import json, sys, re
import httpx as requests
from pymongo import MongoClient
BASE=sys.argv[1]; DBN=sys.argv[2]; OUT=sys.argv[3]; ROUTES=sys.argv[4]
db=MongoClient('mongodb://localhost:27017')[DBN]
def login(email):
    r=requests.post(f'{BASE}/api/auth/login',json={'email':email,'password':PW}); r.raise_for_status(); return r.json()['accessToken']
tokens={'ANÔNIMO':None,
 'ALUNO':login('lucas.carvalho@aluno.local'),
 'PROFESSOR':login('marina.ferreira@pluseduc.local'),
 'ADMIN':login('admin.avaliacao@pluseduc.local')}
lucas=db.students.find_one({'email':'lucas.carvalho@aluno.local'})
sid=str(lucas['_id']); cid=lucas['class_id']
act=db.activities.find_one({'classroom_id':cid}) or db.activities.find_one({})
grade=db.grades.find_one({'studentId':sid}) or db.grades.find_one({})
sub=db.activity_submissions.find_one({})
subj=db.subjects.find_one({}); topic=db.subject_topics.find_one({}); teacher=db.teachers.find_one({'email':'marina.ferreira@pluseduc.local'})
FAKE='000000000000000000000000'
real={'classroom_id':cid,'class_id':cid,'student_id':sid,'teacher_id':str(teacher['_id']),'activity_id':str(act['_id']),
 'grade_id':str(grade['_id']),'subject_id':str(subj['_id']),'item_id':str(topic['_id']) if topic else FAKE,'year':'2026',
 'subject':'Matematica','email':'marina.ferreira@pluseduc.local','report_type':'boletim','submission_id':str(sub['_id']) if sub else FAKE,'question_index':'0'}
routes=json.load(open(ROUTES))
SKIP={('POST','/api/auth/forgot-password'),('POST','/api/auth/reset-password'),('POST','/api/auth/login')}
rows=[]
for r in routes:
    path=r['path']; m=r['method']
    use_real = (m=='GET')
    p=re.sub(r'\{(\w+)\}',lambda mo:(real if use_real else {k:FAKE for k in real} | {'year':'2026','subject':'Matematica','email':'x@x.x','report_type':'boletim','question_index':'0'}).get(mo.group(1),FAKE),path)
    q='?q=lucas' if path=='/api/search' else ''
    res={}
    for prof,tok in tokens.items():
        if (m,path) in SKIP: res[prof]=None; continue
        h={'Authorization':f'Bearer {tok}'} if tok else {}
        kw={'headers':h,'timeout':60}
        if m in('POST','PUT','PATCH'): kw['json']={}
        resp=requests.request(m,BASE+p+q,**kw)
        res[prof]=resp.status_code
    rows.append({**r,'url':p,'results':res})
json.dump(rows,open(OUT,'w'),indent=1,ensure_ascii=False)
bad=[]
for x in rows:
    print(f"{x['method']:6} {x['path']:62} "+' '.join(f"{k[:3]}={v}" for k,v in x['results'].items()))
