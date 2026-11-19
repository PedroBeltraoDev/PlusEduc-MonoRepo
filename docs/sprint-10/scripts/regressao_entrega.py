"""Regressão funcional da entrega da Sprint 10 (versão atual da main: release candidate + atualização de segurança).

    PLUSEDUC_EVAL_PASSWORD=... python regressao_entrega.py http://127.0.0.1:8093 pluseduc_sprint10_entrega saida.json

Reaproveita os 104 casos da regressão da Sprint 10 (92 da Sprint 09 + 12 da release candidate, em regressao_api.py).
Depois da Sprint 10 entrou a atualização de segurança (PR #14 integrado pelo PR #15), que mudou de propósito algumas
regras. Os casos afetados foram reescritos aqui com o novo resultado esperado, e cada um diz o que mudou e por quê:

* professor só atua nas turmas sob sua responsabilidade: turma, aluno ou atividade fora do escopo (inclusive um id
  inexistente) responde 403 para ele; para o ADMIN continua 404/400 (TUR-06, TUR-14, ALU-05, ATI-03);
* turma criada por professor é sempre dele: o teacherId enviado é ignorado (TUR-05, TUR-15);
* criar, alterar e desativar professores e alterar ou desativar matérias do catálogo é tarefa do ADMIN (PRO-01 a PRO-05, MAT-03);
* o dashboard do professor mostra só os dados das turmas dele; o do ADMIN, os da escola (REL-01);
* a senha fica só em users; trocar a senha encerra as sessões abertas (SEN-02).

Os casos SEG-01 a SEG-07 cobrem as regras novas: escopo por turma, transferência entre professores, refresh token de
uso único com detecção de reuso, logout e limite de tentativas de login.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("regressao_api_s10", HERE / "regressao_api.py")
r10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r10)  # registra os 104 casos (lê BASE, banco e saída de sys.argv)
t = r10.t
c, db, H, TOK, X, PW, RUN, CREATED, st, caso, login, P = t.c, t.db, t.H, t.TOK, t.X, t.PW, t.RUN, t.CREATED, t.st, t.caso, t.login, t.P
ANTES = len(t.CASES)
GRADE = "7º Ano do Ensino Fundamental"


REESCRITOS = []


def substituir(cid):
    """Troca a função e a descrição do caso cid pela versão registrada em seguida."""
    def deco(fn):
        novo = t.CASES.pop()  # o @caso acabou de registrar o caso novo no fim da lista
        pos = next(i for i, case in enumerate(t.CASES) if case[0] == cid)
        t.CASES[pos] = novo
        REESCRITOS.append(cid)
        return fn
    return deco


def criar_turma(token, name, teacher_id=None, grade=GRADE):
    body = {"name": name, "year": 2026, "gradeLevel": grade}
    if teacher_id:
        body["teacherId"] = teacher_id
    r = c.post("/api/classrooms", headers=H(token), json=body)
    if r.status_code == 201:
        CREATED["classrooms"].append(r.json()["id"])
    return r


# ------------------------------------------------------------------ turmas
@substituir("TUR-05")
@caso("TUR-05", "Turmas", "Professor cria turma: ela é sempre dele; ADMIN com professor inexistente",
      "POST /api/classrooms como professora com teacherId inexistente; o mesmo como ADMIN",
      "professora: 201 com ela mesma como responsável (o teacherId enviado é ignorado); ADMIN: 400")
def _(x):
    a = criar_turma(TOK["prof"], f"Turma Sem Prof {RUN}", "000000000000000000000000")
    dono = str((db.classrooms.find_one({"name": f"Turma Sem Prof {RUN}"}) or {}).get("teacher_id"))
    if a.status_code == 201:
        c.delete(f"/api/classrooms/{a.json()['id']}", headers=H(TOK["admin"]))  # não ocupa vaga no limite de 5 turmas
    b = criar_turma(TOK["admin"], f"Turma Sem Prof Admin {RUN}", "000000000000000000000000")
    return (f"professora: HTTP {a.status_code}, responsável gravada = ela mesma: {dono == x['marina']}; ADMIN: {st(b, 400)[0]}",
            a.status_code == 201 and dono == x["marina"] and b.status_code == 400)


@substituir("TUR-06")
@caso("TUR-06", "Turmas", "Consultar turma por id",
      "GET /api/classrooms/{id} da turma da professora; id inexistente como professora e como ADMIN",
      "200 com o nome certo; inexistente: 403 para a professora (fora do escopo dela) e 404 para o ADMIN")
def _(x):
    a = P(f"/api/classrooms/{X['class_id']}")
    b = P("/api/classrooms/000000000000000000000000")
    d = c.get("/api/classrooms/000000000000000000000000", headers=H(TOK["admin"]))
    ok = a.status_code == 200 and a.json().get("name", "").startswith("Turma Teste S9") and b.status_code == 403 and d.status_code == 404
    return f"existente: {a.status_code}; inexistente (professora): {b.status_code}; inexistente (ADMIN): {d.status_code}", ok


@substituir("TUR-14")
@caso("TUR-14", "Turmas", "Excluir turma vazia e id inexistente",
      "DELETE /api/classrooms/{id} da turma vazia; DELETE de id inexistente como professora e como ADMIN",
      "204 e a turma sai da lista de ativas; inexistente: 403 (professora) e 404 (ADMIN)")
def _(x):
    a = c.delete(f"/api/classrooms/{X['class2']}", headers=H(TOK["prof"]))
    b = c.delete("/api/classrooms/000000000000000000000000", headers=H(TOK["prof"]))
    d = c.delete("/api/classrooms/000000000000000000000000", headers=H(TOK["admin"]))
    listed = X["class2"] in [i["id"] for i in P("/api/classrooms").json()]
    return (f"vazia: {a.status_code}; inexistente: {b.status_code} (professora) e {d.status_code} (ADMIN); ainda na lista: {listed}",
            a.status_code == 204 and b.status_code == 403 and d.status_code == 404 and not listed)


@substituir("TUR-15")
@caso("TUR-15", "Turmas", "Limite de 5 turmas ativas por professor",
      "Como ADMIN, criar turmas para o professor recém-aprovado até passar de 5",
      "A sexta criação é recusada com 400 \"Limite máximo de 5 turmas ativas por professor\"")
def _(x):
    tid = str(db.teachers.find_one({"email": X["new_teacher_email"]})["_id"])
    codes, last = [], None
    for i in range(6):
        last = criar_turma(TOK["admin"], f"Turma Limite {i} {RUN}", tid, "6º Ano do Ensino Fundamental")
        codes.append(last.status_code)
    return f"respostas em sequência: {codes}; última: {st(last, 400)[0]}", codes[:5] == [201] * 5 and codes[5] == 400 and "Limite" in st(last, 400)[0]


# ------------------------------------------------------------------ alunos e atividades
@substituir("ALU-05")
@caso("ALU-05", "Alunos", "Criar aluno em turma inexistente",
      "POST /api/students com classId inexistente, como professora e como ADMIN",
      "professora: 403 (turma fora do escopo); ADMIN: 400 \"Turma não encontrada\"")
def _(x):
    body = {"name": "Aluno Turma Fantasma", "email": f"aluno.fantasma.{RUN}@aluno.local", "birthDate": "2012-05-06", "classId": "000000000000000000000000"}
    a = c.post("/api/students", headers=H(TOK["prof"]), json=body)
    b = c.post("/api/students", headers=H(TOK["admin"]), json=body)
    CREATED["students"].append(body["email"])
    return f"professora: {st(a, 403)[0]}; ADMIN: {st(b, 400)[0]}", a.status_code == 403 and b.status_code == 400


@substituir("ATI-03")
@caso("ATI-03", "Atividades", "Atividade para turma inexistente",
      "POST /api/activities com classroomId inexistente, como professora e como ADMIN",
      "professora: 403 (turma fora do escopo); ADMIN: 400 ou 404")
def _(x):
    body = t.act_body(f"Atividade Turma Ruim {RUN}", "000000000000000000000000")
    a = c.post("/api/activities", headers=H(TOK["prof"]), json=body)
    b = c.post("/api/activities", headers=H(TOK["admin"]), json=body)
    for r in (a, b):
        if r.status_code == 201:
            CREATED["activities"].append(r.json().get("id"))
    return f"professora: {st(a, 403)[0]}; ADMIN: {st(b, 400, 404, 422)[0]}", a.status_code == 403 and b.status_code in (400, 404, 422)


# ------------------------------------------------------------------ professores (CRUD só do ADMIN)
@substituir("PRO-01")
@caso("PRO-01", "Professores", "ADMIN cria professor; professora não cria",
      "POST /api/teachers com senha, como professora e como ADMIN; login do professor criado",
      "professora 403; ADMIN 201 sem password na resposta; senha com bcrypt só em users (nada em teachers); o criado entra")
def _(x):
    email = f"prof.crud.{RUN}@professor.local"
    body = {"name": "Professor Crud Teste", "email": email, "password": PW, "subjects": ["Matemática"]}
    a = c.post("/api/teachers", headers=H(TOK["prof"]), json=body)
    r = c.post("/api/teachers", headers=H(TOK["admin"]), json=body)
    CREATED["teachers"].append(email)
    CREATED["users"].append(email)
    if r.status_code == 201:
        X["tcrud_id"], X["tcrud_email"] = r.json()["id"], email
    user = db.users.find_one({"email": email}) or {}
    teacher = db.teachers.find_one({"email": email}) or {}
    lg = login(email)
    ok = (a.status_code == 403 and r.status_code == 201 and "password" not in r.json() and str(user.get("password", "")).startswith("$2")
          and "password" not in teacher and lg.status_code == 200)
    return (f"professora: {a.status_code}; ADMIN: {r.status_code}; password na resposta: {'password' in r.json() if r.status_code == 201 else '-'}; "
            f"users: {'bcrypt' if str(user.get('password', '')).startswith('$2') else 'sem senha'}; teachers guarda senha: {'password' in teacher}; login: {lg.status_code}"), ok


@substituir("PRO-02")
@caso("PRO-02", "Professores", "Criar professor com e-mail repetido", "POST /api/teachers (ADMIN) com o mesmo e-mail", "409")
def _(x):
    return st(c.post("/api/teachers", headers=H(TOK["admin"]), json={"name": "Professor Repetido", "email": X["tcrud_email"], "password": PW}), 409)


@substituir("PRO-03")
@caso("PRO-03", "Professores", "Criar professor com e-mail em formato inválido", "POST /api/teachers (ADMIN) com e-mail \"abc\"", "422")
def _(x):
    return st(c.post("/api/teachers", headers=H(TOK["admin"]), json={"name": "Professor Email Ruim", "email": "abc", "password": PW}), 422)


@substituir("PRO-04")
@caso("PRO-04", "Professores", "Criar professor sem senha", "POST /api/teachers (ADMIN) sem o campo password", "422 (professor sem senha não consegue entrar)")
def _(x):
    return st(c.post("/api/teachers", headers=H(TOK["admin"]), json={"name": "Professor Sem Senha", "email": f"prof.semsenha.{RUN}@professor.local"}), 422)


@substituir("PRO-05")
@caso("PRO-05", "Professores", "Consultar, editar e excluir professor",
      "GET (professora), PUT e DELETE (professora e ADMIN) /api/teachers/{id}; login do excluído",
      "consulta 200; professora 403 em editar e excluir; ADMIN 200 com nome novo e 204; sai da lista e o login é recusado (401)")
def _(x):
    tid = X["tcrud_id"]
    g = P(f"/api/teachers/{tid}")
    pu = c.put(f"/api/teachers/{tid}", headers=H(TOK["prof"]), json={"name": "Professor Crud Invasor"})
    pd = c.delete(f"/api/teachers/{tid}", headers=H(TOK["prof"]))
    u = c.put(f"/api/teachers/{tid}", headers=H(TOK["admin"]), json={"name": "Professor Crud Editado"})
    d = c.delete(f"/api/teachers/{tid}", headers=H(TOK["admin"]))
    listed = tid in [i["id"] for i in P("/api/teachers").json()]
    lg = login(X["tcrud_email"])
    ok = g.status_code == 200 and (pu.status_code, pd.status_code) == (403, 403) and u.status_code == 200 and d.status_code == 204 and not listed and lg.status_code == 401
    return (f"consulta {g.status_code}; professora editar/excluir {pu.status_code}/{pd.status_code}; ADMIN editar {u.status_code} "
            f"({u.json().get('name') if u.status_code == 200 else '-'}) e excluir {d.status_code}; ainda na lista: {listed}; login do excluído {lg.status_code}"), ok


# ------------------------------------------------------------------ matérias
@substituir("MAT-03")
@caso("MAT-03", "Matérias e tópicos", "Desativar e excluir matéria do catálogo",
      "PATCH active=false e DELETE /api/subjects/{id} como professora e como ADMIN; id inexistente (ADMIN)",
      "professora 403 nos dois; ADMIN 200 e 204; inexistente 404")
def _(x):
    sid = X["subj_id"]
    pp = c.patch(f"/api/subjects/{sid}", headers=H(TOK["prof"]), json={"active": False})
    pd = c.delete(f"/api/subjects/{sid}", headers=H(TOK["prof"]))
    p = c.patch(f"/api/subjects/{sid}", headers=H(TOK["admin"]), json={"active": False})
    d = c.delete(f"/api/subjects/{sid}", headers=H(TOK["admin"]))
    n = c.delete("/api/subjects/000000000000000000000000", headers=H(TOK["admin"]))
    ok = (pp.status_code, pd.status_code) == (403, 403) and p.status_code == 200 and d.status_code == 204 and n.status_code == 404
    return f"professora PATCH/DELETE {pp.status_code}/{pd.status_code}; ADMIN PATCH {p.status_code}, DELETE {d.status_code}; inexistente {n.status_code}", ok


# ------------------------------------------------------------------ dashboard
@substituir("REL-01")
@caso("REL-01", "Dashboard e relatórios", "Indicadores do dashboard batem com o banco e com o escopo",
      "GET /api/dashboard/overview como ADMIN e como professora; contagem direta no MongoDB e lista de alunos da professora",
      "ADMIN: alunos ativos e atividades iguais ao banco; professora: o mesmo número de alunos que ela consegue listar")
def _(x):
    ka = c.get("/api/dashboard/overview", headers=H(TOK["admin"])).json()
    ka = ka.get("kpis", ka)
    kp = P("/api/dashboard/overview").json()
    kp = kp.get("kpis", kp)
    students = db.students.count_documents({"active": {"$ne": False}})
    activities = db.activities.count_documents({})
    visible = len(P("/api/students").json())
    ok = (ka.get("students"), ka.get("activities")) == (students, activities) and kp.get("students") == visible and visible < students
    return (f"ADMIN ({ka.get('students')}, {ka.get('activities')}) x banco ({students}, {activities}); "
            f"professora: {kp.get('students')} aluno(s) no dashboard, {visible} na lista dela"), ok


# ------------------------------------------------------------------ troca de senha
@substituir("SEN-02")
@caso("SEN-02", "Troca de senha", "Trocar a própria senha encerra as sessões",
      "POST /api/auth/change-password com a senha atual correta; token antigo; login com a senha antiga e com a nova",
      "200 com um par de tokens novo; token antigo 401; senha antiga 401; nova 200; hash novo só em users (nada em teachers)")
def _(x):
    from app.core.passwords import verify_password
    nova = "Nova@" + RUN
    old_tokens = X["new_teacher_tokens"]
    r = c.post("/api/auth/change-password", headers=H(old_tokens["accessToken"]), json={"currentPassword": PW, "newPassword": nova})
    antigo = c.get("/api/classrooms", headers=H(old_tokens["accessToken"]))
    novo = c.get("/api/classrooms", headers=H(r.json().get("accessToken", "x")))
    old, new = login(X["new_teacher_email"]), login(X["new_teacher_email"], nova)
    user = db.users.find_one({"email": X["new_teacher_email"]})
    teacher = db.teachers.find_one({"email": X["new_teacher_email"]})
    hashes = verify_password(nova, user["password"]) and "password" not in teacher
    ok = (r.status_code, antigo.status_code, novo.status_code, old.status_code, new.status_code) == (200, 401, 200, 401, 200) and hashes
    return (f"troca: {r.status_code}; token antigo: {antigo.status_code}; token novo: {novo.status_code}; senha antiga: {old.status_code}; "
            f"senha nova: {new.status_code}; hash só em users: {hashes}"), ok


# ------------------------------------------------------------------ casos novos: segurança
@caso("SEG-01", "Segurança", "Professora só vê as turmas dela",
      "GET /api/classrooms como professora e como ADMIN; GET da turma de outro professor",
      "a lista da professora é menor que a do ADMIN e não tem a turma de outro professor; GET dessa turma: 403 (ADMIN 200)")
def _(x):
    mine = {i["id"] for i in P("/api/classrooms").json()}
    every = {i["id"] for i in c.get("/api/classrooms", headers=H(TOK["admin"])).json()}
    alheia = next(i for i in every - mine)
    a = P(f"/api/classrooms/{alheia}")
    b = c.get(f"/api/classrooms/{alheia}", headers=H(TOK["admin"]))
    X["turma_alheia"] = alheia
    ok = mine < every and a.status_code == 403 and b.status_code == 200
    return f"professora: {len(mine)} turma(s); ADMIN: {len(every)}; turma de outro professor: {a.status_code} (ADMIN {b.status_code})", ok


@caso("SEG-02", "Segurança", "Professora não acessa aluno nem notas de outra turma",
      "GET /api/students/{id}, /api/grades/student/{id} e relatório de desempenho de um aluno de turma alheia",
      "403 nas três; ADMIN 200 no cadastro do aluno")
def _(x):
    sid = next(str(s["_id"]) for s in db.students.find({"active": {"$ne": False}, "class_id": X["turma_alheia"]}))
    a = P(f"/api/students/{sid}")
    b = P(f"/api/grades/student/{sid}")
    d = P(f"/api/students/{sid}/performance")
    adm = c.get(f"/api/students/{sid}", headers=H(TOK["admin"]))
    return (f"aluno: {a.status_code}; notas: {b.status_code}; desempenho: {d.status_code}; ADMIN: {adm.status_code}",
            (a.status_code, b.status_code, d.status_code, adm.status_code) == (403, 403, 403, 200))


@caso("SEG-03", "Segurança", "Transferência de aluno entre professores fica com o ADMIN",
      "POST /api/classrooms/{turma da professora}/enroll/{aluno de turma alheia} como professora",
      "403; o aluno continua na turma de origem")
def _(x):
    sid = next(str(s["_id"]) for s in db.students.find({"active": {"$ne": False}, "class_id": X["turma_alheia"]}))
    r = c.post(f"/api/classrooms/{X['class_id']}/enroll/{sid}", headers=H(TOK["prof"]))
    still = str((db.students.find_one({"_id": __import__("bson").ObjectId(sid)}) or {}).get("class_id")) == X["turma_alheia"]
    return f"{st(r, 403)[0]}; continua na turma de origem: {still}", r.status_code == 403 and still


@caso("SEG-04", "Segurança", "Refresh token vale uma vez; reuso derruba a sessão",
      "Login; refresh (A→B); reapresentar A; depois usar B",
      "1º refresh 200; reapresentar A: 401; B também passa a 401 (a cadeia do login é revogada)")
def _(x):
    tokens = login("lucas.carvalho@aluno.local").json()
    a = tokens["refreshToken"]
    first = c.post("/api/auth/refresh", json={"refreshToken": a})
    b = first.json().get("refreshToken", "")
    reuse = c.post("/api/auth/refresh", json={"refreshToken": a})
    after = c.post("/api/auth/refresh", json={"refreshToken": b})
    return (f"1º refresh: {first.status_code}; reuso do antigo: {reuse.status_code}; refresh novo depois do reuso: {after.status_code}",
            (first.status_code, reuse.status_code, after.status_code) == (200, 401, 401))


@caso("SEG-05", "Segurança", "Logout revoga o refresh token",
      "Login; POST /api/auth/logout com o refresh token; tentar renovar com ele",
      "logout 204; renovação 401")
def _(x):
    tokens = login("lucas.carvalho@aluno.local").json()
    out = c.post("/api/auth/logout", json={"refreshToken": tokens["refreshToken"]})
    again = c.post("/api/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    return f"logout: {out.status_code}; renovação depois: {again.status_code}", (out.status_code, again.status_code) == (204, 401)


@caso("SEG-06", "Segurança", "Limite de tentativas de login",
      "6 logins seguidos com senha errada para o mesmo e-mail",
      "as 5 primeiras 401; a 6ª 429 com o cabeçalho Retry-After")
def _(x):
    email = f"limite.{RUN}@pluseduc.local"
    codes = [login(email, "senha-errada") for _ in range(6)]
    retry = codes[-1].headers.get("Retry-After")
    return (f"respostas: {[r.status_code for r in codes]}; Retry-After: {retry}",
            [r.status_code for r in codes] == [401] * 5 + [429] and bool(retry))


@caso("SEG-07", "Segurança", "Aluno desativado perde a sessão na hora",
      "Login de um aluno novo; ADMIN exclui o aluno; o token do aluno é usado em seguida",
      "token anterior: 401 (a conta foi desativada e as sessões revogadas)")
def _(x):
    email = f"aluno.sessao.{RUN}@aluno.local"
    reg = c.post("/api/auth/register/student", json={"name": "Aluno Sessao Teste", "email": email, "password": PW})
    CREATED["users"].append(email)
    CREATED["students"].append(email)
    tok = reg.json().get("accessToken", "x")
    before = c.get("/api/student-portal/me", headers=H(tok))
    sid = str(db.students.find_one({"email": email})["_id"])
    d = c.delete(f"/api/students/{sid}", headers=H(TOK["admin"]))
    after = c.get("/api/student-portal/me", headers=H(tok))
    return (f"cadastro: {reg.status_code}; portal antes: {before.status_code}; exclusão: {d.status_code}; portal depois: {after.status_code}",
            (reg.status_code, before.status_code, d.status_code, after.status_code) == (200, 200, 204, 401))


t.VALIDACAO.update({"TUR-05", "TUR-06", "ALU-05", "ATI-03", "PRO-02", "PRO-03", "PRO-04", "SEG-06"})
NOVOS_SEG = len(t.CASES) - ANTES

if __name__ == "__main__":
    sys.path.insert(0, str(HERE.parents[2] / "PlusEduc-BE-Python"))
    print(f"{ANTES} casos da release candidate ({len(REESCRITOS)} reescritos para as regras novas) + {NOVOS_SEG} novos = {len(t.CASES)}")
    t.main()
