import os

PW = os.environ["PLUSEDUC_EVAL_PASSWORD"]  # senha das contas de teste do banco descartável (defina no ambiente)
import sys, datetime
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3] / 'PlusEduc-BE-Python'))
from pymongo import MongoClient
from app.core.passwords import hash_password
db=MongoClient('mongodb://localhost:27017')['pluseduc_sprint8_eval']
h=hash_password(PW)
def setpw(email):
    db.users.update_one({'email':email},{'$set':{'password':h,'active':True}})
    db.teachers.update_one({'email':email},{'$set':{'password':h}})
    db.students.update_one({'email':email},{'$set':{'password':h}})
for e in ['marina.ferreira@pluseduc.local','lucas.carvalho@aluno.local']: setpw(e)
lucas=db.students.find_one({'email':'lucas.carvalho@aluno.local'})
# second student: has user, different class
other=None
for s in db.students.find({'active':{'$ne':False},'class_id':{'$ne':lucas['class_id']}}):
    u=db.users.find_one({'email':s.get('email'),'role':'STUDENT'})
    if u and s.get('class_id'): other=s; break
setpw(other['email'])
# second teacher
t2=None
for t in db.teachers.find({'email':{'$ne':'marina.ferreira@pluseduc.local'},'active':{'$ne':False}}):
    if db.users.find_one({'email':t['email'],'role':'TEACHER'}): t2=t; break
setpw(t2['email'])
# admin (does not exist in seed)
db.users.delete_many({'email':'admin.avaliacao@pluseduc.local'})
db.users.insert_one({'email':'admin.avaliacao@pluseduc.local','password':h,'role':'ADMIN','active':True,'name':'Administrador de Avaliacao','createdAt':datetime.datetime.utcnow()})
print('Marina: marina.ferreira@pluseduc.local')
print('Lucas :', lucas['email'], lucas['name'], lucas['class_id'])
print('Other student:', other['email'], other['name'], other['class_id'], str(other['_id']))
print('Teacher2:', t2['email'], t2['name'])
print('Admin: admin.avaliacao@pluseduc.local')
print('classroom Lucas', db.classrooms.find_one({'_id':__import__('bson').ObjectId(lucas['class_id'])})['name'])
print('classroom other', db.classrooms.find_one({'_id':__import__('bson').ObjectId(other['class_id'])})['name'])
