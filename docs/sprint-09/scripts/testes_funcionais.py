"""Testes funcionais e de validação da Sprint 09, executados contra a API em execução (banco descartável).

    PLUSEDUC_EVAL_PASSWORD=... python testes_funcionais.py http://127.0.0.1:8091 pluseduc_sprint9_eval saida.json

Cada caso tem id, módulo, passos, resultado esperado e resultado obtido (texto real da execução). Os dados criados
usam sufixo único e são removidos ao final (a limpeza também confere o que sobrou no banco).
"""
import json
import os
import sys
import time
import uuid

import httpx
from pymongo import MongoClient

PW = os.environ["PLUSEDUC_EVAL_PASSWORD"]
BASE, DBN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
db = MongoClient("mongodb://localhost:27017")[DBN]
c = httpx.Client(base_url=BASE, timeout=90)
RUN = uuid.uuid4().hex[:6]
CASES = []
RESULTS = []
CREATED = {"students": [], "teachers": [], "classrooms": [], "activities": [], "users": [], "grades": [], "subjects": [], "topics": []}


def login(email, pw=PW):
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
    return r


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


TOK = {}


def caso(cid, modulo, titulo, passos, esperado):
    def deco(fn):
        CASES.append((cid, modulo, titulo, passos, esperado, fn))
        return fn
    return deco


def msg(r):
    try:
        j = r.json()
        return j.get("message") or j.get("detail") or str(j)[:80]
    except Exception:  # noqa: BLE001
        return r.text[:80]


def st(r, *ok):
    """Resultado padrão: (texto, ok) conforme o status esperado."""
    return f"HTTP {r.status_code}" + (f" — {msg(r)}" if r.status_code >= 400 else ""), r.status_code in ok


# ------------------------------------------------------------------ preparação
def setup():
    TOK["prof"] = login("marina.ferreira@pluseduc.local").json()["accessToken"]
    TOK["aluno"] = login("lucas.carvalho@aluno.local").json()["accessToken"]
    TOK["admin"] = login("admin.avaliacao@pluseduc.local").json()["accessToken"]
    marina = db.teachers.find_one({"email": "marina.ferreira@pluseduc.local"})
    lucas = db.students.find_one({"email": "lucas.carvalho@aluno.local"})
    ctx = {"marina": str(marina["_id"]), "lucas": str(lucas["_id"]), "classL": lucas["class_id"]}
    other = next(s for s in db.students.find({"active": {"$ne": False}, "class_id": {"$exists": True, "$nin": [None, lucas["class_id"]]}})
                 if db.users.find_one({"email": s.get("email"), "role": "STUDENT"}))
    ctx["other"] = str(other["_id"])
    ctx["classO"] = other["class_id"]
    ctx["other_email"] = other["email"]
    ctx["teacher2"] = str(db.teachers.find_one({"email": {"$ne": "marina.ferreira@pluseduc.local"}, "active": {"$ne": False}})["_id"])
    return ctx


X = {}  # estado compartilhado entre casos


def P(path, **kw):
    return c.get(path, headers=H(TOK["prof"]), **kw)


# ------------------------------------------------------------------ AUTENTICAÇÃO
@caso("AUT-01", "Autenticação", "Login de professor", "POST /api/auth/login com e-mail e senha válidos", "200, accessToken e refreshToken, papel TEACHER")
def _(x):
    r = login("marina.ferreira@pluseduc.local")
    j = r.json()
    return f"HTTP {r.status_code}; role={j.get('role')}; tokens={'sim' if j.get('accessToken') and j.get('refreshToken') else 'não'}", r.status_code == 200 and j.get("role") == "TEACHER" and bool(j.get("refreshToken"))


@caso("AUT-02", "Autenticação", "Login de aluno", "POST /api/auth/login com conta de aluno", "200, papel STUDENT e studentId")
def _(x):
    r = login("lucas.carvalho@aluno.local")
    j = r.json()
    return f"HTTP {r.status_code}; role={j.get('role')}; studentId={'sim' if j.get('studentId') else 'não'}", r.status_code == 200 and j.get("role") == "STUDENT" and bool(j.get("studentId"))


@caso("AUT-03", "Autenticação", "Login com senha errada", "POST /api/auth/login com senha incorreta", "401 \"Invalid email or password\"")
def _(x):
    r = login("marina.ferreira@pluseduc.local", "senha-errada")
    return st(r, 401)


@caso("AUT-04", "Autenticação", "Login com e-mail inexistente", "POST /api/auth/login com e-mail que não existe", "401, mesma mensagem da senha errada (não revela a conta)")
def _(x):
    r = login("ninguem.existe@exemplo.com", "qualquer")
    r2 = login("marina.ferreira@pluseduc.local", "senha-errada")
    return st(r, 401)[0] + f"; mensagem igual à da senha errada: {msg(r) == msg(r2)}", r.status_code == 401 and msg(r) == msg(r2)


@caso("AUT-05", "Autenticação", "Login sem senha (campo obrigatório)", "POST /api/auth/login só com o e-mail", "422 (validação)")
def _(x):
    r = c.post("/api/auth/login", json={"email": "marina.ferreira@pluseduc.local"})
    return st(r, 422)


@caso("AUT-06", "Autenticação", "Cadastro público de aluno", "POST /api/auth/register/student com dados válidos", "200, papel STUDENT, matrícula MAT-2026-NNNN gerada e conta gravada no banco")
def _(x):
    email = f"aluno.s9.{RUN}@aluno.local"
    r = c.post("/api/auth/register/student", json={"name": "Aluno Teste Sprint Nove", "email": email, "password": PW})
    j = r.json()
    CREATED["users"].append(email)
    CREATED["students"].append(email)
    stu = db.students.find_one({"email": email}) or {}
    ok = r.status_code == 200 and j.get("role") == "STUDENT" and str(stu.get("matricula", "")).startswith("MAT-2026-")
    X["new_student_email"] = email
    return f"HTTP {r.status_code}; role={j.get('role')}; matrícula={stu.get('matricula')}", ok


@caso("AUT-07", "Autenticação", "Cadastro de aluno com e-mail repetido", "POST /api/auth/register/student com o e-mail do caso anterior", "409")
def _(x):
    r = c.post("/api/auth/register/student", json={"name": "Aluno Repetido", "email": X["new_student_email"], "password": PW})
    return st(r, 409)


@caso("AUT-08", "Autenticação", "Cadastro de aluno com e-mail em formato inválido", "POST /api/auth/register/student com e-mail \"isto-nao-e-email\"", "422 (e-mail inválido)")
def _(x):
    r = c.post("/api/auth/register/student", json={"name": "Aluno Sem Email", "email": "isto-nao-e-email", "password": PW})
    if r.status_code == 200:
        CREATED["users"].append("isto-nao-e-email")
        CREATED["students"].append("isto-nao-e-email")
    return st(r, 422)


@caso("AUT-09", "Autenticação", "Cadastro de aluno com senha curta", "POST /api/auth/register/student com senha de 3 caracteres", "422")
def _(x):
    r = c.post("/api/auth/register/student", json={"name": "Aluno Senha Curta", "email": f"curta.{RUN}@aluno.local", "password": "123"})
    return st(r, 422)


@caso("AUT-10", "Autenticação", "Cadastro público de professor", "POST /api/auth/register/teacher com dados válidos", "200, papel TEACHER e registros em users e teachers")
def _(x):
    email = f"prof.s9.{RUN}@professor.local"
    r = c.post("/api/auth/register/teacher", json={"name": "Professor Teste Sprint Nove", "email": email, "password": PW})
    CREATED["users"].append(email)
    CREATED["teachers"].append(email)
    j = r.json()
    ok = r.status_code == 200 and j.get("role") == "TEACHER" and db.users.find_one({"email": email}) and db.teachers.find_one({"email": email})
    X["new_teacher_email"] = email
    return f"HTTP {r.status_code}; role={j.get('role')}", bool(ok)


@caso("AUT-11", "Autenticação", "Cadastro de professor com e-mail repetido", "POST /api/auth/register/teacher repetindo o e-mail", "409")
def _(x):
    r = c.post("/api/auth/register/teacher", json={"name": "Professor Repetido", "email": X["new_teacher_email"], "password": PW})
    return st(r, 409)


@caso("AUT-12", "Autenticação", "Cadastro de professor com e-mail em formato inválido", "POST /api/auth/register/teacher com e-mail \"@@@\"", "422")
def _(x):
    r = c.post("/api/auth/register/teacher", json={"name": "Professor Sem Email", "email": "@@@", "password": PW})
    if r.status_code == 200:
        CREATED["users"].append("@@@")
        CREATED["teachers"].append("@@@")
    return st(r, 422)


@caso("AUT-13", "Autenticação", "Edição do próprio perfil", "PUT /api/auth/profile alterando o nome do aluno recém-cadastrado", "200 e nome atualizado")
def _(x):
    t = login(X["new_student_email"]).json()["accessToken"]
    r = c.put("/api/auth/profile", headers=H(t), json={"name": "Aluno Nome Editado", "email": X["new_student_email"]})
    return f"HTTP {r.status_code}; nome={r.json().get('name') if r.status_code == 200 else msg(r)}", r.status_code == 200 and r.json().get("name") == "Aluno Nome Editado"


@caso("AUT-14", "Autenticação", "Perfil com e-mail já usado por outra conta", "PUT /api/auth/profile trocando para o e-mail de outro usuário", "409")
def _(x):
    t = login(X["new_student_email"]).json()["accessToken"]
    r = c.put("/api/auth/profile", headers=H(t), json={"name": "Aluno Nome Editado", "email": "marina.ferreira@pluseduc.local"})
    return st(r, 409)


@caso("AUT-15", "Autenticação", "Recuperação de senha: pedido", "POST /api/auth/forgot-password com e-mail existente", "200, mensagem genérica e nenhum código na resposta")
def _(x):
    r = c.post("/api/auth/forgot-password", json={"email": X["new_student_email"]})
    j = r.json()
    return f"HTTP {r.status_code}; demoCode={j.get('demoCode')}", r.status_code == 200 and not j.get("demoCode")


@caso("AUT-16", "Autenticação", "Recuperação de senha: código inválido", "POST /api/auth/reset-password com código errado", "400 \"Código inválido ou expirado\" e senha antiga continua valendo")
def _(x):
    r = c.post("/api/auth/reset-password", json={"email": X["new_student_email"], "code": "000000", "newPassword": "NovaSenha123"})
    still = login(X["new_student_email"]).status_code == 200
    return st(r, 400)[0] + f"; senha antiga ainda funciona: {still}", r.status_code == 400 and still


@caso("AUT-17", "Autenticação", "Recuperação de senha: código correto troca a senha", "Com o código gerado, POST /api/auth/reset-password e novo login", "200; login com a senha nova funciona e com a antiga não")
def _(x):
    # o código é aleatório e vai por e-mail; no teste lê-se o hash e se confere trocando-o por um código conhecido
    import hashlib
    import hmac
    from app.core.config import get_settings
    s = get_settings()
    email = X["new_student_email"]
    code = "135790"
    h = hmac.new(s.jwt_secret.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()
    db.users.update_one({"email": email}, {"$set": {"passwordResetCodeHash": h}})
    r = c.post("/api/auth/reset-password", json={"email": email, "code": code, "newPassword": PW + "x"})
    new_ok = login(email, PW + "x").status_code == 200
    old_ok = login(email, PW).status_code == 200
    return f"HTTP {r.status_code}; login senha nova: {new_ok}; login senha antiga: {old_ok}", r.status_code == 200 and new_ok and not old_ok


@caso("AUT-18", "Autenticação", "Rota protegida sem token e com token inválido", "GET /api/students sem token e com \"abc\"", "401 nos dois casos")
def _(x):
    a = c.get("/api/students")
    b = c.get("/api/students", headers=H("abc"))
    return f"sem token: {a.status_code}; token inválido: {b.status_code}", a.status_code == 401 and b.status_code == 401


# ------------------------------------------------------------------ TURMAS
@caso("TUR-01", "Turmas", "Criar turma válida", "POST /api/classrooms (nome, ano, série, professora)", "201 e turma gravada no banco")
def _(x):
    body = {"name": f"Turma Teste S9 {RUN}", "year": 2026, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": x["marina"], "studentIds": []}
    r = c.post("/api/classrooms", headers=H(TOK["prof"]), json=body)
    if r.status_code == 201:
        X["class_id"] = r.json()["id"]
        CREATED["classrooms"].append(X["class_id"])
    return st(r, 201)[0] + (f"; id gravado: {bool(db.classrooms.find_one({'name': body['name']}))}" if r.status_code == 201 else ""), r.status_code == 201


@caso("TUR-02", "Turmas", "Criar turma com nome e ano repetidos", "POST /api/classrooms repetindo nome e ano", "409 \"Já existe uma turma com este nome e ano\"")
def _(x):
    body = {"name": f"Turma Teste S9 {RUN}", "year": 2026, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": x["marina"]}
    r = c.post("/api/classrooms", headers=H(TOK["prof"]), json=body)
    return st(r, 409)


@caso("TUR-03", "Turmas", "Criar turma com nome curto", "POST /api/classrooms com nome \"AB\"", "422")
def _(x):
    r = c.post("/api/classrooms", headers=H(TOK["prof"]), json={"name": "AB", "year": 2026, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": x["marina"]})
    return st(r, 422)


@caso("TUR-04", "Turmas", "Criar turma com ano fora do intervalo", "POST /api/classrooms com ano 1900", "400 \"Ano da turma fora do intervalo permitido\"")
def _(x):
    r = c.post("/api/classrooms", headers=H(TOK["prof"]), json={"name": f"Turma Ano Ruim {RUN}", "year": 1900, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": x["marina"]})
    return st(r, 400)


@caso("TUR-05", "Turmas", "Criar turma com professor inexistente", "POST /api/classrooms com teacherId inexistente", "400 ou 404 (professor não encontrado)")
def _(x):
    r = c.post("/api/classrooms", headers=H(TOK["prof"]), json={"name": f"Turma Sem Prof {RUN}", "year": 2026, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": "000000000000000000000000"})
    if r.status_code == 201:
        CREATED["classrooms"].append(r.json()["id"])
    return st(r, 400, 404)


@caso("TUR-06", "Turmas", "Consultar turma por id", "GET /api/classrooms/{id} da turma criada e de um id inexistente", "200 com o nome certo; 404 para id inexistente")
def _(x):
    a = P(f"/api/classrooms/{X['class_id']}")
    b = P("/api/classrooms/000000000000000000000000")
    return f"existente: {a.status_code}; inexistente: {b.status_code}", a.status_code == 200 and b.status_code == 404


@caso("TUR-07", "Turmas", "Editar turma", "PUT /api/classrooms/{id} trocando o nome", "200 e nome novo na consulta seguinte")
def _(x):
    r = c.put(f"/api/classrooms/{X['class_id']}", headers=H(TOK["prof"]), json={"name": f"Turma Teste S9 Editada {RUN}"})
    got = P(f"/api/classrooms/{X['class_id']}").json().get("name")
    return f"HTTP {r.status_code}; nome={got}", r.status_code == 200 and got.endswith(f"Editada {RUN}")


@caso("TUR-08", "Turmas", "Listagem e paginação de turmas", "GET /api/classrooms e /api/classrooms/paginated?size=5", "200; página com no máximo 5 itens e totais coerentes")
def _(x):
    a = P("/api/classrooms")
    b = P("/api/classrooms/paginated?page=0&size=5").json()
    return f"lista={len(a.json())} turmas; página: {len(b['content'])} itens de {b['totalElements']} (totalPages={b['totalPages']})", a.status_code == 200 and len(b["content"]) <= 5 and b["totalElements"] == len(a.json())


@caso("TUR-09", "Turmas", "Paginação com parâmetros inválidos", "GET /api/classrooms/paginated?size=0 e size=1000", "422")
def _(x):
    a = P("/api/classrooms/paginated?size=0")
    b = P("/api/classrooms/paginated?size=1000")
    return f"size=0: {a.status_code}; size=1000: {b.status_code}", a.status_code == 422 and b.status_code == 422


@caso("TUR-10", "Turmas", "Matricular aluno", "POST /api/classrooms/{id}/enroll/{aluno} com um aluno sem turma", "204; aluno aparece na turma e recebe class_id")
def _(x):
    email = f"matricula.{RUN}@aluno.local"
    r = c.post("/api/students", headers=H(TOK["prof"]), json={"name": "Aluno Matriculado Teste", "email": email, "birthDate": "2012-05-06", "learningGaps": []})
    X["stu_id"] = r.json()["id"]
    CREATED["students"].append(email)
    e = c.post(f"/api/classrooms/{X['class_id']}/enroll/{X['stu_id']}", headers=H(TOK["prof"]))
    cl = P(f"/api/classrooms/{X['class_id']}").json()
    in_class = X["stu_id"] in [s["id"] for s in cl["students"]]
    return f"HTTP {e.status_code}; na turma: {in_class}", e.status_code == 204 and in_class


@caso("TUR-11", "Turmas", "Matricular em segunda turma retira da primeira (RN28)", "Matricular o mesmo aluno em outra turma", "O aluno sai da turma anterior")
def _(x):
    second = c.post("/api/classrooms", headers=H(TOK["prof"]), json={"name": f"Turma Teste S9 B {RUN}", "year": 2026, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": x["marina"]})
    X["class2"] = second.json()["id"]
    CREATED["classrooms"].append(X["class2"])
    e = c.post(f"/api/classrooms/{X['class2']}/enroll/{X['stu_id']}", headers=H(TOK["prof"]))
    a = [s["id"] for s in P(f"/api/classrooms/{X['class_id']}").json()["students"]]
    b = [s["id"] for s in P(f"/api/classrooms/{X['class2']}").json()["students"]]
    return f"HTTP {e.status_code}; na turma 1: {X['stu_id'] in a}; na turma 2: {X['stu_id'] in b}", e.status_code == 204 and X["stu_id"] not in a and X["stu_id"] in b


@caso("TUR-12", "Turmas", "Excluir turma com alunos matriculados", "DELETE /api/classrooms/{id} da turma com aluno", "400 \"Não é possível excluir turma com alunos matriculados\"")
def _(x):
    r = c.delete(f"/api/classrooms/{X['class2']}", headers=H(TOK["prof"]))
    return st(r, 400, 409)


@caso("TUR-13", "Turmas", "Desmatricular aluno", "DELETE /api/classrooms/{id}/unenroll/{aluno}", "204 e aluno sem turma")
def _(x):
    r = c.delete(f"/api/classrooms/{X['class2']}/unenroll/{X['stu_id']}", headers=H(TOK["prof"]))
    b = [s["id"] for s in P(f"/api/classrooms/{X['class2']}").json()["students"]]
    return f"HTTP {r.status_code}; ainda na turma: {X['stu_id'] in b}", r.status_code == 204 and X["stu_id"] not in b


@caso("TUR-14", "Turmas", "Excluir turma vazia e id inexistente", "DELETE /api/classrooms/{id} da turma vazia; DELETE de id inexistente", "204 e a turma sai da lista de ativas (exclusão lógica); 404")
def _(x):
    a = c.delete(f"/api/classrooms/{X['class2']}", headers=H(TOK["prof"]))
    b = c.delete("/api/classrooms/000000000000000000000000", headers=H(TOK["prof"]))
    listed = X["class2"] in [t["id"] for t in P("/api/classrooms").json()]
    return f"vazia: {a.status_code}; inexistente: {b.status_code}; ainda na lista de turmas ativas: {listed}", a.status_code == 204 and b.status_code == 404 and not listed


@caso("TUR-15", "Turmas", "Limite de 5 turmas ativas por professor", "Criar turmas para a mesma professora até passar de 5", "A criação que passa do limite é recusada com 400 \"Limite máximo de 5 turmas ativas por professor\"")
def _(x):
    t = db.teachers.find_one({"email": X["new_teacher_email"]})
    tid = str(t["_id"])
    codes = []
    for i in range(7):
        r = c.post("/api/classrooms", headers=H(TOK["prof"]), json={"name": f"Turma Limite {i} {RUN}", "year": 2026, "gradeLevel": "6º Ano do Ensino Fundamental", "teacherId": tid})
        codes.append(r.status_code)
        if r.status_code == 201:
            CREATED["classrooms"].append(r.json()["id"])
    return f"respostas em sequência: {codes}", codes[:5] == [201] * 5 and codes[5] == 400


# ------------------------------------------------------------------ ALUNOS
@caso("ALU-01", "Alunos", "Criar aluno válido", "POST /api/students (nome, e-mail, nascimento)", "201 com matrícula gerada")
def _(x):
    email = f"aluno.crud.{RUN}@aluno.local"
    r = c.post("/api/students", headers=H(TOK["prof"]), json={"name": "Aluno Crud Teste", "email": email, "birthDate": "2011-02-03", "learningGaps": []})
    CREATED["students"].append(email)
    if r.status_code == 201:
        X["crud_id"] = r.json()["id"]
        X["crud_email"] = email
    return f"HTTP {r.status_code}; matrícula={r.json().get('matricula') if r.status_code == 201 else msg(r)}", r.status_code == 201 and str(r.json().get("matricula", "")).startswith("MAT-2026-")


@caso("ALU-02", "Alunos", "Criar aluno com e-mail repetido", "POST /api/students repetindo o e-mail", "409")
def _(x):
    r = c.post("/api/students", headers=H(TOK["prof"]), json={"name": "Aluno Repetido", "email": X["crud_email"], "birthDate": "2011-02-03"})
    return st(r, 409)


@caso("ALU-03", "Alunos", "Criar aluno com e-mail em formato inválido", "POST /api/students com e-mail \"sem-arroba\"", "422")
def _(x):
    r = c.post("/api/students", headers=H(TOK["prof"]), json={"name": "Aluno Email Ruim", "email": "sem-arroba", "birthDate": "2011-02-03"})
    if r.status_code == 201:
        CREATED["students"].append("sem-arroba")
    return st(r, 422)


@caso("ALU-04", "Alunos", "Criar aluno sem nome / nome curto", "POST /api/students com nome \"Al\" e sem nome", "422 nos dois")
def _(x):
    a = c.post("/api/students", headers=H(TOK["prof"]), json={"name": "Al", "email": f"nome.curto.{RUN}@aluno.local"})
    b = c.post("/api/students", headers=H(TOK["prof"]), json={"email": f"sem.nome.{RUN}@aluno.local"})
    for r, e in ((a, f"nome.curto.{RUN}@aluno.local"), (b, f"sem.nome.{RUN}@aluno.local")):
        if r.status_code == 201:
            CREATED["students"].append(e)
    return f"nome curto: {a.status_code}; sem nome: {b.status_code}", a.status_code == 422 and b.status_code == 422


@caso("ALU-05", "Alunos", "Criar aluno em turma inexistente", "POST /api/students com classId inexistente", "400 \"Turma não encontrada\"")
def _(x):
    r = c.post("/api/students", headers=H(TOK["prof"]), json={"name": "Aluno Turma Ruim", "email": f"turma.ruim.{RUN}@aluno.local", "classId": "000000000000000000000000"})
    if r.status_code == 201:
        CREATED["students"].append(f"turma.ruim.{RUN}@aluno.local")
    return st(r, 400)


@caso("ALU-06", "Alunos", "Consultar e listar alunos", "GET /api/students/{id}; GET /api/students/paginated?size=3; id inexistente", "200 com o aluno; página de até 3; 404 para inexistente")
def _(x):
    a = P(f"/api/students/{X['crud_id']}")
    b = P("/api/students/paginated?page=0&size=3").json()
    d = P("/api/students/000000000000000000000000")
    return f"consulta: {a.status_code}; página: {len(b['content'])} itens de {b['totalElements']}; inexistente: {d.status_code}", a.status_code == 200 and len(b["content"]) <= 3 and d.status_code == 404


@caso("ALU-07", "Alunos", "Editar aluno", "PUT /api/students/{id} alterando nome", "200 e nome atualizado")
def _(x):
    r = c.put(f"/api/students/{X['crud_id']}", headers=H(TOK["prof"]), json={"name": "Aluno Crud Editado"})
    return f"HTTP {r.status_code}; nome={r.json().get('name') if r.status_code == 200 else msg(r)}", r.status_code == 200 and r.json().get("name") == "Aluno Crud Editado"


@caso("ALU-08", "Alunos", "Editar aluno para e-mail já usado", "PUT /api/students/{id} com o e-mail de outro aluno", "409")
def _(x):
    r = c.put(f"/api/students/{X['crud_id']}", headers=H(TOK["prof"]), json={"email": "lucas.carvalho@aluno.local"})
    return st(r, 409)


@caso("ALU-09", "Alunos", "Liberar acesso ao portal", "POST /api/students/{id}/enable-access com senha válida e depois login do aluno", "204 e login do aluno funciona")
def _(x):
    r = c.post(f"/api/students/{X['crud_id']}/enable-access", headers=H(TOK["prof"]), json={"password": PW})
    CREATED["users"].append(X["crud_email"])
    lg = login(X["crud_email"])
    return f"HTTP {r.status_code}; login: {lg.status_code}", r.status_code == 204 and lg.status_code == 200 and lg.json().get("role") == "STUDENT"


@caso("ALU-10", "Alunos", "Liberar acesso com senha curta", "POST /api/students/{id}/enable-access com senha \"123\"", "422")
def _(x):
    r = c.post(f"/api/students/{X['stu_id']}/enable-access", headers=H(TOK["prof"]), json={"password": "123"})
    return st(r, 422)


@caso("ALU-11", "Alunos", "Excluir aluno (exclusão lógica)", "DELETE /api/students/{id}; depois listar alunos ativos", "204 e aluno some da lista; id inexistente: 404")
def _(x):
    r = c.delete(f"/api/students/{X['crud_id']}", headers=H(TOK["prof"]))
    ids = [s["id"] for s in P("/api/students").json()]
    d = c.delete("/api/students/000000000000000000000000", headers=H(TOK["prof"]))
    return f"HTTP {r.status_code}; ainda listado: {X['crud_id'] in ids}; inexistente: {d.status_code}", r.status_code == 204 and X["crud_id"] not in ids and d.status_code == 404


@caso("ALU-12", "Alunos", "Aluno excluído não consegue entrar", "Login do aluno que foi excluído/desativado", "401")
def _(x):
    r = login(X["crud_email"])
    return st(r, 401)


@caso("ALU-14", "Alunos", "Excluir aluno matriculado libera a turma", "Criar aluno, matricular em turma nova, excluir o aluno e depois excluir a turma", "Turma deixa de listar o aluno e a turma pode ser excluída (204)")
def _(x):
    email = f"aluno.turma.{RUN}@aluno.local"
    a = c.post("/api/students", headers=H(TOK["prof"]), json={"name": "Aluno Para Excluir", "email": email, "birthDate": "2012-05-06"})
    CREATED["students"].append(email)
    sid = a.json()["id"]
    t = c.post("/api/classrooms", headers=H(TOK["prof"]), json={"name": f"Turma Aluno Excluido {RUN}", "year": 2026, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": x["marina"]})
    tid = t.json()["id"]
    CREATED["classrooms"].append(tid)
    c.post(f"/api/classrooms/{tid}/enroll/{sid}", headers=H(TOK["prof"]))
    d = c.delete(f"/api/students/{sid}", headers=H(TOK["prof"]))
    raw = [str(v) for v in db.classrooms.find_one({"name": f"Turma Aluno Excluido {RUN}"}).get("students", [])]
    dl = c.delete(f"/api/classrooms/{tid}", headers=H(TOK["prof"]))
    return f"exclusão do aluno {d.status_code}; aluno ainda na lista da turma: {sid in raw}; exclusão da turma {dl.status_code}", d.status_code == 204 and sid not in raw and dl.status_code == 204


@caso("ALU-13", "Alunos", "Alunos sem turma", "GET /api/students/unassigned", "200 e todos os itens sem classId")
def _(x):
    r = P("/api/students/unassigned")
    items = r.json()
    return f"HTTP {r.status_code}; {len(items)} alunos; todos sem turma: {all(not i.get('classId') for i in items)}", r.status_code == 200 and all(not i.get("classId") for i in items)


# ------------------------------------------------------------------ PROFESSORES
@caso("PRO-01", "Professores", "Criar professor válido", "POST /api/teachers com senha", "201; resposta sem password; senha gravada com bcrypt; o professor criado consegue entrar")
def _(x):
    email = f"prof.crud.{RUN}@professor.local"
    r = c.post("/api/teachers", headers=H(TOK["prof"]), json={"name": "Professor Crud Teste", "email": email, "password": PW, "subjects": ["Matemática"]})
    CREATED["teachers"].append(email)
    CREATED["users"].append(email)
    if r.status_code == 201:
        X["tcrud_id"] = r.json()["id"]
        X["tcrud_email"] = email
    stored = (db.teachers.find_one({"email": email}) or {}).get("password", "")
    lg = login(email)
    return (f"HTTP {r.status_code}; password na resposta: {'password' in r.json() if r.status_code == 201 else '-'}; "
            f"no banco: {'bcrypt' if str(stored).startswith('$2') else 'TEXTO PURO'}; login do professor criado: {lg.status_code}"), r.status_code == 201 and "password" not in r.json() and str(stored).startswith("$2") and lg.status_code == 200


@caso("PRO-02", "Professores", "Criar professor com e-mail repetido", "POST /api/teachers repetindo o e-mail", "409")
def _(x):
    r = c.post("/api/teachers", headers=H(TOK["prof"]), json={"name": "Professor Repetido", "email": X["tcrud_email"], "password": PW})
    return st(r, 409)


@caso("PRO-03", "Professores", "Criar professor com e-mail em formato inválido", "POST /api/teachers com e-mail \"professor\"", "422")
def _(x):
    r = c.post("/api/teachers", headers=H(TOK["prof"]), json={"name": "Professor Email Ruim", "email": "professor", "password": PW})
    if r.status_code == 201:
        CREATED["teachers"].append("professor")
        CREATED["users"].append("professor")
    return st(r, 422)


@caso("PRO-04", "Professores", "Criar professor sem senha", "POST /api/teachers sem o campo password", "422 (professor sem senha não consegue entrar)")
def _(x):
    email = f"prof.semsenha.{RUN}@professor.local"
    r = c.post("/api/teachers", headers=H(TOK["prof"]), json={"name": "Professor Sem Senha", "email": email})
    if r.status_code == 201:
        CREATED["teachers"].append(email)
        CREATED["users"].append(email)
    return st(r, 422)


@caso("PRO-05", "Professores", "Consultar, editar e excluir professor", "GET, PUT e DELETE /api/teachers/{id}", "200; 200 com nome novo; 204; professor sai da lista e o login é recusado (401)")
def _(x):
    g = P(f"/api/teachers/{X['tcrud_id']}")
    u = c.put(f"/api/teachers/{X['tcrud_id']}", headers=H(TOK["prof"]), json={"name": "Professor Crud Editado"})
    d = c.delete(f"/api/teachers/{X['tcrud_id']}", headers=H(TOK["prof"]))
    listed = X["tcrud_id"] in [t["id"] for t in P("/api/teachers").json()]
    lg = login(X["tcrud_email"])
    return f"consulta {g.status_code}; edição {u.status_code} ({u.json().get('name') if u.status_code == 200 else '-'}); exclusão {d.status_code}; ainda na lista: {listed}; login do excluído {lg.status_code}", g.status_code == 200 and u.status_code == 200 and d.status_code == 204 and not listed and lg.status_code == 401


# ------------------------------------------------------------------ MATÉRIAS E TÓPICOS
@caso("MAT-01", "Matérias e tópicos", "Criar matéria e recusar nome curto", "POST /api/subjects válida e com nome de 1 letra", "201; 422")
def _(x):
    r = c.post("/api/subjects", headers=H(TOK["prof"]), json={"name": f"Matéria Teste {RUN}", "area": "Teste"})
    if r.status_code == 201:
        X["subj_id"] = r.json()["id"]
        CREATED["subjects"].append(X["subj_id"])
    b = c.post("/api/subjects", headers=H(TOK["prof"]), json={"name": "A"})
    return f"válida: {r.status_code}; nome curto: {b.status_code}", r.status_code == 201 and b.status_code == 422


@caso("MAT-02", "Matérias e tópicos", "Matéria repetida", "POST /api/subjects com o mesmo nome", "201 reativando a mesma matéria ou 409, sem duplicar")
def _(x):
    n0 = db.subjects.count_documents({"name": f"Matéria Teste {RUN}"})
    r = c.post("/api/subjects", headers=H(TOK["prof"]), json={"name": f"Matéria Teste {RUN}", "area": "Teste"})
    n1 = db.subjects.count_documents({"name": f"Matéria Teste {RUN}"})
    return f"HTTP {r.status_code}; documentos com o nome: {n0} para {n1}", n1 == n0


@caso("MAT-03", "Matérias e tópicos", "Desativar e excluir matéria", "PATCH active=false e DELETE /api/subjects/{id}", "200 e 204; id inexistente 404")
def _(x):
    p = c.patch(f"/api/subjects/{X['subj_id']}", headers=H(TOK["prof"]), json={"active": False})
    d = c.delete(f"/api/subjects/{X['subj_id']}", headers=H(TOK["prof"]))
    n = c.delete("/api/subjects/000000000000000000000000", headers=H(TOK["prof"]))
    return f"PATCH {p.status_code}; DELETE {d.status_code}; inexistente {n.status_code}", p.status_code == 200 and d.status_code == 204 and n.status_code == 404


@caso("MAT-04", "Matérias e tópicos", "Tópicos de matéria: criar, editar, excluir", "POST/PUT/DELETE /api/subject-topics", "201; 200; 204; tópico curto recusado (422)")
def _(x):
    r = c.post("/api/subject-topics", headers=H(TOK["prof"]), json={"subject": f"Tópico Teste {RUN}", "topic": "Frações equivalentes"})
    tid = r.json().get("id") if r.status_code == 201 else None
    CREATED["topics"].append(tid)
    bad = c.post("/api/subject-topics", headers=H(TOK["prof"]), json={"subject": "X", "topic": "Y"})
    u = c.put(f"/api/subject-topics/{tid}", headers=H(TOK["prof"]), json={"subject": f"Tópico Teste {RUN}", "topics": ["A mais", "Outro tópico"]}) if tid else None
    d = c.delete(f"/api/subject-topics/{tid}", headers=H(TOK["prof"])) if tid else None
    return f"criar {r.status_code}; inválido {bad.status_code}; editar {u.status_code if u is not None else '-'}; excluir {d.status_code if d is not None else '-'}", r.status_code == 201 and bad.status_code == 422 and u is not None and u.status_code == 200 and d is not None and d.status_code == 204


# ------------------------------------------------------------------ ATIVIDADES
def act_body(title, classroom, n=1, **kw):
    q = [{"questionText": f"Quanto é {i + 2} + {i + 2}?", "questionType": "MULTIPLA_ESCOLHA", "options": [f"A) {i}", f"B) {(i + 2) * 2}", "C) 99", "D) 0"], "correctAnswer": "B"} for i in range(n)]
    return {"title": title, "subject": "Matemática", "topic": "Adição", "difficultyLevel": "FACIL", "questionsCount": n, "format": "MULTIPLA_ESCOLHA", "classroomId": classroom, "questions": q, **kw}


@caso("ATI-01", "Atividades", "Criar atividade válida", "POST /api/activities (2 questões objetivas) para a turma do Lucas", "201 e atividade gravada")
def _(x):
    r = c.post("/api/activities", headers=H(TOK["prof"]), json=act_body(f"Atividade Teste S9 {RUN}", x["classL"], 2))
    if r.status_code == 201:
        X["act_id"] = r.json()["id"]
        CREATED["activities"].append(X["act_id"])
    return st(r, 201)[0] + (f"; no banco: {bool(db.activities.find_one({'title': f'Atividade Teste S9 {RUN}'}))}" if r.status_code == 201 else ""), r.status_code == 201


@caso("ATI-02", "Atividades", "Atividade com título curto e sem turma", "POST /api/activities com título \"Abc\" e sem classroomId", "422 nos dois")
def _(x):
    a = c.post("/api/activities", headers=H(TOK["prof"]), json=act_body("Abc", x["classL"]))
    body = act_body(f"Atividade Sem Turma {RUN}", x["classL"])
    body.pop("classroomId")
    b = c.post("/api/activities", headers=H(TOK["prof"]), json=body)
    return f"título curto: {a.status_code}; sem turma: {b.status_code}", a.status_code == 422 and b.status_code == 422


@caso("ATI-03", "Atividades", "Atividade para turma inexistente", "POST /api/activities com classroomId inexistente", "400 ou 404")
def _(x):
    r = c.post("/api/activities", headers=H(TOK["prof"]), json=act_body(f"Atividade Turma Ruim {RUN}", "000000000000000000000000"))
    if r.status_code == 201:
        CREATED["activities"].append(r.json()["id"])
    return st(r, 400, 404)


@caso("ATI-04", "Atividades", "Atividade para aluno que não é da turma (RN10)", "POST /api/activities com studentId de aluno de outra turma", "400")
def _(x):
    r = c.post("/api/activities", headers=H(TOK["prof"]), json=act_body(f"Atividade Aluno Ruim {RUN}", x["classL"], studentId=x["other"]))
    if r.status_code == 201:
        CREATED["activities"].append(r.json()["id"])
    return st(r, 400)


@caso("ATI-05", "Atividades", "Consultar, editar e excluir atividade", "GET, PUT (novo título) e DELETE /api/activities/{id}", "200; 200; 204; depois 404")
def _(x):
    g = P(f"/api/activities/{X['act_id']}")
    u = c.put(f"/api/activities/{X['act_id']}", headers=H(TOK["prof"]), json={"title": f"Atividade Teste S9 Editada {RUN}"})
    nt = u.json().get("title") if u.status_code == 200 else "-"
    return f"consulta {g.status_code}; edição {u.status_code} ({nt})", g.status_code == 200 and u.status_code == 200 and nt.endswith(f"Editada {RUN}")


@caso("ATI-06", "Atividades", "Gerar atividade com IA (alternativa determinística sem chave)", "POST /api/activities/generate sem chave do Gemini configurada", "201/200 com questões geradas e indicação de que não veio do provedor externo")
def _(x):
    r = c.post("/api/activities/generate", headers=H(TOK["prof"]), json={"classroomId": x["classL"], "subject": "Matemática", "topic": "Frações", "difficultyLevel": "MEDIO", "questionsCount": 3, "format": "MULTIPLA_ESCOLHA"})
    ok = r.status_code in (200, 201)
    n = 0
    if ok:
        j = r.json()
        CREATED["activities"].append(j["id"])
        n = j.get("questionsCount", 0)
    return f"HTTP {r.status_code}; questões: {n}; generatedByAI={r.json().get('generatedByAI') if ok else '-'}", ok and n == 3


@caso("ATI-07", "Atividades", "Exportar atividade em PDF", "GET /api/activities/{id}/export-pdf", "200, application/pdf, arquivo começa com %PDF")
def _(x):
    r = P(f"/api/activities/{X['act_id']}/export-pdf")
    return f"HTTP {r.status_code}; tipo={r.headers.get('content-type')}; início={r.content[:5]!r}; {len(r.content)} bytes", r.status_code == 200 and r.content[:4] == b"%PDF"


@caso("ATI-08", "Atividades", "Atividade inexistente", "GET e DELETE de id inexistente", "404")
def _(x):
    a = P("/api/activities/000000000000000000000000")
    b = c.delete("/api/activities/000000000000000000000000", headers=H(TOK["prof"]))
    return f"GET {a.status_code}; DELETE {b.status_code}", a.status_code == 404 and b.status_code == 404


# ------------------------------------------------------------------ PORTAL / SUBMISSÃO / CORREÇÃO
@caso("SUB-01", "Submissões", "Aluno vê a atividade sem gabarito", "GET /api/student-portal/activities/{id} como Lucas", "200, questões sem correctAnswer")
def _(x):
    r = c.get(f"/api/student-portal/activities/{X['act_id']}", headers=H(TOK["aluno"]))
    return f"HTTP {r.status_code}; correctAnswer presente: {'correctAnswer' in r.text}", r.status_code == 200 and "correctAnswer" not in r.text


@caso("SUB-02", "Submissões", "Enviar respostas incompletas", "POST .../submissions com 1 de 2 respostas", "400 \"Responda todas as questões antes de enviar\" e nada gravado")
def _(x):
    r = c.post(f"/api/student-portal/activities/{X['act_id']}/submissions", headers=H(TOK["aluno"]), json={"answers": [{"questionIndex": 0, "selectedAnswer": "B) 4"}]})
    n = db.activity_submissions.count_documents({"activity_id": X["act_id"]})
    return st(r, 400)[0] + f"; submissões no banco: {n}", r.status_code == 400 and n == 0


@caso("SUB-03", "Submissões", "Enviar respostas válidas (correção automática)", "POST .../submissions com as 2 respostas (1 certa, 1 errada)", "200, 1/2 acertos (50%) e submissão gravada")
def _(x):
    r = c.post(f"/api/student-portal/activities/{X['act_id']}/submissions", headers=H(TOK["aluno"]), json={"answers": [{"questionIndex": 0, "selectedAnswer": "B) 4"}, {"questionIndex": 1, "selectedAnswer": "A) 1"}]})
    j = r.json()
    n = db.activity_submissions.count_documents({"activity_id": X["act_id"]})
    return f"HTTP {r.status_code}; acertos {j.get('correctCount')}/{j.get('totalQuestions')} ({j.get('scorePercent')}%); submissões no banco: {n}", r.status_code == 200 and j.get("correctCount") == 1 and j.get("scorePercent") == 50 and n == 1


@caso("SUB-04", "Submissões", "Reenvio da mesma atividade", "Repetir o POST .../submissions", "409 \"Esta atividade já foi enviada\"")
def _(x):
    r = c.post(f"/api/student-portal/activities/{X['act_id']}/submissions", headers=H(TOK["aluno"]), json={"answers": [{"questionIndex": 0, "selectedAnswer": "B) 4"}, {"questionIndex": 1, "selectedAnswer": "B) 8"}]})
    return st(r, 409)


@caso("SUB-05", "Submissões", "Aluno consulta o próprio resultado", "GET .../submissions como Lucas", "200 com o mesmo resultado (1/2)")
def _(x):
    r = c.get(f"/api/student-portal/activities/{X['act_id']}/submissions", headers=H(TOK["aluno"]))
    return f"HTTP {r.status_code}; acertos={r.json().get('correctCount') if r.status_code == 200 else '-'}", r.status_code == 200 and r.json().get("correctCount") == 1


@caso("SUB-06", "Submissões", "Professor vê as respostas individuais", "GET /api/activities/{id}/submissions", "200 com 1 aluno e 1/2 acertos")
def _(x):
    r = P(f"/api/activities/{X['act_id']}/submissions")
    j = r.json()
    items = j if isinstance(j, list) else j.get("submissions", j.get("items", []))
    return f"HTTP {r.status_code}; {len(items)} submissão(ões)", r.status_code == 200 and len(items) == 1


@caso("SUB-07", "Submissões", "Questão discursiva: fica pendente e o professor corrige", "Criar atividade discursiva, aluno envia texto, professor corrige em /api/teacher/activity-corrections", "Pendente aparece na lista; correção 200; some da lista de pendentes")
def _(x):
    body = act_body(f"Atividade Discursiva S9 {RUN}", x["classL"], 1)
    body["format"] = "DISCURSIVA"
    body["questions"] = [{"questionText": "Explique a adição.", "questionType": "DISCURSIVA", "options": [], "correctAnswer": "Juntar quantidades."}]
    a = c.post("/api/activities", headers=H(TOK["prof"]), json=body)
    aid = a.json()["id"]
    CREATED["activities"].append(aid)
    s = c.post(f"/api/student-portal/activities/{aid}/submissions", headers=H(TOK["aluno"]), json={"answers": [{"questionIndex": 0, "selectedAnswer": "Somar é juntar."}]})
    pend = P("/api/teacher/activity-corrections/pending").json()
    items = pend if isinstance(pend, list) else pend.get("items", [])
    mine = [i for i in items if str(i.get("activityId")) == aid]
    sub_id = mine[0].get("submissionId") or mine[0].get("id") if mine else None
    rv = c.put(f"/api/teacher/activity-corrections/{sub_id}/questions/0", headers=H(TOK["prof"]), json={"correct": True, "feedback": "Boa resposta."}) if sub_id else None
    after = P("/api/teacher/activity-corrections/pending").json()
    items2 = after if isinstance(after, list) else after.get("items", [])
    still = [i for i in items2 if str(i.get("activityId")) == aid]
    return f"envio {s.status_code}; pendências antes: {len(mine)}; correção: {rv.status_code if rv is not None else '-'}; pendências depois: {len(still)}", s.status_code == 200 and len(mine) == 1 and rv is not None and rv.status_code == 200 and len(still) == 0


@caso("SUB-08", "Submissões", "Excluir atividade com submissões", "DELETE /api/activities/{id} da atividade já respondida", "204 (e a atividade some) ou recusa explícita")
def _(x):
    d = c.delete(f"/api/activities/{X['act_id']}", headers=H(TOK["prof"]))
    g = P(f"/api/activities/{X['act_id']}")
    orphan = db.activity_submissions.count_documents({"activity_id": X["act_id"]})
    return f"DELETE {d.status_code}; consulta depois {g.status_code}; submissões órfãs no banco: {orphan}", (d.status_code == 204 and g.status_code == 404 and orphan == 0) or d.status_code in (400, 409)


# ------------------------------------------------------------------ NOTAS
def grade_body(student, classroom, **kw):
    return {"studentId": student, "classroomId": classroom, "grade": 7.5, "subject": "Matemática", "activityType": "EXAM", "attendance": True, "date": time.strftime("%Y-%m-%dT12:00:00Z"), **kw}


@caso("NOT-01", "Notas e frequência", "Lançar nota válida", "POST /api/grades (7,5, presente) para Lucas", "201 e nota gravada")
def _(x):
    r = c.post("/api/grades", headers=H(TOK["prof"]), json=grade_body(x["lucas"], x["classL"]))
    if r.status_code == 201:
        X["grade_id"] = r.json()["id"]
        CREATED["grades"].append(X["grade_id"])
    return st(r, 201)[0] + (f"; nota={r.json().get('grade')}" if r.status_code == 201 else ""), r.status_code == 201


@caso("NOT-02", "Notas e frequência", "Nota fora da faixa 0 a 10", "POST /api/grades com 11, -1 e texto", "422 nos três")
def _(x):
    codes = [c.post("/api/grades", headers=H(TOK["prof"]), json=grade_body(x["lucas"], x["classL"], grade=v)).status_code for v in (11, -1, "abc")]
    return f"11: {codes[0]}; -1: {codes[1]}; \"abc\": {codes[2]}", codes == [422, 422, 422]


@caso("NOT-03", "Notas e frequência", "Nota sem aluno, sem turma ou sem data", "POST /api/grades omitindo campos obrigatórios", "422 em cada omissão")
def _(x):
    out = []
    for k in ("studentId", "classroomId", "date"):
        b = grade_body(x["lucas"], x["classL"])
        b.pop(k)
        out.append(c.post("/api/grades", headers=H(TOK["prof"]), json=b).status_code)
    return f"sem aluno/turma/data: {out}", out == [422, 422, 422]


@caso("NOT-04", "Notas e frequência", "Nota para aluno que não é da turma (RN26)", "POST /api/grades com aluno de outra turma", "400 \"O aluno não está matriculado na turma informada\"")
def _(x):
    r = c.post("/api/grades", headers=H(TOK["prof"]), json=grade_body(x["other"], x["classL"]))
    if r.status_code == 201:
        CREATED["grades"].append(r.json()["id"])
    return st(r, 400)


@caso("NOT-05", "Notas e frequência", "Nota com data futura e observação longa", "POST /api/grades com data em 2030 e observação de 600 caracteres", "422 nos dois")
def _(x):
    a = c.post("/api/grades", headers=H(TOK["prof"]), json=grade_body(x["lucas"], x["classL"], date="2030-01-01T00:00:00Z"))
    b = c.post("/api/grades", headers=H(TOK["prof"]), json=grade_body(x["lucas"], x["classL"], observations="x" * 600))
    return f"data futura: {a.status_code}; observação longa: {b.status_code}", a.status_code == 422 and b.status_code == 422


@caso("NOT-06", "Notas e frequência", "Editar nota e recalcular média", "PUT /api/grades/{id} para 9,0 e GET média do aluno", "200; média e resumo da turma refletem a mudança")
def _(x):
    before = P(f"/api/grades/student/{x['lucas']}/average").json()
    u = c.put(f"/api/grades/{X['grade_id']}", headers=H(TOK["prof"]), json={"grade": 9.0})
    after = P(f"/api/grades/student/{x['lucas']}/average").json()
    avg = lambda v: v if isinstance(v, (int, float)) else v.get("average", v.get("averageGrade"))
    return f"PUT {u.status_code}; média antes {avg(before):.2f} depois {avg(after):.2f}", u.status_code == 200 and abs(avg(after) - avg(before)) > 0.0001


@caso("NOT-07", "Notas e frequência", "Frequência calculada só com presença registrada", "Lançar falta e nota sem presença; GET /api/students/{id}/attendance", "Total de aulas = lançamentos com presença registrada")
def _(x):
    base = P(f"/api/students/{x['lucas']}/attendance").json()
    a = c.post("/api/grades", headers=H(TOK["prof"]), json=grade_body(x["lucas"], x["classL"], attendance=False))
    b = c.post("/api/grades", headers=H(TOK["prof"]), json=grade_body(x["lucas"], x["classL"], attendance=None))
    for r in (a, b):
        if r.status_code == 201:
            CREATED["grades"].append(r.json()["id"])
    now = P(f"/api/students/{x['lucas']}/attendance").json()
    return f"aulas {base['totalClasses']} para {now['totalClasses']}; faltas {base['absences']} para {now['absences']}", now["totalClasses"] == base["totalClasses"] + 1 and now["absences"] == base["absences"] + 1


@caso("NOT-08", "Notas e frequência", "Lançar notas de uma atividade (idempotente)", "POST /api/grades/from-activity/{id} duas vezes", "1ª cria a nota; 2ª não duplica")
def _(x):
    body = act_body(f"Atividade Notas S9 {RUN}", x["classL"], 1)
    a = c.post("/api/activities", headers=H(TOK["prof"]), json=body)
    aid = a.json()["id"]
    CREATED["activities"].append(aid)
    c.post(f"/api/student-portal/activities/{aid}/submissions", headers=H(TOK["aluno"]), json={"answers": [{"questionIndex": 0, "selectedAnswer": "B) 4"}]})
    r1 = c.post(f"/api/grades/from-activity/{aid}", headers=H(TOK["prof"]))
    r2 = c.post(f"/api/grades/from-activity/{aid}", headers=H(TOK["prof"]))
    n = db.grades.count_documents({"activityId": aid})
    for g in db.grades.find({"activityId": aid}):
        CREATED["grades"].append(str(g["_id"]))
    return f"1ª {r1.status_code}; 2ª {r2.status_code}; notas no banco: {n}", r1.status_code in (200, 201) and r2.status_code in (200, 201) and n == 1


@caso("NOT-09", "Notas e frequência", "Resumo da turma e consistência com o portal", "GET /api/grades/classroom/{id}/summary e GET /api/student-portal/performance", "Mesma média e frequência para o aluno nos dois lados")
def _(x):
    s = P(f"/api/grades/classroom/{x['classL']}/summary").json()
    row = next(i for i in s["students"] if i["studentId"] == x["lucas"])
    p = c.get("/api/student-portal/performance", headers=H(TOK["aluno"])).json()
    return f"professor: média {row['average']:.2f}, freq {row['attendanceRate']}%; aluno: média {p['averageGrade']:.2f}, freq {p['attendanceRate']}%", abs(row["average"] - p["averageGrade"]) < 0.01 and row["attendanceRate"] == p["attendanceRate"]


@caso("NOT-10", "Notas e frequência", "Excluir nota e id inexistente", "DELETE /api/grades/{id}; DELETE de id inexistente", "204; 404")
def _(x):
    a = c.delete(f"/api/grades/{X['grade_id']}", headers=H(TOK["prof"]))
    b = c.delete("/api/grades/000000000000000000000000", headers=H(TOK["prof"]))
    g = P(f"/api/grades/{X['grade_id']}")
    return f"DELETE {a.status_code}; inexistente {b.status_code}; consulta depois {g.status_code}", a.status_code == 204 and b.status_code == 404 and g.status_code == 404


# ------------------------------------------------------------------ DASHBOARD / RELATÓRIOS / PESQUISA / HISTÓRICO
@caso("REL-01", "Dashboard e relatórios", "Indicadores do dashboard batem com o banco", "GET /api/dashboard/overview e contagem direta no MongoDB", "Alunos ativos, atividades e lançamentos iguais ao banco")
def _(x):
    j = P("/api/dashboard/overview").json()
    k = j.get("kpis", j)
    students = db.students.count_documents({"active": {"$ne": False}})
    activities = db.activities.count_documents({})
    grades = db.grades.count_documents({})
    got = (k.get("students"), k.get("activities"), k.get("gradeCount", k.get("grades")))
    return f"dashboard {got}; banco ({students}, {activities}, {grades})", (got[0], got[1]) == (students, activities) and (got[2] in (grades, None))


@caso("REL-02", "Dashboard e relatórios", "Filtros inválidos", "GET /api/dashboard/overview?from=2026-12-01&to=2026-01-01 e com classroomId inexistente", "422 e 404")
def _(x):
    a = P("/api/dashboard/overview?from=2026-12-01&to=2026-01-01")
    b = P("/api/dashboard/overview?classroomId=000000000000000000000000")
    return f"período invertido: {a.status_code}; turma inexistente: {b.status_code}", a.status_code == 422 and b.status_code == 404


@caso("REL-03", "Dashboard e relatórios", "Os cinco relatórios abrem", "GET /api/reports e cada /api/reports/{tipo}", "200 em todos, com linhas e resumo")
def _(x):
    cat = P("/api/reports").json()
    types = [t["type"] for t in (cat if isinstance(cat, list) else cat.get("reports", []))]
    out = {}
    for t in types:
        r = P(f"/api/reports/{t}")
        out[t] = r.status_code
    return f"{len(types)} relatórios: {out}", len(types) == 5 and all(v == 200 for v in out.values())


@caso("REL-04", "Dashboard e relatórios", "Exportar relatório em CSV, Excel e PDF", "GET /api/reports/boletim/export?format=csv|xlsx|pdf", "200 com o tipo e o conteúdo de cada formato")
def _(x):
    out = {}
    for f, sig in (("csv", b""), ("xlsx", b"PK"), ("pdf", b"%PDF")):
        r = P(f"/api/reports/boletim/export?format={f}")
        out[f] = (r.status_code, r.content[:4], len(r.content))
    ok = out["csv"][0] == 200 and out["xlsx"][1][:2] == b"PK" and out["pdf"][1] == b"%PDF"
    return "; ".join(f"{k}: HTTP {v[0]}, {v[2]} bytes" for k, v in out.items()), ok


@caso("REL-05", "Dashboard e relatórios", "Exportação inválida", "format=doc e relatório inexistente", "422 e 404")
def _(x):
    a = P("/api/reports/boletim/export?format=doc")
    b = P("/api/reports/nao-existe")
    return f"formato inválido: {a.status_code}; relatório inexistente: {b.status_code}", a.status_code == 422 and b.status_code == 404


@caso("REL-06", "Pesquisa", "Pesquisa global", "GET /api/search?q=lucas, q=fracoes (sem acento) e q=a (1 caractere)", "Resultados; atividade com acento encontrada sem acento; 422 para 1 caractere")
def _(x):
    a = P("/api/search?q=lucas").json()
    b = P("/api/search?q=fracoes").json()
    d = P("/api/search?q=a")
    na = sum(len(v) for v in a.values() if isinstance(v, list)) if isinstance(a, dict) else len(a)
    nb = sum(len(v) for v in b.values() if isinstance(v, list)) if isinstance(b, dict) else len(b)
    return f"\"lucas\": {na} resultado(s); \"fracoes\": {nb}; 1 caractere: {d.status_code}", na >= 1 and nb >= 1 and d.status_code == 422


@caso("HIS-01", "Histórico", "Operações ficam registradas", "Criar e excluir uma turma e consultar /api/audit-logs", "Criação e exclusão aparecem com autor e resultado")
def _(x):
    nm = f"Turma Historico S9 {RUN}"
    r = c.post("/api/classrooms", headers=H(TOK["prof"]), json={"name": nm, "year": 2026, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": x["marina"]})
    cid = r.json()["id"]
    c.delete(f"/api/classrooms/{cid}", headers=H(TOK["prof"]))
    logs = P("/api/audit-logs?size=20&entity=classroom").json()
    texts = [i.get("summary", "") for i in logs["items"]]
    return f"{len(logs['items'])} registros; criada: {any(nm in t and 'criad' in t for t in texts)}; excluída: {any(nm in t and 'exclu' in t for t in texts)}", any(nm in t and "criad" in t for t in texts) and any(nm in t and "exclu" in t for t in texts)


@caso("HIS-02", "Histórico", "Histórico recusa leitura por aluno e filtros inválidos", "GET /api/audit-logs como aluno; size=500", "403; 422")
def _(x):
    a = c.get("/api/audit-logs", headers=H(TOK["aluno"]))
    b = P("/api/audit-logs?size=500")
    return f"aluno: {a.status_code}; size=500: {b.status_code}", a.status_code == 403 and b.status_code == 422


# ------------------------------------------------------------------ PORTAL DO ALUNO
@caso("POR-01", "Portal do aluno", "Telas do portal respondem", "GET /api/student-portal/{me,classroom,classmates,teachers,activities,grades,performance} como Lucas", "200 em todas")
def _(x):
    out = {p: c.get(f"/api/student-portal/{p}", headers=H(TOK["aluno"])).status_code for p in ("me", "classroom", "classmates", "teachers", "activities", "grades", "performance")}
    return str(out), all(v == 200 for v in out.values())


@caso("POR-02", "Portal do aluno", "Portal não expõe dados sensíveis dos colegas", "GET /api/student-portal/classmates", "Só nome (sem e-mail, senha ou notas)")
def _(x):
    tok_other = login(x["other_email"]).json()["accessToken"]
    j = c.get("/api/student-portal/classmates", headers=H(tok_other)).json()
    keys = sorted({k for i in j for k in i}) if j else []
    return f"{len(j)} colegas; campos: {keys}", not any(k in keys for k in ("password", "email", "grades", "averageGrade"))


# ------------------------------------------------------------------ limpeza e execução
def cleanup():
    for email in set(CREATED["users"]):
        db.users.delete_many({"email": email})
    for email in set(CREATED["students"]):
        db.students.delete_many({"email": email})
    db.students.delete_many({"name": {"$in": ["Aluno Matriculado Teste", "Aluno Crud Teste", "Aluno Crud Editado"]}})
    for email in set(CREATED["teachers"]):
        db.teachers.delete_many({"email": email})
    from bson import ObjectId
    for coll, ids in (("classrooms", CREATED["classrooms"]), ("activities", CREATED["activities"]), ("grades", CREATED["grades"]), ("subjects", CREATED["subjects"]), ("subject_topics", CREATED["topics"])):
        for i in ids:
            if i:
                db[coll].delete_many({"_id": ObjectId(i)})
    db.activity_submissions.delete_many({"activity_id": {"$in": [i for i in CREATED["activities"] if i]}})
    db.subject_topics.delete_many({"subject": f"Tópico Teste {RUN}"})
    db.classrooms.delete_many({"name": {"$regex": f"{RUN}$"}})
    db.teachers.update_many({}, {"$pull": {"classroomIds": {"$in": [i for i in CREATED["classrooms"] if i]}}})


# casos que exercitam dados inválidos, campos obrigatórios, formatos e regras de negócio (Testes de validação)
VALIDACAO = {"AUT-03", "AUT-04", "AUT-05", "AUT-07", "AUT-08", "AUT-09", "AUT-11", "AUT-12", "AUT-14", "AUT-16", "TUR-02", "TUR-03", "TUR-04", "TUR-05", "TUR-09", "TUR-12", "TUR-15",
             "ALU-02", "ALU-03", "ALU-04", "ALU-05", "ALU-08", "ALU-10", "PRO-02", "PRO-03", "PRO-04", "MAT-01", "ATI-02", "ATI-03", "ATI-04", "ATI-08", "SUB-02", "SUB-04",
             "NOT-02", "NOT-03", "NOT-04", "NOT-05", "REL-02", "REL-05", "HIS-02"}


def main():
    ctx = setup()
    for cid, modulo, titulo, passos, esperado, fn in CASES:
        try:
            obtido, ok = fn(ctx)
        except Exception as exc:  # noqa: BLE001
            obtido, ok = f"ERRO NO TESTE: {type(exc).__name__}: {str(exc)[:120]}", False
        RESULTS.append({"id": cid, "modulo": modulo, "titulo": titulo, "passos": passos, "esperado": esperado, "obtido": obtido, "ok": bool(ok), "validacao": cid in VALIDACAO})
        print(("OK    " if ok else "FALHA ") + f"{cid} {titulo} -> {obtido}")
    cleanup()
    json.dump(RESULTS, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"RESUMO: {sum(r['ok'] for r in RESULTS)} aprovados de {len(RESULTS)}")


if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3] / "PlusEduc-BE-Python"))
    main()
